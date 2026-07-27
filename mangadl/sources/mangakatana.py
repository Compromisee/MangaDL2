"""Mangakatana source (HTML scraping).

Mangakatana has no public API, so everything here comes from parsing pages.
Two quirks worth documenting, both discovered by inspecting live pages:

Page images are hidden in JavaScript
    The reader does not emit ``<img src=...>`` for pages; every ``<img>`` in
    the markup has ``data-src="#"``. The real URLs live in a script tag as a
    plain JS array with a *randomised* variable name, e.g.::

        var thzq=['https://i1.mangakatana.com/token/....../0.jpg', ...];
        var ytaw=['https://i1.mangakatana.com/token/....../0.jpg',];

    Both arrays appear on every chapter page and the names change per page, so
    the variable name cannot be relied on. The second one is a decoy holding a
    single URL. We therefore collect *every* JS array of image URLs and keep
    the longest, which is the real page list.

Image CDN
    Hosts are ``i1.mangakatana.com`` etc. and serve pages as
    ``application/octet-stream`` rather than an ``image/*`` content type, so
    the base downloader's magic-byte sniffing does the validation. No Referer
    header is required (verified against the live CDN).

Search
    ``/?search=<query>&search_by=book_name`` returns a result grid. A search
    matching exactly one title redirects straight to that manga page, which is
    handled by detecting the redirect target.
"""

import logging
import re
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .base import Source, ScrapeError

logger = logging.getLogger(__name__)

SITE = "https://mangakatana.com"

# Matches a JS array literal made of quoted http(s) URLs:
#   var xxxx=['https://...','https://...',]
_JS_ARRAY = re.compile(r"=\s*\[\s*((?:'https?://[^']+'\s*,?\s*)+)\]")
_JS_URL = re.compile(r"'(https?://[^']+)'")


class MangakatanaSource(Source):
    id = "mangakatana"
    name = "Mangakatana"
    base_url = SITE
    domains = ("mangakatana.com",)

    supports_search = True
    supports_language = False
    supports_browse = True
    supports_genres = True
    search_sorts = ("Latest Updates", "New", "Popularity", "Alphabet")
    browse_sorts = ("Trending", "Latest Updates", "New", "Alphabet")

    _SORTS = {
        # the site has no separate trending feed; chapter count ("numc") is
        # its own popularity ordering, which is what /manga?order=numc uses
        "Trending": "numc",
        "Popularity": "numc",
        "Latest Updates": "latest",
        "New": "new",
        "Alphabet": "az",
    }

    # Slugs used by /genre/<slug>; taken from the site's own genre menu.
    GENRES = (
        "4-koma", "action", "adult", "adventure", "artbook", "award-winning",
        "comedy", "cooking", "doujinshi", "drama", "ecchi", "erotica",
        "fantasy", "gender-bender", "gore", "harem", "historical", "horror",
        "isekai", "josei", "manhua", "manhwa", "martial-arts", "mature",
        "mecha", "medical", "musical", "mystery", "one-shot", "psychological",
        "romance", "school-life", "sci-fi", "seinen", "shoujo", "shoujo-ai",
        "shounen", "shounen-ai", "slice-of-life", "smut", "sports",
        "supernatural", "tragedy", "webtoon", "yaoi", "yuri",
    )

    def headers(self):
        h = super().headers()
        h["Referer"] = SITE + "/"
        return h

    # ---------------------------------------------------------- search

    def search(self, query: str, limit: int = 32, sort: str = None,
               status=None, **_):
        query = (query or "").strip()
        if not query:
            return []

        url = f"{SITE}/?search={quote(query)}&search_by=book_name"
        if sort and sort in self._SORTS:
            url += f"&order={self._SORTS[sort]}"
        if status and status != "Any":
            url += f"&status={quote(status.lower())}"

        try:
            response = self.fetch(url)
        except ScrapeError as e:
            logger.error("Mangakatana search failed: %s", e)
            return []

        # An exact single match redirects straight to the manga page.
        final_url = str(getattr(response, "url", "") or "")
        if "/manga/" in final_url and "search" not in final_url:
            try:
                info = self.get_manga_info(final_url)
                return [self._result(info["title"], info["url"],
                                     cover=info.get("cover"),
                                     status=info.get("status"),
                                     authors=info.get("authors", []))]
            except Exception:
                pass

        return self._parse_listing(response, limit)

    def _parse_listing(self, response, limit):
        """Parse a grid of series cards (shared by search and browse)."""
        soup = BeautifulSoup(response.content, "html.parser")
        results, seen = [], set()

        # #book_list is the real results grid. A bare "div.item" also matches
        # sidebar/recommendation cards that appear BEFORE the grid in the
        # markup, so it is only used when the grid is genuinely absent.
        items = soup.select("#book_list .item") or soup.select(".book_list .item")
        if not items:
            items = soup.select("div.item")

        for item in items:
            link = item.select_one('a[href*="/manga/"]')
            if not link or not link.get("href"):
                continue
            href = urljoin(SITE, link["href"])
            # skip links that point at a chapter rather than the series
            if re.search(r"/manga/[^/]+/c[\d.]+", href):
                continue
            if href in seen:
                continue
            seen.add(href)

            title_el = item.select_one("h3.title a, .title a, h3 a")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                title = (link.get("title") or link.get_text(strip=True) or "").strip()

            cover = None
            img = item.select_one("img")
            if img is not None:
                cover = img.get("src") or img.get("data-src")
                source_tag = item.select_one("source[srcset]")
                if source_tag and source_tag.get("srcset"):
                    cover = source_tag["srcset"].split()[0]
                if cover:
                    cover = urljoin(SITE, cover)

            status_el = item.select_one(".status")
            latest_el = item.select_one(".chapter a")

            results.append(self._result(
                title, href, cover=cover,
                status=status_el.get_text(strip=True) if status_el else None,
                latest=latest_el.get_text(strip=True) if latest_el else None,
            ))
            if len(results) >= limit:
                break
        return results

    # ---------------------------------------------------------- browse

    def genres(self) -> list:
        return [{"id": slug, "name": slug.replace("-", " ").title()}
                for slug in self.GENRES]

    def browse(self, sort: str = "Trending", genre: str = None, page: int = 1,
               limit: int = 32, status=None, **_):
        """Trending / latest listings, optionally narrowed to one genre.

        Two things worth knowing, both established against the live site:

        * ``/manga/page/N`` returns a plain alphabetical dump and ignores
          ``order`` completely. The ``?filter=1`` form is the one the site's
          own browse page uses and returns its curated recent listing, so
          that is what we request.
        * Even on the filter form the ``order`` value does not visibly change
          the result set, so the sort choice is passed through but treated as
          advisory rather than guaranteed.
        """
        page = max(1, int(page or 1))
        order = self._SORTS.get(sort, "numc")

        if genre:
            slug = str(genre).strip().lower().replace(" ", "-")
            url = f"{SITE}/genre/{quote(slug)}"
            if page > 1:
                url += f"/page/{page}"
            url += f"?filter=1&order={order}"
        elif page > 1:
            url = f"{SITE}/page/{page}?filter=1&order={order}"
        else:
            url = f"{SITE}/?filter=1&order={order}"
        if status and status != "Any":
            url += f"&status={quote(str(status).lower())}"

        try:
            response = self.fetch(url)
        except ScrapeError as e:
            logger.error("Mangakatana browse failed: %s", e)
            return []
        return self._parse_listing(response, limit)

    # ------------------------------------------------------------ info

    def get_manga_info(self, manga_url: str) -> dict:
        manga_url = self.normalize_url(manga_url)
        response = self.fetch(manga_url)
        soup = BeautifulSoup(response.content, "html.parser")

        title_el = soup.select_one("h1.heading") or soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown Manga"

        cover = None
        cover_el = soup.select_one("div.cover img") or soup.select_one(".media img")
        if cover_el is not None:
            cover = cover_el.get("src") or cover_el.get("data-src")
            if cover:
                cover = urljoin(SITE, cover)

        description = None
        desc_el = soup.select_one("div.summary p") or soup.select_one("div.summary")
        if desc_el is not None:
            description = re.sub(r"\s+", " ", desc_el.get_text(" ", strip=True)).strip()
            description = re.sub(r"^Description\s*", "", description).strip() or None

        # The info table is a list of label/value pairs.
        meta = {}
        for li in soup.select("ul.meta li, .meta.d-table li"):
            label_el = li.select_one(".label")
            value_el = li.select_one(".value")
            if not label_el:
                continue
            label = label_el.get_text(strip=True).rstrip(":").lower()
            if value_el is None:
                continue
            links = [a.get_text(strip=True) for a in value_el.select("a")]
            meta[label] = {
                "text": re.sub(r"\s+", " ", value_el.get_text(" ", strip=True)).strip(),
                "links": links,
            }

        def pick(*keys):
            for key in keys:
                for label, value in meta.items():
                    if key in label:
                        return value
            return None

        authors_meta = pick("author", "artist")
        genres_meta = pick("genre")
        status_meta = pick("status")
        alt_meta = pick("alt name")
        updated_meta = pick("update")

        authors = []
        if authors_meta:
            authors = authors_meta["links"] or [
                a.strip() for a in re.split(r"[,;/]", authors_meta["text"]) if a.strip()
            ]

        tags = []
        if genres_meta:
            tags = genres_meta["links"] or [
                g.strip() for g in re.split(r"[,;]", genres_meta["text"]) if g.strip()
            ]

        alt_titles = []
        if alt_meta:
            alt_titles = [
                a.strip() for a in re.split(r"[;|]", alt_meta["text"]) if a.strip()
            ]

        return {
            "url": manga_url,
            "title": title,
            "alt_titles": alt_titles,
            "cover": cover,
            "description": description,
            "tags": tags,
            "status": status_meta["text"] if status_meta else None,
            "authors": authors,
            "artists": [],
            "updated": updated_meta["text"] if updated_meta else None,
            "source": self.id,
            "source_name": self.name,
        }

    # -------------------------------------------------------- chapters

    def get_chapters(self, manga_url: str) -> list:
        manga_url = self.normalize_url(manga_url)
        response = self.fetch(manga_url)
        soup = BeautifulSoup(response.content, "html.parser")

        rows = soup.select("div.chapters table tr")
        if not rows:
            rows = soup.select("div.chapters .chapter")

        chapters = []
        for row in rows:
            link = row.select_one('a[href*="/manga/"]')
            if not link or not link.get("href"):
                continue
            href = urljoin(SITE, link["href"])
            name = link.get("title") or link.get_text(strip=True)
            if not name:
                continue
            date_el = row.select_one(".update_time")
            chapters.append({
                "url": href,
                "name": re.sub(r"\s+", " ", name).strip(),
                "date": date_el.get_text(strip=True) if date_el else None,
                "source": self.id,
            })

        # The site lists newest first; the engine wants oldest first.
        chapters.reverse()
        return chapters

    # ----------------------------------------------------------- pages

    def get_chapter_images(self, chapter) -> list:
        chapter_url = self.normalize_url(self._chapter_url(chapter))
        if not chapter_url:
            return []
        response = self.fetch(chapter_url)
        html = response.text

        # Collect every JS array of URLs, then keep the longest: the page
        # carries a decoy single-entry array alongside the real page list,
        # and both variable names are randomised per request.
        candidates = []
        for match in _JS_ARRAY.finditer(html):
            urls = _JS_URL.findall(match.group(1))
            urls = [u for u in urls if self._looks_like_page(u)]
            if urls:
                candidates.append(urls)

        if not candidates:
            # last resort: some older chapters use plain img tags
            soup = BeautifulSoup(response.content, "html.parser")
            urls = []
            for img in soup.select("#imgs img, .wrap_content img, img"):
                src = img.get("data-src") or img.get("src")
                if src and src != "#" and self._looks_like_page(src):
                    urls.append(urljoin(SITE, src))
            if urls:
                return urls
            raise ScrapeError(f"No page images found for {chapter_url}")

        best = max(candidates, key=len)
        return self._sort_pages(best)

    @staticmethod
    def _looks_like_page(url: str) -> bool:
        if not url.startswith("http"):
            return False
        lowered = url.lower()
        if any(bad in lowered for bad in ("/imgs/cover/", "logo", "banner", "avatar")):
            return False
        return True

    @staticmethod
    def _sort_pages(urls):
        """Order by the numeric filename the CDN uses (0.jpg, 1.jpg, ... 10.jpg)."""
        def key(item):
            index, url = item
            match = re.search(r"/(\d+)\.(?:jpg|jpeg|png|webp|gif)(?:\?|$)", url, re.I)
            return (int(match.group(1)) if match else index, index)

        indexed = list(enumerate(urls))
        ordered = sorted(indexed, key=key)
        return [url for _i, url in ordered]
