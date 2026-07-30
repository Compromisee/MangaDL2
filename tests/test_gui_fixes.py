"""Regression tests for the reported crash, covers, lock order, radii and
download-location persistence."""

import importlib
import os
import re
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")


def read(path):
    return open(path, encoding="utf-8").read()


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    home = tempfile.mkdtemp()
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("USERPROFILE", home)
    yield home


# ============================ 1. unhashable type: 'dict' on window close


def test_closed_handler_returns_nothing():
    """pywebview does `return_values.add(handler())` into a *set*, so any
    handler returning a dict raises "unhashable type: 'dict'"."""
    source = read(os.path.join(ROOT, "mangadl", "gui", "__init__.py"))
    assert "window.events.closed += _on_closed" in source
    assert "window.events.closed += api.shutdown" not in source

    # Strip the docstring before checking: it legitimately explains the
    # return-value problem, so a naive substring search matches its prose.
    handler = source[source.index("def _on_closed():"):]
    handler = handler[:handler.index("window.events.closed")]
    body = re.sub(r'""".*?"""', "", handler, flags=re.S)
    # [^\S\n] = whitespace except newline. Plain \s spans newlines, so a bare
    # "return" followed by the next statement matched and the test failed on
    # correct code -- an early bare return is exactly what a guard clause is.
    assert not re.search(r"^[^\S\n]+return[^\S\n]+\S", body, re.M)


def test_shutdown_result_would_break_the_event_system():
    """Guards the reason for the wrapper: shutdown() must stay dict-returning
    for the JS bridge, so it cannot be attached to the event directly."""
    import mangadl.gui as gui
    importlib.reload(gui)

    api = gui.Api()
    assert isinstance(api.shutdown(), dict)
    with pytest.raises(TypeError):
        {api.shutdown()}          # exactly what pywebview does


def test_wrapped_handler_is_set_safe():
    import mangadl.gui as gui
    importlib.reload(gui)

    api = gui.Api()

    def on_closed():
        try:
            api.shutdown()
        except Exception:
            pass

    assert {on_closed()} == {None}     # no TypeError


def test_loaded_handler_also_returns_none():
    source = read(os.path.join(ROOT, "mangadl", "gui", "__init__.py"))
    handler = source[source.index("def _on_loaded():"):]
    handler = handler[:handler.index("window.events.loaded")]
    assert not re.search(r"^\s+return\s+\S", handler, re.M)


# ================================================ 2. Natomanga covers


def test_cover_host_is_never_rewritten():
    """Natomanga's cover hosts are shards, not mirrors.

    v1.4.1 assumed they were interchangeable and rewrote a cover onto every
    sibling host as a fallback. Re-measuring in v1.4.4 disproved it: over ten
    consecutive search covers the host named in the markup was 200 10/10
    while the siblings managed 3/10, 1/10 and 6/10 -- e.g.
    /thumb/naruto.webp is 200 on img-r1 and a hard 404 on img-r2. Rewriting
    the host therefore sends the UI to guaranteed 404s, so the URL from the
    page must be the only candidate.
    """
    from mangadl.sources.natomanga import NatomangaSource

    url = "https://img-r1.2xstorage.com/thumb/naruto.webp"
    assert NatomangaSource.cover_mirrors(url) == [url]


def test_cover_mirrors_handle_a_foreign_host():
    from mangadl.sources.natomanga import NatomangaSource

    url = "https://storage.waitst.com/thumb/x.webp"
    assert NatomangaSource.cover_mirrors(url) == [url]


@pytest.mark.parametrize("value", [None, "", "not a url"])
def test_cover_mirrors_degrade_safely(value):
    from mangadl.sources.natomanga import NatomangaSource

    result = NatomangaSource.cover_mirrors(value)
    assert result == ([] if not value else [value])


def test_frontend_walks_the_mirror_list():
    js = read(os.path.join(WEB, "app.js"))
    body = js[js.index("function attachCover"):]
    body = body[:body.index("\nfunction renderCards")]
    assert "cover_mirrors" in body
    assert "tryNext" in body
    assert 'addEventListener("error", tryNext)' in body


# =================================== 3. passcode must gate everything


def test_lock_runs_before_any_data_loads():
    js = read(os.path.join(WEB, "app.js"))
    boot = js[js.index("whenReady(async () => {"):]

    lock_at = boot.index('bootStep("lock"')
    for later in ('bootStep("settings"', 'bootStep("sources"',
                  'bootStep("stats"', 'get_library'):
        assert lock_at < boot.index(later), f"{later} must not precede the lock"


def test_boot_waits_for_the_unlock():
    js = read(os.path.join(WEB, "app.js"))
    boot = js[js.index("whenReady(async () => {"):]
    assert "waitForUnlock()" in boot
    assert 'classList.contains("locked")' in boot


def test_unlocking_resolves_the_waiters():
    js = read(os.path.join(WEB, "app.js"))
    block = js[js.index("function showLock"):]
    block = block[:block.index("\n}") + 2]
    assert "_unlockResolvers" in block


def test_lock_check_is_not_duplicated_later_in_boot():
    js = read(os.path.join(WEB, "app.js"))
    boot = js[js.index("whenReady(async () => {"):]
    boot = boot[:boot.index("doSearch(true);")]
    assert boot.count('bootStep("lock"') == 1


# ============================================= 4. corner rounding


def test_radius_scale_is_defined():
    css = read(os.path.join(WEB, "style.css"))
    for token in ("--radius-sm", "--radius-md", "--radius-lg", "--radius-xl"):
        assert token in css


def test_corner_radii_snap_to_the_scale():
    """Rounding had drifted to 13 ad-hoc px values, which read as sloppy
    across the settings panels."""
    css = read(os.path.join(WEB, "style.css"))
    values = set(re.findall(r"border-radius:\s*([^;]+);", css))

    # "inherit" is a fill matching the rounded track it sits in -- it cannot
    # drift from the scale, because it has no value of its own.
    allowed_px = {"3px", "999px", "50%", "4px 4px 2px 2px", "inherit"}
    stray = set()
    for value in values:
        # the square-corners mode legitimately forces 0 / 50% with !important
        cleaned = value.replace("!important", "").strip()
        if cleaned in ("0", "0px", "50%"):
            continue
        if cleaned.startswith("var(--radius") or cleaned in allowed_px:
            continue
        stray.add(cleaned)
    assert stray == set(), f"unmapped radii: {stray}"


def test_settings_inputs_use_the_scale():
    css = read(os.path.join(WEB, "style.css"))
    block = css[css.index('.settings-card input[type="text"],'):]
    block = block[:block.index("}")]
    assert "var(--radius" in block


# ================================ 5. download location saved to JSON


def test_choosing_a_folder_persists_it():
    js = read(os.path.join(WEB, "app.js"))
    block = js[js.index('$("browseBtn").addEventListener'):]
    block = block[:block.index("async function saveOutputDir")]
    assert "saveOutputDir(folder)" in block


def test_save_helper_writes_to_settings():
    js = read(os.path.join(WEB, "app.js"))
    helper = js[js.index("async function saveOutputDir"):]
    helper = helper[:helper.index("\n}") + 2]
    assert 'callApi("set_settings"' in helper
    assert "output_dir" in helper


def test_typing_a_path_also_saves():
    js = read(os.path.join(WEB, "app.js"))
    assert '$("outputDir").addEventListener("change"' in js


def test_settings_round_trip_through_disk():
    """The value must actually land in settings.json, not just in memory."""
    import mangadl.gui as gui
    importlib.reload(gui)

    api = gui.Api()
    api.set_settings({"output_dir": "/tmp/chosen/place"})

    importlib.reload(gui)          # fresh read from disk
    assert gui.load_settings()["output_dir"] == "/tmp/chosen/place"


def test_output_dir_survives_alongside_other_settings():
    import mangadl.gui as gui
    importlib.reload(gui)

    api = gui.Api()
    api.set_settings({"output_dir": "/a/b", "theme": "plum"})
    settings = gui.load_settings()
    assert settings["output_dir"] == "/a/b"
    assert settings["theme"] == "plum"
