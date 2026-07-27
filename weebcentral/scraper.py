"""WeebCentral scraping: manga info, chapter lists, image URLs, search."""

import logging
import os
import re
import time
import random
from urllib.parse import urljoin, urlparse, quote

import requests
from bs4 import BeautifulSoup

from .flaresolverr import FlareSolverrSession

logger = logging.getLogger(__name__)

BASE_URL = "https://weebcentral.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


class ScrapeError(Exception):
    """Raised when WeebCentral cannot be scraped."""


class WeebCentralScraper:
    """Stateless-ish scraper for weebcentral.com with Cloudflare fallback."""

    def __init__(self, delay: float = 0.5):
        self.delay = float(delay)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._solverr = None  # lazy FlareSolverr fallback

    # ------------------------------------------------------------------ http

    def _backoff(self, attempt, base=2.0, cap=45.0):
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

    def fetch(self, url: str, max_retries: int = 5):
        """GET a page, retrying with backoff and falling back to FlareSolverr."""
        last_exc = None
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=20)

                if response.status_code == 429:
                    wait = self._backoff(attempt)
                    logger.warning("Rate limited (429), retrying in %.1fs", wait)
                    time.sleep(wait)
                    continue

                if self._looks_like_challenge(response):
                    logger.warning("Cloudflare challenge detected, using FlareSolverr")
                    if self._solverr is None:
                        self._solverr = FlareSolverrSession()
                    try:
                        return self._solverr.get(url)
                    except Exception as e:
                        logger.error("FlareSolverr fallback failed: %s", e)
                        last_exc = e
                        time.sleep(self._backoff(attempt))
                        continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                last_exc = e
                if attempt < max_retries - 1:
                    wait = self._backoff(attempt)
                    logger.warning("Request failed (%s), retrying in %.1fs", e, wait)
                    time.sleep(wait)

        raise ScrapeError(f"Failed to fetch {url}: {last_exc}")

    # ----------------------------------------------------------------- pages

    @staticmethod
    def normalize_url(url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def get_manga_info(self, manga_url: str) -> dict:
        """Return {title, cover, description, tags, status, authors, url}."""
        manga_url = self.normalize_url(manga_url)
        response = self.fetch(manga_url)
        soup = BeautifulSoup(response.content, "html.parser")

        title_el = soup.select_one("section[x-data] > section:nth-of-type(2) h1")
        title = title_el.text.strip() if title_el else "Unknown Manga"

        cover = None
        cover_el = soup.select_one("img[alt$='cover']")
        if cover_el and cover_el.get("src"):
            cover = urljoin(BASE_URL, cover_el["src"])

        description = None
        desc_el = soup.select_one("li:has(strong:-soup-contains('Description')) p")
        if desc_el:
            description = desc_el.text.strip()

        tags = [a.text.strip() for a in soup.select("li:has(strong:-soup-contains('Tag')) a")]
        status_el = soup.select_one("li:has(strong:-soup-contains('Status')) a")
        status = status_el.text.strip() if status_el else None
        authors = [a.text.strip() for a in soup.select("li:has(strong:-soup-contains('Author')) a")]

        return {
            "url": manga_url,
            "title": title,
            "cover": cover,
            "description": description,
            "tags": tags,
            "status": status,
            "authors": authors,
        }

    def get_chapters(self, manga_url: str) -> list:
        """Return chapters oldest-first: [{url, name}]."""
        manga_url = self.normalize_url(manga_url)
        parts = urlparse(manga_url).path.split("/")
        list_url = f"{BASE_URL}{'/'.join(parts[:3])}/full-chapter-list"
        response = self.fetch(list_url)
        soup = BeautifulSoup(response.content, "html.parser")

        chapters = []
        for element in reversed(soup.select("div[x-data] > a")):
            href = element.get("href")
            if isinstance(href, list):
                href = href[0]
            if not href:
                continue
            name_el = element.select_one("span.flex > span")
            name = name_el.text.strip() if name_el else "Unknown Chapter"
            chapters.append({"url": urljoin(BASE_URL, href), "name": name})
        return chapters

    def get_chapter_images(self, chapter_url: str) -> list:
        """Return the ordered list of page image URLs for a chapter."""
        images_url = f"{chapter_url}/images?reading_style=long_strip"
        response = self.fetch(images_url)
        soup = BeautifulSoup(response.content, "html.parser")

        urls = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if isinstance(src, list):
                src = src[0]
            if src and "broken_image" not in src and src.startswith("http"):
                urls.append(src)
        return urls

    SEARCH_SORTS = ["Best Match", "Alphabet", "Popularity", "Subscribers",
                    "Recently Added", "Latest Updates"]

    def search(self, query: str, limit: int = 32, sort: str = "Best Match",
               order: str = "Ascending", official: str = "Any",
               status: str = None, series_type: str = None) -> list:
        """Search WeebCentral with optional filters. Returns [{title, url, cover}].

        sort:        Best Match | Alphabet | Popularity | Subscribers |
                     Recently Added | Latest Updates
        order:       Ascending | Descending
        official:    Any | True | False
        status:      Any/None | Ongoing | Complete | Hiatus | Canceled
        series_type: Any/None | Manga | Manhwa | Manhua | OEL
        """
        if sort not in self.SEARCH_SORTS:
            sort = "Best Match"
        if order not in ("Ascending", "Descending"):
            order = "Ascending"
        if official not in ("Any", "True", "False"):
            official = "Any"

        url = (
            f"{BASE_URL}/search/data?limit={limit}&offset=0&text={quote(query)}"
            f"&sort={quote(sort)}&order={quote(order)}&official={official}"
            f"&display_mode=Full%20Display"
        )
        if status and status != "Any":
            url += f"&included_status={quote(status)}"
        if series_type and series_type != "Any":
            url += f"&included_type={quote(series_type)}"
        try:
            response = self.fetch(url)
        except ScrapeError:
            return []
        soup = BeautifulSoup(response.content, "html.parser")

        results, seen = [], set()
        for article in soup.select("article"):
            link = article.select_one("a[href*='/series/']")
            if not link:
                continue
            href = urljoin(BASE_URL, link["href"])
            if href in seen:
                continue
            seen.add(href)
            img = article.select_one("img")
            title = None
            # Prefer a plain text link (no nested cover markup) over the image link
            for a in article.select("a[href*='/series/']"):
                if a.find("article") or a.find("img"):
                    continue
                text = a.get_text(strip=True)
                if text:
                    title = text
                    break
            if not title and img is not None:
                title = re.sub(r"\s*cover\s*$", "", img.get("alt", ""), flags=re.I).strip()
            results.append({
                "title": title or "Unknown",
                "url": href,
                "cover": urljoin(BASE_URL, img["src"]) if img is not None and img.get("src") else None,
            })
        return results

    def download_file(self, url: str, filepath, referer: str = None, max_retries: int = 5) -> bool:
        """Download a binary file (image) with retries. Returns True on success.

        Writes to a temporary .part file and renames atomically, so a crash
        mid-write never leaves a corrupt file that resume would skip.
        """
        headers = dict(HEADERS)
        if referer:
            headers["Referer"] = referer
        tmp_path = str(filepath) + ".part"

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=headers, timeout=20, allow_redirects=True)
                if response.status_code == 429:
                    time.sleep(self._backoff(attempt, base=1.0, cap=30.0))
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    raise ValueError(f"Non-image content-type: {content_type}")
                with open(tmp_path, "wb") as f:
                    f.write(response.content)
                os.replace(tmp_path, filepath)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(self._backoff(attempt, base=1.0, cap=30.0))
                else:
                    logger.error("Failed to download %s: %s", url, e)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False
