"""Tests for the landing page and the GUI tabs.

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


def test_every_cli_tab_has_a_pane():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(SITE), "html.parser")
    tabs = {t["data-p"] for t in soup.select(".tab[data-p]")}
    panes = {p["id"].replace("p-", "") for p in soup.select(".pane[id]")}
    assert tabs, "no CLI tabs found"
    assert tabs <= panes, f"tabs with no pane: {tabs - panes}"


def test_every_screenshot_tab_has_a_panel():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(read(SITE), "html.parser")
    tabs = {t["data-s"] for t in soup.select(".shot-tab[data-s]")}
    shots = {s["id"].replace("s-", "") for s in soup.select(".shot[id]")}
    assert tabs == shots


def test_no_fabricated_social_counts():
    """A static page cannot know real star/fork counts, so it must not show
    any. Inventing them would present made-up numbers as fact."""
    html = read(SITE)
    for fragment in ("btn-count", "stargazers", "Watch<", "Fork<"):
        assert fragment not in html, fragment


def test_stated_counters_match_the_repository():
    """Every number the page shows has to be real."""
    html = read(SITE)

    features = sum(1 for line in open(os.path.join(ROOT, "FEATURES.md"),
                                      encoding="utf-8")
                   if re.match(r"^\d+\.", line))
    sources = len(re.findall(r"^\s+\w+Source,",
                             read(os.path.join(ROOT, "mangadl", "sources",
                                               "__init__.py")), re.M))
    assert f"{features} documented features" in html
    assert f'<div class="hs-n">{sources}</div>' in html


def test_source_tiles_match_the_registry():
    """The grid lists sites by hand, so it can drift from the code."""
    from bs4 import BeautifulSoup

    from mangadl.sources import list_sources

    soup = BeautifulSoup(read(SITE), "html.parser")
    listed = {t.get_text(strip=True).lower() for t in soup.select(".src-n")}
    real = {m["name"].lower() for m in list_sources()}
    assert listed == real, f"drifted: {listed ^ real}"


def test_adult_sources_are_marked():
    from bs4 import BeautifulSoup

    from mangadl.sources import list_sources

    soup = BeautifulSoup(read(SITE), "html.parser")
    tagged = set()
    for tile in soup.select(".src"):
        if tile.select_one(".tag-adult"):
            name = tile.select_one(".src-n")
            if name:
                tagged.add(name.get_text(strip=True).lower())
    expected = {m["name"].lower() for m in list_sources() if m["adult_only"]}
    assert tagged == expected


def test_version_badge_matches_the_package():
    version = re.search(r'__version__ = "([^"]+)"',
                        read(os.path.join(ROOT, "mangadl", "__init__.py"))).group(1)
    assert version in read(SITE)


def test_links_point_at_the_right_repository():
    html = read(SITE)
    assert "github.com/Compromisee/MDL" in html
    assert "Compromisee/WeebDL" not in html
    assert "Yui007" not in html


def test_both_colour_modes_are_defined():
    html = read(SITE)
    assert 'data-theme="night"' in html
    assert 'html[data-theme="dawn"]' in html


def test_site_respects_reduced_motion():
    assert "prefers-reduced-motion" in read(SITE)


def test_page_is_not_styled_like_github():
    """The brief was an original design, not a code-host clone."""
    html = read(SITE)
    for borrowed in ("repo-tab", "gh-logo", "gh-search", "octicon",
                     "data-color-mode", "lang-bar"):
        assert borrowed not in html, f"GitHub chrome left behind: {borrowed}"


# ================================================ landing page: interactive


def test_site_loads_without_errors(site):
    assert site.errors == []
    assert site.evaluate(
        "() => document.querySelector('.panel .pane.on').id") == "p-dl"


@pytest.mark.parametrize("pane", ["dl", "search", "menu", "lib", "cfg"])
def test_each_cli_tab_switches(site, pane):
    site.click(f'.tab[data-p="{pane}"]')
    site.wait_for_timeout(200)
    assert site.evaluate(
        "() => document.querySelector('.panel .pane.on').id") == f"p-{pane}"


def test_only_one_cli_pane_visible_at_a_time(site):
    site.click('.tab[data-p="search"]')
    site.wait_for_timeout(200)
    visible = site.evaluate("""() =>
        [...document.querySelectorAll('.panel .pane')]
          .filter(p => getComputedStyle(p).display !== 'none').length""")
    assert visible == 1


def test_theme_toggles_and_persists(site):
    before = site.evaluate("() => document.documentElement.dataset.theme")
    site.click("#themeBtn")
    site.wait_for_timeout(250)
    after = site.evaluate("() => document.documentElement.dataset.theme")
    assert after != before
    assert site.evaluate("() => localStorage.getItem('mdl-theme')") == after
    # the change must be visible, not merely an attribute
    bg = site.evaluate("() => getComputedStyle(document.body).backgroundColor")
    assert bg in ("rgb(251, 247, 244)", "rgb(11, 10, 18)")


def test_screenshot_tabs_switch(site):
    site.click('.shot-tab[data-s="s3"]')
    site.wait_for_timeout(200)
    assert site.evaluate("() => document.querySelector('#s-s3').classList.contains('on')")
    assert not site.evaluate("() => document.querySelector('#s-s1').classList.contains('on')")


def test_page_does_not_scroll_sideways(site):
    """A horizontal scrollbar is the usual sign of a broken width somewhere."""
    assert not site.evaluate(
        "() => document.documentElement.scrollWidth > window.innerWidth + 1")


def test_anchor_links_all_resolve(site):
    missing = site.evaluate("""() =>
        [...document.querySelectorAll('a[href^="#"]')]
          .map(a => a.getAttribute('href'))
          .filter(h => h.length > 1 && !document.querySelector(h))""")
    assert missing == []


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
