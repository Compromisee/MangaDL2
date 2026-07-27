"""MangaDL source.

This is the original scraper from the project, adapted to the Source
interface. Behaviour is unchanged: MangaDL sits behind Cloudflare, so the
base class's FlareSolverr fallback matters here more than for other sources.
"""

import logging
import re
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import Source, ScrapeError

logger = logging.getLogger(__name__)

SITE = "https://weebcentral.com"


class WeebCentralSource(Source):
    id = "weebcentral"
    name = "Weeb Central"
    base_url = SITE
    domains = ("weebcentral.com",)

    supports_search = True
    supports_browse = True
    supports_genres = True
    needs_flaresolverr = True
    search_sorts = ("Best Match", "Alphabet", "Popularity", "Subscribers",
                    "Recently Added", "Latest Updates")
    browse_sorts = ("Trending", "Popularity", "Subscribers",
                    "Recently Added", "Latest Updates", "Alphabet")

    # WeebCentral exposes these as `included_tag` values on its search route
    GENRES = (
        "Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy",
        "Harem", "Historical", "Horror", "Isekai", "Josei", "Martial Arts",
        "Mature", "Mecha", "Mystery", "Psychological", "Romance",
        "School Life", "Sci-fi", "Seinen", "Shoujo", "Shounen",
        "Slice of Life", "Sports", "Supernatural", "Tragedy",
    )

    # ---------------------------------------------------------- browse

    def genres(self) -> list:
        return [{"id": name, "name": name} for name in self.GENRES]

    def browse(self, sort: str = "Trending", genre: str = None, page: int = 1,
               limit: int = 32, status=None, series_type=None, **_):
        """Query-less discovery.

        WeebCentral has no dedicated trending feed, but its search route
        accepts an empty ``text`` and a sort, which is exactly what its own
        browse page issues. "Trending" maps to Popularity descending.
        """
        page = max(1, int(page or 1))
        limit = max(1, min(100, limit))
        api_sort = "Popularity" if sort == "Trending" else sort
        if api_sort not in self.search_sorts:
            api_sort = "Popularity"

        url = (
            f"{SITE}/search/data?limit={limit}&offset={(page - 1) * limit}"
            f"&text=&sort={quote(api_sort)}&order=Descending&official=Any"
            f"&display_mode=Full%20Display"
        )
        if genre:
            url += f"&included_tag={quote(str(genre))}"
        if status and status != "Any":
            url += f"&included_status={quote(str(status))}"
        if series_type and series_type != "Any":
            url += f"&included_type={quote(str(series_type))}"

        try:
            response = self.fetch(url)
        except ScrapeError as e:
            logger.error("WeebCentral browse failed: %s", e)
            return []
        return self._parse_articles(response, limit)

    # ---------------------------------------------------------- search

    def search(self, query: str, limit: int = 32, sort: str = "Best Match",
               order: str = "Ascending", official: str = "Any",
               status: str = None, series_type: str = None, **_):
        if sort not in self.search_sorts:
            sort = "Best Match"
        if order not in ("Ascending", "Descending"):
            order = "Ascending"
        if official not in ("Any", "True", "False"):
            official = "Any"

        url = (
            f"{SITE}/search/data?limit={limit}&offset=0&text={quote(query)}"
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
        return self._parse_articles(response, limit)

    def _parse_articles(self, response, limit=32):
        """Parse the article grid shared by search and browse."""
        soup = BeautifulSoup(response.content, "html.parser")

        results, seen = [], set()
        for article in soup.select("article"):
            link = article.select_one("a[href*='/series/']")
            if not link:
                continue
            href = urljoin(SITE, link["href"])
            if href in seen:
                continue
            seen.add(href)

            img = article.select_one("img")
            title = None
            # Prefer a plain text link over the one wrapping the cover image
            for a in article.select("a[href*='/series/']"):
                if a.find("article") or a.find("img"):
                    continue
                text = a.get_text(strip=True)
                if text:
                    title = text
                    break
            if not title and img is not None:
                title = re.sub(r"\s*cover\s*$", "", img.get("alt", ""),
                               flags=re.I).strip()

            results.append(self._result(
                title, href,
                cover=urljoin(SITE, img["src"])
                if img is not None and img.get("src") else None,
            ))
            if len(results) >= limit:
                break
        return results

    # ------------------------------------------------------------ info

    def get_manga_info(self, manga_url: str) -> dict:
        manga_url = self.normalize_url(manga_url)
        response = self.fetch(manga_url)
        soup = BeautifulSoup(response.content, "html.parser")

        title_el = soup.select_one("section[x-data] > section:nth-of-type(2) h1")
        title = title_el.text.strip() if title_el else "Unknown Manga"

        cover = None
        cover_el = soup.select_one("img[alt$='cover']")
        if cover_el and cover_el.get("src"):
            cover = urljoin(SITE, cover_el["src"])

        description = None
        desc_el = soup.select_one("li:has(strong:-soup-contains('Description')) p")
        if desc_el:
            description = desc_el.text.strip()

        tags = [a.text.strip()
                for a in soup.select("li:has(strong:-soup-contains('Tag')) a")]
        status_el = soup.select_one("li:has(strong:-soup-contains('Status')) a")
        authors = [a.text.strip()
                   for a in soup.select("li:has(strong:-soup-contains('Author')) a")]

        return {
            "url": manga_url,
            "title": title,
            "cover": cover,
            "description": description,
            "tags": tags,
            "status": status_el.text.strip() if status_el else None,
            "authors": authors,
            "artists": [],
            "source": self.id,
            "source_name": self.name,
        }

    # -------------------------------------------------------- chapters

    def get_chapters(self, manga_url: str) -> list:
        manga_url = self.normalize_url(manga_url)
        parts = urlparse(manga_url).path.split("/")
        list_url = f"{SITE}{'/'.join(parts[:3])}/full-chapter-list"
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
            chapters.append({
                "url": urljoin(SITE, href),
                "name": name_el.text.strip() if name_el else "Unknown Chapter",
                "source": self.id,
            })
        return chapters

    # ----------------------------------------------------------- pages

    def get_chapter_images(self, chapter) -> list:
        chapter_url = self._chapter_url(chapter)
        if not chapter_url:
            return []
        response = self.fetch(f"{chapter_url}/images?reading_style=long_strip")
        soup = BeautifulSoup(response.content, "html.parser")

        urls = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if isinstance(src, list):
                src = src[0]
            if src and "broken_image" not in src and src.startswith("http"):
                urls.append(src)
        return urls
