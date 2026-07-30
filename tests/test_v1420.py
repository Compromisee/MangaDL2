"""Regression tests for v1.4.20 -- the CBZ cover rebuilder.

The tool walks a folder tree, recovers a series title from each ``.cbz``
filename, offers covers from every source, and writes the chosen one as
``cover.jpg`` **beside that archive**.

Two rules carry the risk, and both are tested hard here:

* a folder holding several different series is split so each cover lands in
  the right place -- and a folder that is already tidy is never touched;
* titles must survive every naming convention, MangaDL's own included, or
  the search matches nothing.
"""

import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def make(tmp_path, *relative):
    """Create empty files at the given relative paths."""
    for item in relative:
        path = tmp_path / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    return str(tmp_path)


# ======================================================== title recovery


@pytest.mark.parametrize("filename,expected", [
    # MangaDL's own output -- these are the shapes downloader.py produces
    ("Afterlife Diner - Chapters 001.cbz", "Afterlife Diner"),
    ("Afterlife Diner - Chapters 001-050.cbz", "Afterlife Diner"),
    ("Afterlife Diner - Chapters 001-003, 007-008, 020.cbz", "Afterlife Diner"),
    ("Afterlife Diner - Chapter 005.cbz", "Afterlife Diner"),
    ("Martial God Chat Group - Chapters 001-027.cbz", "Martial God Chat Group"),
    # third-party conventions
    ("[Group] Solo Leveling - c045 (2024) [1080p].cbz", "Solo Leveling"),
    ("Solo Leveling v03.cbz", "Solo Leveling"),
    ("One Piece Ch. 1050.cbz", "One Piece"),
    ("Berserk #12.cbz", "Berserk"),
    ("Nano.Machine.Chapter.5.cbz", "Nano Machine"),
    ("Tower of God - 005.cbz", "Tower of God"),
    ("The Beginning After The End Vol 3.cbz", "The Beginning After The End"),
    ("Eleceed - Episode 200.cbz", "Eleceed"),
    ("Omniscient Reader [Official Colored] c001-c010.cbz", "Omniscient Reader"),
    # a number that is part of the title, not an index
    ("Series 2 - Chapters 001.cbz", "Series 2"),
    ("Kingdom 2.cbz", "Kingdom 2"),
    # non-latin titles must survive intact
    ("\u30ef\u30f3\u30d4\u30fc\u30b9 - Chapters 001.cbz", "\u30ef\u30f3\u30d4\u30fc\u30b9"),
])
def test_clean_title(filename, expected):
    from mangadl.covers import clean_title

    assert clean_title(filename) == expected


def test_clean_title_never_returns_empty():
    """A title stripped to "" would search for nothing and match everything,
    so the least-stripped form is kept instead."""
    from mangadl.covers import clean_title

    for name in ("Chapter 5.cbz", "v03.cbz", "[Group].cbz", "001.cbz"):
        assert clean_title(name), name


def test_clean_title_handles_junk():
    from mangadl.covers import clean_title

    assert clean_title("") == ""
    assert clean_title(None) == ""


def test_series_key_groups_case_and_punctuation_variants():
    from mangadl.covers import series_key

    assert series_key("Solo Leveling - Chapter 1.cbz") == \
        series_key("solo.leveling.c002.cbz")
    assert series_key("Nano Machine v1.cbz") != series_key("One Piece v1.cbz")


# ============================================================== scanning


def test_scan_finds_archives_recursively(tmp_path):
    from mangadl.covers import scan

    root = make(tmp_path,
                "A/Series One - Chapters 001.cbz",
                "B/deep/nested/Series Two - Chapter 003.cbz")
    titles = {g["title"] for g in scan(root)}
    assert titles == {"Series One", "Series Two"}


def test_a_tidy_folder_is_never_reorganised(tmp_path):
    """One series alone in its folder must be left exactly where it is."""
    from mangadl.covers import scan

    root = make(tmp_path,
                "Afterlife Diner/Afterlife Diner - Chapters 001.cbz",
                "Afterlife Diner/Afterlife Diner - Chapters 002.cbz")
    groups = scan(root)
    assert len(groups) == 1
    assert groups[0]["needs_move"] is False
    assert groups[0]["target_dir"] == groups[0]["directory"]


def test_mixed_folder_gives_each_series_its_own_target(tmp_path):
    """Several series loose in one folder: a single cover.jpg there would be
    wrong for all but one of them."""
    from mangadl.covers import scan

    root = make(tmp_path,
                "Mixed/Solo Leveling - Chapters 001-010.cbz",
                "Mixed/Solo Leveling - Chapters 011-020.cbz",
                "Mixed/Nano Machine - Chapter 005.cbz",
                "Mixed/[Grp] Tower of God v03 (2024).cbz")
    groups = {g["title"]: g for g in scan(root)}

    assert set(groups) == {"Solo Leveling", "Nano Machine", "Tower of God"}
    assert all(g["needs_move"] for g in groups.values())
    assert groups["Solo Leveling"]["target_dir"].endswith("Solo Leveling")
    # the two Solo Leveling archives group together
    assert len(groups["Solo Leveling"]["archives"]) == 2


def test_scan_ignores_the_raw_page_folders(tmp_path):
    """The downloader leaves raw/ behind; it holds images, not archives."""
    from mangadl.covers import scan

    root = make(tmp_path,
                "Series/Series - Chapters 001.cbz",
                "Series/raw/Chapter 1/001.jpg")
    assert len(scan(root)) == 1


def test_existing_cover_is_detected(tmp_path):
    from mangadl.covers import existing_cover, scan

    root = make(tmp_path, "S/S - Chapters 001.cbz", "S/cover.jpg")
    assert existing_cover(os.path.join(root, "S"))
    assert scan(root)[0]["has_cover"] is True


def test_plan_skips_folders_that_already_have_a_cover(tmp_path):
    from mangadl.covers import plan

    root = make(tmp_path,
                "Has/Has - Chapters 001.cbz", "Has/cover.jpg",
                "Needs/Needs - Chapters 001.cbz")
    assert [g["title"] for g in plan(root)] == ["Needs"]
    assert len(plan(root, overwrite=True)) == 2


def test_an_empty_cover_file_does_not_count(tmp_path):
    from mangadl.covers import existing_cover

    root = make(tmp_path, "S/S - Chapters 001.cbz")
    open(os.path.join(root, "S", "cover.jpg"), "w").close()   # 0 bytes
    assert existing_cover(os.path.join(root, "S")) is None


def test_scan_of_a_missing_root_is_empty_not_an_error():
    from mangadl.covers import scan

    assert scan("/no/such/place") == []
    assert scan("") == []


# =============================================================== moving


def test_isolate_moves_only_mixed_groups(tmp_path):
    from mangadl.covers import isolate, scan

    root = make(tmp_path,
                "Mixed/Solo Leveling - Chapters 001.cbz",
                "Mixed/Nano Machine - Chapter 005.cbz",
                "Tidy/Tidy - Chapters 001.cbz")
    for group in scan(root):
        isolate(group)

    assert os.path.isfile(os.path.join(
        root, "Mixed", "Solo Leveling", "Solo Leveling - Chapters 001.cbz"))
    assert os.path.isfile(os.path.join(
        root, "Mixed", "Nano Machine", "Nano Machine - Chapter 005.cbz"))
    # the tidy one stayed put
    assert os.path.isfile(os.path.join(root, "Tidy", "Tidy - Chapters 001.cbz"))


def test_isolate_is_idempotent(tmp_path):
    """Running the tool twice must not nest folders inside folders."""
    from mangadl.covers import isolate, scan

    root = make(tmp_path,
                "Mixed/A Series - Chapters 001.cbz",
                "Mixed/B Series - Chapters 001.cbz")
    for group in scan(root):
        isolate(group)
    second = scan(root)
    assert all(not g["needs_move"] for g in second)
    for group in second:
        isolate(group)
    assert not os.path.isdir(os.path.join(root, "Mixed", "A Series", "A Series"))


def test_isolate_never_overwrites_an_existing_file(tmp_path):
    from mangadl.covers import isolate, scan

    root = make(tmp_path,
                "Mixed/A Series - Chapters 001.cbz",
                "Mixed/B Series - Chapters 001.cbz",
                "Mixed/A Series/A Series - Chapters 001.cbz")
    before = read(os.path.join(root, "Mixed", "A Series",
                               "A Series - Chapters 001.cbz"))
    for group in scan(root):
        if group["needs_move"]:
            isolate(group)
    # the original survives untouched...
    assert read(os.path.join(root, "Mixed", "A Series",
                             "A Series - Chapters 001.cbz")) == before
    # ...and the incoming file was renamed rather than clobbering it
    names = os.listdir(os.path.join(root, "Mixed", "A Series"))
    assert any("(2)" in n for n in names), names


def test_dry_run_moves_nothing(tmp_path):
    from mangadl.covers import isolate, scan

    root = make(tmp_path,
                "Mixed/A Series - Chapters 001.cbz",
                "Mixed/B Series - Chapters 001.cbz")
    for group in scan(root):
        isolate(group, dry_run=True)
    assert sorted(os.listdir(os.path.join(root, "Mixed"))) == [
        "A Series - Chapters 001.cbz", "B Series - Chapters 001.cbz"]


# ============================================================== ranking


def test_candidates_rank_exact_titles_first():
    """A fuzzy hit on a big catalogue is usually a different series."""
    from mangadl import covers

    rows = [
        {"title": "Something Else", "cover": "c1", "source": "a",
         "source_name": "A", "url": "u1"},
        {"title": "Solo Leveling", "cover": "c2", "source": "b",
         "source_name": "B", "url": "u2"},
        {"title": "Solo Leveling Ragnarok", "cover": "c3", "source": "c",
         "source_name": "C", "url": "u3"},
    ]
    covers.search_all = None            # ensure the stub below is used
    import mangadl.sources as sources_module
    original = sources_module.search_all
    sources_module.search_all = lambda *a, **k: rows
    try:
        ranked = covers.candidates("Solo Leveling")
    finally:
        sources_module.search_all = original

    assert ranked[0]["title"] == "Solo Leveling"
    assert ranked[0]["score"] == 100
    assert [r["score"] for r in ranked] == sorted(
        (r["score"] for r in ranked), reverse=True)


def test_candidates_skip_results_with_no_cover():
    from mangadl import covers
    import mangadl.sources as sources_module

    original = sources_module.search_all
    sources_module.search_all = lambda *a, **k: [
        {"title": "X", "cover": "", "source": "a", "url": "u"},
        {"title": "X", "cover": None, "source": "b", "url": "u"},
    ]
    try:
        assert covers.candidates("X") == []
    finally:
        sources_module.search_all = original


def test_candidates_of_an_empty_title_is_empty():
    from mangadl.covers import candidates

    assert candidates("") == []
    assert candidates(None) == []


def test_a_failing_search_does_not_raise():
    from mangadl import covers
    import mangadl.sources as sources_module

    original = sources_module.search_all

    def boom(*a, **k):
        raise RuntimeError("network down")

    sources_module.search_all = boom
    try:
        assert covers.candidates("X") == []
    finally:
        sources_module.search_all = original


# ============================================================ endpoints


def test_gui_exposes_the_three_endpoints():
    from mangadl.gui import Api

    api = Api()
    for name in ("scan_covers", "cover_candidates", "apply_cover"):
        assert callable(getattr(api, name, None)), name


def test_scan_covers_is_read_only(tmp_path):
    from mangadl.gui import Api

    root = make(tmp_path,
                "Mixed/A Series - Chapters 001.cbz",
                "Mixed/B Series - Chapters 001.cbz")
    before = sorted(os.listdir(os.path.join(root, "Mixed")))
    result = Api().scan_covers(root)
    assert result["ok"]
    assert len(result["groups"]) == 2
    assert sorted(os.listdir(os.path.join(root, "Mixed"))) == before


def test_apply_cover_refuses_an_empty_choice(tmp_path):
    from mangadl.gui import Api

    root = make(tmp_path, "S/S - Chapters 001.cbz")
    result = Api().apply_cover(
        {"directory": os.path.join(root, "S"), "archives": []}, {})
    assert result["ok"] is False
    assert "No cover" in result["error"]


def test_apply_cover_refuses_a_group_with_no_folder():
    from mangadl.gui import Api

    result = Api().apply_cover({}, {"cover": "https://example.com/c.jpg"})
    assert result["ok"] is False


def test_aggregate_member_ids_resolve_for_proxying():
    """Members like "madara.toonily" are real sources but not in the
    registry. Without a lookup for them, proxying their covers failed with
    "Unknown source" and 3 of 15 thumbnails rendered blank."""
    from mangadl.gui import Api

    source = Api()._source("madara.toonily")
    assert source is not None
    assert "toonily.com" in " ".join(source.domains)


def test_every_preview_is_proxied_not_just_referer_gated_ones():
    """The embedded browser blocks cross-origin images
    (ERR_BLOCKED_BY_RESPONSE.NotSameOrigin). Picking a cover you cannot see
    is not a choice."""
    source = read(os.path.join(ROOT, "mangadl", "gui", "__init__.py"))
    body = source[source.index("def _cover_preview"):]
    body = body[:body.index("def apply_cover")]
    assert "proxy_cover" in body
    assert "cover_needs_referer" not in body, \
        "previews must not be limited to Referer-gated sources"


# ================================================================== UI


def test_tools_tab_has_the_rebuilder():
    html = read(os.path.join(ROOT, "mangadl", "gui", "web", "index.html"))
    assert 'data-tool="covers"' in html
    assert 'id="tool-covers"' in html
    assert 'id="scanCoversBtn"' in html
    assert 'id="coverList"' in html


def test_ui_wires_the_endpoints():
    app = read(os.path.join(ROOT, "mangadl", "gui", "web", "app.js"))
    for call in ("scan_covers", "cover_candidates", "apply_cover"):
        assert call in app, call


def test_ui_says_nothing_changes_until_you_choose():
    """The tool moves files; the panel has to say so before it runs."""
    html = read(os.path.join(ROOT, "mangadl", "gui", "web", "index.html"))
    panel = html[html.index('id="tool-covers"'):]
    panel = panel[:panel.index('id="tool-history"')]
    assert "Nothing is changed until you choose" in panel
    assert "own" in panel        # explains the move
