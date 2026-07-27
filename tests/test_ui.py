"""Tests for the GitHub-style landing page and the new GUI tabs.

Structural checks run everywhere. The interactive checks drive real headless
Chromium and skip automatically when Playwright is unavailable.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")
DOCS = os.path.join(ROOT, "docs")
SITE = os.path.join(DOCS, "index.html")

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is not installed")


def read(path):
    return open(path, encoding="utf-8").read()


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
def site(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("file://" + SITE)
    page.wait_for_timeout(300)
    page.errors = errors
    yield page
    page.close()


# ===================================================== landing page: static


def test_site_has_no_duplicate_ids():
    from collections import Counter

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(SITE), "html.parser")
    ids = [e["id"] for e in soup.find_all(id=True)]
    assert [k for k, v in Counter(ids).items() if v > 1] == []


def test_every_referenced_image_exists():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(SITE), "html.parser")
    missing = [img["src"] for img in soup.find_all("img")
               if not os.path.exists(os.path.join(DOCS, img["src"]))]
    assert missing == []


def test_every_tab_has_a_matching_pane():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(SITE), "html.parser")
    tabs = {t["data-pane"] for t in soup.select(".repo-tab")}
    panes = {p["id"].replace("pane-", "") for p in soup.select(".pane")}
    assert tabs == panes
    assert len(tabs) >= 5


def test_no_fabricated_social_counts():
    """A static page cannot know real star/fork counts, so it must not show any.

    Inventing them would present made-up numbers as fact.
    """
    html = read(SITE)
    assert 'Star<span class="btn-count">' not in html
    assert 'Fork<span class="btn-count">' not in html
    assert 'Watch<span class="btn-count">' not in html


def test_stated_counters_match_the_repository():
    """The numbers the page does show must be real."""
    html = read(SITE)

    features = sum(1 for line in open(os.path.join(ROOT, "FEATURES.md"),
                                      encoding="utf-8")
                   if re.match(r"^\d+\.", line))
    sources = len(re.findall(r"^\s+\w+Source,",
                             read(os.path.join(ROOT, "mangadl", "sources",
                                               "__init__.py")), re.M))
    assert f'counter">{features}<' in html
    assert f'counter">{sources}<' in html


def test_version_badge_matches_the_package():
    version = re.search(r'__version__ = "([^"]+)"',
                        read(os.path.join(ROOT, "mangadl", "__init__.py"))).group(1)
    assert version in read(SITE)


def test_links_point_at_the_right_repository():
    html = read(SITE)
    assert "github.com/Compromisee/WeebDL" in html
    assert "Yui007" not in html


def test_both_colour_modes_are_defined():
    html = read(SITE)
    assert '[data-color-mode="dark"]' in html
    assert '[data-color-mode="light"]' in html


def test_site_respects_reduced_motion():
    assert "prefers-reduced-motion" in read(SITE)


# ================================================ landing page: interactive


def test_site_loads_without_errors(site):
    assert site.errors == []
    assert site.evaluate("() => document.querySelector('.pane.active').id") == "pane-readme"


@pytest.mark.parametrize("pane", ["features", "screens", "cli", "sources", "readme"])
def test_each_tab_switches(site, pane):
    site.click(f'.repo-tab[data-pane="{pane}"]')
    site.wait_for_timeout(200)
    assert site.evaluate("() => document.querySelector('.pane.active').id") == f"pane-{pane}"


def test_only_one_pane_visible_at_a_time(site):
    site.click('.repo-tab[data-pane="cli"]')
    site.wait_for_timeout(200)
    visible = site.evaluate("""() =>
        [...document.querySelectorAll('.pane')]
          .filter(p => getComputedStyle(p).display !== 'none').length""")
    assert visible == 1


def test_deep_link_opens_the_right_tab(browser):
    page = browser.new_page()
    page.goto("file://" + SITE + "#cli")
    page.wait_for_timeout(400)
    assert page.evaluate("() => document.querySelector('.pane.active').id") == "pane-cli"
    page.close()


def test_hashchange_switches_tabs(site):
    """Same-document hash changes do not reload, so this needs a listener."""
    site.click('[data-goto="cli"]')
    site.wait_for_timeout(300)
    assert site.evaluate("() => document.querySelector('.pane.active').id") == "pane-cli"


def test_browser_back_returns_to_the_previous_tab(site):
    site.click('.repo-tab[data-pane="cli"]')
    site.wait_for_timeout(200)
    site.click('.repo-tab[data-pane="sources"]')
    site.wait_for_timeout(200)
    site.go_back()
    site.wait_for_timeout(350)
    assert site.evaluate("() => document.querySelector('.pane.active').id") == "pane-cli"


def test_colour_mode_toggles_and_persists(site):
    before = site.evaluate("() => document.documentElement.getAttribute('data-color-mode')")
    site.click("#modeBtn")
    site.wait_for_timeout(250)
    after = site.evaluate("() => document.documentElement.getAttribute('data-color-mode')")
    assert after != before
    assert site.evaluate("() => localStorage.getItem('mangadl-mode')") == after
    # the change must be visible, not just an attribute
    bg = site.evaluate("() => getComputedStyle(document.body).backgroundColor")
    assert bg in ("rgb(255, 255, 255)", "rgb(13, 17, 23)")


def test_screenshot_subtabs_switch(site):
    site.click('.repo-tab[data-pane="screens"]')
    site.wait_for_timeout(200)
    site.click('.shot-tab[data-shot="tui"]')
    site.wait_for_timeout(200)
    assert site.evaluate("() => document.querySelector('#shot-tui').classList.contains('active')")
    assert not site.evaluate("() => document.querySelector('#shot-gui').classList.contains('active')")


def test_language_bar_widths_sum_to_100(site):
    total = site.evaluate("""() =>
        [...document.querySelectorAll('.lang-bar span')]
          .reduce((s, el) => s + parseFloat(el.style.width), 0)""")
    assert 99 <= total <= 101


# ==================================================== GUI: new tabs static


def test_gui_has_the_new_views():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(os.path.join(WEB, "index.html")), "html.parser")
    views = {v["id"] for v in soup.select(".view")}
    assert {"view-updates", "view-insights", "view-tools"} <= views


def test_every_rail_button_has_a_view():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(os.path.join(WEB, "index.html")), "html.parser")
    rails = {b["data-view"] for b in soup.select(".rail-btn[data-view]")}
    views = {v["id"].replace("view-", "") for v in soup.select(".view")}
    assert rails == views


def test_new_views_are_wired_into_showview():
    js = read(os.path.join(WEB, "app.js"))
    block = js[js.index("function showView"):]
    block = block[:block.index("\n}") + 2]
    for name in ("updates", "insights", "tools"):
        assert f'"{name}"' in block


def test_gui_ids_all_resolve():
    html = read(os.path.join(WEB, "index.html"))
    js = read(os.path.join(WEB, "app.js"))
    referenced = set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)', js))
    assert sorted(i for i in referenced if f'id="{i}"' not in html) == []


def test_callapi_wrapper_is_defensive():
    """A missing endpoint must not blank out a whole tab."""
    js = read(os.path.join(WEB, "app.js"))
    helper = js[js.index("async function callApi"):]
    helper = helper[:helper.index("\n}") + 2]
    assert "try {" in helper and "catch" in helper
    assert "return null" in helper


def test_new_views_use_callapi_not_raw_bridge():
    js = read(os.path.join(WEB, "app.js"))
    for fn in ("loadUpdates", "loadInsights", "loadHealth", "loadHistoryList"):
        body = js[js.index(f"function {fn}"):]
        body = body[:body.index("\n}") + 2]
        assert "callApi(" in body, f"{fn} should call the bridge defensively"


def test_bar_fill_is_a_block():
    """Spans are inline by default, so width/height are ignored and the bar
    renders as an empty track."""
    css = read(os.path.join(WEB, "style.css"))
    block = css[css.index(".bar-row .b-fill"):]
    block = block[:block.index("}")]
    assert "display: block" in block


def test_get_health_endpoint_exists():
    import importlib
    import tempfile

    os.environ["HOME"] = tempfile.mkdtemp()
    import mangadl.gui as gui
    importlib.reload(gui)
    assert hasattr(gui.Api, "get_health")
    report = gui.Api().get_health()
    assert report["ok"] is True
    assert {"breakers", "browse_cache", "genre_cache"} <= set(report["report"])
