"""Regression tests for v1.4.6.

Covers:

* the "downloaded chapters" count on the manga page being wrong
* URLs carrying a query string returning zero chapters
* multi-genre search / browse
* the layout sitting in a fixed centred column
* keyboard shortcuts and other QOL additions
"""

import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ============================================ downloaded chapter counts


@pytest.mark.parametrize("variant", [
    "https://x.test/manga/a",
    "https://x.test/manga/a/",
    "http://x.test/manga/a",
    "https://www.x.test/manga/a",
    "https://x.test/manga/a?utm_source=t",
    "https://x.test/manga/a#top",
])
def test_library_key_survives_url_variants(variant):
    """Five of these seven variants used to miss the library entirely, so a
    downloaded manga looked untouched when reached by a different link."""
    from mangadl import library

    assert library._key(variant) == library._key("https://x.test/manga/a")


def test_library_key_keeps_distinct_manga_apart():
    """Normalising must not merge two different series."""
    from mangadl import library

    assert library._key("https://x.test/manga/a") != library._key("https://x.test/manga/b")
    assert library._key("https://x.test/m/a") != library._key("https://y.test/m/a")


def test_chapter_identity_ignores_a_changed_date():
    """Sources append a release date the site later edits."""
    from mangadl.library import _chapter_key

    assert _chapter_key("Chapter 02 21/02/2026") == _chapter_key("Chapter 02 22/02/2026")
    assert _chapter_key("Chapter 2") == _chapter_key("Chapter 02")
    assert _chapter_key("Chapter 1") != _chapter_key("Chapter 2")


def test_downloaded_count_matches_the_highlighted_rows():
    """The pill counted recorded chapters while the rows matched on the exact
    label, so a changed date made the two disagree."""
    from mangadl import library

    url = "https://x.test/manga/a"
    library.record_chapter(url, "A", "Chapter 01", pages=31)
    library.record_chapter(url, "A", "Chapter 02 21/02/2026", pages=30)

    listed = [{"name": "Chapter 01"},
              {"name": "Chapter 02 22/02/2026"},     # date edited by the site
              {"name": "Chapter 03"}]
    matched = library.match_downloaded(url, listed)

    assert matched == ["Chapter 01", "Chapter 02 22/02/2026"]
    names = [c["name"] for c in listed]
    assert all(m in names for m in matched), "every counted chapter is shown"


def test_downloaded_lookup_works_through_another_url_form():
    from mangadl import library

    library.record_chapter("https://x.test/manga/a/", "A", "Chapter 01", pages=1)
    listed = [{"name": "Chapter 01"}]
    assert library.match_downloaded("http://www.x.test/manga/a?ref=1", listed) == ["Chapter 01"]


def test_entry_keeps_a_usable_url():
    """The dict key is normalised, but the stored URL must stay openable."""
    from mangadl import library

    library.record_chapter("https://x.test/manga/a", "A", "Chapter 01", pages=1)
    entry = library.get_entry("https://x.test/manga/a")
    assert entry["url"].startswith("http")


def test_get_entry_is_used_instead_of_raw_indexing():
    """Indexing load_library() with a raw URL is the bug, not the fix."""
    src = read(os.path.join(ROOT, "mangadl", "gui", "__init__.py"))
    assert "load_library().get(url" not in src


def test_manga_page_matches_on_chapter_number():
    src = read(os.path.join(ROOT, "mangadl", "gui", "__init__.py"))
    assert "library.match_downloaded(url, chapters)" in src


# =================================================== URLs with a query


def test_series_path_drops_query_and_fragment():
    """A tracking parameter made every chapter link fail the prefix test, so
    the manga silently showed zero chapters."""
    from mangadl.sources.base import Source

    expected = "/manhwa/pure-love"
    for url in ("https://s.test/manhwa/pure-love",
                "https://s.test/manhwa/pure-love/",
                "https://s.test/manhwa/pure-love?ref=x",
                "https://s.test/manhwa/pure-love?utm_source=a&b=c",
                "https://s.test/manhwa/pure-love#chapters"):
        assert Source.series_path(url) == expected


@pytest.mark.parametrize("module", ["manhwaread", "mangadass", "manhwa18",
                                    "manga18club"])
def test_sources_use_the_shared_series_path(module):
    src = read(os.path.join(ROOT, "mangadl", "sources", module + ".py"))
    assert "self.series_path(manga_url)" in src
    assert 'series_path = re.sub(r"^https?://[^/]+"' not in src


# ========================================================= multi-genre


def test_split_genres_accepts_lists_and_strings():
    from mangadl.sources import split_genres

    assert split_genres("Action, Romance") == ["Action", "Romance"]
    assert split_genres("Action|Romance") == ["Action", "Romance"]
    assert split_genres(["Action", "Romance", "action"]) == ["Action", "Romance"]
    assert split_genres(None) == []
    assert split_genres("") == []


def test_browse_multi_intersects_per_source(monkeypatch):
    """AND must be a real intersection, and must not pair a hit from one
    source with a hit from another -- the same title has different URLs on
    different sites, so that would invent matches neither site agrees with."""
    from mangadl import sources

    data = {
        "Action": [
            {"title": "A", "url": "https://s1/a", "source": "s1"},
            {"title": "B", "url": "https://s1/b", "source": "s1"},
            {"title": "C", "url": "https://s2/c", "source": "s2"},
        ],
        "Romance": [
            {"title": "A", "url": "https://s1/a", "source": "s1"},
            {"title": "C", "url": "https://s2/c", "source": "s2"},
        ],
    }
    monkeypatch.setattr(sources, "browse_all",
                        lambda genre=None, **kw: list(data.get(genre, [])))

    both = sources.browse_multi(["Action", "Romance"], match="all",
                                limit=0, interleave=False)
    assert sorted(r["title"] for r in both) == ["A", "C"]
    assert all(r["matched_genres"] == ["Action", "Romance"] for r in both)


def test_browse_multi_any_is_a_union(monkeypatch):
    from mangadl import sources

    data = {
        "Action": [{"title": "A", "url": "https://s1/a", "source": "s1"}],
        "Romance": [{"title": "B", "url": "https://s1/b", "source": "s1"}],
    }
    monkeypatch.setattr(sources, "browse_all",
                        lambda genre=None, **kw: list(data.get(genre, [])))

    rows = sources.browse_multi(["Action", "Romance"], match="any",
                                limit=0, interleave=False)
    assert sorted(r["title"] for r in rows) == ["A", "B"]


def test_browse_multi_with_one_genre_delegates(monkeypatch):
    from mangadl import sources

    seen = {}

    def fake(genre=None, **kw):
        seen["genre"] = genre
        return []

    monkeypatch.setattr(sources, "browse_all", fake)
    sources.browse_multi(["Action"], limit=5)
    assert seen["genre"] == "Action"


def test_narrow_by_genres_keeps_untagged_results():
    """Sources that do not report tags must not vanish from the results."""
    from mangadl.gui import _narrow_by_genres

    rows = [{"title": "A", "tags": ["Action", "Romance"]},
            {"title": "B", "tags": ["Action"]},
            {"title": "C"}]
    assert [r["title"] for r in _narrow_by_genres(rows, ["Romance"], "all")] == ["A", "C"]
    assert [r["title"] for r in _narrow_by_genres(rows, ["Romance"], "any")] == ["A", "C"]


def test_frontend_tracks_several_genres():
    js = read(os.path.join(WEB, "app.js"))
    assert "let pickedGenres" in js
    assert "function toggleGenre" in js
    # chips must toggle, not replace the whole selection
    body = js[js.index("function renderGenreChips"):]
    body = body[:body.index("function updateFilterDot")]
    assert "toggleGenre" in body


def test_browse_request_forwards_the_genre_list():
    js = read(os.path.join(WEB, "app.js"))
    assert "genres: filters.genres" in js
    assert "genre_match: filters.genre_match" in js


def test_multi_genre_markup_and_styles_exist():
    html = read(os.path.join(WEB, "index.html"))
    css = read(os.path.join(WEB, "style.css"))
    for node in ("pickedGenres", "pickedGenreList", "clearGenresBtn",
                 "fGenreMatch", "genreMatchGroup"):
        assert f'id="{node}"' in html, node
    for rule in (".picked-genres", ".pg-chip", ".pg-list"):
        assert rule in css, rule


# ============================================ genre endpoints that 404'd


def test_manhwa18_uses_the_singular_genre_path():
    """/genres/, /genre/ and /manga-genre/ are all 404 on that site."""
    src = read(os.path.join(ROOT, "mangadl", "sources", "manhwa18.py"))
    body = src[src.index("def browse"):src.index("def genres")]
    assert "/webtoon-genre/" in body
    assert '{SITE}/genres/' not in body


def test_nhentai_falls_back_for_an_unknown_tag():
    """Shared genre labels ("action") are not nhentai tags and 404."""
    from mangadl.sources.nhentai import NhentaiSource

    src = read(os.path.join(ROOT, "mangadl", "sources", "nhentai.py"))
    body = src[src.index("def browse"):src.index("def genres")]
    assert "self.GENRES" in body
    assert "/search/?q=" in body
    assert "action" not in {g.lower() for g in NhentaiSource.GENRES}


# ============================================================== layout


def test_grids_are_not_pinned_to_a_narrow_centred_column():
    """Measured before the change: at 1920px the grid used 1080px and left
    42% of the content area empty, still showing only 6 columns."""
    css = read(os.path.join(WEB, "style.css"))
    block = css[css.index(".results-grid {"):]
    block = block[:block.index("}")]
    assert "max-width: 1080px" not in block
    assert "var(--content-max" in block
    assert "margin: 0 auto" not in block


def test_content_width_variables_are_defined():
    css = read(os.path.join(WEB, "style.css"))
    for var in ("--content-max:", "--content-wide:", "--content-narrow:"):
        assert var in css, var


def test_manga_layout_also_widens():
    css = read(os.path.join(WEB, "style.css"))
    block = css[css.index(".manga-layout {"):]
    block = block[:block.index("}")]
    assert "max-width: 1080px" not in block
    assert "var(--content-max" in block


# =========================================================== shortcuts


def test_shortcuts_are_declared_as_data():
    """The help overlay is generated from the same list the handler uses, so
    the two cannot drift apart."""
    js = read(os.path.join(WEB, "app.js"))
    assert "const SHORTCUTS" in js
    assert "function renderShortcuts" in js
    assert "SHORTCUTS.forEach" in js


def test_shortcuts_never_fire_while_typing():
    js = read(os.path.join(WEB, "app.js"))
    assert "function isTypingTarget" in js
    handler = js[js.index('document.addEventListener("keydown"'):]
    handler = handler[:handler.index("\n});")]
    assert "isTypingTarget(document.activeElement)" in handler
    # modifier combos belong to the browser / OS
    assert "e.ctrlKey || e.metaKey || e.altKey" in handler


def test_shortcuts_do_not_hijack_the_lock_screen():
    js = read(os.path.join(WEB, "app.js"))
    handler = js[js.index('document.addEventListener("keydown"'):]
    handler = handler[:handler.index("\n});")]
    assert "lockOverlay" in handler


def test_shift_slash_does_not_trigger_focus_search():
    """Chromium reports Shift+/ as key "/" with shiftKey set, which matched
    "focus search" before the help overlay could open."""
    js = read(os.path.join(WEB, "app.js"))
    body = js[js.index("function matchShortcut"):]
    body = body[:body.index("\n}")]
    assert "shift" in body


def test_shortcut_targets_exist_in_the_markup():
    """A shortcut pointing at a missing element would silently do nothing."""
    html = read(os.path.join(WEB, "index.html"))
    for node in ("searchInput", "selectAllBtn", "selectNoneBtn", "selectNewBtn",
                 "selectInvertBtn", "downloadBtn", "addCartBtn", "bookmarkBtn",
                 "shortcutsOverlay", "shortcutsBody", "settingsShortcuts"):
        assert f'id="{node}"' in html, node


def test_shortcut_styles_exist():
    css = read(os.path.join(WEB, "style.css"))
    for rule in (".sc-overlay", ".sc-panel", ".sc-row", ".sc-keys", "kbd {"):
        assert rule in css, rule


# ================================================================= QOL


def test_invert_acts_on_visible_rows_only():
    """Selecting filtered-out chapters would download rows you cannot see."""
    js = read(os.path.join(WEB, "app.js"))
    body = js[js.index('$("selectInvertBtn")'):]
    body = body[:body.index("});")]
    assert "visibleChapterIndices()" in body


def test_copy_helper_has_a_fallback():
    """WebView2 does not always grant clipboard-write."""
    js = read(os.path.join(WEB, "app.js"))
    body = js[js.index("async function copyText"):]
    body = body[:body.index("\n}\n")]
    assert "navigator.clipboard" in body
    assert "execCommand" in body


def test_refresh_covers_every_view():
    js = read(os.path.join(WEB, "app.js"))
    body = js[js.index("function refreshCurrentView"):]
    for view in ("search", "bookmarks", "library", "updates", "insights", "manga"):
        assert f'"{view}"' in body, view
