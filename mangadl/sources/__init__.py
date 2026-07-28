"""Source registry: every supported manga site lives here.

Adding a new site is a three-step job:

    1. write ``mangadl/sources/<name>.py`` with a Source subclass
    2. import it below and append it to ``SOURCE_CLASSES``
    3. that's it -- CLI, GUI and TUI pick it up automatically

Nothing else in the codebase hardcodes a site.
"""

import logging
import re

from .base import BASE_HEADERS, DEFAULT_UA, ScrapeError, Source
from .hentaiakane import HentaiAkaneSource
from .manga18club import Manga18ClubSource
from .mangadass import MangadassSource
from .mangadex import MangaDexSource
from .mangakatana import MangakatanaSource
from .manhwa18 import Manhwa18Source
from .manhwaread import ManhwaReadSource
from .natomanga import NatomangaSource
from .nhentai import NhentaiSource
from .omegascans import OmegaScansSource
from .webtoons import WebtoonsSource
from .weebcentral import WeebCentralSource

logger = logging.getLogger(__name__)

# Order matters: this is the order shown in the UI, and the order used when
# guessing a source for an ambiguous URL.
SOURCE_CLASSES = [
    MangaDexSource,
    MangakatanaSource,
    NatomangaSource,
    WeebCentralSource,
    OmegaScansSource,
    ManhwaReadSource,
    WebtoonsSource,
    MangadassSource,
    Manhwa18Source,
    Manga18ClubSource,
    HentaiAkaneSource,
    NhentaiSource,
]

SOURCES = {cls.id: cls for cls in SOURCE_CLASSES}

DEFAULT_SOURCE = MangaDexSource.id

__all__ = [
    "BASE_HEADERS", "DEFAULT_SOURCE", "DEFAULT_UA", "SOURCES", "SOURCE_CLASSES",
    "ScrapeError", "Source", "MangaDexSource", "MangakatanaSource",
    "NatomangaSource", "WeebCentralSource", "OmegaScansSource",
    "ManhwaReadSource", "Manhwa18Source", "WebtoonsSource",
    "MangadassSource", "Manga18ClubSource", "HentaiAkaneSource",
    "NhentaiSource",
    "get_source", "source_for_url", "detect_source", "list_sources",
    "search_all", "browse_all", "browse_multi", "genres_all",
    "split_genres",
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
            "supports_browse": cls.supports_browse,
            "supports_genres": cls.supports_genres,
            "browse_sorts": list(cls.browse_sorts),
            "supports_language": cls.supports_language,
            "supports_scanlator": cls.supports_scanlator,
            "needs_flaresolverr": cls.needs_flaresolverr,
            "adult_only": getattr(cls, "adult_only", False),
            "cover_needs_referer": getattr(cls, "cover_needs_referer", False),
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

    from ..robust import SOURCE_BREAKER

    def run(source_id):
        def fetch():
            source = get_source(source_id)
            try:
                return source.search(query, limit=limits.get(source_id) or limit,
                                     **filters)
            finally:
                source.close()

        return SOURCE_BREAKER.call(source_id, fetch)

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


def _enabled_ids(source_ids=None, use_config=True):
    """Resolve which sources to hit, honouring the user's config."""
    if source_ids:
        return [s for s in source_ids if s in SOURCES], {}
    if use_config:
        try:
            from ..config import load_config, search_ids
            ids = search_ids()
            entries = load_config()["sources"]
            return ids, {sid: entries[sid].get("rank", 100) for sid in ids}
        except Exception:
            pass
    return list(SOURCES), {}


def browse_all(sort="Trending", genre=None, page=1, limit=12,
               source_ids=None, workers=4, use_config=True,
               interleave=True, use_cache=True, **filters) -> list:
    """Trending / genre listings merged across every enabled source.

    This is what powers "press search with an empty box". Sources that do
    not support browsing are skipped rather than raising, and one dead site
    cannot break the whole listing.

    Results interleave by default so the first screen shows a mix of sites
    instead of one site's entire page.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ids, ranks = _enabled_ids(source_ids, use_config)
    ids = [sid for sid in ids if SOURCES[sid].supports_browse]
    if not ids:
        return []
    if not ranks:
        ranks = {sid: i for i, sid in enumerate(ids)}

    from ..robust import BROWSE_CACHE, SOURCE_BREAKER, cache_key

    buckets = {}

    def run(source_id):
        key = cache_key("browse", source_id, sort, genre, page, limit,
                        sorted(filters.items()))
        if use_cache:
            cached = BROWSE_CACHE.get(key)
            if cached is not None:
                return cached

        def fetch():
            source = get_source(source_id)
            try:
                return source.browse(sort=sort, genre=genre, page=page,
                                     limit=limit, **filters)
            finally:
                source.close()

        # the breaker stops a dead site costing a full timeout every call
        rows = SOURCE_BREAKER.call(source_id, fetch) or []
        if use_cache and rows:
            BROWSE_CACHE.set(key, rows)
        return rows

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(ids)))) as pool:
        futures = {pool.submit(run, sid): sid for sid in ids}
        for future in as_completed(futures):
            source_id = futures[future]
            try:
                buckets[source_id] = future.result() or []
            except Exception as e:
                logger.warning("Browse failed on %s: %s", source_id, e)
                buckets[source_id] = []

    ordered = sorted(buckets, key=lambda sid: ranks.get(sid, 100))
    if not interleave:
        merged = []
        for source_id in ordered:
            merged.extend(buckets[source_id])
        return merged

    merged, index = [], 0
    while True:
        added = False
        for source_id in ordered:
            items = buckets[source_id]
            if index < len(items):
                merged.append(items[index])
                added = True
        if not added:
            break
        index += 1
    return merged


def _result_identity(item):
    """Stable identity for a search/browse result, for set operations."""
    url = (item.get("url") or "").strip().lower().rstrip("/")
    if url:
        return url
    return re.sub(r"\s+", " ", (item.get("title") or "").strip().lower())


def split_genres(genre):
    """Accept a genre as a list, or as a comma/pipe separated string."""
    if genre is None:
        return []
    if isinstance(genre, (list, tuple, set)):
        values = list(genre)
    else:
        values = re.split(r"[,|]", str(genre))
    out = []
    for value in values:
        value = str(value or "").strip()
        if value and value.lower() not in {v.lower() for v in out}:
            out.append(value)
    return out


def browse_multi(genres, sort="Trending", page=1, limit=12, match="all",
                 source_ids=None, use_config=True, interleave=True,
                 **filters) -> list:
    """Browse several genres at once.

    No source accepts more than one genre per request, so each is fetched
    separately and combined here:

    * ``match="all"``  -- intersection, titles carrying **every** genre
    * ``match="any"``  -- union, titles carrying at least one

    Intersecting is done per source. Comparing across sources would be
    wrong: the same title on two sites has two different URLs, so a title
    listed under "Action" on one and "Romance" on another would look like a
    match for "Action AND Romance" when neither site agrees it is both.
    """
    wanted = split_genres(genres)
    if not wanted:
        return browse_all(sort=sort, genre=None, page=page, limit=limit,
                          source_ids=source_ids, use_config=use_config,
                          interleave=interleave, **filters)
    if len(wanted) == 1:
        return browse_all(sort=sort, genre=wanted[0], page=page, limit=limit,
                          source_ids=source_ids, use_config=use_config,
                          interleave=interleave, **filters)

    per_genre = []
    for name in wanted:
        rows = browse_all(sort=sort, genre=name, page=page,
                          limit=max(limit, 40), source_ids=source_ids,
                          use_config=use_config, interleave=False, **filters)
        per_genre.append(rows)

    # group by source so intersections only compare like with like
    by_source = {}
    for index, rows in enumerate(per_genre):
        for row in rows:
            bucket = by_source.setdefault(row.get("source", ""), {})
            entry = bucket.setdefault(_result_identity(row),
                                      {"row": row, "hits": set()})
            entry["hits"].add(index)

    need = len(wanted) if str(match).lower() != "any" else 1
    kept = []
    for bucket in by_source.values():
        for entry in bucket.values():
            if len(entry["hits"]) >= need:
                row = dict(entry["row"])
                row["matched_genres"] = [wanted[i] for i in sorted(entry["hits"])]
                kept.append(row)

    if interleave:
        kept = _interleave_by_source(kept)
    return kept[:limit] if limit else kept


def _interleave_by_source(rows):
    """Round-robin rows by source so one site cannot fill the first screen."""
    buckets = {}
    for row in rows:
        buckets.setdefault(row.get("source", ""), []).append(row)
    out = []
    while any(buckets.values()):
        for key in list(buckets):
            if buckets[key]:
                out.append(buckets[key].pop(0))
    return out


def genres_all(source_ids=None, use_config=True) -> list:
    """Union of every genre offered by the enabled sources.

    Names are matched case-insensitively across sites, so "Sci-Fi" from one
    source and "sci-fi" from another collapse into a single entry that lists
    which sources provide it.
    """
    ids, _ranks = _enabled_ids(source_ids, use_config)
    ids = [sid for sid in ids if SOURCES[sid].supports_genres]

    from ..robust import GENRE_CACHE, cache_key

    cached = GENRE_CACHE.get(cache_key("genres", *sorted(ids)))
    if cached is not None:
        return cached

    merged = {}
    for source_id in ids:
        source = get_source(source_id)
        try:
            for genre in source.genres() or []:
                name = (genre.get("name") or "").strip()
                if not name:
                    continue
                key = name.lower()
                entry = merged.setdefault(key, {"name": name, "sources": {}})
                entry["sources"][source_id] = genre.get("id", name)
        except Exception as e:
            logger.warning("Genre listing failed on %s: %s", source_id, e)
        finally:
            source.close()

    rows = list(merged.values())
    rows.sort(key=lambda row: (-len(row["sources"]), row["name"].lower()))
    GENRE_CACHE.set(cache_key("genres", *sorted(ids)), rows)
    return rows
