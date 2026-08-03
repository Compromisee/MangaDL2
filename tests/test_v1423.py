"""Regression tests for v1.4.23.

* the "downloaded chapters" count leaking between books -- reported, and
  reproduced in a browser before being fixed
* the queue redesign: grouped by manga, collapsible, sparkline + fraction
* per-job speed/ETA/history on the progress snapshot
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "mangadl", "gui", "web")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ================================================ the cross-book count bug


def test_mark_downloaded_is_scoped_to_the_open_manga():
    """The bug: browsing to any book while a download ran made its
    "N downloaded" pill climb 1, 2, 3... in step with the *other* book.

    chapter_done carries no manga of its own, so the job's URL is the only
    correct source of truth."""
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function markChapterDownloaded"):]
    body = body[:body.index("\n}\n") + 2]

    assert "jobUrl" in body, "the handler ignores which job the event is for"
    assert "sameManga" in body
    assert "return" in body      # it bails out for a different manga


def test_chapter_done_passes_the_job_url():
    app = read(os.path.join(WEB, "app.js"))
    assert "markChapterDownloaded(event.chapter, job ? job.url : undefined)" in app


def test_same_manga_comparison_ignores_trailing_slash_and_case():
    """Sources spell the same URL differently; a naive === misses matches and
    the pill then never updates for the book you are actually watching."""
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function sameManga"):]
    body = body[:body.index("\n}\n")]
    assert "toLowerCase" in body
    assert "replace" in body and "\\/+$" in body


def test_downloaded_pill_still_updates_for_the_open_manga():
    """Scoping must not go too far: the book you are looking at has to keep
    updating live."""
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function markChapterDownloaded"):]
    body = body[:body.index("\n}\n") + 2]
    assert "state.downloaded.add(name)" in body
    assert "downloadedCount" in body


# ============================================================ queue tiles


def test_queue_groups_by_manga():
    app = read(os.path.join(WEB, "app.js"))
    assert "function groupCartRows" in app
    assert "function mangaKey" in app


def test_manga_key_prefers_url_over_title():
    """Two sources spell the same series differently, so grouping on the
    title alone would split one book into several tiles."""
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function mangaKey"):]
    body = body[:body.index("\n}\n")]
    assert "row.url" in body
    assert "title:" in body       # the fallback, only when there is no URL


def test_tiles_are_collapsed_by_default():
    """A long queue should read as a list of books, not a wall of chapters."""
    app = read(os.path.join(WEB, "app.js"))
    assert "const cartOpen = new Set()" in app
    # a tile is only open when the user has expanded it
    assert 'cartOpen.has(group.key)' in app

    css = read(os.path.join(WEB, "style.css"))
    body = css[css.index(".q-body {"):]
    body = body[:body.index("}")]
    assert "grid-template-rows: 0fr" in body


def test_expanding_is_animated_and_reversible():
    css = read(os.path.join(WEB, "style.css"))
    assert ".q-tile.open .q-body { grid-template-rows: 1fr; }" in css
    assert "transition: grid-template-rows" in css
    app = read(os.path.join(WEB, "app.js"))
    assert "cartOpen.delete(key)" in app and "cartOpen.add(key)" in app


def test_collapsed_tile_shows_a_sparkline_and_a_fraction_pill():
    app = read(os.path.join(WEB, "app.js"))
    assert "function sparkline" in app
    head = app[app.index('<button class="q-head"'):]
    head = head[:head.index("</button>")]
    assert "q-spark" in head, "no graph on the collapsed tile"
    assert "q-pill" in head, "no completion pill on the collapsed tile"
    assert "${group.done}/${group.total}" in app


def test_sparkline_is_safe_with_too_few_points():
    """One sample cannot be a line; the SVG must still be valid."""
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function sparkline"):]
    body = body[:body.index("\n}\n")]
    assert "values.length < 2" in body


def test_expanded_tile_shows_the_details_asked_for():
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function cartTileHtml"):]
    body = body[:body.index("async function renderCart")]

    assert "q-cover" in body, "no larger cover"
    assert "group.source" in body, "no source"
    assert "formatEta" in body, "no ETA"
    assert "formatRate" in body, "no speed"
    assert "Downloading now" in body, "no in-flight chapters"


def test_in_flight_chapters_are_tracked_per_job():
    app = read(os.path.join(WEB, "app.js"))
    assert "function trackChapter" in app
    assert "function untrackChapter" in app
    # started and progressed chapters go in, finished and failed come out
    assert "trackChapter(job, event.chapter, 0, event.total || 0)" in app
    assert "untrackChapter(job, event.chapter)" in app


def test_live_refresh_does_not_rebuild_open_tiles():
    """Rebuilding the list on every tick would collapse a tile the user just
    opened, and fight with the expand animation."""
    app = read(os.path.join(WEB, "app.js"))
    body = app[app.index("function refreshCartLive"):]
    body = body[:body.index("\n}\n")]
    assert "innerHTML" not in body.split("spark.innerHTML")[0].replace(
        "list.innerHTML", ""), "live refresh re-renders the whole list"
    assert "querySelector" in body


def test_polling_stops_when_nothing_is_downloading():
    """A 1s timer that never stops is a battery bug."""
    app = read(os.path.join(WEB, "app.js"))
    assert "function stopCartPolling" in app
    assert "if (!res.active) stopCartPolling();" in app


# ======================================================= progress payload


def test_job_snapshot_carries_formatted_text_and_history():
    from mangadl.progress import JobProgress

    job = JobProgress("j", "Title")
    job.set_chapters(done=2, total=10)
    job.add_bytes(2048)
    snap = job.snapshot(sample=True)

    for key in ("speed_text", "eta_text", "downloaded_text", "history",
                "chapters_done", "chapters_total"):
        assert key in snap, key
    assert isinstance(snap["history"], list)


def test_history_is_bounded():
    """An hours-long download must not grow an unbounded list."""

    from mangadl.progress import JobProgress

    job = JobProgress("j", "T")
    for _ in range(job.HISTORY * 3):
        job.add_bytes(1000)
        job._last_sample = 0        # bypass the rate limiter
        job.snapshot(sample=True)
    assert len(job.history) <= job.HISTORY


def test_history_is_rate_limited():
    """Sampling on every read made the sparkline scroll far too fast."""
    from mangadl.progress import JobProgress

    job = JobProgress("j", "T")
    job.add_bytes(1000)
    for _ in range(20):
        job.snapshot(sample=True)
    assert len(job.history) <= 2


def test_summary_samples_each_job_once():
    """The summary used to call snapshot() four times per job, which also
    sampled the history four times."""
    from mangadl.progress import ProgressRegistry

    registry = ProgressRegistry()
    job = registry.job("a", "A")
    job.add_bytes(5000)
    registry.summary()
    assert len(job.history) == 1


def test_summary_jobs_include_history_for_the_sparkline():
    from mangadl.progress import ProgressRegistry

    registry = ProgressRegistry()
    job = registry.job("a", "A")
    job.add_bytes(5000)
    jobs = registry.summary()["jobs"]
    assert jobs and "history" in jobs[0]
    assert "speed_text" in jobs[0]


# ============================================================= animations


def test_animations_are_defined():
    css = read(os.path.join(WEB, "style.css"))
    for name in ("q-in", "q-bump", "toast-in", "card-in"):
        assert f"@keyframes {name}" in css, name


def test_reduced_motion_is_honoured():
    """Motion is decoration; it must never be the only signal, and the OS
    setting has to switch it off."""
    css = read(os.path.join(WEB, "style.css"))
    assert "prefers-reduced-motion: reduce" in css
    block = css[css.index("prefers-reduced-motion: reduce"):]
    block = block[:block.index("\n}\n")]
    assert "animation: none" in block
    assert "transition: none" in block
