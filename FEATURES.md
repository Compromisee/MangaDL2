# Features

Everything MangaDL does, grouped by what you are trying to achieve.

For command syntax see **[SYNTAX.md](SYNTAX.md)**. For what changed in each
release, see **[CHANGELOG.md](CHANGELOG.md)**.

**Contents**

- [At a glance](#at-a-glance)
- [Sources](#sources)
- [Searching and browsing](#searching-and-browsing)
- [Downloading](#downloading)
- [Output files](#output-files)
- [Reliability](#reliability)
- [The desktop app](#the-desktop-app)
- [The queue](#the-queue)
- [Statistics](#statistics)
- [Library and bookmarks](#library-and-bookmarks)
- [Reading progress and updates](#reading-progress-and-updates)
- [Cover rebuilder](#cover-rebuilder)
- [Background mode](#background-mode)
- [Privacy and safety](#privacy-and-safety)
- [The command line](#the-command-line)
- [The terminal menu and TUI](#the-terminal-menu-and-tui)
- [Configuration](#configuration)
- [Packaging](#packaging)
- [Python API](#python-api)

---

## At a glance

| | |
|---|---|
| **Sources** | 19 registered, covering 28 sites |
| **Interfaces** | desktop app, terminal menu, full-screen TUI, scriptable CLI |
| **Output** | CBZ, PDF, EPUB, raw images — several at once |
| **Concurrency** | multiple series in parallel, each with parallel chapters and pages |
| **Resume** | per-job journal; a crash costs the current chapter, not the run |
| **Requirements** | Python 3.9+; everything else is optional |

All four interfaces share one engine, one settings file and one library, so
a change in the app is visible to the CLI immediately.

---

## Sources

### Registered sources

| Source | Site | Notes |
|---|---|---|
| MangaDex | mangadex.org | Official JSON API; language and scanlator preferences |
| Mangakatana | mangakatana.com | Obfuscated JS page decoding |
| Natomanga | natomanga.com | Manganato/Mangakakalot successor, JSON chapter endpoint |
| Weeb Central | weebcentral.com | Behind Cloudflare — see below |
| Asura Scans | asuracomic.net | Uses the JSON API; the website itself is an SPA |
| Flame Comics | flamecomics.xyz | Whole catalogue in one Next.js payload |
| Demonic Scans | demonicscans.org | HTML-fragment search backend |
| Madara Scans | madarascans.org | Themesia theme, not the Madara theme |
| Omega Scans | omegascans.org | |
| ManhwaRead | manhwaread.com | |
| **Madara Sites** | 10 sites | One source fanning out across ten Madara-theme installs |
| Witch Scans | witchscans.com | |
| Writers' Scans | writerscans.com | Page URLs rebuilt from `uid` attributes |
| Webtoons | webtoons.com | |
| Mangadass | mangadass.com | 18+ |
| Manhwa18 | manhwa18.net | 18+ |
| Manga18.club | manga18.club | 18+ |
| HentaiAkane | hentaiakane.com | 18+ |
| nhentai | nhentai.net | 18+ |

**Madara Sites** is a single entry that covers Toonily, Manhua Plus, Manhua
Top, Manhwa Top, MangaRead, Coffee Manga, Manga Sushi, MangaOwl, MangaGG and
Setsu Scans. Members have namespaced ids (`madara.toonily`) and can be
addressed individually, but they share one row in Settings.

Three unrelated things are called "Madara" and are easy to confuse: the
**Madara Sites** aggregate, the site **Madara Scans** (which does *not* run
the Madara theme), and the internal scraping engine for that theme.

### How sources behave

- The source is detected from any pasted URL, including URLs carrying
  tracking parameters.
- Bare MangaDex UUIDs are accepted in place of a URL.
- `-s/--source` forces a specific source; a disabled source still works from
  a direct URL.
- Each source declares its own capabilities (genres, browsing, languages,
  scanlators, Cloudflare), and the UI adapts rather than showing dead
  controls.
- Adding a site is one file plus one registry line — nothing in the CLI, the
  menu or the app needs to change.
- Shared plumbing gives every source retries with backoff, rate-limit
  handling, `Retry-After` support, magic-byte image validation and
  per-chapter `Referer` overrides for hotlink-protected CDNs.

### Cloudflare

Weeb Central and Setsu Scans sit behind Cloudflare. With
[FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) running they
work normally. Without it they fail fast and fall back to a stored snapshot
instead of stalling every other source — a missing solver used to cost 62
seconds of retries per request.

---

## Searching and browsing

- One query searches every enabled source in parallel.
- Duplicates across sites are merged, with the highest-ranked copy kept and
  the others listed as "also on". Matching is Unicode-safe, so CJK titles
  are never collapsed together.
- Interleave mode round-robins the sources instead of grouping them.
- Filters: sort order, ascending/descending, status, series type, genre
  (multiple, with any/all matching), chapter-count range, official-only.
- Results whose data a source does not report are kept rather than silently
  dropped, so a filter cannot make a whole source vanish.
- An empty search box shows a trending/browse feed instead of a blank page.
- Search history with type-ahead suggestions.
- Paste a series URL into the search box to jump straight to it.

### Results you already have

Settings → **Already downloaded** controls what happens to search results
that are in your library:

| Mode | Behaviour |
|---|---|
| **Show normally** | No change |
| **Darken** (default) | Dimmed; hovering fills the cover up to the fraction you have and shows the percentage |
| **Hide** | Removed from the grid, with a note saying how many were hidden |

The percentage is only shown when the source reports a total chapter count.
When it does not, the badge shows the number of chapters you have rather
than inventing a percentage.

---

## Downloading

- Chapter selection: `all`, `5`, `23.5`, `1-20`, `1,5,10-20`, `50-`, `-10`,
  `latest`, `first`.
- Several series download at once (configurable limit), each with parallel
  chapters (1–8) and parallel pages within a chapter (1–10).
- Every progress event carries its job id, so two series downloading
  simultaneously never mix their chapters or their counters.
- Queue jobs while others run; pause and resume the queue without
  interrupting a download in flight.
- A "new only" shortcut selects just the chapters you do not have.
- Large-download confirmation above a configurable threshold.

---

## Output files

- **CBZ**, **PDF** (pages sized exactly to each image), **EPUB** (with a
  chapter table of contents), or raw **images**.
- Produce several formats in one run with `--also`.
- Bundling: everything in one file, one file per chapter, or one file per
  every N chapters.
- Naming templates with `{title}`, `{chapter}`, `{chapters}`, `{start}` and
  `{end}` placeholders, with a live preview in Settings.
- Output goes into a per-series folder, with the cover saved alongside.
- Optionally open the folder when a download finishes.

---

## Reliability

- **Crash-safe resume.** Page-count-verified checkpoints, atomic `.part`
  writes, and one journal file per job. Resume from the app banner or
  `mangadl resume`; finished chapters are skipped and a partial chapter
  continues from the exact page it stopped at. Concurrent jobs each get
  their own journal, so one finishing cannot erase another's.
- **Fail fast on dead ends.** 404 and 410 are not retried — a wrong genre
  path used to cost 31 seconds per attempt.
- **Timeouts everywhere that touches the network**, including the genre
  listing that runs at startup.
- **Rotating log file** shared by every interface, with export and clear
  actions in Settings.
- Failures are reported per chapter; one bad chapter does not abort a run.

---

## The desktop app

### Search

- Cover-art grid with staggered entrance animations.
- Animated hero that compacts to the top once results arrive.
- Source badges, "also on" counts, and an active-filter indicator.
- Covers that require a referrer are proxied server-side so they render
  instead of showing a blank tile.

### Series page

- Cover, title, author, status, tags, description, bookmark toggle.
- Downloaded chapters are highlighted with a counter pill — and the counter
  belongs to the series you are looking at, not whatever is downloading.
- All / None / New only / Latest shortcuts, plus a quick-range box.
- Format, bundling and destination pickers.

### Appearance

- Six themes (Midnight, Mocha, Forest, Plum, Ocean, Light) and six accents.
- Rounded or square corners throughout.
- Animations toggle, honouring the OS "reduce motion" setting.
- Optional animated dot-matrix backdrop.
- Google Material Symbols throughout — no emoji.
- Collapsible side rail, configurable grid density.

### Other views

- **Bookmarks** with drag-and-drop folders, optional per-folder locking.
- **Library** listing every downloaded series, its parts and their sizes,
  with missing files flagged and a **Read** button that opens your
  configured reader.
- **Updates** for watched series.
- **Tools**: disk usage, library health, search history, moved-file repair,
  and the cover rebuilder.

---

## The queue

- One collapsible tile per series rather than a flat list of chapters.
- Collapsed: cover thumbnail, source, live transfer-rate sparkline, ETA, and
  a `done/total` chapter pill.
- Expanded: larger cover, source, speed, ETA, bytes downloaded, overall
  progress, and the chapters currently in flight with their page counts.
- Chapter rows update in place, so an open tile does not flicker or collapse
  while you are reading it.
- Overall progress and the Stop button live in the queue card itself.
- **Advanced logging** (Settings, or the checkbox on the Queue tab) records
  every engine event — page fetches, retries, packaging — instead of just
  milestones. Off by default.

---

## Statistics

- **Contribution calendar**: one square per day for the last 53 weeks,
  brighter the more you downloaded that day.
- Every source has a stable colour, and each day's square is the weighted
  mix of the sources that contributed to it — a year of downloading reads as
  a colour history of which sites you actually use.
- Hovering a day names each source as a fraction of that day's chapters
  (*MangaDex 23/55*).
- A **source carousel** gives each site its total, its share of the library,
  and a miniature activity strip; hovering shows its share as a fraction.
- Totals for series, chapters, pages, bytes on disk, time spent and average
  speed, plus biggest series and most recent downloads.
- Days recorded before per-source tracking existed still count toward the
  totals; they simply have no colour breakdown.

---

## Library and bookmarks

- `~/.mangadl/library.json` records every downloaded chapter per series:
  name, page count, date, output files, title and folder.
- Multi-part downloads are tracked part by part, with file sizes.
- Missing output files are detected and flagged, and moved files can be
  found again and relinked.
- Bookmarks live in `~/.mangadl/bookmarks.json`, organised into folders.
- Export the library as JSON, CSV or Markdown; import merges rather than
  overwrites.
- Notes, 0–5 star ratings, custom tags and named collections per series.

---

## Reading progress and updates

- Mark chapters read or unread, individually or in bulk.
- Per-series percentage and unread count; jump to the next unread chapter.
- Watch a series for new chapters; checks run in parallel across the
  watchlist and a failing site is skipped rather than fatal.
- New-chapter badges, acknowledged to clear.

---

## Cover rebuilder

Rebuild or replace the cover inside existing CBZ files — including ones
MangaDL did not create.

- Point it at any folder; it works recursively.
- Understands MangaDL's own names (`Chapters 001-050`) and third-party ones
  (`[Group] Title (2024) v03`, `Ch.001-036`, `Cap. 12`, `Episode 200`).
- Titles that happen to contain marker words survive intact — Chainsaw Man,
  Case Closed, Cells at Work, Eden's Zero.
- **Smart search** picks a cover automatically using your Settings source
  ranking, preferring a good resolution.
- Sort a flat folder of loose CBZ files into one folder per series.
- `--dry-run` to preview, `--sort-only` to organise without touching covers,
  `--replace` to overwrite existing artwork.

---

## Background mode

- Optional **system tray** mode: closing the window hides it and downloads
  keep running.
- The tray tooltip and menu show live speed, ETA, chapters remaining, queued
  jobs and each running download.
- Reopen, pause/resume the queue, or quit from the tray menu.
- Optional notification when a download finishes, de-duplicated so a repeated
  window event cannot produce a stream of balloons.
- The setting takes effect immediately — no restart.

Requires the `tray` extra (`pip install -e ".[tray]"`).

---

## Privacy and safety

- Optional **passcode lock**: PBKDF2-HMAC-SHA256, 240,000 rounds, per-install
  random salt, constant-time comparison. The passcode is never stored.
- A one-time recovery key is issued at setup, and the recovery flow is built
  into the lock screen.
- Attempt throttling after five failures with an escalating cooldown capped
  at 15 minutes.
- Auto-lock after N idle minutes, optional lock on start, optional cover
  blurring behind the lock screen.
- **Safe mode** hides adult-rated results; adult sources are tagged and can
  be disabled individually.
- Content filters for blocked tags, title words and authors.

---

## The command line

```
mangadl <url>                    every chapter as one CBZ
mangadl --url <url> -c 1-50 -f pdf --also epub
mangadl --url <url> --per 10     one file per ten chapters
mangadl resume                   continue an interrupted run

mangadl search "query"           every enabled source at once
mangadl search "query" --json    machine readable
mangadl search "query" --urls    one URL per line, for pipes
mangadl search "query" --open N  details for result N
mangadl search "query" --download N

mangadl library [--check]        what you have, and what moved
mangadl covers <folder>          rebuild CBZ covers
mangadl updates                  new chapters for watched series
mangadl config --list|--set k=v
mangadl sources [--enable|--disable|--rank]
mangadl lock status|set|change|off
```

- Colour output with progress bars, percentages and ETA, degrading to plain
  ASCII when Rich is unavailable or output is piped.
- `--plain` for scripts and CI.
- Colours respect `NO_COLOR` and `FORCE_COLOR`.

Full reference in **[SYNTAX.md](SYNTAX.md)**.

---

## The terminal menu and TUI

**`mangadl menu`** — a numbered menu needing no extra dependencies. Answer
with a number, `b` goes back, `q` quits. Covers search, download, library,
bookmarks, updates and settings.

**`mangadl-tui`** — a full-screen Textual interface for working over SSH:
tabs for Search / Manga / Downloads / Settings, chapter multi-select, format
and bundling pickers, live progress and a colour log. Requires the `tui`
extra.

---

## Configuration

Everything lives in `~/.mangadl/`:

| File | Contents |
|---|---|
| `config.json` | Settings and per-source configuration |
| `library.json` | What you have downloaded |
| `bookmarks.json` | Bookmarks and folders |
| `stats.json` | Download statistics |
| `jobs/` | Crash-resume journals, one per job |
| `logs/` | Rotating log files |

Settings are written atomically under a lock, so two saves at once cannot
clobber each other.

### Source ranking

- Drag to reorder in the app, or use the keyboard-friendly up/down buttons.
- Rank decides which copy wins when a series exists on several sites.
- Per-source overrides: enabled, searchable, result limit, duplicate weight,
  language, extra delay, free-text note.
- New sources are appended and ranked last; stale entries are pruned.
- The same ranking is used by the CLI, the app and the TUI.

---

## Packaging

`MangaDL.spec` plus `launcher.py` build a standalone executable with
PyInstaller — the app on double-click, and the TUI, CLI, search or resume via
arguments. One-folder and one-file modes are both supported; see
**[PACKAGING.md](PACKAGING.md)**.

---

## Python API

```python
from mangadl.downloader import DownloadEngine, DownloadOptions

result = DownloadEngine(DownloadOptions(url="...", bundle=10)).run()
```

Sources can be used directly too:

```python
from mangadl.sources import get_source, search_all

results = search_all("solo leveling")        # every enabled source
source = get_source("mangadex")
chapters = source.get_chapters(results[0]["url"])
```
