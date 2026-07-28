"""Regression tests for: search Enter, lock timing/UI, square corners and the
collapsible side rail."""

import importlib
import os
import re
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")


def read(name):
    return open(os.path.join(WEB, name), encoding="utf-8").read()


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    home = tempfile.mkdtemp()
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("USERPROFILE", home)
    yield home


# ================================================ search not working


def test_datalist_is_gone():
    """An open <datalist> popup swallows Enter in WebView2, so keydown never
    reached the handler and only the Search button worked."""
    html = read("index.html")
    assert "<datalist" not in html
    assert 'list="searchSuggestions"' not in html


def test_enter_is_handled_on_keydown_and_keyup():
    js = read("app.js")
    assert '$("searchInput").addEventListener("keydown", submitSearch)' in js
    assert '$("searchInput").addEventListener("keyup", submitSearch)' in js


def test_enter_cannot_double_fire():
    """keydown and keyup both call submitSearch, so it must debounce."""
    js = read("app.js")
    body = js[js.index("function submitSearch"):]
    body = body[:body.index("\n}") + 2]
    assert "_lastEnter" in body
    assert "preventDefault" in body


def test_suggestions_use_a_custom_list():
    html, js = read("index.html"), read("app.js")
    assert 'id="suggestBox"' in html
    assert "suggest-item" in js
    assert ".suggest-box" in read("style.css")


def test_no_dangling_reference_to_the_removed_datalist():
    js = read("app.js")
    assert 'searchSuggestions' not in js


# ============================================ lock shows up too late


def test_overlay_is_painted_on_the_first_frame():
    """Previously it started hidden and only appeared after lock_status
    returned, so a protected app was briefly readable."""
    html = read("index.html")
    css = read("style.css")
    assert 'class="lock-overlay lock-pending"' in html
    assert 'class="lock-overlay hidden"' not in html
    assert ".lock-overlay.lock-pending { display: flex !important; }" in css


def test_pending_class_is_cleared_once_status_is_known():
    js = read("app.js")
    body = js[js.index("async function checkLock"):]
    body = body[:body.index("\n}") + 2]
    assert 'classList.remove("lock-pending")' in body
    # both outcomes must settle, or the app stays covered forever
    assert body.count("settle(") >= 3


def test_lock_ui_has_reveal_attempts_and_cooldown():
    html, js = read("index.html"), read("app.js")
    assert 'id="lockEyeBtn"' in html
    assert 'id="lockAttempts"' in html
    assert 'id="lockBtnText"' in html
    assert "function lockCooldown" in js
    assert "function showAttempts" in js


def test_wrong_passcode_shakes_the_panel():
    js = read("app.js")
    css = read("style.css")
    assert 'classList.add("shake")' in js
    assert "@keyframes lockShake" in css


def test_cooldown_disables_the_input():
    js = read("app.js")
    body = js[js.index("function lockCooldown"):]
    body = body[:body.index("\n}\n") + 3]
    assert "input.disabled = true" in body


# ============================================== square corners mode


def test_square_mode_zeroes_the_scale():
    css = read("style.css")
    block = css[css.index('[data-corners="square"] {'):]
    block = block[:block.index("}")]
    for token in ("--radius-sm", "--radius-md", "--radius-lg", "--radius-xl"):
        assert f"{token}: 0px" in block


def test_square_mode_flattens_pills_too():
    """Pills use 999px directly, so the variables alone do not cover them."""
    css = read("style.css")
    assert '[data-corners="square"] .btn' in css
    assert '[data-corners="square"] .switch > span' in css


def test_square_mode_keeps_true_circles():
    """Spinners and the lock badge must stay round or they look broken."""
    css = read("style.css")
    assert '[data-corners="square"] .spinner' in css
    assert "border-radius: 50% !important" in css


def test_corners_setting_exists_and_persists():
    html, js = read("index.html"), read("app.js")
    assert 'id="setCorners"' in html
    assert 'callApi("set_settings", { corners: value })' in js
    assert 'setAttribute("data-corners"' in js


def test_corners_default_is_rounded():
    import mangadl.gui as gui
    importlib.reload(gui)
    assert gui.DEFAULT_SETTINGS["corners"] == "rounded"


# ================================================ collapsible rail


def test_rail_is_narrower_by_default():
    css = read("style.css")
    block = css[css.index(".rail {"):]
    block = block[:block.index("}")]
    width = int(re.search(r"width:\s*(\d+)px", block).group(1))
    assert width <= 64, f"rail is still {width}px"


def test_rail_expands():
    css = read("style.css")
    assert "body.rail-open .rail" in css
    assert 'id="railToggle"' in read("index.html")


def test_rail_state_persists():
    js = read("app.js")
    assert "rail_expanded" in js
    assert "function applyRailState" in js


def test_rail_default_is_collapsed():
    import mangadl.gui as gui
    importlib.reload(gui)
    assert gui.DEFAULT_SETTINGS["rail_expanded"] is False


def test_rail_settings_round_trip():
    import mangadl.gui as gui
    importlib.reload(gui)
    api = gui.Api()
    api.set_settings({"rail_expanded": True, "corners": "square"})
    importlib.reload(gui)
    saved = gui.load_settings()
    assert saved["rail_expanded"] is True
    assert saved["corners"] == "square"


def test_reduced_motion_covers_the_new_animations():
    css = read("style.css")
    tail = css[css.index("@keyframes lockShake"):]
    assert "prefers-reduced-motion" in tail


def test_overlay_cannot_strand_the_app():
    """Regression: painting the overlay on the first frame meant that if the
    bridge never answered (no pywebview, crashed handler, hung call) the app
    stayed covered forever and nothing was clickable."""
    js = read("app.js")
    assert "function clearLockPending" in js
    assert "setTimeout(clearLockPending" in js

    body = js[js.index("function clearLockPending"):]
    body = body[:body.index("\n}") + 2]
    # removing .lock-pending alone leaves .lock-overlay's display:flex active
    assert 'classList.add("hidden")' in body
    assert 'classList.contains("locked")' in body


def test_first_frame_uses_a_remembered_lock_state():
    """Only cover the UI up-front when a passcode was set last run, so an
    unprotected app never flashes an overlay it does not need."""
    js = read("app.js")
    assert "LOCK_HINT_KEY" in js
    assert "localStorage.getItem(LOCK_HINT_KEY)" in js
    assert "localStorage.setItem(LOCK_HINT_KEY" in js


def test_lock_hint_write_is_guarded():
    """localStorage throws in some embedded/private contexts."""
    js = read("app.js")
    block = js[js.index("localStorage.setItem(LOCK_HINT_KEY"):]
    block = block[:block.index("if (!st")]
    assert "catch" in block
