"""pywebview GUI for MangaDL.

A minimalist Material-style web UI served locally. The Python side exposes a
small JSON API to JavaScript; download progress is pushed back with
window.evaluate_js.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback

from ..downloader import DownloadEngine, DownloadOptions
from ..sources import (DEFAULT_SOURCE, SOURCES, browse_all, detect_source,
                       genres_all, get_source, list_sources, search_all,
                       source_for_url)
from .. import config as appconfig
from .. import features
from .. import library
from .. import logs as wclogs
from .. import passlock
from .. import tracking

logger = logging.getLogger(__name__)

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".mangadl", "settings.json")

DEFAULT_SETTINGS = {
    "output_dir": os.path.join(os.path.expanduser("~"), "Downloads", "MangaDL"),
    "format": "cbz",
    "bundle": 0,
    "chapter_workers": 3,
    "image_workers": 6,
    "delay": 0.5,
    "retries": 5,
    "keep_images": False,
    "theme": "midnight",
    "accent": "blue",
    "animations": True,
    "matrix": True,
    "confirm_large": True,
    "large_threshold": 100,
    "sources": [],                  # legacy; per-source config lives in config.json
    "dedupe_results": True,         # collapse the same series across sources
    "interleave_results": False,    # round-robin sources instead of grouping
    "interleave_browse": True,      # trending feed mixes sources by default
    "confirm_delete": True,
    "auto_snapshot": False,
    "default_source": DEFAULT_SOURCE,
    "language": "en",               # MangaDex translation language
    "scanlator": "",                # preferred MangaDex scanlation group
    "data_saver": False,            # MangaDex compressed pages
    "library_search_roots": [],     # extra folders to look in when files move
    "reader_path": "",              # e.g. path to Readest executable
    "open_folder_when_done": False,
    "name_single": "{title} - Chapters {chapters}",
    "name_chapter": "{title} - Chapter {chapter}",
    "name_range": "{title} - Chapters {chapters}",
}


#: Naming templates that predate {chapters}. Anyone still carrying one of
#: these saved from an older version is migrated forward, otherwise their
#: stored value would keep overriding the improved default.
_LEGACY_NAME_TEMPLATES = {
    "name_single": ({"{title}"}, "{title} - Chapters {chapters}"),
    "name_range": ({"{title} - Chapters {start}-{end}"},
                   "{title} - Chapters {chapters}"),
}


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            settings.update(json.load(f))
    except (OSError, ValueError):
        pass

    for key, (legacy, replacement) in _LEGACY_NAME_TEMPLATES.items():
        if (settings.get(key) or "").strip() in legacy:
            settings[key] = replacement
    return settings


def save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def _dialog_types():
    """Dialog type constants across pywebview versions (6.x moved them)."""
    import webview
    fd = getattr(webview, "FileDialog", None)
    if fd is not None:  # pywebview >= 5.1 style
        return fd.FOLDER, fd.OPEN, fd.SAVE
    return webview.FOLDER_DIALOG, webview.OPEN_DIALOG, webview.SAVE_DIALOG


class Api:
    """Methods callable from JavaScript via window.pywebview.api.*"""

    def __init__(self):
        self.window = None
        self.engine = None
        self._thread = None
        self._sources = {}
        self._push_lock = threading.Lock()
        self._pending_events = []
        self._pending_progress = {}
        self._flush_timer = None

    # ----------------------------------------------------------- sources

    def _source(self, source_id=None, url=None):
        """Get (and cache) a source instance by id, or detect it from a URL."""
        settings = load_settings()
        if not source_id and url:
            source_id = detect_source(url)
        source_id = source_id or settings.get("default_source") or DEFAULT_SOURCE
        if source_id not in SOURCES:
            raise ValueError(f"Unknown source: {source_id}")

        key = (source_id, settings.get("language", "en"),
               settings.get("scanlator", ""), bool(settings.get("data_saver")))
        if key not in self._sources:
            self._sources[key] = get_source(
                source_id,
                language=settings.get("language", "en"),
                scanlator=settings.get("scanlator") or None,
                data_saver=bool(settings.get("data_saver")),
            )
        return self._sources[key]

    # ------------------------------------------------------------ passlock

    def lock_status(self):
        return {"ok": True, **passlock.status()}

    def lock_verify(self, passcode: str):
        result = passlock.verify(passcode)
        if result.get("ok"):
            self._unlocked_at = time.time()
        return result

    def lock_set(self, passcode: str, hint: str = "", auto_lock_minutes: int = 0,
                 lock_on_start: bool = True, blur_covers: bool = True):
        return passlock.set_passcode(passcode, hint, auto_lock_minutes,
                                     lock_on_start, blur_covers)

    def lock_change(self, current: str, new: str):
        return passlock.change_passcode(current, new)

    def lock_disable(self, passcode: str):
        return passlock.disable(passcode)

    def lock_recover(self, recovery_key: str, new_passcode: str):
        return passlock.recover(recovery_key, new_passcode)

    def lock_options(self, options: dict):
        return {"ok": True, **passlock.update_options(**(options or {}))}

    def lock_should_lock(self):
        """Whether the UI should show the lock screen right now."""
        status = passlock.status()
        if not status["enabled"]:
            return {"ok": True, "locked": False}
        idle_minutes = status["auto_lock_minutes"]
        if getattr(self, "_unlocked_at", 0) and idle_minutes:
            idle = (time.time() - self._unlocked_at) / 60.0
            return {"ok": True, "locked": idle >= idle_minutes}
        return {"ok": True, "locked": not getattr(self, "_unlocked_at", 0)}

    # -------------------------------------------------- source config

    def get_source_config(self):
        """Sources with their rank/enabled state, for the drag-and-drop list."""
        return {"ok": True, "sources": appconfig.describe()}

    def set_source_config(self, source_id: str, changes: dict):
        return {"ok": True, "entry": appconfig.set_source_config(
            source_id, **(changes or {}))}

    def reorder_sources(self, order: list):
        """Persist a new ranking after a drag-and-drop reorder."""
        appconfig.reorder(list(order or []))
        return {"ok": True, "sources": appconfig.describe()}

    def move_source(self, source_id: str, delta: int):
        appconfig.move(source_id, int(delta))
        return {"ok": True, "sources": appconfig.describe()}

    def toggle_source(self, source_id: str, enabled: bool):
        appconfig.set_enabled(source_id, bool(enabled))
        return {"ok": True, "sources": appconfig.describe()}

    def toggle_source_search(self, source_id: str, enabled: bool):
        appconfig.set_search_enabled(source_id, bool(enabled))
        return {"ok": True, "sources": appconfig.describe()}

    def reset_source_config(self):
        appconfig.reset_config()
        return {"ok": True, "sources": appconfig.describe()}

    # ------------------------------------------------------- features

    def get_history(self, limit: int = 30):
        return {"ok": True, "items": features.get_history(limit)}

    def suggest_query(self, prefix: str):
        return {"ok": True, "items": features.suggest(prefix)}

    def clear_history(self):
        features.clear_history()
        return {"ok": True}

    def remove_history(self, query: str):
        return {"ok": True, "items": features.remove_history(query)}

    def get_filters(self):
        return {"ok": True, "filters": features.get_filters()}

    def set_filters(self, changes: dict):
        return {"ok": True, "filters": features.set_filters(**(changes or {}))}

    def get_stats(self):
        return {"ok": True, "stats": features.get_stats()}

    def reset_stats(self):
        features.reset_stats()
        return {"ok": True}

    def get_insights(self):
        return {"ok": True, "insights": features.library_insights()}

    def get_collections(self):
        return {"ok": True, "collections": features.get_collections()}

    def add_to_collection(self, name: str, item: dict):
        return {"ok": True, "collections": features.add_to_collection(name, item)}

    def remove_from_collection(self, name: str, url: str):
        return {"ok": True,
                "collections": features.remove_from_collection(name, url)}

    def delete_collection(self, name: str):
        return {"ok": True, "collections": features.delete_collection(name)}

    def get_queue(self):
        return {"ok": True, "items": features.queue_list()}

    def queue_add(self, job: dict):
        return {"ok": True, "job": features.queue_add(job or {})}

    def queue_remove(self, job_id: str):
        return {"ok": True, "items": features.queue_remove(job_id)}

    def queue_move(self, job_id: str, delta: int):
        return {"ok": True, "items": features.queue_move(job_id, int(delta))}

    def queue_clear(self, status: str = None):
        return {"ok": True, "items": features.queue_clear(status)}

    def export_library(self, fmt: str = "json"):
        try:
            _, _, save_t = _dialog_types()
            ext = {"json": "json", "csv": "csv", "md": "md"}.get(fmt, "json")
            dest = self.window.create_file_dialog(
                save_t, save_filename=f"mangadl-library.{ext}")
            if not dest:
                return {"ok": False, "cancelled": True}
            if isinstance(dest, (list, tuple)):
                dest = dest[0]
            features.export_library(dest, fmt)
            return {"ok": True, "path": dest}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def import_library(self):
        try:
            _, open_t, _ = _dialog_types()
            chosen = self.window.create_file_dialog(open_t)
            if not chosen:
                return {"ok": False, "cancelled": True}
            if isinstance(chosen, (list, tuple)):
                chosen = chosen[0]
            return {"ok": True, **features.import_library(chosen)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def snapshot(self, label: str = ""):
        return {"ok": True, "snapshot": features.snapshot(label)}

    def list_snapshots(self):
        return {"ok": True, "items": features.list_snapshots()}

    def restore_snapshot(self, snapshot_id: str):
        return {"ok": features.restore_snapshot(snapshot_id)}

    def open_url(self, url: str):
        """Open a link in the user's real browser."""
        try:
            import webbrowser
            webbrowser.open(url)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------- tracking

    def mark_read(self, url: str, chapter_name: str, read: bool = True):
        tracking.mark_read(url, chapter_name, read)
        return {"ok": True}

    def mark_many_read(self, url: str, names: list, read: bool = True):
        tracking.mark_many(url, list(names or []), read)
        return {"ok": True}

    def get_progress(self, url: str, chapters: list = None):
        return {"ok": True,
                "progress": tracking.progress_for(url, chapters or []),
                "read": sorted(tracking.read_chapters(url))}

    def clear_progress(self, url: str = None):
        tracking.clear_progress(url)
        return {"ok": True}

    def watch(self, url: str, title: str, chapter_count: int,
              source: str = None, cover: str = None):
        return {"ok": True,
                "entry": tracking.watch(url, title, chapter_count, source, cover)}

    def unwatch(self, url: str):
        return {"ok": tracking.unwatch(url)}

    def is_watched(self, url: str):
        return {"ok": True, "watched": tracking.is_watched(url)}

    def get_watchlist(self):
        return {"ok": True, "items": tracking.get_watchlist()}

    def check_updates(self):
        try:
            return {"ok": True, "updates": tracking.check_updates()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def acknowledge_updates(self, url: str):
        tracking.acknowledge(url)
        return {"ok": True}

    def set_note(self, url: str, note: str = "", rating: int = 0,
                 tags: list = None):
        return {"ok": True, "entry": tracking.set_note(url, note, rating, tags)}

    def get_note(self, url: str):
        return {"ok": True, "note": tracking.get_note(url)}

    def get_rated(self, minimum: int = 1):
        return {"ok": True, "items": tracking.rated(minimum)}

    # --------------------------------------------------- disk tools

    def disk_usage(self, root: str = None):
        root = root or load_settings().get("output_dir")
        return {"ok": True, "rows": tracking.disk_usage(root),
                "root": root}

    def scan_duplicates(self, root: str = None):
        root = root or load_settings().get("output_dir")
        groups = tracking.scan_duplicates(root)
        return {"ok": True, "groups": groups,
                "wasted": sum(g["wasted"] for g in groups)}

    def find_orphans(self):
        return {"ok": True, "orphans": tracking.find_orphans()}

    def delete_files(self, paths: list):
        """Delete chosen files (used by the duplicate cleaner)."""
        removed, failed = [], []
        for path in paths or []:
            try:
                os.remove(path)
                removed.append(path)
            except OSError as e:
                failed.append({"path": path, "error": str(e)})
        return {"ok": True, "removed": removed, "failed": failed}

    # ---------------------------------------------- moved folders

    def verify_library(self):
        """Which library entries still resolve on disk."""
        return library.verify_entries()

    def relocate_entry(self, url: str, new_dir: str = None):
        """Point one entry at a folder the user moved it to."""
        if not new_dir:
            new_dir = self.choose_folder()
            if not new_dir:
                return {"ok": False, "cancelled": True}
        return library.relocate_entry(url, new_dir)

    def find_moved_entries(self, roots: list = None):
        """Propose relocations by matching folder names under given roots.

        Nothing is written: the UI shows the proposals and the user confirms.
        """
        if not roots:
            settings = load_settings()
            roots = [settings.get("output_dir")]
            extra = settings.get("library_search_roots") or []
            roots += [r for r in extra if r]
        return {"ok": True, "proposals": library.find_moved_entries(roots)}

    def apply_relocations(self, proposals: list):
        return library.apply_relocations(proposals or [])

    def rescan_output_dir(self, root: str = None):
        """Adopt a new downloads folder and relocate everything under it."""
        root = root or self.choose_folder()
        if not root:
            return {"ok": False, "cancelled": True}
        if not os.path.isdir(root):
            return {"ok": False, "error": f"Not a folder: {root}"}

        # remember it as the download location going forward
        settings = load_settings()
        settings["output_dir"] = root
        save_settings(settings)

        proposals = library.find_moved_entries([root])
        result = library.apply_relocations(proposals)
        return {"ok": True, "output_dir": root,
                "relocated": result.get("applied", 0),
                "still_missing": len(library.verify_entries()["missing"])}

    def get_health(self):
        """Circuit-breaker state and cache hit rates, for the Tools tab."""
        try:
            from ..robust import health_report
            return {"ok": True, "report": health_report()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_sources(self):
        """Every supported site, for the source picker."""
        return {"ok": True, "sources": list_sources(),
                "default": load_settings().get("default_source") or DEFAULT_SOURCE}

    # ------------------------------------------------------------- push

    # Progress events fire once per downloaded image. A 700-chapter job at
    # ~60 pages each is >43,000 evaluate_js calls, every one of them a JSON
    # dump interpolated into a JS string and marshalled across the native
    # bridge. That is what pins a CPU core and takes WebView2 down with
    # 0xCFFFFFFF. High-frequency events are therefore coalesced and flushed
    # on a timer as a single batch; lifecycle events still go out at once.
    _FLUSH_INTERVAL = 0.12          # seconds between batches
    _COALESCE = {"chapter_progress"}

    def _push(self, event: dict):
        """Queue an engine event for delivery to the web UI."""
        if self.window is None:
            return

        etype = event.get("type")
        with self._push_lock:
            if etype in self._COALESCE:
                # keep only the newest progress per chapter
                self._pending_progress[event.get("chapter")] = event
            else:
                self._pending_events.append(event)

            if self._flush_timer is None:
                self._flush_timer = threading.Timer(self._FLUSH_INTERVAL,
                                                    self._flush)
                self._flush_timer.daemon = True
                self._flush_timer.start()

        # deliver terminal events immediately so the UI never lags at the end
        if etype in ("finished", "done", "stopped", "error"):
            self._flush()

    def _flush(self):
        """Send everything queued as one batched call."""
        with self._push_lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None
            batch = self._pending_events
            batch += list(self._pending_progress.values())
            self._pending_events = []
            self._pending_progress = {}

        if not batch or self.window is None:
            return
        try:
            payload = json.dumps(batch)
            self.window.evaluate_js(f"window.onEngineEvents({payload})")
        except Exception:
            logger.debug("Failed to push events to the UI", exc_info=True)

    # ------------------------------------------------------------ pages

    def search(self, query: str, filters: dict = None):
        """Search, or show trending when there is no query.

        Pressing Search with an empty box is treated as "show me something":
        the same code path runs, but sources are asked for their discovery
        listing instead of a text match. A genre with no query browses that
        genre; a genre with a query filters the search.
        """
        try:
            f = filters or {}
            source_id = (f.get("source") or "").strip()
            genre = (f.get("genre") or "").strip()
            query = (query or "").strip()

            # pasting a URL jumps straight to that manga
            if query and detect_source(query) and "/" in query:
                return {"ok": True, "results": [], "url": query}

            if not query:
                return self.browse({
                    "source": source_id,
                    "genre": genre,
                    "sort": f.get("browse_sort") or "Trending",
                    "page": f.get("page", 1),
                    "status": f.get("status"),
                })

            kwargs = dict(
                sort=f.get("sort") or None,
                status=f.get("status"),
                series_type=f.get("type"),
                order=f.get("order", "Ascending"),
                official=f.get("official", "Any"),
                genre=genre or None,
            )
            kwargs = {k: v for k, v in kwargs.items() if v not in (None, "", "Any")}

            settings = load_settings()
            if source_id in ("", "all"):
                results = search_all(
                    query, limit=16,
                    interleave=bool(settings.get("interleave_results")),
                    **kwargs)
            else:
                results = self._source(source_id).search(query, **kwargs)

            results = features.apply_filters(results)
            if settings.get("dedupe_results", True) and source_id in ("", "all"):
                ranks = {row["id"]: row.get("rank", 100)
                         for row in appconfig.describe()}
                results = features.dedupe(results, ranks)

            features.add_history(query, source_id or "all", len(results))
            return {"ok": True, "results": results}
        except Exception as e:
            logger.exception("Search failed")
            return {"ok": False, "error": str(e)}

    def browse(self, options: dict = None):
        """Trending / genre discovery, merged across the enabled sources."""
        try:
            o = options or {}
            source_id = (o.get("source") or "").strip()
            genre = (o.get("genre") or "").strip() or None
            sort = o.get("sort") or "Trending"
            page = max(1, int(o.get("page", 1) or 1))
            settings = load_settings()

            extra = {}
            if o.get("status") and o["status"] != "Any":
                extra["status"] = o["status"]

            if source_id in ("", "all"):
                results = browse_all(
                    sort=sort, genre=genre, page=page, limit=12,
                    interleave=bool(settings.get("interleave_browse", True)),
                    **extra)
            else:
                source = self._source(source_id)
                if not getattr(source, "supports_browse", False):
                    return {"ok": True, "results": [], "browse": True,
                            "message": f"{source.name} cannot list trending titles"}
                # a per-source genre id may differ from the shared label
                results = source.browse(sort=sort, genre=genre, page=page,
                                        limit=32, **extra)

            results = features.apply_filters(results)
            if settings.get("dedupe_results", True) and source_id in ("", "all"):
                ranks = {row["id"]: row.get("rank", 100)
                         for row in appconfig.describe()}
                results = features.dedupe(results, ranks)

            return {"ok": True, "results": results, "browse": True,
                    "genre": genre, "sort": sort, "page": page}
        except Exception as e:
            logger.exception("Browse failed")
            return {"ok": False, "error": str(e)}

    def get_genres(self, source_id: str = None):
        """Genres for one source, or the union across enabled sources."""
        try:
            if source_id and source_id != "all":
                source = self._source(source_id)
                return {"ok": True, "genres": source.genres() or []}
            return {"ok": True, "genres": genres_all()}
        except Exception as e:
            return {"ok": False, "error": str(e), "genres": []}

    def get_manga(self, url: str, source_id: str = None):
        try:
            source = self._source(source_id, url=url)
            info = source.get_manga_info(url)
            chapters = source.get_chapters(url)
            return {
                "ok": True,
                "info": info,
                "chapters": chapters,
                "source": source.id,
                "source_name": source.name,
                "downloaded": sorted(library.downloaded_chapters(url)),
                "bookmarked": library.is_bookmarked(url),
                "watched": tracking.is_watched(url),
                "read": sorted(tracking.read_chapters(url)),
                "progress": tracking.progress_for(url, chapters),
                "note": tracking.get_note(url),
            }
        except Exception as e:
            logger.exception("get_manga failed")
            return {"ok": False, "error": str(e)}

    def get_covers(self, url: str, source_id: str = None):
        """Alternative covers (MangaDex volume art), if the source has any."""
        try:
            source = self._source(source_id, url=url)
            if not hasattr(source, "get_covers"):
                return {"ok": True, "covers": []}
            return {"ok": True, "covers": source.get_covers(url)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------------------------------------- library and bookmarks

    def get_library(self):
        lib = library.load_library()
        items = []
        for entry in lib.values():
            outputs = entry.get("outputs", [])
            parts = []
            for out in outputs:
                parts.append({
                    "path": out,
                    "name": os.path.basename(out),
                    "exists": os.path.isfile(out),
                    "size": os.path.getsize(out) if os.path.isfile(out) else 0,
                })
            items.append({
                "url": entry.get("url"),
                "title": entry.get("title"),
                "cover": entry.get("cover"),
                "directory": entry.get("directory"),
                "chapter_count": len(entry.get("chapters", {})),
                "pages": sum(c.get("pages", 0) for c in entry.get("chapters", {}).values()),
                "outputs": outputs,
                "parts": parts,
                "last_download": entry.get("last_download"),
            })
        items.sort(key=lambda x: x.get("last_download") or "", reverse=True)
        return {"ok": True, "items": items, "path": library.LIBRARY_PATH}

    def get_library_entry(self, url: str):
        entry = library.load_library().get(url.rstrip("/"))
        if not entry:
            return {"ok": False, "error": "Not in library"}
        chapters = [
            {"name": name, **meta}
            for name, meta in sorted(entry.get("chapters", {}).items())
        ]
        return {"ok": True, "entry": {**entry, "chapters": chapters}}

    def remove_library_entry(self, url: str):
        return {"ok": library.remove_entry(url)}

    def get_bookmarks(self):
        return {"ok": True, "items": library.load_bookmarks()}

    def toggle_bookmark(self, info: dict):
        try:
            return {"ok": True, "bookmarked": library.toggle_bookmark(info)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_library(self):
        library.clear_library()
        return {"ok": True}

    def clear_bookmarks(self):
        library.clear_bookmarks()
        return {"ok": True}

    # ------------------------------------------------- logs and recovery

    def get_log_info(self):
        return {"ok": True, **wclogs.log_info()}

    def export_log(self):
        """Save-as dialog, then export the combined log there."""
        try:
            _, _, save_t = _dialog_types()
            dest = self.window.create_file_dialog(
                save_t,
                save_filename=f"mangadl-{time.strftime('%Y%m%d-%H%M%S')}.log",
            )
            if not dest:
                return {"ok": False, "cancelled": True}
            if isinstance(dest, (list, tuple)):
                dest = dest[0]
            wclogs.export_log(dest)
            return {"ok": True, "path": dest}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_log(self):
        try:
            for suffix in ("", ".1", ".2", ".3"):
                path = wclogs.LOG_FILE + suffix
                if os.path.isfile(path):
                    open(path, "w").close() if suffix == "" else os.remove(path)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_pending_job(self):
        """A crashed/interrupted job that can be resumed, if any."""
        job = wclogs.read_journal()
        if not job:
            return {"ok": True, "pending": None}
        return {"ok": True, "pending": {
            "title": job.get("title") or "Unknown manga",
            "started": job.get("started"),
            "url": job.get("options", {}).get("url"),
            "selection": job.get("options", {}).get("selection"),
        }}

    def resume_pending_job(self):
        """Restart the journaled job; completed chapters are skipped."""
        job = wclogs.read_journal()
        if not job:
            return {"ok": False, "error": "Nothing to resume"}
        return self.start_download(job["options"])

    def discard_pending_job(self):
        wclogs.clear_journal()
        return {"ok": True}

    # --------------------------------------------------------- settings

    def get_settings(self):
        return load_settings()

    def set_settings(self, settings: dict):
        current = load_settings()
        current.update(settings or {})
        save_settings(current)
        return current

    def choose_folder(self):
        try:
            folder_t, _, _ = _dialog_types()
            result = self.window.create_file_dialog(folder_t)
            if result:
                return result[0] if isinstance(result, (list, tuple)) else result
        except Exception as e:
            logger.error("Folder dialog failed: %s", e)
        return None

    def choose_file(self):
        """Pick a file (used for the reader executable)."""
        try:
            _, open_t, _ = _dialog_types()
            result = self.window.create_file_dialog(open_t)
            if result:
                return result[0] if isinstance(result, (list, tuple)) else result
        except Exception as e:
            logger.error("File dialog failed: %s", e)
        return None

    def open_in_reader(self, path: str):
        """Open a book file in the configured reader (e.g. Readest)."""
        if not path or not os.path.isfile(path):
            return {"ok": False, "error": "File not found"}
        reader = (load_settings().get("reader_path") or "").strip()
        try:
            if reader:
                if not os.path.isfile(reader):
                    return {"ok": False, "error": "Reader executable not found - check Settings"}
                if sys.platform == "darwin" and reader.endswith(".app"):
                    subprocess.Popen(["open", "-a", reader, path])
                else:
                    subprocess.Popen([reader, path])
            else:
                # fall back to system default handler
                if sys.platform == "win32":
                    os.startfile(path)  # noqa: S606
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def open_folder(self, path: str):
        if not path or not os.path.isdir(path):
            return False
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return True
        except Exception:
            return False

    # --------------------------------------------------------- download

    def start_download(self, options: dict):
        if self._thread and self._thread.is_alive():
            return {"ok": False, "error": "A download is already running"}

        settings = load_settings()

        opt = DownloadOptions(
            url=options.get("url", ""),
            selection=options.get("selection", "all"),
            output_dir=options.get("output_dir") or DEFAULT_SETTINGS["output_dir"],
            format=options.get("format", "cbz"),
            bundle=int(options.get("bundle", 0) or 0),
            chapter_workers=max(1, min(8, int(options.get("chapter_workers", 3)))),
            image_workers=max(1, min(10, int(options.get("image_workers", 6)))),
            delay=max(0.0, float(options.get("delay", 0.5))),
            retries=max(1, min(10, int(options.get("retries", 5)))),
            keep_images=bool(options.get("keep_images", False)),
            extra_formats=list(options.get("extra_formats", []) or []),
            name_single=options.get("name_single") or DEFAULT_SETTINGS["name_single"],
            name_chapter=options.get("name_chapter") or DEFAULT_SETTINGS["name_chapter"],
            name_range=options.get("name_range") or DEFAULT_SETTINGS["name_range"],
            source=options.get("source") or "",
            language=options.get("language") or settings.get("language", "en"),
            scanlator=options.get("scanlator") or settings.get("scanlator", ""),
            data_saver=bool(options.get("data_saver",
                                        settings.get("data_saver", False))),
        )
        if opt.format == "images":
            opt.keep_images = True

        self.engine = DownloadEngine(opt, on_event=self._push)

        def runner():
            try:
                result = self.engine.run()
                self._push({"type": "finished", "result": result})
            except Exception as e:
                logger.exception("Download crashed")
                self._push({"type": "error", "message": str(e)})
                self._push({"type": "finished", "result": {"ok": False, "error": str(e)}})

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        return {"ok": True}

    def stop_download(self):
        if self.engine:
            self.engine.stop()
        self._flush()          # deliver whatever is queued before stopping
        return {"ok": True}

    def shutdown(self):
        """Cancel the pending flush timer so it cannot outlive the window."""
        with self._push_lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None
        for source in list(self._sources.values()):
            try:
                source.close()
            except Exception:
                pass
        self._sources.clear()
        return {"ok": True}


def _web_asset_path():
    """Locate web/index.html both in source and in a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)),
                            "mangadl", "gui", "web")
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    return os.path.join(base, "index.html")


def _show_fatal(message: str):
    """Last-resort error reporting: console + native message box on Windows."""
    print("\n[MangaDL] GUI failed to start:\n" + message, file=sys.stderr)
    print(f"\nLog file: {wclogs.LOG_FILE}\nCrash dumps: {wclogs.CRASH_FILE}",
          file=sys.stderr)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                message + f"\n\nDetails were written to:\n{wclogs.LOG_FILE}",
                "MangaDL - startup error",
                0x10,  # MB_ICONERROR
            )
        except Exception:
            pass


def run_gui():
    wclogs.setup_logging()
    wclogs.quiet_pywebview()
    wclogs.enable_crash_dumps()

    try:
        import webview
    except ImportError:
        _show_fatal("pywebview is not installed. Run: pip install pywebview")
        return 1

    html_path = _web_asset_path()
    if not os.path.isfile(html_path):
        _show_fatal(f"GUI assets not found at:\n{html_path}\n\n"
                    "If this is a packaged exe, rebuild it with the provided "
                    "MangaDL.spec so web assets are bundled.")
        return 1

    api = Api()
    try:
        window = webview.create_window(
            "MangaDL",
            html_path,
            js_api=api,
            width=1180,
            height=780,
            min_size=(920, 620),
            background_color="#16161e",
        )
    except Exception:
        logger.exception("create_window failed")
        _show_fatal("Could not create the application window:\n"
                    + traceback.format_exc(limit=3))
        return 1
    api.window = window

    def _on_loaded():
        # Remove the .NET bridge object pywebview injects on Windows.
        # We never use window.native, and Edge's accessibility/autofill
        # layer walks it recursively, which can flood the console and, in
        # the worst case, overflow the native stack and crash the process.
        try:
            window.evaluate_js(
                "try { delete window.native; window.native = undefined; } catch(e) {}"
            )
        except Exception:
            pass

    try:
        window.events.loaded += _on_loaded
    except Exception:
        pass

    # Release the flush timer, cached sessions and sockets on close, so a
    # closing window cannot leave background threads alive.
    try:
        window.events.closed += api.shutdown
    except Exception:
        pass

    # Try the default backend first; on failure retry with alternatives so a
    # broken/outdated runtime (e.g. WebView2) doesn't kill the app outright.
    if sys.platform == "win32":
        backends = [None, "edgechromium", "mshtml"]
    elif sys.platform == "darwin":
        backends = [None, "cocoa"]
    else:
        backends = [None, "gtk", "qt"]

    last_error = None
    for backend in backends:
        try:
            if backend is None:
                webview.start(debug=False)
            else:
                logger.warning("Retrying GUI with '%s' backend", backend)
                webview.start(debug=False, gui=backend)
            return 0
        except Exception as e:
            last_error = e
            logger.exception("webview.start failed (backend=%s)", backend)

    _show_fatal(
        "The embedded browser engine could not start.\n\n"
        f"Last error: {last_error}\n\n"
        "On Windows this usually means the Microsoft Edge WebView2 Runtime "
        "is missing or outdated - install it from:\n"
        "https://developer.microsoft.com/microsoft-edge/webview2/\n"
        "then restart the app."
    )
    return 1
