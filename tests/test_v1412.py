"""Regression tests for v1.4.12 -- GUI crash hardening.

The GUI was described as "very prone to crashing". Four measured causes:

* 87 of 102 bridge endpoints had no try/except, so a Python exception was
  marshalled across the native bridge instead of returned as data;
* a malformed cart entry raised out of ``_spawn`` inside the *finally* of a
  finished job's thread, killing that thread and stalling the queue;
* the proxied-cover cache was bounded by entry count, not bytes, holding
  ~28 MB and scaling without a ceiling for sources with larger art;
* the JS side had no ``unhandledrejection`` handler, so a rejected call left
  a spinner running forever and told the user nothing.

Plus one plain bug the audit turned up: ``Invert`` called a function that
does not exist.
"""

import importlib
import inspect
import json
import os
import sys
import tempfile
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")
sys.path.insert(0, ROOT)


def web(name):
    with open(os.path.join(WEB, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    home = tempfile.mkdtemp()
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("USERPROFILE", home)

    import mangadl.config as appconfig
    import mangadl.features as features
    import mangadl.library as library
    import mangadl.passlock as passlock

    for module in (appconfig, passlock, features, library):
        importlib.reload(module)
    import mangadl.gui as gui
    importlib.reload(gui)
    yield home


# ================================================== bridge never raises


def test_every_endpoint_is_guarded():
    """Hand-wrapping decays: 87 of 102 methods had drifted unguarded."""
    from mangadl.gui import Api

    public = [n for n, _ in inspect.getmembers(Api, inspect.isfunction)
              if not n.startswith("_")]
    unguarded = [n for n in public
                 if not hasattr(getattr(Api, n), "__wrapped__")]
    assert public, "no endpoints found -- the scan is broken"
    assert unguarded == [], f"unguarded endpoints: {unguarded}"


@pytest.mark.parametrize("method, args", [
    ("queue_move", ("x", None)),
    ("get_library_entry", (None,)),
    ("set_filters", (None,)),
    ("mark_many_read", (None, None)),
    ("relocate_entry", (None, None)),
    ("proxy_cover", (None,)),
    ("remove_history", (None,)),
    ("move_bookmark", (None, None)),
])
def test_junk_arguments_return_an_error_instead_of_raising(method, args):
    """JavaScript sends nulls from cleared fields and strings from stale
    handlers. Those must come back as data, not as a bridge exception."""
    from mangadl.gui import Api

    api = Api()
    result = getattr(api, method)(*args)
    assert isinstance(result, dict), f"{method} returned {type(result).__name__}"


def test_the_error_shape_is_what_the_frontend_expects():
    from mangadl.gui import Api

    result = Api().queue_move("x", None)
    assert result["ok"] is False
    assert "error" in result and result["error"]


def test_guarding_does_not_swallow_good_return_values():
    from mangadl.gui import Api

    api = Api()
    assert api.get_settings()["theme"] == "midnight"
    assert api.get_cart()["ok"] is True


# ================================================ worker thread safety


def test_a_bad_cart_entry_cannot_kill_the_job_thread():
    """_start_queued runs in the finally of a finished job. An exception
    there killed the worker thread and stalled the whole queue."""
    from mangadl.gui import Api

    escaped = []
    original = threading.excepthook
    threading.excepthook = lambda a: escaped.append(a.exc_type.__name__)
    try:
        class FakeEngine:
            def run(self):
                return {"ok": True, "title": "A"}

            def stop(self):
                pass

        api = Api()
        api._jobs["job1"] = {
            "id": "job1", "title": "A", "url": "u", "source": "", "cover": "",
            "selection": "all", "status": "running", "engine": FakeEngine(),
            "result": None,
        }
        api._cart.append({"options": {"url": "https://x/a",
                                      "retries": "not-an-int"},
                          "title": "bad", "cover": ""})

        thread = threading.Thread(target=api._run_job, args=("job1",),
                                  daemon=True)
        thread.start()
        thread.join(5)
        time.sleep(0.3)

        assert api._jobs["job1"]["status"] == "done"
        assert escaped == [], f"exception escaped the worker thread: {escaped}"
    finally:
        threading.excepthook = original


@pytest.mark.parametrize("value, expected", [
    ("abc", 5), (None, 5), ("", 5), ("7", 7), (7.9, 7), (99, 10), (-3, 1),
])
def test_option_numbers_are_coerced_not_trusted(value, expected):
    """int('abc') used to escape all the way out of _spawn."""
    from mangadl.gui import Api

    assert Api._as_int(value, 5, 1, 10) == expected


def test_option_floats_are_coerced():
    from mangadl.gui import Api

    assert Api._as_float("abc", 0.5, 0.0, 60.0) == 0.5
    assert Api._as_float("2.5", 0.5, 0.0, 60.0) == 2.5
    assert Api._as_float(-1, 0.5, 0.0, 60.0) == 0.0


def test_build_options_survives_a_hostile_dict():
    from mangadl.gui import Api

    opt = Api()._build_options({
        "url": "https://x/a", "chapter_workers": "abc",
        "image_workers": None, "delay": "slow", "retries": [],
        "bundle": {},
    })
    assert 1 <= opt.chapter_workers <= 8
    assert 1 <= opt.image_workers <= 10
    assert opt.delay >= 0.0
    assert 1 <= opt.retries <= 10


def test_one_bad_entry_does_not_block_the_rest_of_the_queue():
    from mangadl.gui import Api

    api = Api()
    api._push = lambda event: None
    api._cart.append({"options": {"url": "https://x/a", "retries": "bad"},
                      "title": "bad", "cover": ""})
    api._start_queued()          # must not raise
    assert api._cart == [], "the bad entry should be consumed, not stuck"


# ==================================================== memory ceiling


def test_cover_cache_is_bounded_by_bytes():
    """A 116 KB data URI x 240 entries held ~28 MB, and grew unbounded for
    sources with larger art, because the cap counted entries."""
    from mangadl.gui import Api

    api = Api()
    api._COVER_CACHE.clear()
    blob = "data:image/jpeg;base64," + ("A" * 116_000)
    for i in range(600):
        api._cache_cover(f"u{i}", blob)

    total = sum(len(v) for v in api._COVER_CACHE.values())
    assert total <= api._COVER_CACHE_MAX_BYTES + len(blob)
    assert len(api._COVER_CACHE) < 600, "nothing was evicted"


def test_cover_cache_evicts_least_recently_used():
    """The old code called clear(), throwing away every cover at once."""
    from mangadl.gui import Api

    api = Api()
    api._COVER_CACHE.clear()
    blob = "d" * 1_000_000
    for i in range(30):
        api._cache_cover(f"u{i}", blob)
    # the newest survive, the oldest are gone
    assert "u29" in api._COVER_CACHE
    assert "u0" not in api._COVER_CACHE


def test_an_oversized_cover_is_not_retained():
    from mangadl.gui import Api

    api = Api()
    api._COVER_CACHE.clear()
    api._cache_cover("huge", "x" * (5 * 1024 * 1024))
    assert "huge" not in api._COVER_CACHE


# ================================================= frontend resilience


def test_global_error_handlers_exist():
    """Without these a rejected call left a spinner up and said nothing."""
    js = web("app.js")
    assert 'addEventListener("unhandledrejection"' in js
    assert "window.__mangadlErrorHandler" in js
    assert "function reportFailure" in js


def test_error_handler_clears_spinners():
    js = web("app.js")
    body = js[js.index("function reportFailure"):]
    body = body[:body.index("\n}")]
    assert "hidden" in body
    assert "toast" in body


def test_hot_paths_go_through_the_guarded_wrapper():
    """search/browse/get_manga hit twelve sites, so they are the likeliest
    to reject. callApi returns null rather than throwing."""
    js = web("app.js")
    for call in ('callApi("search"', 'callApi("browse"',
                 'callApi("get_manga"', 'callApi("get_sources"'):
        assert call in js, call
    assert "await api().get_manga(" not in js
    assert "await api().search(" not in js


def test_a_failed_search_shows_a_recoverable_state():
    js = web("app.js")
    body = js[js.index("const seq = ++searchSeq;"):]
    body = body[:body.index("renderCards")]
    assert "if (!res)" in body
    assert "Search failed" in body
    assert "Retry" in body


# ==================================================== the Invert bug


def test_invert_calls_a_function_that_exists():
    """renderChapters() was never defined -- the real name is
    renderChapterList(). Invert has thrown a ReferenceError on every click
    since it was added, so the rows never repainted."""
    js = web("app.js")
    assert "renderChapters()" not in js
    body = js[js.index('$("selectInvertBtn")'):]
    body = body[:body.index("});")]
    assert "renderChapterList()" in body


def test_no_helper_is_called_without_being_defined():
    """Catches the whole class of bug, not just this instance."""
    import re

    js = web("app.js")
    called = set(re.findall(r"(?<![\w.\"'])([a-zA-Z][A-Za-z0-9_]{3,})\s*\(", js))
    defined = set(re.findall(r"function\s+([A-Za-z0-9_]+)", js))
    defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=", js))

    # Browser globals share the app's camelCase shape (clearTimeout,
    # clearInterval, ...) so they have to be excluded explicitly.
    builtins = {
        "clearTimeout", "clearInterval", "setTimeout", "setInterval",
        "requestAnimationFrame", "cancelAnimationFrame", "showModal",
        "showPicker", "toggleAttribute", "reportError",
    }

    prefixes = ("render", "show", "load", "update", "apply", "sync", "toggle",
                "attach", "make", "begin", "reset", "clear", "pick", "report",
                "refresh", "collect", "fill")

    def looks_like_a_helper(name):
        return any(name.startswith(p) and len(name) > len(p)
                   and name[len(p)].isupper() for p in prefixes)

    missing = sorted(n for n in called - defined - builtins
                     if looks_like_a_helper(n))
    assert missing == [], f"called but never defined: {missing}"
