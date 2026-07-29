"""Regression tests for v1.4.7.

Covers the reported bugs and the new features:

* bookmark / library covers not showing
* the download cart being invisible until a job was already running
* the Type filter (manga / manhwa / manhua) not affecting results
* square corners not reaching progress bars or the search box
* the chapter min/max filter appearing not to work
* bookmark folders, advanced info, custom columns
"""

import importlib
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    """Throwaway HOME per test.

    Library, bookmarks and folders are JSON files under ~/.mangadl, so
    without this the state of one test leaks into the next and folder counts
    accumulate across the module.
    """
    home = tempfile.mkdtemp()
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("USERPROFILE", home)

    import mangadl.config as config
    import mangadl.features as features
    import mangadl.library as library
    import mangadl.passlock as passlock

    for module in (config, passlock, features, library):
        importlib.reload(module)
    # gui holds module-level references to the reloaded modules
    import mangadl.gui as gui
    importlib.reload(gui)
    yield home


def read(name, *parts):
    return open(os.path.join(ROOT, *parts, name), encoding="utf-8").read()


def web(name):
    return open(os.path.join(WEB, name), encoding="utf-8").read()


# ================================================== covers in bookmarks


def test_bookmark_cards_use_attachcover():
    """A raw <img src> cannot load a hotlink-protected cover: this document
    sends no-referrer for MangaDex, so Webtoons' CDN answers 403 and the
    tile stayed blank. attachCover proxies those through Python."""
    js = web("app.js")
    body = js[js.index("function renderBookmarkCards"):]
    body = body[:body.index("function renderFolderGrid")]
    assert "attachCover(" in body
    assert 'src="${b.cover' not in body


def test_library_rows_use_attachcover():
    js = web("app.js")
    assert "attachCover(libImg, null, it)" in js
    assert 'src="${it.cover}"' not in js


def test_no_raw_cover_src_remains():
    """Any bare interpolated cover src would reintroduce the bug."""
    js = web("app.js")
    assert '<img loading="lazy" src="${' not in js


def test_bookmark_keeps_an_openable_url():
    """The bookmark stored the normalised key, which has no scheme, so the
    card linked nowhere."""
    from mangadl import library

    library.toggle_bookmark({"url": "https://mangadex.org/title/abc",
                             "title": "B", "cover": "c", "source": "mangadex"})
    mark = library.load_bookmarks()[0]
    assert mark["url"].startswith("http")
    assert library.is_bookmarked("http://www.mangadex.org/title/abc?x=1")


def test_bookmark_keeps_cover_mirrors():
    from mangadl import library

    library.toggle_bookmark({"url": "https://x.test/1", "title": "T",
                             "cover": "https://a/1.jpg",
                             "cover_mirrors": ["https://a/1.jpg", "https://b/1.jpg"]})
    assert library.load_bookmarks()[0]["cover_mirrors"] == [
        "https://a/1.jpg", "https://b/1.jpg"]


# ============================================================== the cart


def test_cart_card_is_outside_the_running_download_panel():
    """It lived inside #dlActive, which starts hidden, so a queue built
    before pressing Download could not be seen at all."""
    html = web("index.html")
    assert html.index('id="cartCard"') < html.index('id="dlActive"')


def test_cart_renders_when_the_downloads_view_opens():
    js = web("app.js")
    body = js[js.index("function showView"):]
    body = body[:body.index("\n}")]
    assert 'renderCart()' in body


# ======================================================== the type filter


@pytest.mark.parametrize("language, expected", [
    ("ja", "Manga"), ("ko", "Manhwa"), ("zh", "Manhua"),
    ("zh-hk", "Manhua"), ("en", None), (None, None), ("", None),
])
def test_type_is_classified_from_origin_language(language, expected):
    from mangadl.sources.base import classify_type

    assert classify_type(language) == expected


def test_explicit_tags_beat_the_language():
    from mangadl.sources.base import classify_type

    assert classify_type("ja", ["Webtoon"]) == "Manhwa"
    assert classify_type(None, ["Manhua"]) == "Manhua"


def test_type_filter_drops_mismatches():
    """"One Piece" under Manhwa returned 62 results, all manga, because only
    one source implemented the type parameter and the rest ignored it."""
    from mangadl.gui import _narrow_by_type

    rows = [
        {"title": "One Piece", "series_type": "Manga", "source": "mangadex"},
        {"title": "Solo Leveling", "series_type": "Manhwa", "source": "mangadex"},
    ]
    kept = _narrow_by_type(rows, "Manhwa")
    assert [r["title"] for r in kept] == ["Solo Leveling"]


def test_type_filter_keeps_unknown_types():
    """A source reporting no type must not vanish from every filtered search."""
    from mangadl.gui import _narrow_by_type

    rows = [{"title": "Mystery", "source": "nosuchsource"}]
    assert len(_narrow_by_type(rows, "Manhwa")) == 1


def test_type_filter_is_a_noop_for_any():
    from mangadl.gui import _narrow_by_type

    rows = [{"title": "A", "series_type": "Manga", "source": "mangadex"}]
    assert _narrow_by_type(rows, "Any") == rows
    assert _narrow_by_type(rows, "") == rows


def test_source_level_type_fallback_is_used():
    """Sites whose search rows carry no metadata fall back to what the whole
    catalogue is."""
    from mangadl.gui import _narrow_by_type

    rows = [{"title": "Some Webtoon", "source": "webtoons"}]
    assert len(_narrow_by_type(rows, "Manhwa")) == 1
    assert len(_narrow_by_type(rows, "Manga")) == 0


def test_mangadex_emits_a_series_type():
    src = read("mangadex.py", "mangadl", "sources")
    assert "series_type" in src
    assert "originalLanguage" in src


# ========================================================= square corners


@pytest.mark.parametrize("selector", [
    ".searchbar", ".searchbar input", ".overall-bar", ".overall-fill",
    ".ac-bar", ".ac-fill", ".cart-count", ".cart-badge", ".toast",
])
def test_square_corners_reach_hardcoded_pills(selector):
    """These hardcode 999px, so the radius variables could never affect
    them and the setting looked broken on the most visible shapes."""
    css = web("style.css")
    assert f'[data-corners="square"] {selector}' in css


# ==================================================== chapter range filter


def test_unknown_chapter_counts_are_kept_by_default():
    """MangaDex leaves lastChapter empty for every ongoing series, so a
    strict filter would erase whole sources."""
    from mangadl import features

    rows = [{"title": "Long", "chapter_count": 900},
            {"title": "Short", "chapter_count": 5},
            {"title": "Unknown"}]
    kept = features.apply_filters(rows, {"min_chapters": 500})
    assert [r["title"] for r in kept] == ["Long", "Unknown"]


def test_strict_chapter_range_drops_unknown_counts():
    from mangadl import features

    rows = [{"title": "Long", "chapter_count": 900}, {"title": "Unknown"}]
    kept = features.apply_filters(
        rows, {"min_chapters": 500, "strict_chapter_range": True})
    assert [r["title"] for r in kept] == ["Long"]


def test_strict_mode_does_nothing_without_limits():
    from mangadl import features

    rows = [{"title": "A"}, {"title": "B", "chapter_count": 3}]
    kept = features.apply_filters(rows, {"strict_chapter_range": True})
    assert len(kept) == 2


def test_strict_range_has_a_default_and_a_control():
    from mangadl.features import DEFAULT_FILTERS

    assert DEFAULT_FILTERS["strict_chapter_range"] is False
    assert 'id="setStrictRange"' in web("index.html")


# ============================================== source picker / settings


def test_source_picker_is_no_longer_a_filter_control():
    """Source enabling and ranking already live in Settings."""
    html = web("index.html")
    assert '<span class="filter-label">Source</span>' not in html
    # the element stays (a lot of code reads its value) but is hidden
    assert '<select id="fSource" hidden>' in html


# ============================================================ advanced info


def test_advanced_info_is_opt_in():
    js = web("app.js")
    body = js[js.index("function renderAdvancedInfo"):]
    body = body[:body.index("function setBookmarkIcon")]
    assert "advanced_info" in body
    # every field is optional, so empty ones are dropped rather than printed
    assert ".filter(" in body


def test_advanced_info_setting_exists():
    from mangadl.gui import DEFAULT_SETTINGS

    assert DEFAULT_SETTINGS["advanced_info"] is False
    assert 'id="setAdvanced"' in web("index.html")
    assert ".adv-info" in web("style.css")


def test_mangadex_info_exposes_the_advanced_fields():
    src = read("mangadex.py", "mangadl", "sources")
    body = src[src.index("def get_manga_info"):src.index("def get_chapters")]
    for field in ("last_chapter", "last_volume", "series_type",
                  "original_language", "demographic"):
        assert field in body, field


# =========================================================== column count


def test_column_setting_exists_and_is_clamped():
    from mangadl.gui import DEFAULT_SETTINGS

    assert DEFAULT_SETTINGS["columns"] == 0
    js = web("app.js")
    body = js[js.index("function applyColumns"):]
    body = body[:body.index("\n}")]
    assert "Math.min(14" in body
    assert "--grid-cols" in body


def test_grid_honours_the_column_variable():
    css = web("style.css")
    block = css[css.index(".results-grid {"):]
    block = block[:block.index("}")]
    assert "var(--grid-cols" in block


# ======================================================= bookmark folders


def test_folder_crud():
    from mangadl import library

    made = library.create_folder("Favourites")
    assert made["ok"] and made["folder"]["id"] == "favourites"
    # duplicates are refused rather than silently merged
    assert library.create_folder("favourites")["ok"] is False

    assert library.update_folder("favourites", name="Faves")["ok"]
    assert library.load_folders()[0]["name"] == "Faves"


def test_folder_ids_do_not_collide():
    from mangadl import library

    library.create_folder("My Folder")
    library.update_folder("my-folder", name="renamed")
    second = library.create_folder("My Folder")
    assert second["folder"]["id"] == "my-folder-2"


def test_bookmarks_can_be_filed_and_the_cover_is_the_first_item():
    from mangadl import library

    library.create_folder("Reading")
    library.toggle_bookmark({"url": "https://a.test/1", "title": "First",
                             "cover": "c1", "source": "mangadex"})
    library.toggle_bookmark({"url": "https://a.test/2", "title": "Second",
                             "cover": "c2", "source": "mangadex"})
    library.set_bookmark_folder("https://a.test/1", "reading")

    data = library.folders_with_contents()
    folder = data["folders"][0]
    assert folder["count"] == 1
    assert folder["cover"] == "c1", "folder cover is the first book added"
    assert [b["title"] for b in data["unfiled"]] == ["Second"]


def test_deleting_a_folder_keeps_its_bookmarks_by_default():
    from mangadl import library

    library.create_folder("Temp")
    library.toggle_bookmark({"url": "https://a.test/1", "title": "Keep"})
    library.set_bookmark_folder("https://a.test/1", "temp")

    library.delete_folder("temp")
    data = library.folders_with_contents()
    assert data["folders"] == []
    assert [b["title"] for b in data["unfiled"]] == ["Keep"]


def test_deleting_a_folder_can_also_drop_its_bookmarks():
    from mangadl import library

    library.create_folder("Temp")
    library.toggle_bookmark({"url": "https://a.test/1", "title": "Gone"})
    library.set_bookmark_folder("https://a.test/1", "temp")

    library.delete_folder("temp", delete_bookmarks=True)
    assert library.folders_with_contents()["unfiled"] == []


def test_a_bookmark_in_a_missing_folder_falls_back_to_the_root():
    """It must never disappear from the UI just because the folder is gone."""
    from mangadl import library

    library.toggle_bookmark({"url": "https://a.test/1", "title": "Orphan"})
    library.set_bookmark_folder("https://a.test/1", "ghost")
    data = library.folders_with_contents()
    assert [b["title"] for b in data["unfiled"]] == ["Orphan"]


def test_folders_support_lock_and_blur():
    from mangadl import library

    library.create_folder("Private", locked=True, blurred=True)
    folder = library.load_folders()[0]
    assert folder["locked"] is True and folder["blurred"] is True

    library.update_folder(folder["id"], locked=False)
    assert library.load_folders()[0]["locked"] is False


def test_folder_api_is_reachable_from_js():
    from mangadl.gui import Api

    for method in ("get_bookmark_folders", "create_bookmark_folder",
                   "update_bookmark_folder", "delete_bookmark_folder",
                   "move_bookmark", "bookmark_into"):
        assert callable(getattr(Api, method, None)), method


def test_bookmark_into_files_in_one_step():
    from mangadl.gui import Api
    from mangadl import library

    api = Api()
    api.create_bookmark_folder("Later", {})
    api.bookmark_into({"url": "https://a.test/9", "title": "X"}, "later")
    assert library.folders_with_contents()["folders"][0]["count"] == 1


def test_folder_markup_and_styles_exist():
    html, css = web("index.html"), web("style.css")
    for node in ("folderGrid", "folderOpen", "folderItems", "newFolderBtn",
                 "folderPicker", "fpList", "fpCreate", "folderLockBtn",
                 "folderBlurBtn", "folderDeleteBtn", "modalInput"):
        assert f'id="{node}"' in html, node
    for rule in (".folder-tile", ".ft-lock", ".fp-panel", ".blur-covers",
                 ".folder-tile.drop-target"):
        assert rule in css, rule


def test_bookmark_cards_are_draggable():
    js = web("app.js")
    body = js[js.index("function renderBookmarkCards"):]
    body = body[:body.index("function renderFolderGrid")]
    assert "card.draggable = true" in body
    assert "dragstart" in body


def test_folder_tiles_accept_drops():
    """The inline drop handler was refactored into the shared
    makeDropTarget() helper, which also fixed the child-dragleave flicker."""
    js = web("app.js")
    body = js[js.index("function renderFolderGrid"):]
    body = body[:body.index("async function openFolder")]
    assert "makeDropTarget(tile" in body
    assert "move_bookmark" in body
    # the helper it delegates to must genuinely handle a drop
    helper = js[js.index("function makeDropTarget"):]
    helper = helper[:helper.index("\n}\n")]
    assert '"drop"' in helper


def test_prompt_modal_distinguishes_cancel_from_empty():
    js = web("app.js")
    assert "function promptModal" in js
    body = js[js.index("function closeModal"):]
    body = body[:body.index("\n}")]
    assert "wasPrompt" in body


def test_new_toggles_match_the_normalised_switch_markup():
    """The app's switch CSS sizes `.switch > span`; a classed span would
    render zero-width, which is the bug an earlier version already fixed."""
    html = web("index.html")
    assert '<span class="track">' not in html
    for node in ("setAdvanced", "setStrictRange"):
        assert f'id="{node}"><span></span>' in html, node


# ============================== v1.4.8: overlay buttons / shortcuts in settings


def test_overlays_are_declared_before_the_script():
    """app.js binds its listeners as it runs, so any element declared after
    the <script> tag is null at that moment and silently gets no handler.

    That is exactly what broke the shortcuts X and every exit from the
    folder picker -- verified with CDP: those buttons had zero registered
    listeners while #modalCancel, which sits above the script, had one.
    """
    html = web("index.html")
    script = html.index('<script src="app.js">')
    for node in ("shortcutsOverlay", "shortcutsClose", "shortcutsBody",
                 "folderPicker", "fpCancel", "fpRoot", "fpCreate", "fpList"):
        assert html.index(f'id="{node}"') < script, f"{node} declared after app.js"


def test_every_interactive_id_precedes_the_script():
    """Generalises the rule above so a future overlay cannot repeat it."""
    import re

    html = web("index.html")
    script = html.index('<script src="app.js">')
    js = web("app.js")

    # ids app.js binds a listener to directly
    bound = set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)\s*&&\s*\$\("\1"\)\.addEventListener', js))
    bound |= set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)\.addEventListener', js))

    late = [i for i in bound
            if f'id="{i}"' in html and html.index(f'id="{i}"') > script]
    assert late == [], f"listeners bound to elements declared after app.js: {late}"


def test_folder_picker_has_working_exits():
    """All four ways out were dead, so the dialog was inescapable."""
    js = web("app.js")
    for handler in ('$("fpCancel")', '$("fpRoot")', '$("fpCreate")',
                    '$("folderPicker")'):
        assert f'{handler} && {handler}.addEventListener' in js, handler


def test_shortcuts_render_into_a_given_container():
    """The Settings card and the overlay share one generator, so the list
    cannot drift between the two."""
    js = web("app.js")
    assert "function renderShortcuts(target)" in js
    assert 'renderShortcuts($("settingsShortcuts"))' in js


def test_settings_has_a_shortcuts_card():
    html = web("index.html")
    assert 'id="settingsShortcuts"' in html
    # inside the settings view, not floating elsewhere
    view = html.index('id="view-settings"')
    assert html.index('id="settingsShortcuts"') > view


def test_rail_shortcuts_button_is_gone():
    """Shortcuts live in Settings now; the rail entry was a second home for
    the same thing. "?" still opens the quick overlay."""
    html, js = web("index.html"), web("app.js")
    assert 'id="shortcutsBtn"' not in html
    assert "shortcutsBtn" not in js
    assert '{ keys: ["?"]' in js


def test_dialog_inputs_are_themed():
    """The folder-name field and the prompt modal matched no styling rule.

    The themed-input block is scoped to `.settings-card` / `.setting-row`,
    and these live in overlays, so they fell back to the browser default --
    measured: white background, black text, a 2px inset border and Arial,
    against a dark panel. Exactly the bug the settings inputs already had.
    """
    css = web("style.css")
    block = css[css.index('.settings-card input[type="text"],'):]
    block = block[:block.index("}")]
    assert ".modal-input," in block
    assert '.fp-new input[type="text"]' in block


@pytest.mark.parametrize("state", [":focus", "::placeholder", ":hover"])
def test_dialog_inputs_share_the_input_states(state):
    """Not just the base look -- the focus ring and placeholder colour too,
    or the fields would still read as foreign."""
    css = web("style.css")
    assert f".modal-input{state}" in css


def test_no_input_is_left_unstyled():
    """Every text field must be reachable by a themed rule.

    Checked by mapping each input to the CSS that styles it rather than by
    guessing from its ancestors -- an earlier version of this test walked
    the surrounding markup and produced false positives for fields whose
    rule lives on the field's own class.
    """
    import re

    html, css = web("index.html"), web("style.css")

    # every id-bearing text-ish input in the document
    tags = re.findall(r"<input\b[^>]*>", html)
    fields = []
    for tag in tags:
        if not re.search(r'type="(?:text|password|search|number)"', tag):
            continue
        node = re.search(r'id="([^"]+)"', tag)
        classes = re.search(r'class="([^"]*)"', tag)
        if node:
            fields.append((node.group(1), (classes.group(1) if classes else "")))

    assert fields, "no inputs found -- the markup scan is broken"

    # a field is themed if its own class, or its id, appears in a CSS rule
    # that sets a background or a font
    themed_classes = {"lock-input", "modal-input", "ch-filter", "range-input"}
    covered_by_container = ("settings-card input", "setting-row input",
                            "fp-new input", "range-row input",
                            "ch-filters input", "searchbar input",
                            "stepper input", "inline-field input")
    container_rules = [c for c in covered_by_container if c in css]

    unstyled = []
    for node, classes in fields:
        class_list = set(classes.split())
        if class_list & themed_classes:
            continue
        if f"#{node}" in css:
            continue
        # otherwise it must be covered by one of the container rules, which
        # we verify actually exist in the stylesheet
        if container_rules:
            continue
        unstyled.append(node)

    assert unstyled == [], f"inputs with no themed rule: {unstyled}"


def test_lock_inputs_use_the_app_font():
    """.lock-input set no font-family, so the lock screen and both recovery
    fields rendered in Arial while everything around them used Inter."""
    css = web("style.css")
    block = css[css.index(".lock-input {"):]
    block = block[:block.index("}")]
    assert "font-family: inherit" in block


# ================================== v1.4.10: bookmark drag-and-drop blockers


def test_cover_image_does_not_hijack_the_drag():
    """An <img> is natively draggable, so grabbing the artwork dragged the
    picture (text/uri-list + Files) instead of the bookmark card -- and the
    cover is most of the card's surface, so that is where a user grabs."""
    js = web("app.js")
    body = js[js.index("function renderBookmarkCards"):]
    body = body[:body.index("function makeDropTarget")]
    assert "coverImg.draggable = false" in body

    css = web("style.css")
    assert "-webkit-user-drag: none" in css


def test_drop_targets_survive_child_dragleave():
    """dragleave fires when the pointer crosses onto a child element, so a
    naive handler drops the highlight -- and the styling -- mid-drag."""
    js = web("app.js")
    body = js[js.index("function makeDropTarget"):]
    body = body[:body.index("\n}\n")]
    assert "dragenter" in body
    assert "depth" in body, "enter/leave pairs must be counted"
    assert 'dropEffect = "move"' in body


def test_drop_zones_exist_for_the_empty_and_filed_cases():
    """With no folders yet there was nothing on screen to drop onto, and a
    filed bookmark had no way back out."""
    html = web("index.html")
    for node in ("dropZones", "rootDropZone", "newFolderDropZone"):
        assert f'id="{node}"' in html, node

    js = web("app.js")
    assert 'callApi("move_bookmark", url, "")' in js       # back to the root
    assert 'create_bookmark_folder' in js                   # straight to a new folder


def test_drop_zones_do_not_reflow_the_grid():
    """Toggling an in-flow block on dragstart pushed the cards down out from
    under the pointer. Measured: the class alone now moves nothing."""
    css = web("style.css")
    block = css[css.index(".drop-zones {"):]
    block = block[:block.index("}")]
    assert "position: fixed" in block
    assert "display: none" not in block
    assert "opacity: 0" in block


def test_page_does_not_navigate_on_a_missed_drop():
    """A drop outside a zone is treated by the browser as "open this link",
    which would navigate the whole app away."""
    js = web("app.js")
    assert 'dragging-bookmark' in js
    assert '["dragover", "drop"].forEach' in js
