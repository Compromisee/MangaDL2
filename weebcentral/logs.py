"""File logging and crash-resume journal for WeebCentral Downloader.

- Rotating log file:  ~/.weebcentral/logs/weebcentral.log
- Job journal:        ~/.weebcentral/job.json   (present = interrupted job)
"""

import json
import logging
import os
import shutil
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.join(os.path.expanduser("~"), ".weebcentral")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "weebcentral.log")
JOURNAL_PATH = os.path.join(BASE_DIR, "job.json")

_configured = False


class _BridgeNoiseFilter(logging.Filter):
    """Drop pywebview .NET-bridge noise (harmless but extremely spammy).

    On Windows, Edge's accessibility/autofill layer enumerates the
    `window.native` object pywebview exposes, producing endless
    'Error while processing window.native...' / recursion errors.
    """

    _PATTERNS = (
        "Error while processing window.native",
        "maximum recursion depth exceeded",
        "CoreWebView2 can only be accessed from the UI thread",
        "CoreWebView2Controller members can only be accessed",
    )

    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:
            return True
        return not any(p in message for p in self._PATTERNS)


def quiet_pywebview():
    """Attach the noise filter to pywebview's logger (idempotent)."""
    pw = logging.getLogger("pywebview")
    if not any(isinstance(f, _BridgeNoiseFilter) for f in pw.filters):
        pw.addFilter(_BridgeNoiseFilter())


def setup_logging(level=logging.INFO):
    """Attach a rotating file handler to the root logger (idempotent)."""
    global _configured
    if _configured:
        return LOG_FILE
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        root = logging.getLogger()
        root.addHandler(handler)
        if root.level > level or root.level == logging.NOTSET:
            root.setLevel(level)
        _configured = True
    except OSError:
        pass
    return LOG_FILE


def log_info() -> dict:
    """Path and size of the current log file."""
    size = os.path.getsize(LOG_FILE) if os.path.isfile(LOG_FILE) else 0
    return {"path": LOG_FILE, "size": size, "exists": size > 0}


def export_log(dest_path: str) -> str:
    """Copy the log file (plus rotated parts, concatenated) to dest_path."""
    parts = [LOG_FILE + suffix for suffix in (".3", ".2", ".1", "")]
    parts = [p for p in parts if os.path.isfile(p)]
    if not parts:
        raise FileNotFoundError("No log file yet")
    if len(parts) == 1:
        shutil.copyfile(parts[0], dest_path)
    else:
        with open(dest_path, "wb") as out:
            for p in parts:
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, out)
    return dest_path


# --------------------------------------------------------------- journal


def write_journal(options_dict: dict, extra: dict = None) -> None:
    """Record an in-progress job so it can be resumed after a crash."""
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        data = {"options": options_dict}
        if extra:
            data.update(extra)
        tmp = JOURNAL_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, JOURNAL_PATH)
    except OSError:
        logging.getLogger(__name__).warning("Could not write job journal")


def read_journal() -> dict:
    try:
        with open(JOURNAL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and data.get("options") else None
    except (OSError, ValueError):
        return None


def clear_journal() -> None:
    try:
        os.remove(JOURNAL_PATH)
    except OSError:
        pass
