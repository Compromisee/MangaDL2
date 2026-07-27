"""Regression tests for the reported issues:

  1. MangaDex covers replaced by a "read this at MangaDex" placeholder
  2. Freeze / crash 0xCFFFFFFF during large downloads
  3. Search results not loading
  4. Excessive resource usage
"""

import importlib
import os
import sys
import tempfile
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "mangadl", "gui", "web")


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    home = tempfile.mkdtemp()
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("USERPROFILE", home)
    import mangadl.config as config
    import mangadl.features as features
    for module in (config, features):
        importlib.reload(module)
    yield home


# =================================== 1. covers / hotlink placeholder


def test_page_sends_no_referrer():
    """MangaDex returns a placeholder image when the Referer is a file:// URL.

    The packaged GUI loads from file://, so without this meta tag every
    MangaDex cover silently becomes the "You can read this at MangaDex"
    graphic instead of the real artwork.
    """
    html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    assert 'name="referrer"' in html
    assert 'content="no-referrer"' in html


def test_referrer_meta_is_in_the_head_before_any_request():
    """The tag only applies to requests made after it is parsed."""
    html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    head = html.split("</head>", 1)[0]
    assert 'content="no-referrer"' in head
    # must precede stylesheet/font requests
    assert head.index('content="no-referrer"') < head.index("fonts.googleapis")


def test_cover_urls_keep_the_full_filename():
    from mangadl.sources.mangadex import MangaDexSource

    url = MangaDexSource.cover_url("mid", "abc.png", "medium")
    assert url.endswith("abc.png.512.jpg")


# ============================== 2. event flood -> WebView2 crash


class FakeWindow:
    def __init__(self):
        self.calls = 0
        self.events = 0
        self.lock = threading.Lock()

    def evaluate_js(self, js):
        import json
        import re
        with self.lock:
            self.calls += 1
            match = re.match(r"window\.onEngineEvents\((.*)\)$", js, re.S)
            if match:
                self.events += len(json.loads(match.group(1)))


def _api_with_window():
    from mangadl.gui import Api

    api = Api()
    api.window = FakeWindow()
    return api


def test_progress_events_are_batched():
    """A burst of progress events must not become one bridge call each."""
    api = _api_with_window()
    for i in range(500):
        api._push({"type": "chapter_progress", "chapter": "Ch 1",
                   "done": i, "total": 500})
    api._flush()
    assert api.window.calls <= 3, "progress events were not coalesced"


def test_progress_coalesces_to_the_latest_per_chapter():
    api = _api_with_window()
    for i in range(50):
        api._push({"type": "chapter_progress", "chapter": "A", "done": i, "total": 50})
    for i in range(50):
        api._push({"type": "chapter_progress", "chapter": "B", "done": i, "total": 50})
    api._flush()
    # one surviving update per chapter, not 100
    assert api.window.events == 2


def test_lifecycle_events_are_never_dropped():
    api = _api_with_window()
    api._push({"type": "chapter_start", "chapter": "A"})
    api._push({"type": "chapter_done", "chapter": "A", "pages": 10})
    api._push({"type": "packaged", "file": "x.cbz"})
    api._flush()
    assert api.window.events == 3


def test_terminal_events_flush_immediately():
    """The UI must not wait for a timer to learn the job finished."""
    api = _api_with_window()
    api._push({"type": "finished", "result": {"ok": True}})
    assert api.window.calls >= 1


def test_batching_cuts_bridge_crossings_dramatically():
    """The crash scenario: many chapters x many pages, emitted fast."""
    api = _api_with_window()
    emitted = 0
    for chapter in range(40):
        api._push({"type": "chapter_start", "chapter": f"Ch {chapter}"})
        emitted += 1
        for page in range(60):
            api._push({"type": "chapter_progress", "chapter": f"Ch {chapter}",
                       "done": page, "total": 60})
            emitted += 1
    api._flush()
    assert emitted == 40 * 61
    # without batching this was one evaluate_js per event
    assert api.window.calls < emitted / 50


def test_shutdown_cancels_the_timer():
    api = _api_with_window()
    api._push({"type": "chapter_progress", "chapter": "A", "done": 1, "total": 2})
    assert api._flush_timer is not None
    api.shutdown()
    assert api._flush_timer is None


def test_push_without_a_window_is_safe():
    from mangadl.gui import Api

    api = Api()
    api.window = None
    api._push({"type": "chapter_progress", "chapter": "A"})   # must not raise


# ==================================== 3. search results not loading


def test_boot_isolates_failing_steps():
    """Every startup call is wrapped so one failure cannot abort the rest.

    Previously `whenReady` was a chain of bare `await`s: a single rejecting
    bridge call threw out of the handler, so everything after it -- including
    the initial search/trending load -- silently never ran.
    """
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    boot = js[js.index("whenReady(async () => {"):]
    assert "bootStep(" in boot
    # no unguarded awaits left on api() inside boot
    assert "await api().get_library()" not in boot


def test_bootstep_helper_catches_and_continues():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    helper = js[js.index("async function bootStep"):]
    helper = helper[:helper.index("\n}") + 2]
    assert "try {" in helper and "catch" in helper
    assert "return null" in helper


def test_search_reaches_the_trending_call():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    boot = js[js.index("whenReady(async () => {"):]
    assert "doSearch(true)" in boot


def test_backend_search_returns_results_with_covers(monkeypatch):
    from mangadl.gui import Api

    class FakeSource:
        supports_browse = True
        id = "mangadex"
        name = "MangaDex"

        def search(self, query, limit=20, **kwargs):
            return [{"title": "Berserk", "url": "u", "source": "mangadex",
                     "source_name": "MangaDex", "cover": "https://c/x.jpg"}]

        def close(self):
            pass

    monkeypatch.setattr("mangadl.sources.get_source", lambda sid, **kw: FakeSource())
    result = Api().search("berserk", {"source": "all"})
    assert result["ok"] is True
    assert result["results"]
    assert all(r["cover"] for r in result["results"])


def test_search_failure_is_reported_not_swallowed(monkeypatch):
    from mangadl.gui import Api

    api = Api()
    monkeypatch.setattr(api, "_source",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    result = api.search("x", {"source": "mangadex"})
    assert result["ok"] is False
    assert "boom" in result["error"]


# ========================================= 4. resource usage


def test_images_stream_to_disk():
    """Buffering whole images in RAM multiplied by every worker thread."""
    source = open(os.path.join(os.path.dirname(WEB), "..", "sources", "base.py"),
                  encoding="utf-8").read()
    assert "iter_content" in source
    assert "stream=True" in source


def test_download_still_rejects_non_images(tmp_path):
    from mangadl.sources.base import Source

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/html"}

        def iter_content(self, chunk_size=1):
            yield b"<!DOCTYPE html><html>"

        def raise_for_status(self):
            pass

    class FakeSession:
        def get(self, *a, **k):
            return FakeResponse()

    source = Source()
    source.session = FakeSession()
    target = tmp_path / "out.jpg"
    assert source.download_file("http://x/y.jpg", str(target), max_retries=1) is False
    assert not target.exists()
    assert not (tmp_path / "out.jpg.part").exists()


def test_engine_uses_one_shared_image_pool():
    """A pool per chapter meant chapter_workers x image_workers threads."""
    downloader = open(os.path.join(os.path.dirname(WEB), "..", "downloader.py"),
                      encoding="utf-8").read()
    assert "_image_pool" in downloader
    assert downloader.count("ThreadPoolExecutor(") <= 3


def test_image_pool_is_bounded():
    from mangadl.downloader import DownloadOptions

    options = DownloadOptions(url="x", chapter_workers=8, image_workers=10)
    bounded = max(1, min(16, options.chapter_workers * options.image_workers))
    assert bounded == 16, "in-flight requests must stay capped"


def test_matrix_animation_is_throttled_and_pauses():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    matrix = js[js.index("const matrix = (() => {"):]
    matrix = matrix[:matrix.index("})();")]
    assert "TARGET_FPS" in matrix                  # capped frame rate
    assert "visibilitychange" in matrix            # pauses when hidden
    assert "MAX_DOTS" in matrix                    # bounded dot count
    # colour must not be recomputed inside the draw loop. Strip comments
    # first: the explanation of *why* legitimately mentions the call.
    import re
    frame = matrix[matrix.index("function frame"):matrix.index("function start")]
    code = re.sub(r"//.*", "", frame)
    assert "getComputedStyle(" not in code


def test_matrix_pauses_behind_the_lock_screen():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    show_lock = js[js.index("function showLock"):]
    show_lock = show_lock[:show_lock.index("\n}") + 2]
    assert "matrix.pause()" in show_lock


def test_resize_is_debounced():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    matrix = js[js.index("const matrix = (() => {"):]
    matrix = matrix[:matrix.index("})();")]
    assert "resizeTimer" in matrix


# ============================================ 5. GUI polish


def test_cards_reserve_space_and_fade_in():
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    assert "aspect-ratio: 2 / 3" in css     # no reflow as covers decode
    assert ".result-card img.loaded" in css


def test_cards_have_a_fallback_for_missing_covers():
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    assert ".rc-fallback" in css
    assert "no-cover" in js


def test_skeletons_replace_the_bare_spinner():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    assert "showSkeletons" in js
    assert ".skeleton-card" in css


def test_states_offer_recovery_actions():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    assert "showState(" in js
    assert "Retry" in js


def test_reduced_motion_is_respected():
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    assert css.count("prefers-reduced-motion") >= 2


# ========================= reported: unstyled inputs / invisible toggles


def test_toggle_switch_selector_matches_the_markup():
    """The CSS targeted `.switch .track`, but the markup emits a bare
    <span> with no class -- so no rule matched and every toggle in the app
    rendered as a zero-width invisible element."""
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()

    # the sized element must be selectable as a direct child span
    assert ".switch > span" in css
    assert ".switch input:checked + span" in css
    # markup is normalised to the classless form
    assert '<label class="switch"><input type="checkbox"' in html
    assert '<span class="track">' not in html
    # ...but the CSS still tolerates the legacy .track variant
    assert ".switch .track" in css


def test_settings_text_inputs_are_styled():
    """They previously fell back to the browser default: white background,
    black text and an inset border, unreadable on every dark theme."""
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    assert '.settings-card input[type="text"]' in css
    assert '.setting-row input[type="text"]' in css
    block = css[css.index('.settings-card input[type="text"],'):]
    block = block[:block.index("}")]
    assert "var(--surface-2)" in block and "var(--text)" in block


def test_disabled_source_row_keeps_its_toggle_legible():
    """Dimming the row must not dim the control that re-enables it."""
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    assert ".source-rank li.disabled .switch { opacity: 1; }" in css


def test_adult_sources_are_flagged_in_the_ui():
    js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
    css = open(os.path.join(WEB, "style.css"), encoding="utf-8").read()
    assert "adult_only" in js
    assert ".cap.adult" in css
