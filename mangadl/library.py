"""Persistent library and bookmarks stored as JSON in the user folder.

~/.mangadl/library.json    - every downloaded chapter, per manga
~/.mangadl/bookmarks.json  - bookmarked manga

The download engine records chapters here so any UI (GUI / TUI / CLI)
can highlight what has already been downloaded.
"""

import json
import os
import threading
import time

DIR = os.path.join(os.path.expanduser("~"), ".mangadl")
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


def record_chapter(url, title, chapter_name, pages=0, cover=None, directory=None,
                   source=None):
    """Remember that a chapter of a manga has been downloaded."""
    with _lock:
        lib = _load(LIBRARY_PATH, {})
        key = _key(url)
        entry = lib.setdefault(key, {
            "title": title, "url": key, "cover": cover, "source": source,
            "directory": directory, "chapters": {}, "added": _now(),
        })
        entry["title"] = title or entry.get("title")
        if cover:
            entry["cover"] = cover
        if source:
            entry["source"] = source
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
                "source": info.get("source"),
                "source_name": info.get("source_name"),
                "added": _now(),
            })
            _save(BOOKMARKS_PATH, kept)
            return True
        _save(BOOKMARKS_PATH, kept)
        return False


def clear_bookmarks():
    with _lock:
        _save(BOOKMARKS_PATH, [])


# ------------------------------------------------------- relocation

def _relocate_paths(entry, old_dir, new_dir):
    """Rewrite an entry's directory and output paths onto a new folder."""
    entry["directory"] = new_dir
    outputs = entry.get("outputs") or []
    moved = []
    for path in outputs:
        name = os.path.basename(path)
        candidate = os.path.join(new_dir, name)
        # only adopt the new location if the file is actually there
        moved.append(candidate if os.path.isfile(candidate) else path)
    if outputs:
        entry["outputs"] = moved
    entry["relocated"] = _now()
    return entry


def relocate_entry(url, new_dir) -> dict:
    """Point one library entry at a folder the user moved it to."""
    new_dir = os.path.abspath(os.path.expanduser(new_dir or ""))
    if not os.path.isdir(new_dir):
        return {"ok": False, "error": f"Not a folder: {new_dir}"}
    with _lock:
        lib = _load(LIBRARY_PATH, {})
        entry = lib.get(_key(url))
        if entry is None:
            return {"ok": False, "error": "Not in library"}
        old = entry.get("directory")
        _relocate_paths(entry, old, new_dir)
        _save(LIBRARY_PATH, lib)
        return {"ok": True, "old": old, "new": new_dir,
                "title": entry.get("title")}


def find_moved_entries(search_roots=None) -> list:
    """Look for library folders that were moved, by matching folder name.

    Returns proposals only -- nothing is written until :func:`relocate_entry`
    or :func:`apply_relocations` is called, so a wrong guess cannot silently
    rewrite the library.
    """
    roots = [os.path.abspath(os.path.expanduser(r))
             for r in (search_roots or []) if r]
    roots = [r for r in roots if os.path.isdir(r)]
    if not roots:
        return []

    # index candidate folders by name, one level deep (and the root itself)
    index = {}
    for root in roots:
        try:
            for name in os.listdir(root):
                path = os.path.join(root, name)
                if os.path.isdir(path):
                    index.setdefault(name, []).append(path)
        except OSError:
            continue

    proposals = []
    for entry in _load(LIBRARY_PATH, {}).values():
        directory = entry.get("directory")
        if not directory or os.path.isdir(directory):
            continue                      # still where we left it
        name = os.path.basename(directory.rstrip(os.sep))
        for candidate in index.get(name, []):
            if os.path.isdir(candidate):
                proposals.append({
                    "url": entry.get("url"),
                    "title": entry.get("title"),
                    "old": directory,
                    "new": candidate,
                })
                break
    return proposals


def apply_relocations(proposals) -> dict:
    """Apply a list of ``{url, new}`` relocation proposals."""
    applied, failed = [], []
    for item in proposals or []:
        result = relocate_entry(item.get("url"), item.get("new"))
        (applied if result.get("ok") else failed).append(result)
    return {"ok": True, "applied": len(applied), "failed": failed,
            "details": applied}


def verify_entries() -> dict:
    """Report which library entries still resolve on disk."""
    present, missing = [], []
    for entry in _load(LIBRARY_PATH, {}).values():
        directory = entry.get("directory")
        outputs = entry.get("outputs") or []
        gone = [o for o in outputs if not os.path.isfile(o)]
        row = {
            "url": entry.get("url"),
            "title": entry.get("title"),
            "directory": directory,
            "directory_ok": bool(directory and os.path.isdir(directory)),
            "missing_outputs": gone,
        }
        (missing if (not row["directory_ok"] or gone) else present).append(row)
    return {"ok": True, "present": present, "missing": missing}
