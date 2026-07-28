"""Extra feature modules: history, queue, stats, filters, dedupe, export.

These are deliberately dependency-free and file-backed so every interface
(CLI, GUI, TUI) can share them. Everything lives under ``~/.mangadl/``.
"""

import csv
import json
import os
import re
import threading
import time
from collections import Counter, defaultdict

DIR = os.path.join(os.path.expanduser("~"), ".mangadl")

HISTORY_PATH = os.path.join(DIR, "history.json")
QUEUE_PATH = os.path.join(DIR, "queue.json")
STATS_PATH = os.path.join(DIR, "stats.json")
FILTERS_PATH = os.path.join(DIR, "filters.json")
COLLECTIONS_PATH = os.path.join(DIR, "collections.json")
SNAPSHOT_PATH = os.path.join(DIR, "snapshots.json")

_lock = threading.RLock()

HISTORY_LIMIT = 500


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


def _save(path, data):
    os.makedirs(DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ============================================================== search history


def add_history(query, source="", results=0):
    """Record a search so it can be suggested later."""
    query = (query or "").strip()
    if not query:
        return []
    with _lock:
        items = [h for h in _load(HISTORY_PATH, [])
                 if h.get("query", "").lower() != query.lower()]
        items.insert(0, {"query": query, "source": source,
                         "results": results, "date": _now()})
        items = items[:HISTORY_LIMIT]
        _save(HISTORY_PATH, items)
        return items


def get_history(limit=30):
    return _load(HISTORY_PATH, [])[:limit]


def suggest(prefix, limit=8):
    """Type-ahead suggestions from history."""
    prefix = (prefix or "").strip().lower()
    items = _load(HISTORY_PATH, [])
    if not prefix:
        return [h["query"] for h in items[:limit]]
    starts = [h["query"] for h in items if h["query"].lower().startswith(prefix)]
    contains = [h["query"] for h in items
                if prefix in h["query"].lower() and h["query"] not in starts]
    return (starts + contains)[:limit]


def clear_history():
    with _lock:
        _save(HISTORY_PATH, [])
        return []


def remove_history(query):
    with _lock:
        items = [h for h in _load(HISTORY_PATH, [])
                 if h.get("query", "").lower() != (query or "").lower()]
        _save(HISTORY_PATH, items)
        return items


# ==================================================================== queue


def _queue():
    return _load(QUEUE_PATH, [])


def queue_add(job):
    """Append a download job. ``job`` mirrors DownloadOptions as a dict."""
    with _lock:
        items = _queue()
        entry = {
            "id": f"{int(time.time() * 1000)}-{len(items)}",
            "status": "pending",           # pending | running | done | failed | paused
            "added": _now(),
            "title": job.get("title") or job.get("url", ""),
            "options": job,
            "progress": 0,
            "total": 0,
            "error": "",
        }
        items.append(entry)
        _save(QUEUE_PATH, items)
        return entry


def queue_list(status=None):
    items = _queue()
    return [i for i in items if not status or i.get("status") == status]


def queue_update(job_id, **changes):
    with _lock:
        items = _queue()
        for item in items:
            if item["id"] == job_id:
                item.update(changes)
                break
        _save(QUEUE_PATH, items)
        return items


def queue_remove(job_id):
    with _lock:
        items = [i for i in _queue() if i["id"] != job_id]
        _save(QUEUE_PATH, items)
        return items


def queue_clear(status=None):
    with _lock:
        items = [] if not status else [i for i in _queue()
                                       if i.get("status") != status]
        _save(QUEUE_PATH, items)
        return items


def queue_move(job_id, delta):
    """Reorder a queued job."""
    with _lock:
        items = _queue()
        index = next((i for i, x in enumerate(items) if x["id"] == job_id), None)
        if index is None:
            return items
        target = max(0, min(len(items) - 1, index + delta))
        items.insert(target, items.pop(index))
        _save(QUEUE_PATH, items)
        return items


def queue_next():
    """The next pending job, or None."""
    return next((i for i in _queue() if i.get("status") == "pending"), None)


# ==================================================================== stats


def record_stat(source, chapters=0, pages=0, bytes_=0, seconds=0.0, failed=0):
    """Accumulate download statistics, overall and per source and per day."""
    with _lock:
        stats = _load(STATS_PATH, {})
        totals = stats.setdefault("totals", {
            "chapters": 0, "pages": 0, "bytes": 0, "seconds": 0.0,
            "failed": 0, "downloads": 0})
        totals["chapters"] += chapters
        totals["pages"] += pages
        totals["bytes"] += bytes_
        totals["seconds"] += seconds
        totals["failed"] += failed
        totals["downloads"] += 1

        per_source = stats.setdefault("sources", {}).setdefault(source or "?", {
            "chapters": 0, "pages": 0, "bytes": 0, "seconds": 0.0, "downloads": 0})
        per_source["chapters"] += chapters
        per_source["pages"] += pages
        per_source["bytes"] += bytes_
        per_source["seconds"] += seconds
        per_source["downloads"] += 1

        day = time.strftime("%Y-%m-%d")
        per_day = stats.setdefault("days", {}).setdefault(day, {
            "chapters": 0, "pages": 0, "bytes": 0})
        per_day["chapters"] += chapters
        per_day["pages"] += pages
        per_day["bytes"] += bytes_

        stats["updated"] = _now()
        _save(STATS_PATH, stats)
        return stats


def get_stats():
    stats = _load(STATS_PATH, {})
    totals = stats.get("totals", {})
    seconds = totals.get("seconds", 0) or 0
    pages = totals.get("pages", 0) or 0
    stats["derived"] = {
        "avg_pages_per_second": round(pages / seconds, 2) if seconds else 0,
        "human_bytes": human_size(totals.get("bytes", 0)),
        "human_time": human_time(seconds),
        "busiest_day": max(stats.get("days", {}).items(),
                           key=lambda kv: kv[1].get("chapters", 0),
                           default=("-", {}))[0],
        "top_source": max(stats.get("sources", {}).items(),
                          key=lambda kv: kv[1].get("chapters", 0),
                          default=("-", {}))[0],
    }
    return stats


def reset_stats():
    with _lock:
        _save(STATS_PATH, {})
        return {}


def human_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def human_time(seconds):
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours, rest = divmod(seconds, 3600)
    return f"{hours}h {rest // 60}m"


# ========================================================== content filters


DEFAULT_FILTERS = {
    "blocked_tags": [],        # hide results carrying these tags
    "blocked_titles": [],      # substring matches on the title
    "blocked_authors": [],
    "min_chapters": 0,          # hide series with fewer chapters than this
    "max_chapters": 0,          # 0 = no upper limit
    "hide_no_cover": False,
    "safe_mode": False,        # drop adult ratings where the source reports them
}


def get_filters():
    return {**DEFAULT_FILTERS, **_load(FILTERS_PATH, {})}


def set_filters(**changes):
    with _lock:
        filters = get_filters()
        for key, value in changes.items():
            if key in DEFAULT_FILTERS:
                filters[key] = value
        _save(FILTERS_PATH, filters)
        return filters


def _chapter_count(item):
    """Best-effort chapter count for a search result, or None if unknown.

    Different sources expose this differently: an explicit count, a
    ``last_chapter`` number, or only a "Chapter 123" label on the newest
    release. None means "do not judge this item".
    """
    for key in ("chapter_count", "chapters", "total_chapters", "last_chapter"):
        value = item.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
        if isinstance(value, list):
            return float(len(value))
        if isinstance(value, str) and value.strip():
            match = re.search(r"(\d+(?:\.\d+)?)", value)
            if match:
                return float(match.group(1))

    latest = item.get("latest")
    if isinstance(latest, str) and latest.strip():
        match = re.search(r"(\d+(?:\.\d+)?)", latest)
        if match:
            return float(match.group(1))
    return None


def apply_filters(results, filters=None):
    """Drop results the user has chosen to hide."""
    filters = filters or get_filters()
    blocked_tags = {t.lower() for t in filters.get("blocked_tags", [])}
    blocked_titles = [t.lower() for t in filters.get("blocked_titles", []) if t]
    blocked_authors = {a.lower() for a in filters.get("blocked_authors", [])}
    safe = filters.get("safe_mode")
    adult = {"pornographic", "erotica", "smut", "hentai", "adult"}

    try:
        min_chapters = int(filters.get("min_chapters") or 0)
    except (TypeError, ValueError):
        min_chapters = 0
    try:
        max_chapters = int(filters.get("max_chapters") or 0)
    except (TypeError, ValueError):
        max_chapters = 0

    kept = []
    for item in results:
        # Chapter-count limits. Sources report this inconsistently, so only
        # filter when a count is actually known -- otherwise a source that
        # omits it would vanish entirely from every filtered search.
        count = _chapter_count(item)
        if count is not None:
            if min_chapters and count < min_chapters:
                continue
            if max_chapters and count > max_chapters:
                continue

        title = (item.get("title") or "").lower()
        if any(b in title for b in blocked_titles):
            continue
        tags = {str(t).lower() for t in (item.get("tags") or [])}
        if blocked_tags & tags:
            continue
        if safe and (adult & tags):
            continue
        if safe and str(item.get("content_rating", "")).lower() in adult:
            continue
        authors = {str(a).lower() for a in (item.get("authors") or [])}
        if blocked_authors & authors:
            continue
        if filters.get("hide_no_cover") and not item.get("cover"):
            continue
        kept.append(item)
    return kept


# ================================================================== dedupe


def _normalise_title(title):
    title = (title or "").lower()
    title = re.sub(r"\(.*?\)|\[.*?\]", " ", title)
    title = re.sub(r"\b(official|colored|full color|doujinshi|fan ?colou?red)\b",
                   " ", title)
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return " ".join(title.split())


def group_duplicates(results):
    """Group search hits that look like the same series across sources."""
    groups = defaultdict(list)
    for item in results:
        groups[_normalise_title(item.get("title"))].append(item)
    return [items for items in groups.values()]


def dedupe(results, ranks=None):
    """Collapse cross-source duplicates, keeping the best-ranked copy.

    The survivor carries ``also_on`` listing the other sources that had it,
    so the UI can offer a source switch without a second search.
    """
    ranks = ranks or {}
    merged = []
    for group in group_duplicates(results):
        if len(group) == 1:
            merged.append(group[0])
            continue
        group.sort(key=lambda r: ranks.get(r.get("source"), 99))
        best = dict(group[0])
        best["also_on"] = [
            {"source": g.get("source"), "source_name": g.get("source_name"),
             "url": g.get("url")}
            for g in group[1:]
        ]
        merged.append(best)
    return merged


# ============================================================= collections


def get_collections():
    return _load(COLLECTIONS_PATH, {})


def create_collection(name, description=""):
    with _lock:
        data = get_collections()
        data.setdefault(name, {"description": description, "items": [],
                               "created": _now()})
        _save(COLLECTIONS_PATH, data)
        return data


def add_to_collection(name, item):
    with _lock:
        data = get_collections()
        entry = data.setdefault(name, {"description": "", "items": [],
                                       "created": _now()})
        url = (item.get("url") or "").rstrip("/")
        if not any((i.get("url") or "").rstrip("/") == url for i in entry["items"]):
            entry["items"].append({
                "url": url,
                "title": item.get("title"),
                "cover": item.get("cover"),
                "source": item.get("source"),
                "added": _now(),
            })
        _save(COLLECTIONS_PATH, data)
        return data


def remove_from_collection(name, url):
    with _lock:
        data = get_collections()
        if name in data:
            url = (url or "").rstrip("/")
            data[name]["items"] = [
                i for i in data[name]["items"]
                if (i.get("url") or "").rstrip("/") != url
            ]
            _save(COLLECTIONS_PATH, data)
        return data


def delete_collection(name):
    with _lock:
        data = get_collections()
        data.pop(name, None)
        _save(COLLECTIONS_PATH, data)
        return data


# ================================================================== export


def export_library(path, fmt="json"):
    """Export the library to JSON, CSV or Markdown."""
    from . import library

    data = library.load_library()
    entries = list(data.values())
    fmt = (fmt or "json").lower()

    if fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    elif fmt == "csv":
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["title", "source", "url", "chapters", "pages",
                             "directory", "last_download"])
            for entry in entries:
                chapters = entry.get("chapters", {})
                writer.writerow([
                    entry.get("title", ""), entry.get("source", ""),
                    entry.get("url", ""), len(chapters),
                    sum(c.get("pages", 0) for c in chapters.values()),
                    entry.get("directory", ""), entry.get("last_download", ""),
                ])
    elif fmt in ("md", "markdown"):
        lines = ["# MangaDL library", "",
                 "| Title | Source | Chapters | Last download |",
                 "|---|---|---|---|"]
        for entry in sorted(entries, key=lambda e: (e.get("title") or "").lower()):
            lines.append(
                f"| [{entry.get('title', '?')}]({entry.get('url', '')}) "
                f"| {entry.get('source', '-')} "
                f"| {len(entry.get('chapters', {}))} "
                f"| {entry.get('last_download', '-')} |"
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    return path


def import_library(path, merge=True):
    """Import a previously exported JSON library."""
    from . import library

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    entries = payload if isinstance(payload, list) else list(payload.values())

    current = library.load_library() if merge else {}
    added = 0
    for entry in entries:
        url = (entry.get("url") or "").rstrip("/")
        if not url:
            continue
        if url not in current:
            added += 1
        current[url] = entry
    library._save(library.LIBRARY_PATH, current)
    return {"imported": len(entries), "added": added}


# =============================================================== snapshots


def snapshot(label=""):
    """Save a point-in-time copy of library + bookmarks + config."""
    from . import config as cfg
    from . import library

    with _lock:
        snaps = _load(SNAPSHOT_PATH, [])
        snaps.insert(0, {
            "id": str(int(time.time())),
            "label": label or _now(),
            "date": _now(),
            "library": library.load_library(),
            "bookmarks": library.load_bookmarks(),
            "config": cfg.load_config(),
        })
        snaps = snaps[:20]
        _save(SNAPSHOT_PATH, snaps)
        return snaps[0]


def list_snapshots():
    return [{k: v for k, v in s.items() if k in ("id", "label", "date")}
            for s in _load(SNAPSHOT_PATH, [])]


def restore_snapshot(snapshot_id):
    from . import config as cfg
    from . import library

    for snap in _load(SNAPSHOT_PATH, []):
        if snap.get("id") == snapshot_id:
            library._save(library.LIBRARY_PATH, snap.get("library", {}))
            library._save(library.BOOKMARKS_PATH, snap.get("bookmarks", []))
            cfg.save_config(snap.get("config", {}))
            return True
    return False


# ================================================================= insights


def library_insights():
    """Aggregate view of the library, for a dashboard."""
    from . import library

    entries = list(library.load_library().values())
    sources = Counter(e.get("source") or "?" for e in entries)
    total_chapters = sum(len(e.get("chapters", {})) for e in entries)
    total_pages = sum(c.get("pages", 0) for e in entries
                      for c in e.get("chapters", {}).values())

    on_disk = 0
    for entry in entries:
        for out in entry.get("outputs", []) or []:
            try:
                on_disk += os.path.getsize(out)
            except OSError:
                pass

    return {
        "series": len(entries),
        "chapters": total_chapters,
        "pages": total_pages,
        "bytes": on_disk,
        "human_bytes": human_size(on_disk),
        "by_source": dict(sources),
        "largest": sorted(
            ({"title": e.get("title"),
              "chapters": len(e.get("chapters", {}))} for e in entries),
            key=lambda x: x["chapters"], reverse=True)[:10],
        "recent": sorted(
            ({"title": e.get("title"), "date": e.get("last_download") or ""}
             for e in entries),
            key=lambda x: x["date"], reverse=True)[:10],
    }
