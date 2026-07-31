"""v1.4.24 regression tests.

Covers, in the order the issues were reported:

* closing to tray must not end the process
* the stylesheet must not be blocked by a remote font CDN
* the bouncing search icon must not be clipped by its container
* the queue must theme itself instead of hardcoding dark colours
* the duplicated "Active chapters" panel must be gone
* advanced queue logging
* the contribution calendar and the source carousel

The browser tests skip automatically without Playwright.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")


def read(path):
    return open(path, encoding="utf-8").read()


# ============================================================ system tray


FAKE_PYSTRAY = textwrap.dedent("""
    import sys, threading, types
    ps = types.ModuleType("pystray")
    class Menu:
        SEPARATOR = object()
        def __init__(self, *a): pass
    class MenuItem:
        def __init__(self, *a, **k): pass
    class Icon:
        def __init__(self, *a, **k): self._s = threading.Event()
        def run(self): self._s.wait()
        def stop(self): self._s.set()
        def update_menu(self): pass
        def notify(self, *a, **k): pass
    ps.Menu, ps.MenuItem, ps.Icon = Menu, MenuItem, Icon
    sys.modules["pystray"] = ps
""")


def run_child(body, timeout=6):
    """Run a snippet in a real subprocess; report whether it stayed alive."""
    code = ('import sys\nsys.path.insert(0, %r)\n' % ROOT) + FAKE_PYSTRAY + body
    env = dict(os.environ, HOME=tempfile.mkdtemp())
    proc = subprocess.Popen([sys.executable, "-c", code], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    started = time.time()
    try:
        out, _ = proc.communicate(timeout=timeout)
        return {"alive": False, "seconds": time.time() - started,
                "out": out, "rc": proc.returncode}
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return {"alive": True, "seconds": time.time() - started, "out": out}


FAKE_WEBVIEW = textwrap.dedent("""
    import types
    from webview.event import Event, EventContainer
    wv = types.ModuleType("webview")
    class FakeWindow:
        def __init__(self):
            self.events = EventContainer()
            self.events.closed = Event(self)
            self.events.closing = Event(self, True)
            self.events.loaded = Event(self)
            self.hidden = False
        def hide(self): self.hidden = True
        def show(self): self.hidden = False
        def restore(self): pass
        def destroy(self): pass
        def evaluate_js(self, *a, **k): pass
    WIN = FakeWindow()
    wv.create_window = lambda *a, **k: WIN
    def start(*a, **k):
        WIN.events.closing.set()
        WIN.events.closed.set()
        print("loop-returned", flush=True)
    wv.start = start
    wv.FileDialog = None
    wv.FOLDER_DIALOG = wv.OPEN_DIALOG = wv.SAVE_DIALOG = 0
    sys.modules["webview"] = wv
""")


def test_closing_to_tray_does_not_end_the_process():
    """The reported bug: minimise-to-tray hid the window and the app died.

    Root cause: the tray icon runs on a *daemon* thread, as does every
    worker, so once webview.start() returned the interpreter exited and took
    the downloads with it. Measured before the fix: 0.06s to exit.
    """
    result = run_child(FAKE_WEBVIEW + textwrap.dedent("""
        from mangadl.config import update_settings
        update_settings({"minimize_to_tray": True})
        import mangadl.gui as g
        g.Api.get_progress = lambda self: {"active": 1, "queued": 0, "jobs": []}
        g.run_gui()
        print("run_gui-returned", flush=True)
    """), timeout=5)
    assert "loop-returned" in result["out"]
    assert result["alive"], (
        "the process exited after the GUI loop returned; the tray is not "
        f"holding it open (exited in {result['seconds']:.2f}s)")


def test_quit_from_the_tray_lets_the_process_exit():
    """The hold must not become a hang: Quit has to end it."""
    result = run_child(textwrap.dedent("""
        import threading
        from mangadl.tray import TrayController
        from mangadl.gui import _hold_for_tray
        class Api:
            _really_quitting = False
            def get_progress(self): return {"active": 5, "queued": 0}
            def shutdown(self): pass
        tray = TrayController(callbacks={"summary": lambda: {"active": 5}})
        tray.start()
        threading.Timer(0.6, tray._on_quit).start()
        _hold_for_tray(Api(), tray)
        print("released", flush=True)
    """), timeout=6)
    assert not result["alive"], "Quit did not release the main thread"
    assert "released" in result["out"]


def test_an_idle_hidden_app_exits_instead_of_lingering():
    """With no downloads left there is nothing to stay alive for."""
    result = run_child(textwrap.dedent("""
        from mangadl.tray import TrayController
        from mangadl.gui import _hold_for_tray
        class Api:
            _really_quitting = False
            def get_progress(self): return {"active": 0, "queued": 0}
            def shutdown(self): pass
        tray = TrayController(callbacks={"summary": lambda: {"active": 0}})
        tray.start()
        _hold_for_tray(Api(), tray)
        print("released", flush=True)
    """), timeout=6)
    assert not result["alive"]


def test_no_tray_means_no_hold():
    """Without a tray the app must exit exactly as it always did."""
    result = run_child(textwrap.dedent("""
        from mangadl.gui import _hold_for_tray
        class Api:
            _really_quitting = False
            def get_progress(self): return {"active": 9}
            def shutdown(self): pass
        _hold_for_tray(Api(), None)
        print("released", flush=True)
    """), timeout=6)
    assert not result["alive"]
    assert result["seconds"] < 3


def test_run_gui_actually_calls_the_hold():
    """Guard the wiring, not just the helper.

    An earlier version of this suite exercised _hold_for_tray directly and
    still passed with the call deleted from run_gui.
    """
    source = read(os.path.join(ROOT, "mangadl", "gui", "__init__.py"))
    body = source[source.index("def run_gui():"):]
    assert "_hold_for_tray(api, tray)" in body


def test_turning_the_setting_off_lets_the_window_close():
    """The toggle must take effect without a restart."""
    from webview.event import Event, EventContainer

    sys.modules.pop("pystray", None)
    exec(FAKE_PYSTRAY, {"sys": sys})

    from mangadl.config import update_settings
    from mangadl.gui import _install_tray

    class Window:
        def __init__(self):
            self.events = EventContainer()
            self.events.closing = Event(self, True)
            self.events.closed = Event(self)
            self.hidden = False

        def hide(self):
            self.hidden = True

        def show(self):
            pass

        def restore(self):
            pass

        def destroy(self):
            pass

    class Api:
        def get_progress(self):
            return {"active": 0}

        def set_queue_paused(self, paused=None):
            return {"ok": True}

        def shutdown(self):
            return {"ok": True}

    update_settings({"minimize_to_tray": True})
    api, window = Api(), Window()
    tray = _install_tray(api, window)
    assert tray is not None

    assert window.events.closing.set() is True, "close should be vetoed"
    assert window.hidden

    # The user turns the setting off while the app is running.
    update_settings({"minimize_to_tray": False})
    window.events.closing.clear()
    assert window.events.closing.set() is False, \
        "with the setting off the window must close for real"
    tray.stop()


def test_tray_keepalive_is_exposed():
    from mangadl.tray import TrayController

    controller = TrayController()
    assert hasattr(controller, "wait_for_quit")
    assert controller.quit_requested() is False
    controller.stop()
    assert controller.quit_requested() is True


def test_packaging_bundles_pystray():
    """PyInstaller cannot follow pystray's backend import chain."""
    spec = read(os.path.join(ROOT, "MangaDL.spec"))
    for module in ("pystray", "pystray._win32", "PIL.ImageDraw"):
        assert f'"{module}"' in spec, f"{module} missing from MangaDL.spec"


# ====================================================== startup stylesheet


def test_local_stylesheet_loads_before_remote_fonts():
    """A desktop app must not block first paint on a font CDN.

    Measured with the old ordering: styled in 0.04s when the CDN answered,
    but 6.0s when it was slow and 20.0s when blackholed.
    """
    html = read(os.path.join(WEB, "index.html"))
    head = html[:html.index("</head>")]
    local = head.index('href="style.css"')
    # Compare against the first font *stylesheet*; a <link rel=preconnect>
    # is only a DNS/TLS hint and never blocks rendering.
    remote = min(m.start() for m in
                 re.finditer(r'<link[^>]*fonts\.googleapis\.com[^>]*'
                             r'rel="stylesheet"', head))
    assert local < remote, \
        "style.css must be linked before the Google Fonts stylesheets"


def test_remote_font_stylesheets_are_non_blocking():
    html = read(os.path.join(WEB, "index.html"))
    head = html[:html.index("</head>")]
    # A <noscript> copy is the correct fallback and cannot block the
    # scripted path, so it is excluded.
    head = re.sub(r"<noscript>.*?</noscript>", "", head, flags=re.S)
    links = re.findall(r'<link[^>]*fonts\.googleapis\.com[^>]*'
                       r'rel="stylesheet"[^>]*>', head)
    assert links, "expected the Google Fonts stylesheets to still be linked"
    for tag in links:
        assert 'media="print"' in tag and "onload" in tag, \
            f"render-blocking font link: {tag[:90]}"


def test_icons_are_hidden_until_the_font_arrives():
    """Ligature icons render as their literal names until the font loads."""
    css = read(os.path.join(WEB, "style.css"))
    assert "html:not(.icons-ready) .material-symbols-rounded" in css
    html = read(os.path.join(WEB, "index.html"))
    assert "icons-ready" in html
    # There must be a timeout, or an offline app would never show any icon.
    assert re.search(r"setTimeout\(\s*reveal", html)


# ========================================================= queue theming


def test_queue_variables_are_defined():
    """--panel-2 / --edge-c were used but never defined, so the queue kept
    its hardcoded near-black fallback on every theme."""
    css = read(os.path.join(WEB, "style.css"))
    root = css[css.index(":root {"):css.index("/* no-animation mode */")]
    for token in ("--panel-2:", "--edge-c:"):
        assert token in root, f"{token} is used but never defined"


def test_queue_tiles_do_not_hardcode_colours():
    css = read(os.path.join(WEB, "style.css"))
    block = css[css.index("grouped download queue"):css.index("contribution calendar")]
    stray = re.findall(r"#[0-9a-fA-F]{3,8}\b", block)
    assert stray == [], f"hardcoded colours in the queue block: {stray}"


def test_queue_sparkline_does_not_reuse_the_stats_class():
    """.spark already existed for the stats bar chart (flex, 110px tall) and
    silently applied to the queue's inline SVG."""
    app = read(os.path.join(WEB, "app.js"))
    assert 'class="spark"' not in app
    assert 'class="q-sparkline"' in app


# ============================================= duplicated chapters panel


def test_active_chapters_card_is_gone():
    """The chapters in flight are listed inside the expanded tiles; the
    separate card under the queue said the same thing twice."""
    html = read(os.path.join(WEB, "index.html"))
    # Strip comments first: the one documenting this removal mentions the
    # old title, which is not the same as rendering it.
    visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    assert "Active chapters" not in visible
    # The node itself must survive as a hidden stub: the event handlers
    # still write progress rows into it.
    assert 'id="activeChapters"' in html
    section = html[html.index('id="view-downloads"'):html.index('id="view-bookmarks"')]
    stub = section[section.index('id="activeChapters"') - 120:
                   section.index('id="activeChapters"') + 60]
    assert "hidden" in stub


def test_expanded_tile_renders_its_own_chapter_rows():
    app = read(os.path.join(WEB, "app.js"))
    assert "function chapterRowHtml" in app
    assert "q-now-list" in app


def test_the_floating_downloads_card_is_merged_into_the_queue():
    """The queue tab used to stack a queue card and a separate summary card
    that repeated the same totals."""
    html = read(os.path.join(WEB, "index.html"))
    section = html[html.index('id="view-downloads"'):html.index('id="view-bookmarks"')]
    assert "dl-header-card" not in section
    # The overall bar and Stop button now live inside the queue card.
    cart = section[section.index('id="cartCard"'):]
    for needle in ('id="dlActive"', 'id="stopBtn"', 'id="overallFill"'):
        assert needle in cart[:cart.index('id="cartList"') + 40], \
            f"{needle} is not inside the queue card"


# ======================================================= advanced logging


def test_advanced_log_setting_exists():
    from mangadl.gui import DEFAULT_SETTINGS

    assert "queue_log_advanced" in DEFAULT_SETTINGS
    assert DEFAULT_SETTINGS["queue_log_advanced"] is False


def test_advanced_log_is_reachable_from_both_places():
    html = read(os.path.join(WEB, "index.html"))
    assert 'id="setLogAdvanced"' in html      # Settings
    assert 'id="logAdvanced"' in html         # Queue tab


def test_verbose_lines_are_suppressed_by_default():
    app = read(os.path.join(WEB, "app.js"))
    assert "function logAdvanced()" in app
    assert "if (verbose && !logAdvanced()) return;" in app
    # Per-page chatter must be tagged verbose.
    progress = app[app.index('case "chapter_progress"'):]
    progress = progress[:progress.index("break;")]
    assert "logLine(" in progress and "true)" in progress


def test_tray_switch_ids_are_in_the_bound_list():
    """Static half of the check: the ids must be in the array that gets
    listeners, not merely mentioned in the payload built inside it."""
    app = read(os.path.join(WEB, "app.js"))
    array = app[app.index('["setDedupe"'):]
    array = array[:array.index("]") + 1]      # only the id list itself
    for name in ("setTray", "setTrayNotify", "setLogAdvanced"):
        assert f'"{name}"' in array, f"{name} is never bound to a listener"


# ==================================================== contribution graph


def test_calendar_covers_whole_weeks_and_fills_gaps():
    from mangadl import features

    cal = features.stat_calendar(weeks=53, today="2026-07-30")
    assert len(cal["days"]) == 53 * 7
    # Must start on a Sunday, like GitHub's grid.
    first = datetime.date.fromisoformat(cal["days"][0]["date"])
    assert first.weekday() == 6
    # Every day present, including empty ones.
    dates = [d["date"] for d in cal["days"]]
    assert len(set(dates)) == len(dates)
    gaps = [d for d in cal["days"] if d["chapters"] == 0]
    assert gaps, "a calendar with no empty days is not filling gaps"
    assert all(d["level"] == 0 for d in gaps)


def test_calendar_levels_scale_to_the_busiest_day(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    import importlib

    from mangadl import features
    importlib.reload(features)

    today = datetime.date.today()
    for offset, count in ((0, 100), (1, 50), (2, 25), (3, 1)):
        day = (today - datetime.timedelta(days=offset)).isoformat()
        features._save(features.STATS_PATH, {"days": {
            **features._load(features.STATS_PATH, {}).get("days", {}),
            day: {"chapters": count, "pages": 0, "bytes": 0, "sources": {}},
        }})

    cal = features.stat_calendar()
    levels = {d["date"]: d["level"] for d in cal["days"]}
    assert levels[today.isoformat()] == 4
    # A single chapter must never round down to "nothing happened".
    assert levels[(today - datetime.timedelta(days=3)).isoformat()] >= 1


def test_per_day_sources_are_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    import importlib

    from mangadl import features
    importlib.reload(features)

    features.record_stat("mangadex", chapters=3)
    features.record_stat("flamecomics", chapters=7)

    cal = features.stat_calendar()
    today = [d for d in cal["days"]
             if d["date"] == datetime.date.today().isoformat()][0]
    assert today["sources"] == {"mangadex": 3, "flamecomics": 7}
    assert today["chapters"] == 10
    assert today["top"] == "flamecomics"


def test_old_stats_without_source_days_still_count(tmp_path, monkeypatch):
    """Days recorded before per-source tracking must not be dropped."""
    monkeypatch.setenv("HOME", str(tmp_path))
    import importlib

    from mangadl import features
    importlib.reload(features)

    day = datetime.date.today().isoformat()
    os.makedirs(features.DIR, exist_ok=True)
    json.dump({"days": {day: {"chapters": 12, "pages": 100, "bytes": 5}}},
              open(features.STATS_PATH, "w"))

    cal = features.stat_calendar()
    entry = [d for d in cal["days"] if d["date"] == day][0]
    assert entry["chapters"] == 12
    assert entry["sources"] == {}
    assert entry["level"] > 0


def test_calendar_api_returns_display_names(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    import importlib

    from mangadl import features
    importlib.reload(features)
    features.record_stat("madara.toonily", chapters=2)
    features.record_stat("mangadex", chapters=1)

    from mangadl.gui import Api
    result = Api().get_calendar()
    assert result["ok"]
    names = result["calendar"]["names"]
    # Aggregate members must resolve, not show their raw namespaced slug.
    assert names["madara.toonily"] == "Toonily"
    assert names["mangadex"] == "MangaDex"


def test_source_name_resolution():
    from mangadl.gui import Api

    api = Api()
    assert api._source_name("mangadex") == "MangaDex"
    assert api._source_name("madaranet") == "Madara Sites"
    assert api._source_name("madarascans") == "Madara Scans"
    assert api._source_name("madara.toonily") == "Toonily"
    assert api._source_name("?") == "Unknown"
    # An unknown id must degrade to something readable, never crash.
    assert api._source_name("something.else")


def test_calendar_markup_and_carousel_exist():
    html = read(os.path.join(WEB, "index.html"))
    for node in ('id="calGrid"', 'id="calMonths"', 'id="srcTrack"',
                 'id="srcPrev"', 'id="srcNext"'):
        assert node in html, f"{node} missing"


def test_source_colours_are_stable_and_distinct():
    """Colours are hashed from the id so adding a source never renumbers
    everyone else's hue."""
    app = read(os.path.join(WEB, "app.js"))
    assert "function sourceColor" in app
    assert "137.508" in app, "expected the golden-angle hue rotation"


def test_calendar_squares_honour_the_corner_setting():
    css = read(os.path.join(WEB, "style.css"))
    assert '[data-corners="square"] .cal-day' in css


def test_reduced_motion_covers_the_new_animations():
    css = read(os.path.join(WEB, "style.css"))
    block = css[css.rindex("prefers-reduced-motion"):]
    for cls in (".cal-day", ".src-card", ".cal-tip"):
        assert cls in block, f"{cls} is not exempted under reduced motion"


# ============================================================== browser


playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is not installed")

PAGE_URL = "file://" + os.path.join(WEB, "index.html")

BRIDGE = """
(() => {
  const ok = (e) => Object.assign({ok: true}, e || {});
  const api = {
    get_settings: async () => ({theme: "light", accent: "teal",
                                output_dir: "/tmp/out"}),
    check_lock: async () => ({locked: false, enabled: false}),
    get_sources: async () => ok({sources: []}),
    get_genres: async () => ok({genres: []}),
    get_cart: async () => ok({queued: []}),
    get_progress: async () => Object.assign({ok: true},
      window.__progress || {active: 0, jobs: []}),
    get_calendar: async () => ok({calendar: window.__calendar || null}),
    get_stats: async () => ok({stats: window.__stats ||
      {totals: {}, derived: {}, sources: {}, days: {}}}),
    get_insights: async () => ok({insights: {}}),
    // Without this the catch-all Proxy answers {ok:true} with no
    // `available`, and refreshTrayState() disables the switch -- a quirk of
    // the stub, not the app.
    get_tray_state: async () => ok({available: true, enabled: false,
                                    running: false}),
    search: async () => ok({results: []}),
    trending: async () => ok({results: []}),
  };
  window.pywebview = {api: new Proxy(api, {
    get: (t, k) => (k in t) ? t[k] : (async () => ({ok: true})),
  })};
})();
"""


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        for candidate in (os.path.expanduser("~/.cache/ms-playwright"),
                          "/home/user/.cache/ms-playwright"):
            if os.path.isdir(candidate):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = candidate
                break
    with sync_playwright() as p:
        try:
            launched = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        yield launched
        launched.close()


@pytest.fixture()
def page(browser):
    page = browser.new_page(viewport={"width": 1400, "height": 950})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.add_init_script(BRIDGE)
    page.goto(PAGE_URL)
    page.wait_for_timeout(400)
    yield page
    page.close()


JOBS = """
window.__progress = {active: 1, jobs: [{job_id: "a", title: "Solo Leveling",
  bytes_per_second: 5033164, eta_seconds: 92, bytes: 88010000,
  history: [1,4,9,16,25,36,44,48,50,49].map(v => v * 100000)}]};
jobs.set("a", {id: "a", title: "Solo Leveling", url: "https://x/solo",
  source: "Asura Scans", done: 11, total: 18, finished: false,
  chapters: [{name: "Chapter 11", done: 12, total: 16}]});
state.downloading = true;
"""


def test_hero_icon_is_not_clipped(page):
    """The float animation lifts the icon 7px inside an overflow:hidden
    parent; with no headroom its top was sliced off on every bounce."""
    worst = page.evaluate("""() => {
      const icon = document.querySelector('.hero-icon');
      const wrap = document.querySelector('.hero-title');
      let worst = Infinity;
      for (let i = 0; i <= 20; i++) {
        icon.style.animationPlayState = 'paused';
        icon.style.animationDelay = `-${(i / 20) * 5}s`;
        worst = Math.min(worst,
          icon.getBoundingClientRect().top - wrap.getBoundingClientRect().top);
      }
      icon.style.animationDelay = '';
      icon.style.animationPlayState = '';
      return worst;
    }""")
    assert worst >= 0, (
        f"the search icon is clipped by {abs(worst):.1f}px at the top of its "
        "bounce")


def test_queue_tiles_are_readable_on_the_light_theme(page):
    page.evaluate("showView('downloads')")
    page.evaluate(JOBS)
    page.evaluate("renderCart()")
    page.wait_for_timeout(300)

    probe = page.evaluate("""() => {
      const tile = document.querySelector('.q-tile');
      if (!tile) return null;
      const lum = (c) => {
        const [r, g, b] = (c.match(/[\\d.]+/g) || []).map(Number);
        return r === undefined ? null : (0.2126*r + 0.7152*g + 0.0722*b) / 255;
      };
      const name = tile.querySelector('.q-name');
      return {
        contrast: Math.abs(lum(getComputedStyle(name).color) -
                           lum(getComputedStyle(tile).backgroundColor)),
        tileBg: getComputedStyle(tile).backgroundColor,
      };
    }""")
    assert probe is not None, "no queue tile rendered"
    assert probe["contrast"] > 0.4, (
        f"queue title is unreadable on its own tile ({probe})")


def test_a_single_download_still_shows_a_tile(page):
    """The card required two rows, so the commonest case showed nothing."""
    page.evaluate("showView('downloads')")
    page.evaluate(JOBS)
    page.evaluate("renderCart()")
    page.wait_for_timeout(300)
    assert page.eval_on_selector_all(".q-tile", "els => els.length") == 1
    assert not page.evaluate(
        "() => document.getElementById('cartCard').classList.contains('hidden')")


def test_tiles_start_collapsed_and_toggle(page):
    page.evaluate("showView('downloads')")
    page.evaluate(JOBS)
    page.evaluate("renderCart()")
    page.wait_for_timeout(300)
    assert not page.evaluate(
        "() => document.querySelector('.q-tile').classList.contains('open')")
    page.eval_on_selector(".q-head", "e => e.click()")
    page.wait_for_timeout(350)
    assert page.evaluate(
        "() => document.querySelector('.q-tile').classList.contains('open')")


def test_chapters_are_listed_once(page):
    """They used to appear in the tile AND in a separate card below it."""
    page.evaluate("showView('downloads')")
    page.evaluate(JOBS)
    page.evaluate("renderCart()")
    page.wait_for_timeout(250)
    page.eval_on_selector(".q-head", "e => e.click()")
    page.wait_for_timeout(350)
    counts = page.evaluate("""() => ({
      inTiles: document.querySelectorAll('.q-chapter').length,
      inPanel: (() => {
        const el = document.getElementById('activeChapters');
        return el && el.offsetParent !== null
          ? el.querySelectorAll('.ac-row').length : 0;
      })(),
    })""")
    assert counts["inTiles"] >= 1
    assert counts["inPanel"] == 0, "the old Active chapters panel is visible"


def test_sparkline_is_drawn_at_its_own_size(page):
    page.evaluate("showView('downloads')")
    page.evaluate(JOBS)
    page.evaluate("renderCart()")
    # The rate history arrives from get_progress, so the poll has to run
    # before there is anything to draw.
    page.evaluate("startCartPolling()")
    page.wait_for_timeout(1400)
    box = page.evaluate("""() => {
      const s = document.querySelector('.q-sparkline');
      if (!s) return null;
      const cs = getComputedStyle(s);
      return {display: cs.display, height: parseFloat(cs.height),
              paths: s.querySelectorAll('path').length};
    }""")
    assert box, "no sparkline rendered"
    assert box["display"] == "block"
    assert box["height"] < 40, \
        f"the sparkline inherited the 110px stats chart height: {box}"
    assert box["paths"] == 2


def test_verbose_log_lines_only_appear_in_advanced_mode(page):
    page.evaluate("showView('downloads')")
    page.evaluate("""() => {
      document.getElementById('logAdvanced').checked = false;
      logLine('info', 'chatter', true);
      logLine('ok', 'milestone');
    }""")
    text = page.eval_on_selector("#dlLog", "e => e.textContent")
    assert "milestone" in text
    assert "chatter" not in text

    page.evaluate("""() => {
      document.getElementById('logAdvanced').checked = true;
      logLine('info', 'chatter', true);
    }""")
    assert "chatter" in page.eval_on_selector("#dlLog", "e => e.textContent")


CAL = """
window.__calendar = (() => {
  const days = [];
  const start = new Date('2025-08-03T00:00:00');
  for (let i = 0; i < 371; i++) {
    const d = new Date(start.getTime() + i * 86400000);
    const busy = i % 3 === 0;
    days.push({
      date: d.toISOString().slice(0, 10),
      chapters: busy ? (i % 40) + 1 : 0,
      pages: 0, bytes: 0,
      level: busy ? Math.min(4, Math.floor((i % 40) / 10) + 1) : 0,
      sources: busy ? {mangadex: (i % 9) + 1, flamecomics: (i % 5) + 1} : {},
      top: busy ? 'mangadex' : '',
    });
  }
  return {days, weeks: 53, peak: 40,
          total: days.reduce((n, d) => n + d.chapters, 0),
          sources: {mangadex: 900, flamecomics: 400},
          names: {mangadex: 'MangaDex', flamecomics: 'Flame Comics'}};
})();
window.__stats = {totals: {chapters: 1300}, derived: {},
                  sources: {mangadex: {chapters: 900},
                            flamecomics: {chapters: 400}}, days: {}};
"""


def test_calendar_renders_a_full_grid(page):
    page.evaluate(CAL)
    page.evaluate("showView('insights')")
    page.wait_for_timeout(700)
    probe = page.evaluate("""() => ({
      cells: document.querySelectorAll('#calGrid .cal-day').length,
      months: document.querySelectorAll('.cal-month').length,
      colours: new Set([...document.querySelectorAll('#calGrid .cal-day')]
        .map((c) => getComputedStyle(c).backgroundColor)).size,
    })""")
    assert probe["cells"] == 371
    assert probe["months"] == 53
    assert probe["colours"] > 3, \
        "every square is the same colour; intensity is not being applied"
    assert page.errors == []


def test_brighter_squares_mean_more_downloads(page):
    page.evaluate(CAL)
    page.evaluate("showView('insights')")
    page.wait_for_timeout(700)
    alphas = page.evaluate("""() => {
      const out = {};
      document.querySelectorAll('#calGrid .cal-day').forEach((c) => {
        const lvl = [...c.classList].find((x) => x.startsWith('lvl-'));
        const m = getComputedStyle(c).backgroundColor.match(/[\\d.]+/g);
        const a = m && m.length > 3 ? parseFloat(m[3]) : 1;
        if (!(lvl in out)) out[lvl] = [];
        out[lvl].push(a);
      });
      const avg = {};
      Object.entries(out).forEach(([k, v]) =>
        avg[k] = v.reduce((x, y) => x + y, 0) / v.length);
      return avg;
    }""")
    assert alphas["lvl-4"] > alphas["lvl-1"], (
        f"a busy day is not brighter than a quiet one: {alphas}")


def test_day_tooltip_names_sources_as_a_fraction(page):
    page.evaluate(CAL)
    page.evaluate("showView('insights')")
    page.wait_for_timeout(700)
    target = page.evaluate(
        "() => [...document.querySelectorAll('#calGrid .cal-day')]"
        ".find((c) => !c.classList.contains('lvl-0')).dataset.date")
    page.hover(f'#calGrid .cal-day[data-date="{target}"]')
    page.wait_for_timeout(300)
    tip = page.evaluate("""() => {
      const t = document.querySelector('.cal-tip');
      return t && t.classList.contains('show')
        ? t.textContent.replace(/\\s+/g, ' ').trim() : null;
    }""")
    assert tip, "no tooltip appeared"
    assert "MangaDex" in tip, f"source not named: {tip}"
    assert re.search(r"\d+/\d+", tip), f"no fraction in the tooltip: {tip}"


def test_empty_day_tooltip_says_nothing_happened(page):
    page.evaluate(CAL)
    page.evaluate("showView('insights')")
    page.wait_for_timeout(700)
    target = page.evaluate(
        "() => [...document.querySelectorAll('#calGrid .cal-day')]"
        ".find((c) => c.classList.contains('lvl-0')).dataset.date")
    page.hover(f'#calGrid .cal-day[data-date="{target}"]')
    page.wait_for_timeout(300)
    tip = page.eval_on_selector(".cal-tip", "t => t.textContent")
    assert "No downloads" in tip


def test_source_carousel_renders_and_scrolls(page):
    page.evaluate(CAL)
    page.evaluate("showView('insights')")
    page.wait_for_timeout(700)
    probe = page.evaluate("""() => ({
      cards: document.querySelectorAll('.src-card').length,
      names: [...document.querySelectorAll('.src-card-name')]
        .map((n) => n.textContent),
      colours: new Set([...document.querySelectorAll('.src-swatch')]
        .map((s) => getComputedStyle(s).backgroundColor)).size,
      prevDisabled: document.getElementById('srcPrev').disabled,
    })""")
    assert probe["cards"] == 2
    assert "MangaDex" in probe["names"]
    assert probe["colours"] == 2, "sources share a colour"
    assert probe["prevDisabled"] is True


def test_carousel_card_tooltip_shows_a_share(page):
    page.evaluate(CAL)
    page.evaluate("showView('insights')")
    page.wait_for_timeout(700)
    page.hover(".src-card")
    page.wait_for_timeout(300)
    tip = page.eval_on_selector(".cal-tip", "t => t.textContent")
    assert re.search(r"\d+/\d+ chapters", tip.replace("\n", " ")), tip


def test_flipping_the_tray_switch_saves_it(page):
    """Behavioural half: click the real switch and watch the bridge call.

    The static check cannot tell "bound" from "mentioned in the payload",
    which is exactly how this bug survived -- minimize_to_tray was in the
    saved object but its checkbox had no listener.
    """
    page.evaluate("""() => {
      window.__saved = [];
      const real = window.pywebview.api;
      window.pywebview = {api: new Proxy(real, {
        get: (t, k) => k === 'set_settings'
          ? (async (s) => { window.__saved.push(s); return {ok: true}; })
          : t[k],
      })};
    }""")
    page.evaluate("showView('settings')")
    page.wait_for_timeout(200)
    page.eval_on_selector("#setTray", "e => e.click()")
    page.wait_for_timeout(300)

    saved = page.evaluate("() => window.__saved")
    assert saved, "clicking 'Minimise to system tray' saved nothing"
    assert any("minimize_to_tray" in s for s in saved), saved
    assert saved[-1]["minimize_to_tray"] is True


def test_flipping_advanced_logging_saves_it(page):
    page.evaluate("""() => {
      window.__saved = [];
      const real = window.pywebview.api;
      window.pywebview = {api: new Proxy(real, {
        get: (t, k) => k === 'set_settings'
          ? (async (s) => { window.__saved.push(s); return {ok: true}; })
          : t[k],
      })};
    }""")
    page.evaluate("showView('downloads')")
    page.eval_on_selector("#logAdvanced", "e => e.click()")
    page.wait_for_timeout(300)
    saved = page.evaluate("() => window.__saved")
    assert saved and saved[-1].get("queue_log_advanced") is True, saved
    # The Settings copy of the same switch must follow.
    assert page.eval_on_selector("#setLogAdvanced", "e => e.checked") is True


def test_no_console_errors_across_views(page):
    page.evaluate(CAL)
    for view in ("search", "downloads", "insights", "settings", "tools"):
        page.evaluate(f"showView('{view}')")
        page.wait_for_timeout(220)
    assert page.errors == []
