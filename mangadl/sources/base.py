"""Base class and shared plumbing for every manga source.

A *source* is a plugin that knows how to talk to one website. Every source
subclasses :class:`Source` and implements four things:

    search(query, **filters)  -> list of SearchResult dicts
    get_manga_info(url)       -> dict with title / cover / description / ...
    get_chapters(url)         -> list of chapter dicts, OLDEST FIRST
    get_chapter_images(chap)  -> ordered list of page image URLs

Everything else (retries, backoff, Cloudflare fallback, binary downloads)
is provided here so individual sources stay small and readable.

Contracts the download engine relies on
---------------------------------------
* ``get_chapters`` returns oldest-first, each item having at least
  ``{"url": str, "name": str}``. ``url`` is opaque to the engine: it is only
  ever handed straight back to ``get_chapter_images``.
* ``get_chapter_images`` returns direct, downloadable image URLs.
* A chapter may carry ``"referer"`` and ``"headers"`` keys; the engine passes
  them through to :meth:`download_file` so hotlink-protected CDNs work.
"""

import logging
import os
import random
import time

import requests

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")


class ScrapeError(Exception):
    """Raised when a source cannot be scraped."""


class Source:
    """Abstract base class for a manga source.

    Subclasses must set the class attributes below and override the four
    abstract methods. See ``mangadex.py`` for a JSON-API example and
    ``mangakatana.py`` for an HTML-scraping example.
    """

    # -- identity -----------------------------------------------------
    id = "base"                 # short machine name, e.g. "mangadex"
    name = "Base"               # human label shown in the UI
    base_url = ""               # site root, used for urljoin and matching
    domains = ()                # hostnames this source claims

    # -- capabilities (the UI reads these to show/hide controls) -------
    supports_search = True
    supports_language = False   # exposes a language filter
    supports_scanlator = False  # multiple releases per chapter number
    needs_flaresolverr = False  # site sits behind Cloudflare
    adult_only = False          # site hosts adult content exclusively
    search_sorts = ()           # sort options offered by the site
    languages = ()              # available translation languages

    def __init__(self, delay: float = 0.5, session: requests.Session = None,
                 language: str = "en", **options):
        self.delay = float(delay)
        self.language = language or "en"
        self.options = options
        self.session = session or requests.Session()
        self.session.headers.update(self.headers())
        self._solverr = None

    # ------------------------------------------------------------ setup

    def headers(self) -> dict:
        """Default headers for this source. Override to add site-specific ones."""
        return dict(BASE_HEADERS)

    @classmethod
    def handles(cls, url: str) -> bool:
        """True if this source recognises the given URL."""
        url = (url or "").lower()
        return any(domain in url for domain in cls.domains)

    @staticmethod
    def normalize_url(url: str) -> str:
        url = (url or "").strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    # ------------------------------------------------------------- http

    def _backoff(self, attempt, base=2.0, cap=45.0):
        """Exponential backoff with +/-20% jitter so retries don't sync up."""
        d = min(base * (2 ** attempt), cap)
        return max(0.5, d + d * 0.2 * (random.random() - 0.5) * 2)

    def _looks_like_challenge(self, response) -> bool:
        if response.status_code in (403, 503):
            return True
        text = getattr(response, "text", "") or ""
        return (
            "<title>Just a moment...</title>" in text
            or "Enable JavaScript and cookies to continue" in text
        )

    def fetch(self, url: str, max_retries: int = 5, headers: dict = None,
              params=None, timeout: int = 20):
        """GET a page with retries, rate-limit handling and Cloudflare fallback."""
        last_exc = None
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url, headers=headers, params=params, timeout=timeout
                )

                if response.status_code == 429:
                    wait = self._retry_after(response) or self._backoff(attempt)
                    logger.warning("[%s] rate limited (429), waiting %.1fs", self.id, wait)
                    time.sleep(wait)
                    continue

                if self._looks_like_challenge(response):
                    solved = self._solve_challenge(url, attempt)
                    if solved is not None:
                        return solved
                    last_exc = ScrapeError("Cloudflare challenge not solved")
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                last_exc = e
                if attempt < max_retries - 1:
                    wait = self._backoff(attempt)
                    logger.warning("[%s] request failed (%s), retrying in %.1fs",
                                   self.id, e, wait)
                    time.sleep(wait)

        raise ScrapeError(f"Failed to fetch {url}: {last_exc}")

    def fetch_json(self, url: str, params=None, max_retries: int = 5,
                   headers: dict = None):
        """GET and parse JSON, with the same retry policy as :meth:`fetch`."""
        response = self.fetch(url, max_retries=max_retries, headers=headers,
                              params=params)
        try:
            return response.json()
        except ValueError as e:
            raise ScrapeError(f"Invalid JSON from {url}: {e}")

    @staticmethod
    def _retry_after(response):
        """Honour Retry-After / X-RateLimit-Retry-After when the server sends it."""
        for key in ("Retry-After", "X-RateLimit-Retry-After"):
            value = response.headers.get(key)
            if not value:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            # X-RateLimit-Retry-After is an absolute unix timestamp
            if number > 1e6:
                number -= time.time()
            if 0 < number <= 120:
                return number
        return None

    def _solve_challenge(self, url, attempt):
        """Route a Cloudflare-protected URL through FlareSolverr."""
        logger.warning("[%s] Cloudflare challenge, trying FlareSolverr", self.id)
        try:
            from ..flaresolverr import FlareSolverrSession
            if self._solverr is None:
                self._solverr = FlareSolverrSession()
            return self._solverr.get(url)
        except Exception as e:
            logger.error("[%s] FlareSolverr fallback failed: %s", self.id, e)
            time.sleep(self._backoff(attempt))
            return None

    # -------------------------------------------------------- downloads

    def download_file(self, url: str, filepath, referer: str = None,
                      max_retries: int = 5, headers: dict = None) -> bool:
        """Download a binary image, writing atomically via a .part file.

        Writing to a temp file and renaming means a crash mid-write can never
        leave a truncated image that resume would mistake for a complete one.
        """
        request_headers = dict(self.headers())
        if referer:
            request_headers["Referer"] = referer
        if headers:
            request_headers.update(headers)
        tmp_path = str(filepath) + ".part"

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url, headers=request_headers, timeout=30,
                    allow_redirects=True, stream=True
                )
                if response.status_code == 429:
                    time.sleep(self._retry_after(response)
                               or self._backoff(attempt, base=1.0, cap=30.0))
                    continue
                response.raise_for_status()

                # Stream to disk instead of holding the whole image in RAM.
                # With chapter_workers x image_workers in flight, buffering
                # every response meant tens of multi-MB blobs resident at once.
                head = b""
                with open(tmp_path, "wb") as f:
                    for block in response.iter_content(chunk_size=65536):
                        if not block:
                            continue
                        if len(head) < 16:
                            head += block[:16 - len(head)]
                        f.write(block)

                if not self._is_image(response, head):
                    ctype = response.headers.get("content-type", "?")
                    raise ValueError(f"Not an image (content-type: {ctype})")
                if os.path.getsize(tmp_path) == 0:
                    raise ValueError("Empty response")

                os.replace(tmp_path, filepath)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(self._backoff(attempt, base=1.0, cap=30.0))
                else:
                    logger.error("[%s] failed to download %s: %s", self.id, url, e)

        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False

    @staticmethod
    def _is_image(response, content: bytes) -> bool:
        """Validate a response really is an image.

        Some CDNs (Mangakatana's token hosts, for one) serve images as
        ``application/octet-stream``, so a content-type check alone rejects
        perfectly good files. Fall back to magic-byte sniffing.
        """
        ctype = (response.headers.get("content-type") or "").lower()
        if ctype.startswith("image/"):
            return True
        if not content:
            return False
        return (
            content[:3] == b"\xff\xd8\xff"                      # JPEG
            or content[:8] == b"\x89PNG\r\n\x1a\n"              # PNG
            or content[:6] in (b"GIF87a", b"GIF89a")            # GIF
            or (content[:4] == b"RIFF" and content[8:12] == b"WEBP")
            or content[4:12] in (b"ftypavif", b"ftypavis")      # AVIF
        )

    @staticmethod
    def guess_extension(url: str, default: str = ".jpg") -> str:
        """Pick a file extension from an image URL."""
        path = url.split("?")[0].split("#")[0]
        ext = os.path.splitext(path)[1].lower()
        return ext if ext in IMAGE_EXTENSIONS else default

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass
        if self._solverr is not None:
            try:
                self._solverr.destroy_session()
            except Exception:
                pass

    # ----------------------------------------------------- abstract api

    def search(self, query: str, limit: int = 32, **filters) -> list:
        """Return ``[{title, url, cover, source, ...}]``."""
        raise NotImplementedError

    def browse(self, sort: str = None, genre: str = None, page: int = 1,
               limit: int = 32, **filters) -> list:
        """Discovery without a query: trending / popular / latest.

        Sources that cannot do this leave ``supports_browse`` False; the
        registry then falls back to an empty list for them rather than
        failing the whole request.
        """
        raise NotImplementedError

    def genres(self) -> list:
        """Available genres as ``[{"id": ..., "name": ...}]``."""
        return []

    def get_manga_info(self, manga_url: str) -> dict:
        """Return ``{url, title, cover, description, tags, status, authors}``."""
        raise NotImplementedError

    def get_chapters(self, manga_url: str) -> list:
        """Return chapters OLDEST FIRST: ``[{url, name, ...}]``."""
        raise NotImplementedError

    def get_chapter_images(self, chapter) -> list:
        """Return ordered page image URLs. Accepts a chapter dict or a URL."""
        raise NotImplementedError

    # ------------------------------------------------------------ utils

    @staticmethod
    def _chapter_url(chapter):
        """Accept either a chapter dict or a bare URL string."""
        if isinstance(chapter, dict):
            return chapter.get("url") or chapter.get("id") or ""
        return chapter or ""

    def _result(self, title, url, cover=None, **extra):
        """Build a search result with the source stamped on it."""
        return {
            "title": title or "Unknown",
            "url": url,
            "cover": cover,
            "source": self.id,
            "source_name": self.name,
            **extra,
        }
