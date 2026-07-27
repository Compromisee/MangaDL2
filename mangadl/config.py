"""Per-source configuration: ranking, exclusion and overrides.

Stored at ``~/.mangadl/config.json``. Every source gets an entry:

    {
      "sources": {
        "mangadex":    {"enabled": true,  "rank": 0, "weight": 1.0, ...},
        "mangakatana": {"enabled": true,  "rank": 1, ...},
        "natomanga":   {"enabled": false, "rank": 2, ...}
      }
    }

``rank`` drives ordering in merged search results (lower = higher priority) and
is what the GUI's drag-and-drop list writes back. ``enabled: false`` removes a
site from searches entirely while still allowing a direct URL to be opened, so
you can exclude a site from discovery without losing the ability to use a link
someone sends you. ``search_enabled`` is the softer variant: keep the source
usable but leave it out of "all sources" searches.
"""

import json
import os
import threading

from .sources import SOURCES

DIR = os.path.join(os.path.expanduser("~"), ".mangadl")
CONFIG_PATH = os.path.join(DIR, "config.json")

_lock = threading.RLock()

# Defaults applied to any source that has no saved entry yet.
SOURCE_DEFAULTS = {
    "enabled": True,          # false = excluded everywhere except direct URLs
    "search_enabled": True,   # false = excluded from multi-source search only
    "rank": 100,              # lower sorts first in merged results
    "weight": 1.0,            # score multiplier when merging duplicates
    "limit": 0,               # per-source result cap, 0 = use the caller's
    "language": "",           # override translation language (MangaDex)
    "delay": 0.0,             # extra politeness delay, 0 = source default
    "note": "",               # free-text user note
}


def _default_config() -> dict:
    return {
        "sources": {
            source_id: {**SOURCE_DEFAULTS, "rank": index}
            for index, source_id in enumerate(SOURCES)
        }
    }


def _load_raw() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_raw(data: dict) -> None:
    os.makedirs(DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def load_config() -> dict:
    """Full config, backfilled so every registered source has an entry.

    New sources added to the registry appear automatically, ranked last.
    """
    with _lock:
        data = _load_raw()
        sources = data.get("sources")
        if not isinstance(sources, dict):
            sources = {}

        highest = max((entry.get("rank", 0) for entry in sources.values()
                       if isinstance(entry, dict)), default=-1)

        for source_id in SOURCES:
            entry = sources.get(source_id)
            if not isinstance(entry, dict):
                highest += 1
                sources[source_id] = {**SOURCE_DEFAULTS, "rank": highest}
            else:
                sources[source_id] = {**SOURCE_DEFAULTS, **entry}

        # drop entries for sources that no longer exist
        for stale in [k for k in sources if k not in SOURCES]:
            del sources[stale]

        data["sources"] = sources
        return data


def save_config(data: dict) -> dict:
    with _lock:
        _save_raw(data)
        return data


def get_source_config(source_id: str) -> dict:
    return load_config()["sources"].get(source_id, dict(SOURCE_DEFAULTS))


def set_source_config(source_id: str, **changes) -> dict:
    """Update one source's settings."""
    with _lock:
        config = load_config()
        entry = config["sources"].setdefault(source_id, dict(SOURCE_DEFAULTS))
        for key, value in changes.items():
            if key in SOURCE_DEFAULTS:
                entry[key] = value
        save_config(config)
        return entry


def set_enabled(source_id: str, enabled: bool) -> dict:
    """Exclude a source entirely (direct URLs still work)."""
    return set_source_config(source_id, enabled=bool(enabled))


def set_search_enabled(source_id: str, enabled: bool) -> dict:
    """Keep the source usable but leave it out of multi-source search."""
    return set_source_config(source_id, search_enabled=bool(enabled))


def reorder(order) -> dict:
    """Apply a new ranking from an ordered list of source ids.

    This is what the GUI's drag-and-drop list calls after a drop.
    """
    with _lock:
        config = load_config()
        rank = 0
        for source_id in order:
            if source_id in config["sources"]:
                config["sources"][source_id]["rank"] = rank
                rank += 1
        # anything not mentioned keeps a stable position at the end
        for source_id, entry in config["sources"].items():
            if source_id not in order:
                entry["rank"] = rank
                rank += 1
        save_config(config)
        return config


def move(source_id: str, delta: int) -> dict:
    """Nudge a source up (-1) or down (+1) the ranking."""
    order = ranked_ids(include_disabled=True)
    if source_id not in order:
        return load_config()
    index = order.index(source_id)
    target = max(0, min(len(order) - 1, index + delta))
    if target != index:
        order.insert(target, order.pop(index))
    return reorder(order)


def reset_config() -> dict:
    with _lock:
        return save_config(_default_config())


# ------------------------------------------------------------------ queries


def ranked_ids(include_disabled: bool = False, for_search: bool = False) -> list:
    """Source ids in user-defined rank order."""
    sources = load_config()["sources"]
    items = []
    for source_id, entry in sources.items():
        if not include_disabled:
            if not entry.get("enabled", True):
                continue
            if for_search and not entry.get("search_enabled", True):
                continue
        items.append((entry.get("rank", 100), source_id))
    items.sort()
    return [source_id for _rank, source_id in items]


def search_ids() -> list:
    """Sources that take part in a multi-source search."""
    return ranked_ids(for_search=True)


def is_enabled(source_id: str) -> bool:
    return bool(get_source_config(source_id).get("enabled", True))


def rank_of(source_id: str) -> int:
    return int(get_source_config(source_id).get("rank", 100))


def weight_of(source_id: str) -> float:
    try:
        return float(get_source_config(source_id).get("weight", 1.0))
    except (TypeError, ValueError):
        return 1.0


def describe() -> list:
    """Source metadata merged with its config, in rank order (for the UI)."""
    from .sources import list_sources

    config = load_config()["sources"]
    metas = {meta["id"]: meta for meta in list_sources()}
    rows = []
    for source_id in ranked_ids(include_disabled=True):
        meta = metas.get(source_id, {})
        rows.append({**meta, **config.get(source_id, {}), "id": source_id})
    return rows
