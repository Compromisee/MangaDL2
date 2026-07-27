"""Browser tests for the custom dropdown component.

These drive the real GUI page in headless Chromium, because the whole point of
this component is DOM/keyboard/pointer behaviour that cannot be asserted from
Python alone.

Skipped automatically when Playwright or its browser binary is unavailable.

    pip install playwright && python -m playwright install chromium
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is not installed")

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "mangadl", "gui", "web")
PAGE_URL = "file://" + os.path.join(WEB, "index.html")


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    # Other test modules point HOME at a temp dir, which hides Playwright's
    # browser cache. Pin it explicitly so the suite behaves the same either way.
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        for candidate in (os.path.expanduser("~/.cache/ms-playwright"),
                          "/home/user/.cache/ms-playwright"):
            if os.path.isdir(candidate):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = candidate
                break

    with sync_playwright() as p:
        try:
            launched = p.chromium.launch()
        except Exception as exc:                      # no browser binary
            pytest.skip(f"chromium unavailable: {exc}")
        yield launched
        launched.close()


@pytest.fixture()
def page(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE_URL)
    # app.js needs the pywebview bridge, which does not exist in a plain
    # browser; the dropdown module is independent and still enhances.
    page.wait_for_function("() => window.MangaDropdown !== undefined")
    page.wait_for_timeout(120)
    page.errors = errors
    yield page
    page.close()


def open_filters(page):
    """The filter row starts collapsed."""
    page.click("#filterToggle")
    page.wait_for_timeout(80)


# =============================================================== wiring


def test_dropdown_module_loads(page):
    assert page.evaluate("() => typeof window.MangaDropdown.enhance") == "function"


def test_every_select_is_enhanced(page):
    counts = page.evaluate("""() => ({
        selects: document.querySelectorAll('select').length,
        native: document.querySelectorAll('select.dd-native').length,
        buttons: document.querySelectorAll('.dd-btn').length,
    })""")
    assert counts["selects"] > 0
    assert counts["native"] == counts["selects"]
    assert counts["buttons"] == counts["selects"]


def test_native_selects_are_visually_hidden(page):
    hidden = page.evaluate("""() => {
        const s = document.querySelector('#fSort');
        const cs = getComputedStyle(s);
        return { opacity: cs.opacity, pointer: cs.pointerEvents,
                 inDom: document.body.contains(s) };
    }""")
    assert hidden["inDom"] is True          # still present for existing code
    assert hidden["opacity"] == "0"
    assert hidden["pointer"] == "none"


def test_closed_panels_are_not_rendered(page):
    """Regression: `.dd-panel { display:flex }` is author-level CSS and beats
    the UA stylesheet's `[hidden] { display:none }`, which left every panel
    painted on top of the page. Attribute checks alone do not catch this --
    computed style must be asserted."""
    state = page.evaluate("""() => {
        const all = [...document.querySelectorAll('.dd-panel')];
        return {
            total: all.length,
            visible: all.filter(p => getComputedStyle(p).display !== 'none').length,
        };
    }""")
    assert state["total"] > 0
    assert state["visible"] == 0, "closed dropdown panels must not be rendered"


def test_opened_panel_becomes_visible(page):
    open_filters(page)
    page.evaluate("""() => {
        document.querySelector('#fStatus').closest('.dd').querySelector('.dd-btn').click();
    }""")
    page.wait_for_timeout(100)
    visible = page.evaluate("""() =>
        [...document.querySelectorAll('.dd-panel')]
            .filter(p => getComputedStyle(p).display !== 'none').length""")
    assert visible == 1


def test_trigger_shows_the_selected_option(page):
    open_filters(page)
    label = page.text_content("#fSort ~ .dd-btn .dd-label, .dd .dd-btn .dd-label")
    assert label.strip()


# ============================================================= opening


def test_clicking_opens_a_themed_panel(page):
    open_filters(page)
    page.evaluate("""() => {
        const dd = document.querySelector('#fSort').closest('.dd');
        dd.querySelector('.dd-btn').click();
    }""")
    page.wait_for_timeout(120)
    state = page.evaluate("""() => {
        const p = document.querySelector('.dd-panel:not([hidden])');
        if (!p) return null;
        const cs = getComputedStyle(p);
        return { items: p.querySelectorAll('.dd-item').length,
                 position: cs.position,
                 portalled: p.parentElement === document.body };
    }""")
    assert state is not None, "no panel opened"
    assert state["items"] > 0
    assert state["position"] == "fixed"
    assert state["portalled"] is True      # cannot be clipped by ancestors


def test_only_one_panel_open_at_a_time(page):
    open_filters(page)
    page.evaluate("""() => {
        document.querySelector('#fSort').closest('.dd').querySelector('.dd-btn').click();
    }""")
    page.wait_for_timeout(60)
    page.evaluate("""() => {
        document.querySelector('#fStatus').closest('.dd').querySelector('.dd-btn').click();
    }""")
    page.wait_for_timeout(60)
    assert page.evaluate(
        "() => document.querySelectorAll('.dd-panel:not([hidden])').length") == 1


def test_outside_click_closes(page):
    open_filters(page)
    page.evaluate("""() => {
        document.querySelector('#fSort').closest('.dd').querySelector('.dd-btn').click();
    }""")
    page.wait_for_timeout(80)
    # Pick a point provably outside the panel: it is portalled to <body> and
    # may sit anywhere, so a fixed coordinate can land inside it.
    point = page.evaluate("""() => {
        const r = document.querySelector('.dd-panel:not([hidden])').getBoundingClientRect();
        return { x: Math.round(r.right + 150), y: Math.round(r.bottom + 150) };
    }""")
    page.mouse.click(point["x"], point["y"])
    page.wait_for_timeout(100)
    assert page.evaluate(
        "() => document.querySelectorAll('.dd-panel:not([hidden])').length") == 0


# =========================================================== selecting


def test_choosing_writes_through_to_the_native_select(page):
    open_filters(page)
    result = page.evaluate("""() => {
        const sel = document.querySelector('#fStatus');
        const dd = sel.closest('.dd');
        dd.querySelector('.dd-btn').click();
        const panel = document.querySelector('.dd-panel:not([hidden])');
        const rows = [...panel.querySelectorAll('.dd-item')];
        const target = rows.find(r => r.dataset.value !== sel.value);
        const wanted = target.dataset.value;
        target.click();
        return { wanted, actual: sel.value,
                 label: dd.querySelector('.dd-label').textContent.trim() };
    }""")
    assert result["actual"] == result["wanted"]
    assert result["label"] == result["wanted"]


def test_choosing_fires_a_change_event(page):
    """Existing app listeners are bound to `change`, so it must still fire."""
    open_filters(page)
    fired = page.evaluate("""() => {
        const sel = document.querySelector('#fStatus');
        let count = 0;
        sel.addEventListener('change', () => count++);
        const dd = sel.closest('.dd');
        dd.querySelector('.dd-btn').click();
        const rows = [...document.querySelector('.dd-panel:not([hidden])')
                        .querySelectorAll('.dd-item')];
        rows.find(r => r.dataset.value !== sel.value).click();
        return count;
    }""")
    assert fired == 1


def test_reselecting_the_same_value_does_not_fire_change(page):
    open_filters(page)
    fired = page.evaluate("""() => {
        const sel = document.querySelector('#fStatus');
        let count = 0;
        sel.addEventListener('change', () => count++);
        const dd = sel.closest('.dd');
        dd.querySelector('.dd-btn').click();
        const rows = [...document.querySelector('.dd-panel:not([hidden])')
                        .querySelectorAll('.dd-item')];
        rows.find(r => r.dataset.value === sel.value).click();
        return count;
    }""")
    assert fired == 0


def test_selected_row_is_marked(page):
    open_filters(page)
    marked = page.evaluate("""() => {
        const sel = document.querySelector('#fStatus');
        sel.closest('.dd').querySelector('.dd-btn').click();
        const panel = document.querySelector('.dd-panel:not([hidden])');
        const row = panel.querySelector('.dd-item.dd-selected');
        return row ? { value: row.dataset.value,
                       aria: row.getAttribute('aria-selected') } : null;
    }""")
    assert marked is not None
    assert marked["aria"] == "true"


# ================================================ programmatic updates


def test_setting_value_from_code_repaints_the_trigger(page):
    """`sel.value = x` is used all over app.js and must stay working."""
    open_filters(page)
    result = page.evaluate("""() => {
        const sel = document.querySelector('#fStatus');
        const target = [...sel.options].map(o => o.value)
                        .find(v => v !== sel.value);
        sel.value = target;
        return { value: sel.value,
                 label: sel.closest('.dd').querySelector('.dd-label').textContent.trim() };
    }""")
    assert result["value"] == result["label"]


def test_rebuilding_options_updates_the_dropdown(page):
    """app.js rewrites innerHTML for source/genre/sort lists."""
    open_filters(page)
    result = page.evaluate("""() => {
        const sel = document.querySelector('#fSort');
        sel.innerHTML = '';
        ['Alpha', 'Beta', 'Gamma'].forEach(n => {
            const o = document.createElement('option');
            o.textContent = n; sel.appendChild(o);
        });
        sel.value = 'Beta';
        return new Promise(res => setTimeout(() => {
            const dd = sel.closest('.dd');
            dd.querySelector('.dd-btn').click();
            const panel = document.querySelector('.dd-panel:not([hidden])');
            res({
              label: dd.querySelector('.dd-label').textContent.trim(),
              rows: [...panel.querySelectorAll('.dd-item')].map(r => r.dataset.value),
            });
        }, 60));
    }""")
    assert result["label"] == "Beta"
    assert result["rows"] == ["Alpha", "Beta", "Gamma"]


def test_appendchild_options_appear(page):
    open_filters(page)
    count = page.evaluate("""() => {
        const sel = document.querySelector('#fType');
        const before = sel.options.length;
        const o = document.createElement('option');
        o.textContent = 'Brand New'; sel.appendChild(o);
        return new Promise(res => setTimeout(() => {
            sel.closest('.dd').querySelector('.dd-btn').click();
            const panel = document.querySelector('.dd-panel:not([hidden])');
            res({ before, rows: panel.querySelectorAll('.dd-item').length });
        }, 60));
    }""")
    assert count["rows"] == count["before"] + 1


def test_disabled_select_is_reflected(page):
    open_filters(page)
    state = page.evaluate("""() => {
        const sel = document.querySelector('#fType');
        sel.disabled = true;
        return new Promise(res => setTimeout(() => {
            const btn = sel.closest('.dd').querySelector('.dd-btn');
            btn.click();
            res({ disabled: btn.disabled,
                  open: document.querySelectorAll('.dd-panel:not([hidden])').length });
        }, 60));
    }""")
    assert state["disabled"] is True
    assert state["open"] == 0


# ============================================================= filtering


def test_filter_box_appears_only_for_long_lists(page):
    open_filters(page)
    result = page.evaluate("""() => {
        const short = document.querySelector('#fStatus');   // 5 options
        short.closest('.dd').querySelector('.dd-btn').click();
        const shortHidden = document.querySelector('.dd-panel:not([hidden]) .dd-filter').hidden;
        document.querySelector('.dd-btn').blur();
        window.MangaDropdown.closeAll();

        const long = document.querySelector('#fLanguage');  // 17 options
        long.closest('.dd').querySelector('.dd-btn').click();
        const longHidden = document.querySelector('.dd-panel:not([hidden]) .dd-filter').hidden;
        return { shortHidden, longHidden };
    }""")
    assert result["shortHidden"] is True
    assert result["longHidden"] is False


def test_typing_filters_the_list(page):
    open_filters(page)
    result = page.evaluate("""() => {
        const sel = document.querySelector('#fLanguage');
        sel.closest('.dd').querySelector('.dd-btn').click();
        const panel = document.querySelector('.dd-panel:not([hidden])');
        const before = panel.querySelectorAll('.dd-item').length;
        const input = panel.querySelector('.dd-filter-input');
        input.value = 'span';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const rows = [...panel.querySelectorAll('.dd-item')].map(r => r.textContent.trim());
        return { before, after: rows.length, rows };
    }""")
    assert result["after"] < result["before"]
    assert all("span" in r.lower() for r in result["rows"])


def test_no_matches_shows_a_message(page):
    open_filters(page)
    shown = page.evaluate("""() => {
        const sel = document.querySelector('#fLanguage');
        sel.closest('.dd').querySelector('.dd-btn').click();
        const panel = document.querySelector('.dd-panel:not([hidden])');
        const input = panel.querySelector('.dd-filter-input');
        input.value = 'zzzzzz';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return { rows: panel.querySelectorAll('.dd-item').length,
                 empty: !panel.querySelector('.dd-empty').hidden };
    }""")
    assert shown["rows"] == 0
    assert shown["empty"] is True


# ============================================================= keyboard


def test_enter_opens_the_panel(page):
    open_filters(page)
    page.evaluate("() => document.querySelector('#fStatus').closest('.dd').querySelector('.dd-btn').focus()")
    page.keyboard.press("Enter")
    page.wait_for_timeout(90)
    assert page.evaluate(
        "() => document.querySelectorAll('.dd-panel:not([hidden])').length") == 1


def test_arrows_move_and_enter_commits(page):
    open_filters(page)
    result = page.evaluate("""() => {
        const sel = document.querySelector('#fStatus');
        sel.value = sel.options[0].value;
        sel.closest('.dd').querySelector('.dd-btn').focus();
        return { start: sel.value, options: [...sel.options].map(o => o.value) };
    }""")
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)
    after = page.evaluate("() => document.querySelector('#fStatus').value")
    assert after == result["options"][1]


def test_escape_closes_without_changing(page):
    open_filters(page)
    before = page.evaluate("() => document.querySelector('#fStatus').value")
    page.evaluate("() => document.querySelector('#fStatus').closest('.dd').querySelector('.dd-btn').focus()")
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Escape")
    page.wait_for_timeout(80)
    assert page.evaluate("() => document.querySelector('#fStatus').value") == before
    assert page.evaluate(
        "() => document.querySelectorAll('.dd-panel:not([hidden])').length") == 0


def test_home_and_end_jump(page):
    open_filters(page)
    options = page.evaluate("() => [...document.querySelector('#fStatus').options].map(o => o.value)")
    page.evaluate("() => document.querySelector('#fStatus').closest('.dd').querySelector('.dd-btn').focus()")
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)
    assert page.evaluate("() => document.querySelector('#fStatus').value") == options[-1]


def test_typeahead_on_closed_trigger(page):
    """Pressing a letter jumps to a matching option, like a native select."""
    open_filters(page)
    page.evaluate("""() => {
        const sel = document.querySelector('#fLanguage');
        sel.value = 'en';
        sel.closest('.dd').querySelector('.dd-btn').focus();
    }""")
    page.keyboard.press("f")            # French
    page.wait_for_timeout(120)
    assert page.evaluate("() => document.querySelector('#fLanguage').value") == "fr"


# =========================================================== accessibility


def test_aria_roles_and_state(page):
    open_filters(page)
    aria = page.evaluate("""() => {
        const dd = document.querySelector('#fStatus').closest('.dd');
        const btn = dd.querySelector('.dd-btn');
        const closed = btn.getAttribute('aria-expanded');
        btn.click();
        const panel = document.querySelector('.dd-panel:not([hidden])');
        return {
            closed,
            opened: btn.getAttribute('aria-expanded'),
            haspopup: btn.getAttribute('aria-haspopup'),
            role: panel.getAttribute('role'),
            optionRole: panel.querySelector('.dd-item').getAttribute('role'),
            active: btn.getAttribute('aria-activedescendant'),
        };
    }""")
    assert aria["closed"] == "false"
    assert aria["opened"] == "true"
    assert aria["haspopup"] == "listbox"
    assert aria["role"] == "listbox"
    assert aria["optionRole"] == "option"
    assert aria["active"]


def test_no_page_errors(page):
    open_filters(page)
    page.evaluate("""() => {
        document.querySelectorAll('.dd-btn').forEach(b => { b.click(); });
        window.MangaDropdown.closeAll();
    }""")
    page.wait_for_timeout(150)
    dropdown_errors = [e for e in page.errors if "pywebview" not in e.lower()]
    assert dropdown_errors == []
