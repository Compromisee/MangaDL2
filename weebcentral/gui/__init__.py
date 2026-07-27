"""pywebview GUI for WeebCentral Downloader.

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

from ..downloader import DownloadEngine, DownloadOptions
from ..scraper import WeebCentralScraper
from .. import library
from .. import logs as wclogs

logger = logging.getLogger(__name__)

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".weebcentral", "settings.json")

DEFAULT_SETTINGS = {
    "output_dir": os.path.join(os.path.expanduser("~"), "Downloads", "WeebCentral"),
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
    "reader_path": "",              # e.g. path to Readest executable
    "open_folder_when_done": False,
    "name_single": "{title}",
    "name_chapter": "{title} - Chapter {chapter}",
    "name_range": "{title} - Chapters {start}-{end}",
}


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            settings.update(json.load(f))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


class Api:
    """Methods callable from JavaScript via window.pywebview.api.*"""

    def __init__(self):
        self.window = None
        self.scraper = WeebCentralScraper()
        self.engine = None
        self._thread = None

    # ------------------------------------------------------------- push

    def _push(self, event: dict):
        if self.window is not None:
            payload = json.dumps(event)
            try:
                self.window.evaluate_js(f"window.onEngineEvent({payload})")
            except Exception:
                pass

    # ------------------------------------------------------------ pages

    def search(self, query: str, filters: dict = None):
        try:
            f = filters or {}
            return {"ok": True, "results": self.scraper.search(
                query,
                sort=f.get("sort", "Best Match"),
                order=f.get("order", "Ascending"),
                official=f.get("official", "Any"),
                status=f.get("status"),
                series_type=f.get("type"),
            )}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_manga(self, url: str):
        try:
            info = self.scraper.get_manga_info(url)
            chapters = self.scraper.get_chapters(url)
            return {
                "ok": True,
                "info": info,
                "chapters": chapters,
                "downloaded": sorted(library.downloaded_chapters(url)),
                "bookmarked": library.is_bookmarked(url),
            }
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
            import webview
            dest = self.window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=f"weebcentral-{time.strftime('%Y%m%d-%H%M%S')}.log",
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
            import webview
            result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if result:
                return result[0] if isinstance(result, (list, tuple)) else result
        except Exception as e:
            logger.error("Folder dialog failed: %s", e)
        return None

    def choose_file(self):
        """Pick a file (used for the reader executable)."""
        try:
            import webview
            result = self.window.create_file_dialog(webview.OPEN_DIALOG)
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
        return {"ok": True}


def _web_asset_path():
    """Locate web/index.html both in source and in a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)),
                            "weebcentral", "gui", "web")
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    return os.path.join(base, "index.html")


def run_gui():
    wclogs.setup_logging()
    wclogs.quiet_pywebview()
    try:
        import webview
    except ImportError:
        print("pywebview is not installed. Run: pip install pywebview")
        return 1

    api = Api()
    html_path = _web_asset_path()
    window = webview.create_window(
        "WeebCentral Downloader",
        html_path,
        js_api=api,
        width=1180,
        height=780,
        min_size=(920, 620),
        background_color="#16161e",
    )
    api.window = window

    def _on_loaded():
        # Remove the .NET bridge object pywebview injects on Windows.
        # We never use window.native, and Edge's accessibility/autofill
        # layer walks it recursively, flooding the console with
        # "Error while processing window.native..." errors.
        try:
            window.evaluate_js(
                "try { delete window.native; window.native = undefined; } catch(e) {}"
            )
        except Exception:
            pass

    window.events.loaded += _on_loaded
    webview.start(debug=False)
    return 0
