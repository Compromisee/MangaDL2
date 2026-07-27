"""Source registry: every supported manga site lives here.

Adding a new site is a three-step job:

    1. write ``mangadl/sources/<name>.py`` with a Source subclass
    2. import it below and append it to ``SOURCE_CLASSES``
    3. that's it -- CLI, GUI and TUI pick it up automatically

Nothing else in the codebase hardcodes a site.
"""

import logging

from .base import BASE_HEADERS, DEFAULT_UA, ScrapeError, Source
from .mangadex import MangaDexSource
from .mangakatana import MangakatanaSource
from .natomanga import NatomangaSource
from .weebcentral import WeebCentralSource

logger = logging.getLogger(__name__)

# Order matters: this is the order shown in the UI, and the order used when
# guessing a source for an ambiguous URL.
SOURCE_CLASSES = [
    MangaDexSource,
    MangakatanaSource,
    NatomangaSource,
    WeebCentralSource,
]

SOURCES = {cls.id: cls for cls in SOURCE_CLASSES}

DEFAULT_SOURCE = MangaDexSource.id

__all__ = [
    "BASE_HEADERS", "DEFAULT_SOURCE", "DEFAULT_UA", "SOURCES", "SOURCE_CLASSES",
    "ScrapeError", "Source", "MangaDexSource", "MangakatanaSource",
    "NatomangaSource", "WeebCentralSource",
    "get_source", "source_for_url", "detect_source", "list_sources",
    "search_all",
]


def list_sources() -> list:
    """Metadata for every source, for populating UI pickers."""
    return [
        {
            "id": cls.id,
            "name": cls.name,
            "base_url": cls.base_url,
            "domains": list(cls.domains),
            "supports_search": cls.supports_search,
            "supports_language": cls.supports_language,
            "supports_scanlator": cls.supports_scanlator,
            "needs_flaresolverr": cls.needs_flaresolverr,
            "sorts": list(cls.search_sorts),
            "languages": list(cls.languages),
        }
        for cls in SOURCE_CLASSES
    ]


def detect_source(url: str) -> str:
    """Return the source id that claims this URL, or None."""
    for cls in SOURCE_CLASSES:
        if cls.handles(url):
            return cls.id
    return None


def get_source(source_id: str = None, **kwargs) -> Source:
    """Instantiate a source by id (defaults to MangaDex)."""
    key = (source_id or DEFAULT_SOURCE).strip().lower()
    cls = SOURCES.get(key)
    if cls is None:
        known = ", ".join(SOURCES)
        raise ScrapeError(f"Unknown source '{source_id}'. Available: {known}")
    return cls(**kwargs)


def source_for_url(url: str, **kwargs) -> Source:
    """Instantiate whichever source handles this URL."""
    source_id = detect_source(url)
    if source_id is None:
        known = ", ".join(cls.base_url for cls in SOURCE_CLASSES)
        raise ScrapeError(
            f"No source recognises '{url}'.\nSupported sites: {known}"
        )
    return get_source(source_id, **kwargs)


def search_all(query: str, source_ids=None, limit: int = 20,
               workers: int = 4, **filters) -> list:
    """Search several sources at once and merge the results.

    Failures are logged and skipped so one dead site cannot break a search.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ids = [s for s in (source_ids or list(SOURCES)) if s in SOURCES]
    if not ids:
        return []

    results = []

    def run(source_id):
        source = get_source(source_id)
        try:
            return source.search(query, limit=limit, **filters)
        finally:
            source.close()

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(ids)))) as pool:
        futures = {pool.submit(run, sid): sid for sid in ids}
        for future in as_completed(futures):
            source_id = futures[future]
            try:
                results.extend(future.result() or [])
            except Exception as e:
                logger.warning("Search failed on %s: %s", source_id, e)

    # keep the registry order stable in mixed results
    order = {sid: i for i, sid in enumerate(SOURCES)}
    results.sort(key=lambda r: order.get(r.get("source"), 99))
    return results
