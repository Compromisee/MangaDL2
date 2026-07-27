"""Persistent library and bookmarks stored as JSON in the user folder.

~/.weebcentral/library.json    - every downloaded chapter, per manga
~/.weebcentral/bookmarks.json  - bookmarked manga

The download engine records chapters here so any UI (GUI / TUI / CLI)
can highlight what has already been downloaded.
"""

import json
import os
import threading
import time

DIR = os.path.join(os.path.expanduser("~"), ".weebcentral")
LIBRARY_PATH = os.path.join(DIR, "library.json")
BOOKMARKS_PATH = os.path.join(DIR, "bookmarks.json")

_lock = threading.RLock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _key(url: str) -> str:
    return (url or "").strip().rstrip("/")


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


# ------------------------------------------------------------------ library


def load_library() -> dict:
    with _lock:
        return _load(LIBRARY_PATH, {})


def record_chapter(url, title, chapter_name, pages=0, cover=None, directory=None):
    """Remember that a chapter of a manga has been downloaded."""
    with _lock:
        lib = _load(LIBRARY_PATH, {})
        key = _key(url)
        entry = lib.setdefault(key, {
            "title": title, "url": key, "cover": cover,
            "directory": directory, "chapters": {}, "added": _now(),
        })
        entry["title"] = title or entry.get("title")
        if cover:
            entry["cover"] = cover
        if directory:
            entry["directory"] = directory
        entry["chapters"][chapter_name] = {"pages": pages, "date": _now()}
        entry["last_download"] = _now()
        _save(LIBRARY_PATH, lib)


def record_outputs(url, outputs):
    """Remember the packaged files produced for a manga."""
    with _lock:
        lib = _load(LIBRARY_PATH, {})
        entry = lib.get(_key(url))
        if entry is not None:
            existing = entry.setdefault("outputs", [])
            for out in outputs:
                if out not in existing:
                    existing.append(out)
            _save(LIBRARY_PATH, lib)


def downloaded_chapters(url) -> set:
    """Chapter names already downloaded for this manga."""
    with _lock:
        entry = _load(LIBRARY_PATH, {}).get(_key(url))
        return set(entry["chapters"].keys()) if entry else set()


def remove_entry(url) -> bool:
    with _lock:
        lib = _load(LIBRARY_PATH, {})
        if _key(url) in lib:
            del lib[_key(url)]
            _save(LIBRARY_PATH, lib)
            return True
        return False


def clear_library():
    with _lock:
        _save(LIBRARY_PATH, {})


# ---------------------------------------------------------------- bookmarks


def load_bookmarks() -> list:
    with _lock:
        return _load(BOOKMARKS_PATH, [])


def is_bookmarked(url) -> bool:
    key = _key(url)
    return any(_key(b.get("url")) == key for b in load_bookmarks())


def toggle_bookmark(info: dict) -> bool:
    """Add or remove a bookmark. Returns True if now bookmarked."""
    with _lock:
        marks = _load(BOOKMARKS_PATH, [])
        key = _key(info.get("url"))
        kept = [b for b in marks if _key(b.get("url")) != key]
        if len(kept) == len(marks):
            kept.append({
                "url": key,
                "title": info.get("title", "Unknown"),
                "cover": info.get("cover"),
                "status": info.get("status"),
                "added": _now(),
            })
            _save(BOOKMARKS_PATH, kept)
            return True
        _save(BOOKMARKS_PATH, kept)
        return False


def clear_bookmarks():
    with _lock:
        _save(BOOKMARKS_PATH, [])
