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
               workers: int = 4, use_config: bool = True,
               interleave: bool = False, **filters) -> list:
    """Search several sources at once and merge the results.

    Ordering respects the user's per-source ranking from ``mangadl.config``
    (drag-and-drop in the GUI), and sources the user excluded are skipped.
    Failures are logged and skipped so one dead site cannot break a search.

    interleave=True round-robins the sources so the first screen shows a mix
    rather than every hit from the top-ranked site first.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ranks, limits = {}, {}
    if source_ids:
        ids = [s for s in source_ids if s in SOURCES]
    elif use_config:
        try:
            from ..config import load_config, search_ids
            ids = search_ids()
            entries = load_config()["sources"]
            ranks = {sid: entries[sid].get("rank", 100) for sid in ids}
            limits = {sid: int(entries[sid].get("limit", 0) or 0) for sid in ids}
        except Exception:
            ids = list(SOURCES)
    else:
        ids = list(SOURCES)

    if not ids:
        return []
    if not ranks:
        ranks = {sid: i for i, sid in enumerate(ids)}

    buckets = {}

    def run(source_id):
        source = get_source(source_id)
        try:
            return source.search(query, limit=limits.get(source_id) or limit,
                                 **filters)
        finally:
            source.close()

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(ids)))) as pool:
        futures = {pool.submit(run, sid): sid for sid in ids}
        for future in as_completed(futures):
            source_id = futures[future]
            try:
                buckets[source_id] = future.result() or []
            except Exception as e:
                logger.warning("Search failed on %s: %s", source_id, e)
                buckets[source_id] = []

    ordered_ids = sorted(buckets, key=lambda sid: ranks.get(sid, 100))

    if interleave:
        merged, index = [], 0
        while True:
            added = False
            for source_id in ordered_ids:
                items = buckets[source_id]
                if index < len(items):
                    merged.append(items[index])
                    added = True
            if not added:
                break
            index += 1
        return merged

    merged = []
    for source_id in ordered_ids:
        merged.extend(buckets[source_id])
    return merged
