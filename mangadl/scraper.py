"""Backwards-compatible facade over the multi-source layer.

The scraping logic that used to live here now lives in ``mangadl.sources``,
one module per site. This file remains so older imports keep working:

    from mangadl.scraper import WeebCentralScraper   # still fine

New code should use the registry instead::

    from mangadl.sources import get_source, source_for_url

    source = source_for_url("https://mangadex.org/title/<uuid>")
    chapters = source.get_chapters(url)
"""

from .sources import (  # noqa: F401  (re-exported for compatibility)
    BASE_HEADERS as HEADERS,
    DEFAULT_SOURCE,
    SOURCES,
    ScrapeError,
    Source,
    detect_source,
    get_source,
    list_sources,
    search_all,
    source_for_url,
)
from .sources.weebcentral import SITE as BASE_URL, WeebCentralSource

__all__ = [
    "BASE_URL", "HEADERS", "DEFAULT_SOURCE", "SOURCES", "ScrapeError",
    "Source", "WeebCentralScraper", "WeebCentralSource", "detect_source",
    "get_source", "list_sources", "search_all", "source_for_url",
]


class WeebCentralScraper(WeebCentralSource):
    """Deprecated alias kept for backwards compatibility.

    Prefer ``get_source("weebcentral")`` or ``source_for_url(url)``.
    """
