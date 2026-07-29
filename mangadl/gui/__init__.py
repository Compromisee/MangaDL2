"""pywebview GUI for MangaDL.

A minimalist Material-style web UI served locally. The Python side exposes a
small JSON API to JavaScript; download progress is pushed back with
window.evaluate_js.
"""

import collections
import functools
import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback

from ..downloader import DownloadEngine, DownloadOptions
from ..sources import (DEFAULT_SOURCE, SOURCES, browse_all, browse_multi,
                       detect_source, genres_all, get_source, list_sources,
                       search_all, split_genres,
                       source_for_url)
from .. import config as appconfig
from .. import features
from .. import library
from .. import logs as wclogs
from .. import passlock
from .. import tracking

logger = logging.getLogger(__name__)

#: Where settings actually live now. Kept as a name because other modules and
#: tests import it; it points at config.json, which holds both the app
#: settings and the per-source config.
SETTINGS_PATH = appconfig.CONFIG_PATH

#: Pre-1.4.11 location, read once and migrated. Never written again.
LEGACY_SETTINGS_PATH = appconfig.LEGACY_SETTINGS_PATH

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
    "corners": "rounded",       # "rounded" | "square"
    "rail_expanded": False,     # side rail starts collapsed
    "accent": "blue",
    "animations": True,
    "matrix": True,
    "confirm_large": True,
    "large_threshold": 100,
    "sources": [],                  # legacy; per-source config lives in config.json
    "dedupe_results": True,         # collapse the same series across sources
    "interleave_results": False,    # round-robin sources instead of grouping
    "interleave_browse": True,      # trending feed mixes sources by default
    "max_concurrent_jobs": 2,       # manga downloading at the same time
    "columns": 0,                   # result grid columns, 0 = fit the window
    "advanced_info": False,         # extra metadata on the manga page
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


# Settings live in config.json alongside the per-source config, behind that
# module's lock and atomic write. The old settings.json was written with a
# bare open()/json.dump: an interrupted write left truncated JSON that
# load_settings() silently swallowed and replaced with defaults, and two
# concurrent saves each wrote the state they had read, so the later one
# erased the earlier one's change. Measured on the old code, four threads
# saving at once destroyed the theme, accent and output directory in 5 out
# of 5 runs -- which is what "a lot of settings broke" looked like.
appconfig.register_settings_defaults(DEFAULT_SETTINGS)


def load_settings() -> dict:
    settings = appconfig.load_settings(DEFAULT_SETTINGS)
    for key, (legacy, replacement) in _LEGACY_NAME_TEMPLATES.items():
        if (settings.get(key) or "").strip() in legacy:
            settings[key] = replacement
    return settings


def save_settings(settings: dict) -> None:
    appconfig.save_settings(settings)


def update_settings(changes: dict) -> dict:
    """Merge changes under the config lock, so racing saves cannot clobber."""
    return appconfig.update_settings(changes, DEFAULT_SETTINGS)


def _dialog_types():
    """Dialog type constants across pywebview versions (6.x moved them)."""
    import webview
    fd = getattr(webview, "FileDialog", None)
    if fd is not None:  # pywebview >= 5.1 style
        return fd.FOLDER, fd.OPEN, fd.SAVE
    return webview.FOLDER_DIALOG, webview.OPEN_DIALOG, webview.SAVE_DIALOG


def _narrow_by_type(results, wanted):
    """Keep only results whose series type matches.

    Only one source (Weeb Central) accepts a type parameter, so every other
    site silently ignored it -- searching "Manhwa" for "one piece" returned
    62 results, all of them manga. The type is now classified from the
    origin language and tags instead.

    Items whose type cannot be determined are kept: a source that reports no
    type would otherwise disappear entirely from a filtered search, which is
    a worse failure than showing an extra row.
    """
    wanted = str(wanted or "").strip()
    if not wanted or wanted.lower() in ("any", "all"):
        return results

    from ..sources.base import classify_type

    target = wanted.lower()
    kept = []
    for item in results:
        kind = (item.get("series_type") or item.get("type")
                or classify_type(item.get("original_language"),
                                 item.get("tags"),
                                 item.get("demographic")))
        if not kind:
            # Fall back to what the whole site hosts, for sources whose
            # search rows carry no per-title metadata at all.
            source_cls = SOURCES.get(item.get("source"))
            kind = getattr(source_cls, "default_series_type", None)
        if not kind or str(kind).lower() == target:
            kept.append(item)
    return kept


def _narrow_by_genres(results, extra_genres, match="all"):
    """Filter search hits by additional genres using their tags.

    Only applies to results that actually carry tags. A source that does not
    report them would otherwise vanish entirely from a multi-genre search.
    """
    wanted = [g.strip().lower() for g in extra_genres if g and g.strip()]
    if not wanted:
        return results
    need_all = str(match).lower() != "any"

    kept = []
    for item in results:
        tags = {str(t).strip().lower() for t in (item.get("tags") or [])}
        if not tags:
            kept.append(item)          # unknown, not disqualified
            continue
        hits = [g for g in wanted if g in tags]
        if (len(hits) == len(wanted)) if need_all else bool(hits):
            kept.append(item)
    return kept


def _safe_endpoint(func):
    """Wrap a bridge method so it can never raise into pywebview.

    Every public method here is called from JavaScript. pywebview marshals an
    exception across the native bridge, which on WebView2 surfaces as a
    rejected promise at best and can tear the view down at worst -- and the
    JS side has no way to distinguish "endpoint blew up" from "endpoint
    returned nothing". Of 102 public methods only 15 guarded themselves.

    Failures now come back as ``{"ok": False, "error": ...}``, which is the
    shape callApi() on the JS side already understands.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:                      # noqa: BLE001 - deliberate
            logger.exception("API call %s failed", func.__name__)
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    wrapper.__wrapped__ = func
    return wrapper


class _SafeApiMeta(type):
    """Apply :func:`_safe_endpoint` to every public method of the class.

    Done with a metaclass rather than by hand so a method added later is
    protected automatically -- the previous state of the file, where 87 of
    102 endpoints were unguarded, is exactly what hand-wrapping decays into.
    """

    def __new__(mcls, name, bases, namespace):
        for key, value in list(namespace.items()):
            if key.startswith("_") or not callable(value):
                continue
            if isinstance(value, (staticmethod, classmethod, property)):
                continue
            namespace[key] = _safe_endpoint(value)
        return super().__new__(mcls, name, bases, namespace)


class Api(metaclass=_SafeApiMeta):
    """Methods callable from JavaScript via window.pywebview.api.*"""

    def __init__(self):
        self.window = None
        self.engine = None          # most recent job, kept for back-compat
        self._thread = None
        self._sources = {}
        self._push_lock = threading.Lock()
        self._pending_events = []
        self._pending_progress = {}
        self._flush_timer = None
        # ---- multi-job download manager ----------------------------------
        # Several manga can download at once. Every job gets an id, and every
        # engine event is stamped with it, because chapter names are NOT
        # unique across manga -- two series both having "Chapter 01" was
        # enough to make one overwrite the other's progress.
        self._jobs = {}             # job id -> job record
        self._jobs_lock = threading.RLock()
        self._job_seq = 0
        self._cart = []             # queued jobs waiting for a free slot

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
        update_settings({"output_dir": root})

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

    # Covers whose CDN refuses hotlinks cannot be loaded by an <img> tag:
    # the GUI sends "no-referrer" globally because MangaDex swaps in a
    # placeholder otherwise, and Webtoons' pstatic.net answers 403 to any
    # request that does not carry a webtoons.com Referer. The two demands
    # are mutually exclusive in one document, so those covers are fetched
    # here -- with the right Referer -- and handed back as a data URI.
    # Bounded by BYTES, not entry count. A proxied cover is a base64 data URI
    # -- measured 116 KB for one Webtoons cover -- so the old 240-entry cap
    # held ~28 MB of RSS, and a source with larger art scaled that without
    # any ceiling. An OrderedDict gives proper LRU eviction instead of the
    # previous clear(), which threw away every cover the moment it filled.
    _COVER_CACHE = collections.OrderedDict()
    _COVER_CACHE_MAX_BYTES = 24 * 1024 * 1024
    #: Refuse to cache anything absurd; still returned, just not retained.
    _COVER_MAX_ITEM_BYTES = 4 * 1024 * 1024
    _COVER_LOCK = threading.Lock()

    @classmethod
    def _cache_cover(cls, url, data):
        """Store a cover, evicting least-recently-used entries by size."""
        if len(data) > cls._COVER_MAX_ITEM_BYTES:
            return
        with cls._COVER_LOCK:
            cls._COVER_CACHE.pop(url, None)
            cls._COVER_CACHE[url] = data
            total = sum(len(v) for v in cls._COVER_CACHE.values())
            while total > cls._COVER_CACHE_MAX_BYTES and len(cls._COVER_CACHE) > 1:
                _key, dropped = cls._COVER_CACHE.popitem(last=False)
                total -= len(dropped)

    def proxy_cover(self, url: str, source_id: str = None):
        """Fetch a hotlink-protected cover and return it as a data URI."""
        import base64

        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            return {"ok": False, "error": "unsupported url"}

        with self._COVER_LOCK:
            cached = self._COVER_CACHE.get(url)
            if cached is not None:
                self._COVER_CACHE.move_to_end(url)   # keep it warm
        if cached:
            return {"ok": True, "data": cached, "cached": True}

        try:
            source = self._source(source_id) if source_id else source_for_url(url)
            if source is None:
                return {"ok": False, "error": "unknown source"}
            response = source.fetch(url, max_retries=2)
            blob = response.content
            if not blob:
                return {"ok": False, "error": "empty response"}

            mime = (response.headers.get("Content-Type") or "").split(";")[0].strip()
            if not mime.startswith("image/"):
                mime = "image/jpeg"
            data = f"data:{mime};base64," + base64.b64encode(blob).decode("ascii")

            self._cache_cover(url, data)
            return {"ok": True, "data": data}
        except Exception as e:
            logger.warning("Cover proxy failed for %s: %s", url, e)
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
                # Keep only the newest progress per chapter -- but key on
                # (job, chapter). Keying on the chapter name alone meant two
                # manga downloading at once both reporting "Chapter 01"
                # collapsed into a single event, so one series' progress
                # silently replaced the other's.
                key = (event.get("job"), event.get("chapter"))
                self._pending_progress[key] = event
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
            genres = split_genres(f.get("genres") or f.get("genre"))
            genre = genres[0] if genres else ""
            match = (f.get("genre_match") or "all").lower()
            query = (query or "").strip()

            # pasting a URL jumps straight to that manga
            if query and detect_source(query) and "/" in query:
                return {"ok": True, "results": [], "url": query}

            if not query:
                return self.browse({
                    "source": source_id,
                    "genres": genres,
                    "genre_match": match,
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

            # Sources take one genre per request, so when several are asked
            # for alongside a text query the rest are applied to the tags on
            # the results. Items that do not report tags are kept: dropping
            # them would silently hide whole sources that omit them.
            if len(genres) > 1:
                results = _narrow_by_genres(results, genres[1:], match)
            results = _narrow_by_type(results, f.get("type"))

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
            # A genre may now be a list, or a comma separated string.
            genres = split_genres(o.get("genres") or o.get("genre"))
            genre = genres[0] if genres else None
            match = (o.get("genre_match") or "all").lower()
            sort = o.get("sort") or "Trending"
            page = max(1, int(o.get("page", 1) or 1))
            settings = load_settings()

            extra = {}
            if o.get("status") and o["status"] != "Any":
                extra["status"] = o["status"]

            if source_id in ("", "all"):
                if len(genres) > 1:
                    results = browse_multi(
                        genres, sort=sort, page=page, limit=24, match=match,
                        interleave=bool(settings.get("interleave_browse", True)),
                        **extra)
                else:
                    results = browse_all(
                        sort=sort, genre=genre, page=page, limit=12,
                        interleave=bool(settings.get("interleave_browse", True)),
                        **extra)
            else:
                source = self._source(source_id)
                if not getattr(source, "supports_browse", False):
                    return {"ok": True, "results": [], "browse": True,
                            "message": f"{source.name} cannot list trending titles"}
                if len(genres) > 1:
                    results = browse_multi(
                        genres, sort=sort, page=page, limit=32, match=match,
                        source_ids=[source_id], use_config=False,
                        interleave=False, **extra)
                else:
                    # a per-source genre id may differ from the shared label
                    results = source.browse(sort=sort, genre=genre, page=page,
                                            limit=32, **extra)

            results = features.apply_filters(results)
            if settings.get("dedupe_results", True) and source_id in ("", "all"):
                ranks = {row["id"]: row.get("rank", 100)
                         for row in appconfig.describe()}
                results = features.dedupe(results, ranks)

            return {"ok": True, "results": results, "browse": True,
                    "genre": genre, "genres": genres, "genre_match": match,
                    "sort": sort, "page": page}
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
                # Match on chapter number, not the raw label: several
                # sources append a release date that the site later edits,
                # which made downloaded chapters show as missing while still
                # counting toward the total.
                "downloaded": sorted(library.match_downloaded(url, chapters)),
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
        # Must go through the tolerant lookup: library keys are normalised,
        # so a raw URL (or one carrying ?query) can miss a real entry.
        entry = library.get_entry(url)
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

    # ------------------------------------------------- bookmark folders

    def get_bookmark_folders(self):
        try:
            return {"ok": True, **library.folders_with_contents()}
        except Exception as e:
            logger.exception("Folder listing failed")
            return {"ok": False, "error": str(e), "folders": [], "unfiled": []}

    def create_bookmark_folder(self, name: str, options: dict = None):
        o = options or {}
        return library.create_folder(name, colour=o.get("colour"),
                                     locked=o.get("locked"),
                                     blurred=o.get("blurred"))

    def update_bookmark_folder(self, folder_id: str, changes: dict = None):
        return library.update_folder(folder_id, **(changes or {}))

    def delete_bookmark_folder(self, folder_id: str, delete_bookmarks: bool = False):
        return library.delete_folder(folder_id, bool(delete_bookmarks))

    def move_bookmark(self, url: str, folder_id: str = ""):
        return library.set_bookmark_folder(url, folder_id or "")

    def bookmark_into(self, info: dict, folder_id: str = ""):
        """Bookmark a manga and file it in one step."""
        try:
            added = library.toggle_bookmark(info or {})
            if added and folder_id:
                library.set_bookmark_folder((info or {}).get("url"), folder_id)
            return {"ok": True, "bookmarked": added}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
        # Locked read-modify-write. Doing this in two steps let a concurrent
        # save (the folder picker, a theme click) overwrite the other's keys.
        return update_settings(settings or {})

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

    @staticmethod
    def _as_int(value, default, low=None, high=None):
        """Coerce a UI value to int, clamping. Never raises.

        Values arrive from JavaScript, where a cleared field is "" and a
        stale handler can send a string. int("abc") used to escape all the
        way out of _spawn() and kill the worker thread.
        """
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            number = int(default)
        if low is not None:
            number = max(low, number)
        if high is not None:
            number = min(high, number)
        return number

    @staticmethod
    def _as_float(value, default, low=None, high=None):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = float(default)
        if low is not None:
            number = max(low, number)
        if high is not None:
            number = min(high, number)
        return number

    def _build_options(self, options: dict):
        """Turn a raw options dict from JS into validated DownloadOptions."""
        settings = load_settings()
        opt = DownloadOptions(
            url=options.get("url", ""),
            selection=options.get("selection", "all"),
            output_dir=options.get("output_dir") or DEFAULT_SETTINGS["output_dir"],
            format=options.get("format", "cbz"),
            bundle=self._as_int(options.get("bundle"), 0, 0),
            chapter_workers=self._as_int(options.get("chapter_workers"), 3, 1, 8),
            image_workers=self._as_int(options.get("image_workers"), 6, 1, 10),
            delay=self._as_float(options.get("delay"), 0.5, 0.0, 60.0),
            retries=self._as_int(options.get("retries"), 5, 1, 10),
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
        return opt

    def max_concurrent_jobs(self):
        """How many manga may download at the same time."""
        try:
            value = int(load_settings().get("max_concurrent_jobs", 2) or 2)
        except (TypeError, ValueError):
            value = 2
        return max(1, min(5, value))

    def _active_jobs(self):
        return [j for j in self._jobs.values() if j["status"] == "running"]

    def _job_event(self, job_id):
        """An on_event callback that stamps every event with its job id.

        Without this the UI cannot tell two concurrent downloads apart:
        chapter names are not unique across manga, so "Chapter 01" from one
        series was overwriting "Chapter 01" from another.
        """
        def emit(event):
            record = self._jobs.get(job_id)
            event = dict(event)
            event["job"] = job_id
            if record:
                event.setdefault("job_title", record.get("title") or "")
            self._push(event)
        return emit

    def _run_job(self, job_id):
        """Body of a download thread."""
        record = self._jobs.get(job_id)
        if record is None:
            return
        engine = record["engine"]
        push = self._job_event(job_id)
        try:
            result = engine.run()
            with self._jobs_lock:
                # A user-requested stop is not a failure -- reporting it as
                # one made a deliberate cancel look like a broken download.
                if result.get("stopped"):
                    record["status"] = "stopped"
                elif result.get("ok"):
                    record["status"] = "done"
                else:
                    record["status"] = "failed"
                record["result"] = result
                if result.get("title"):
                    record["title"] = result["title"]
            push({"type": "finished", "result": result})
        except Exception as e:
            logger.exception("Download crashed")
            with self._jobs_lock:
                record["status"] = "failed"
                record["result"] = {"ok": False, "error": str(e)}
            push({"type": "error", "message": str(e)})
            push({"type": "finished", "result": {"ok": False, "error": str(e)}})
        finally:
            self._start_queued()

    def _spawn(self, entry):
        """Start one queued cart entry immediately. Caller holds the lock."""
        self._job_seq += 1
        job_id = f"job{self._job_seq}"
        opt = self._build_options(entry["options"])

        engine = DownloadEngine(opt, on_event=self._job_event(job_id))
        record = {
            "id": job_id,
            "title": entry.get("title") or opt.url,
            "url": opt.url,
            "source": opt.source or "",
            "cover": entry.get("cover") or "",
            "selection": opt.selection,
            "status": "running",
            "engine": engine,
            "result": None,
            "started": time.time(),
        }
        self._jobs[job_id] = record
        self.engine = engine          # back-compat for stop_download()

        thread = threading.Thread(target=self._run_job, args=(job_id,),
                                  daemon=True, name=f"mangadl-{job_id}")
        record["thread"] = thread
        self._thread = thread
        thread.start()

        self._push({"type": "job_started", "job": job_id,
                    "title": record["title"], "url": record["url"],
                    "cover": record["cover"], "source": record["source"]})
        return record

    def _start_queued(self):
        """Promote cart entries into running jobs while slots are free.

        A malformed entry is dropped with an error event rather than allowed
        to raise: this runs in the finally of a finished job's thread, so an
        escaping exception killed that thread and stalled the whole queue.
        """
        started = []
        with self._jobs_lock:
            limit = self.max_concurrent_jobs()
            while self._cart and len(self._active_jobs()) < limit:
                entry = self._cart.pop(0)
                try:
                    started.append(self._spawn(entry))
                except Exception as e:
                    logger.exception("Could not start a queued download")
                    title = entry.get("title") or (
                        entry.get("options") or {}).get("url") or "download"
                    self._push({"type": "error",
                                "message": f"Could not start {title}: {e}"})
        if started:
            self._flush()
        return started

    # ------------------------------------------------------------- cart

    def add_to_cart(self, options: dict):
        """Queue a manga for download. Starts at once if a slot is free."""
        options = options or {}
        if not (options.get("url") or "").strip():
            return {"ok": False, "error": "No manga URL"}

        entry = {
            "options": options,
            "title": options.get("title") or "",
            "cover": options.get("cover") or "",
        }
        with self._jobs_lock:
            # Refuse an exact duplicate that is already queued or running.
            url = options["url"]
            selection = options.get("selection", "all")
            for job in self._jobs.values():
                if (job["url"] == url and job["selection"] == selection
                        and job["status"] == "running"):
                    return {"ok": False, "error": "Already downloading",
                            "job": job["id"]}
            for queued in self._cart:
                if (queued["options"].get("url") == url
                        and queued["options"].get("selection", "all") == selection):
                    return {"ok": False, "error": "Already in the cart"}
            self._cart.append(entry)

        self._start_queued()
        return {"ok": True, "queued": len(self._cart),
                "active": len(self._active_jobs())}

    def get_cart(self):
        """Everything queued or running, for the downloads panel."""
        with self._jobs_lock:
            jobs = [{
                "id": j["id"], "title": j["title"], "url": j["url"],
                "source": j["source"], "cover": j["cover"],
                "selection": j["selection"], "status": j["status"],
            } for j in self._jobs.values()]
            queued = [{
                "title": q.get("title") or q["options"].get("url"),
                "url": q["options"].get("url"),
                "cover": q.get("cover", ""),
                "selection": q["options"].get("selection", "all"),
                "status": "queued",
            } for q in self._cart]
        return {"ok": True, "jobs": jobs, "queued": queued,
                "limit": self.max_concurrent_jobs()}

    def remove_from_cart(self, url: str, selection: str = None):
        """Drop a not-yet-started entry from the queue."""
        with self._jobs_lock:
            before = len(self._cart)
            self._cart = [
                q for q in self._cart
                if not (q["options"].get("url") == url
                        and (selection is None
                             or q["options"].get("selection", "all") == selection))
            ]
            removed = before - len(self._cart)
        return {"ok": True, "removed": removed}

    def clear_cart(self):
        with self._jobs_lock:
            count = len(self._cart)
            self._cart = []
        return {"ok": True, "removed": count}

    # --------------------------------------------------------- download

    def start_download(self, options: dict):
        """Start a download.

        Kept as the single-job entry point the UI has always used. It now
        routes through the cart so several manga can run at once, and
        returns the job id so the caller can track this one specifically.
        """
        options = options or {}
        if not (options.get("url") or "").strip():
            return {"ok": False, "error": "No manga URL"}

        with self._jobs_lock:
            if len(self._active_jobs()) >= self.max_concurrent_jobs():
                self._cart.append({
                    "options": options,
                    "title": options.get("title") or "",
                    "cover": options.get("cover") or "",
                })
                return {"ok": True, "queued": True,
                        "position": len(self._cart)}
            record = self._spawn({
                "options": options,
                "title": options.get("title") or "",
                "cover": options.get("cover") or "",
            })
        return {"ok": True, "job": record["id"]}

    def stop_download(self, job_id: str = None):
        """Stop one job, or every running job when no id is given."""
        with self._jobs_lock:
            if job_id:
                targets = [self._jobs[job_id]] if job_id in self._jobs else []
            else:
                targets = self._active_jobs()
                # a blanket stop should also empty the queue
                self._cart = []
            for job in targets:
                job["status"] = "stopping"

        for job in targets:
            try:
                job["engine"].stop()
            except Exception:
                logger.debug("Could not stop %s", job["id"], exc_info=True)

        self._flush()          # deliver whatever is queued before stopping
        return {"ok": True, "stopped": [j["id"] for j in targets]}

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
    def _on_closed():
        """Release background resources when the window closes.

        pywebview collects handler return values into a *set*, so a handler
        that returns a dict raises "unhashable type: 'dict'". This wrapper
        swallows the return value; api.shutdown() stays dict-returning for
        the JS bridge, which expects one.
        """
        try:
            api.shutdown()
        except Exception:
            logger.debug("shutdown handler failed", exc_info=True)

    try:
        window.events.closed += _on_closed
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
