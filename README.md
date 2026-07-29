<div align="center">

# MangaDL

**Download manga, manhwa and manhua from 24 sites as CBZ, PDF or EPUB — from a modern CLI, an interactive menu, a full-screen TUI or a minimalist desktop GUI.**

[Project landing page](https://compromisee.github.io/WeebDL/) (GitHub Pages, served from `docs/`)

**[Command syntax reference -> SYNTAX.md](SYNTAX.md)**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![pywebview](https://img.shields.io/badge/pywebview-GUI-2962FF?style=for-the-badge)](https://pywebview.flowrl.com)
[![License](https://img.shields.io/badge/License-MIT-00875A?style=for-the-badge)](LICENSE)

<br>

![GUI - manga view](docs/gui-manga.png)

</div>

---

## Highlights

- **24 sources, one tool.** MangaDex and Asura Scans through their JSON APIs, Flame Comics through its Next.js payload, and nineteen more scraped — manga, manhwa and manhua. The right source is detected from the URL you paste — no flags required. See [Sources](#sources).
- **Search everything at once.** One query fans out across every site in parallel and merges the results, each tagged with where it came from.
- **Press Search with an empty box** and you get trending titles instead of nothing — the app opens on a discovery feed rather than a blank page.
- **Browse by genre.** 200+ genres merged across sites, with quick-pick chips, genre-filtered search and per-genre trending.
- **Robust by design.** A circuit breaker skips sites that are down instead of waiting for timeouts, retries use exponential backoff, and discovery listings are cached. One dead site never breaks a search.
- **One command, one CBZ.** By default the CLI downloads *every* chapter and packs them into a single `.cbz` — no flags needed.
- **Flexible bundling.** Choose one file for everything, one file per chapter, or one file per every N chapters (`--per 10`).
- **Organized output.** Everything is sorted into a per-manga folder inside your output directory. Raw page images live in a `raw/` subfolder and are cleaned up automatically after packaging (unless you keep them).
- **Three formats.** CBZ, PDF (pages sized exactly to each image), and EPUB (chapter table of contents included). Produce several at once with `--also`.
- **Three interfaces.** A rich-powered CLI, a full-screen **terminal UI (TUI)** built with Textual, and a minimalist pywebview desktop GUI.
- **Minimalist GUI.** A pywebview desktop app with a pastel-dark ambient interface: circular gradient orbs, an animated dot-matrix backdrop, 6 themes and 6 accent colors, smooth animations. Google Material Symbols only — zero emojis.
- **Library and bookmarks.** Every downloaded chapter is recorded in `~/.mangadl/library.json`; already-downloaded chapters are highlighted green in the chapter list, with a "New only" selector for incremental updates. Bookmark manga you want to come back to.
- **Open in Readest.** Point Settings at your reader executable (Readest or any other) and open finished books straight from the Library — multi-part downloads list every part with its size and a Read button.
- **Custom file naming.** Templates with `{title}`, `{chapter}`, `{start}`, `{end}` placeholders control output filenames, in Settings and via CLI flags.
- **Full-featured TUI.** Search, manga details, chapter multi-select with quick ranges, format/bundling pickers, live per-chapter progress and settings — entirely in your terminal (works over SSH).
- **Modern CLI.** Built on [rich](https://github.com/Textualize/rich): download plan summary, live progress bars per chapter, search and info commands.
- **Fast and polite.** Parallel chapter and image downloads with configurable workers, adaptive backoff on rate limits.
- **Crash-proof resume.** Verified checkpoints, atomic image writes and a job journal: after a crash or outage, hit **Resume** in the GUI (or run `mangadl resume`) and it continues exactly where it left off — completed chapters skipped, partial chapters finish their missing pages only.
- **File logging.** Rotating log at `~/.mangadl/logs/mangadl.log`, exportable from Settings.
- **Cloudflare-ready.** Falls back to [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) automatically if a site puts up a challenge.
- **Pluggable by design.** A new site is one file in `mangadl/sources/` plus one line in the registry; CLI, GUI and TUI pick it up automatically.
- **Rank and exclude sources.** Drag sources into your preferred order, or switch one off to drop it from results entirely. Ranking decides which copy wins when a series exists on several sites.
- **Provider always visible.** Every manga page names the site it came from, right under the title, with a link back to the original.
- **Passcode lock.** Optional PBKDF2-hashed app passcode with auto-lock, cover blurring and a one-time recovery key.
- **Track what you read.** Per-chapter read state, progress percentages, next-unread jump, star ratings and notes.
- **Watch for new chapters.** Keep a watchlist and check every series in parallel for updates.
- **Stats, filters, queue and cleanup.** Download statistics, content filters, a persistent job queue, library import/export, duplicate-file scanning and orphan detection.

See **[FEATURES.md](FEATURES.md)** for the complete feature reference and
**[CHANGELOG.md](CHANGELOG.md)** for the history of every update.

---

## Installation

Requires **Python 3.9+**.

```bash
git clone https://github.com/Compromisee/MDL.git
cd MDL

# install with the GUI and TUI
pip install -e ".[all]"

# or pick: CLI only / +GUI / +TUI
pip install -e .
pip install -e ".[gui]"
pip install -e ".[tui]"
```

Or without installing the package, just grab the dependencies:

```bash
pip install -r requirements.txt
```

> **Linux GUI note:** pywebview needs a webview engine. On Debian/Ubuntu:
> `sudo apt install python3-gi gir1.2-webkit2-4.1` (or install `pywebview[qt]`).
> Windows and macOS work out of the box.

---

## CLI usage

If installed with pip you get a `mangadl` command; otherwise use `python -m mangadl`.

### Download (the default action)

```bash
# Default: ALL chapters -> ONE .cbz, sorted into downloads/<Manga Title>/
mangadl https://mangadex.org/title/<uuid>

# One CBZ per 10 chapters
mangadl <url> --per 10

# One CBZ per chapter
mangadl <url> --per 1

# Chapters 1-50 as a single PDF
mangadl <url> -c 1-50 -f pdf

# Latest chapter only, EPUB, custom output dir
mangadl <url> -c latest -f epub -o ~/Manga

# CBZ volumes of 25 chapters AND a PDF of everything, keep raw images
mangadl <url> --per 25 --also pdf --keep-images
```

### Chapter selection (`-c / --chapters`)

| Selector      | Meaning                                |
|---------------|----------------------------------------|
| `all`         | every chapter (default)                |
| `5` / `23.5`  | a single chapter (decimals supported)  |
| `1-20`        | inclusive range                        |
| `1,5,10-20`   | any combination                        |
| `50-`         | chapter 50 to the end                  |
| `-10`         | start through chapter 10               |
| `latest`      | newest chapter                         |
| `first`       | oldest chapter                         |

### Search and info

```bash
mangadl search "one piece"                # search every source at once
mangadl search "one piece" -s mangadex    # search a single source
mangadl sources                           # list supported sites
mangadl info <url>                        # title, author, status, tags, chapter count
mangadl resume                 # resume an interrupted/crashed download
mangadl menu                   # interactive numbered menu (no extra deps)
mangadl tui                    # full-screen terminal UI (needs Textual)
mangadl gui                    # launch the desktop GUI
```

### Search syntax

```bash
# narrow by series type or status
mangadl search "solo" --type manhwa       # manga | manhwa | manhua | comic | novel
mangadl search "one piece" --status Ongoing

# cap and sort
mangadl search "naruto" -n 5 --sort title
mangadl search "berserk" --sort chapters --reverse   # sort: title|source|chapters|year

# machine-readable output, for pipes and scripts
mangadl search "blue" --urls              # one URL per line
mangadl search "blue" --json | jq '.[].title'

# act on a numbered result without copying a URL
mangadl search "berserk" --open 1         # show details for result 1
mangadl search "berserk" --download 1     # download result 1
```

`--type` is derived rather than requested: only one source accepts a type
parameter, so the type is classified from origin language and tags, with a
per-source default for single-type catalogues. Results whose type cannot be
determined are **kept** — dropping them would erase whole sources from a
filtered search.

### Interactive menu

```bash
mangadl menu
```

A progressive, numbered interface — every prompt is a list you answer with a
number. `b` goes back and `q` quits from any depth, so you cannot get stranded
in a submenu, and a closed stdin exits cleanly instead of raising.

It covers search, trending, pasting a URL, the library, bookmarks, settings
(folders, formats, sources, filters) and tools. It needs nothing beyond the
base install; `mangadl tui` needs Textual, which is an optional extra
(`pip install mangadl[tui]`).

### All options

```
-c, --chapters SEL     chapter selection (default: all)
-o, --output DIR       output directory (default: downloads)
-f, --format FMT       cbz | pdf | epub | images (default: cbz)
    --per N            chapters per file: 0 = one file for everything (default),
                       1 = per chapter, N = every N chapters
    --also FMT         produce an additional format (repeatable)
    --keep-images      keep raw page images after packaging
-w, --workers N        concurrent chapter downloads, 1-8 (default: 3)
    --image-workers N  concurrent images per chapter, 1-10 (default: 6)
    --delay S          delay between chapters in seconds (default: 0.5)
    --name-single TPL  filename template for single-file bundles (default: {title})
    --name-chapter TPL template for per-chapter files (default: {title} - Chapter {chapter})
    --name-range TPL   template for range bundles (default: {title} - Chapters {start}-{end})
-y, --yes              skip the confirmation prompt
    --plain            plain log output (for scripts / CI)

sources:
-s, --source ID        force a source (see `mangadl sources` for all 23)
                       (default: detected from the URL)
-l, --language LANG    translation language, MangaDex only (default: en)
    --scanlator NAME   preferred scanlation group, MangaDex only
    --data-saver       download compressed pages, MangaDex only
```

### Output structure

```
downloads/
└── One Piece/
    ├── cover.jpg
    ├── One Piece - Chapters 001-010.cbz
    ├── One Piece - Chapters 011-020.cbz
    ├── ...
    └── raw/                     # only if --keep-images / format=images
        ├── Chapter 1/
        │   ├── 001.jpg
        │   └── ...
        └── ...
```

---

## TUI (terminal UI)

A full-screen terminal app built with [Textual](https://textual.textualize.io) —
all the GUI's features without leaving the terminal. Works over SSH.

```bash
mangadl tui        # or: mangadl-tui / python -m mangadl tui
```

| | |
|---|---|
| ![TUI manga](docs/tui-manga.png) | ![TUI downloads](docs/tui-downloads.png) |
| **Manga tab** — options + chapter multi-select | **Downloads tab** — live per-chapter bars |
| ![TUI search](docs/tui-search.png) | ![TUI settings](docs/tui-settings.png) |
| **Search tab** — find series, Enter to open | **Settings tab** — persisted defaults |

**TUI features**

- Four tabs: **Search / Manga / Downloads / Settings** (`F1`–`F4` to jump)
- Search MangaDL by name or paste a URL straight into the search box
- Manga panel with title, author, status, tags and description
- Chapter list with checkbox multi-select (`space` toggles), All / None / Latest buttons and a quick-range box (`1-20, 25, 30-40`)
- Format (CBZ / PDF / EPUB / images) and bundling (single file / per chapter / every N) selectors
- Live download queue: overall progress bar, per-chapter image counters, colored activity log, stop button
- Settings shared with the GUI (`~/.mangadl/config.json`)

**Keyboard shortcuts**

| Key | Action |
|---|---|
| `Ctrl+S` | jump to search |
| `Ctrl+D` | start download |
| `Ctrl+X` | stop download |
| `F1`–`F4` | switch tabs |
| `Tab` / arrows | move focus |
| `q` | quit |

---

## GUI

```bash
mangadl gui        # or: python gui.py
```

| | |
|---|---|
| ![Manga](docs/gui-manga.png) | ![Downloads](docs/gui-downloads.png) |
| **Manga** — downloaded chapters glow green | **Queue** — live overall + per-chapter progress |
| ![Library](docs/gui-library.png) | ![Settings](docs/gui-settings.png) |
| **Library** — everything you've downloaded | **Settings** — themes, accents, behavior |
| ![Search](docs/gui-search.png) | ![Plum theme](docs/gui-theme-plum.png) |
| **Search** — find manga with cover thumbnails | **Themes** — 6 pastel-dark bases + light |

**GUI features**

- Animated hero: stylized title (gradient shine + outline), floating icon, search bar centered on screen that glides to the top when you search
- **Search filters**: sort (Best Match / Popularity / Subscribers / Recently Added / Latest Updates / Alphabet) with asc/desc order, status, type (Manga / Manhwa / Manhua / OEL) and official-only — changes re-run the search live
- Search MangaDL with cover thumbnails, or paste a series URL directly
- Full manga page: cover, author, status, tags, description, bookmark button
- Chapter list with click-to-select, **downloaded chapters highlighted green**, All / None / **New only** / Latest shortcuts and a quick-range box (`1-20, 25, 30-40`)
- Format picker (CBZ / PDF / EPUB / raw images) and bundling picker (single file / per chapter / every N chapters)
- Live download queue: overall progress, per-chapter image counters, activity log, stop button, "open folder" when done
- **Bookmarks tab** — save manga for later (`~/.mangadl/bookmarks.json`)
- **Library tab** — every downloaded manga with chapter/page counts, last download time; multi-part downloads expand to show each part with its file size, a **Read** button (opens your configured reader, e.g. Readest) and missing-file detection
- **Appearance settings** — 6 themes (Midnight, Mocha, Forest, Plum, Ocean, Light), 6 accent colors, animation and dot-matrix toggles
- **Behavior settings** — output directory, default format, keep raw images, open-folder-when-done, confirm-large-downloads guard with threshold, worker counts, delays, retries per image
- **File naming settings** — templates for single-file / per-chapter / range bundles with `{title}` `{chapter}` `{start}` `{end}` placeholders and a live preview
- **Reader settings** — path to the Readest executable (or any reader); empty uses your system's default app
- Ambient design: solid pastel-dark backgrounds with drifting circular gradients and an animated dot matrix; Google Material Symbols throughout, no emojis anywhere

---

## Discovery: trending and genres

Pressing **Search with an empty box is not an error** — it is how you browse.
Every interface opens on a trending feed and lets you narrow it by genre.

```bash
mangadl search                     # no query -> trending across all sources
mangadl trending                   # the same thing, explicitly
mangadl trending horror            # top horror right now
mangadl genres                     # every genre, and which sites offer it
mangadl search "blue" -g Romance   # genre-filtered search
mangadl trending -s mangadex       # trending on one source only
```

In the GUI the genre dropdown and quick-pick chips sit in the filter row, and
`Load more` pages through the feed. The TUI has a genre dropdown beside the
source picker (`F1`).

Genres are merged across whichever sources are currently enabled, matched
case-insensitively, and ordered by how widely each one is supported — so
`Action` (on all four sites) sorts above a genre only one site offers.

Sorting differs slightly per site because not every site exposes the same
concept of "trending": MangaDex sorts by follower count, Weeb Central by
popularity, Natomanga uses its hot-manga feed, and Mangakatana's listing
ignores sort parameters entirely, so the choice is passed through as advisory.

---

## Reliability

Third-party sites go down, rate-limit and change their markup. MangaDL assumes
this rather than hoping otherwise:

- **Circuit breaker per source** — after repeated failures a site is skipped
  instantly instead of costing a full timeout on every request. It is probed
  again after a cooldown that doubles with each further trip.
- **Bounded retries** with exponential backoff and jitter, plus a `retry_if`
  hook so hopeless failures (404s) are not retried at all.
- **Caching** of discovery listings (5 min) and genre lists (1 hr), which makes
  repeat browsing effectively instant and spares the sites identical requests.
- **Partial results always win** — search, browse and genre listings keep
  whatever succeeded and log the rest.
- **Rate-limit headers** (`Retry-After`, `X-RateLimit-Retry-After`) are honoured.

```bash
mangadl health      # breaker state per source, plus cache hit rates
```

---

## Source ranking and exclusion

Sources are ranked, and the ranking decides which copy of a series wins when the
same title exists on several sites. Drag the list in **Settings → Sources**, or
use the terminal:

```bash
mangadl config                          # show the table
mangadl config up mangakatana           # rank it higher
mangadl config disable natomanga        # exclude it from results
mangadl config rank mangadex natomanga mangakatana weebcentral
mangadl config reset
```

A **disabled** source is skipped everywhere except direct URLs — paste a link to
an excluded site and it still works, so you never lose access to a link someone
sends you. The TUI has the same controls under its **Sources** tab (`F4`).

---

## Passcode lock

An optional passcode gates the app's interface.

```bash
mangadl lock status
mangadl lock set        # prompts, then prints a one-time recovery key
mangadl lock change
mangadl lock off
```

The passcode is stored as a PBKDF2-HMAC-SHA256 verifier (240,000 rounds) over a
per-install random salt, so the file cannot be reversed and two people with the
same passcode get different hashes. Five wrong attempts start an escalating
cooldown. A recovery key is issued once at setup and is the only way back in if
you forget the passcode.

**Scope:** this is a privacy screen for the UI, not disk encryption. Your
downloaded files stay readable on disk to anyone with access to the machine.

---

## Tracking and maintenance

```bash
mangadl watch add <url>     # track a series
mangadl watch check         # check every watched series in parallel
mangadl watch list

mangadl stats               # download statistics
mangadl history             # recent searches
mangadl export lib.md md    # export the library

mangadl disk usage          # size per series
mangadl disk dupes          # byte-identical files, with wasted space
mangadl disk orphans        # library entries whose files are gone
```

---

## Sources

| Source | Site | How it works | Notes |
|---|---|---|---|
| `mangadex` | [mangadex.org](https://mangadex.org) | Official JSON API | Languages, scanlation groups, data-saver mode |
| `mangakatana` | [mangakatana.com](https://mangakatana.com) | HTML scraping | Large back catalogue, no account needed |
| `natomanga` | [natomanga.com](https://www.natomanga.com) | HTML + JSON chapter endpoint | Manganato / Mangakakalot successor |
| `weebcentral` | [weebcentral.com](https://weebcentral.com) | HTML scraping | May need FlareSolverr |
| `asurascans` | [asuracomic.net](https://asuracomic.net) | JSON API (`api.asurascans.com`) | Site is an SPA that serves one document for every URL; the API is used instead. Pages with `offset`, not `page` |
| `flamecomics` | [flamecomics.xyz](https://flamecomics.xyz) | Next.js `__NEXT_DATA__` | Whole 167-title catalogue in one request |
| `demonicscans` | [demonicscans.org](https://demonicscans.org) | HTML scraping | MangaDemon. Genre filter is POST-only with numeric ids |
| `madarascans` | [madarascans.org](https://madarascans.org) | HTML + `ts_reader` JSON | Madara **Scans** — the site. Unrelated to the Madara *theme* below |
| `omegascans` | [omegascans.org](https://omegascans.org) | JSON API | Coin-locked chapters are skipped |
| `manhwaread` | [manhwaread.com](https://manhwaread.com) | HTML + base64 chapter payload | CDN needs a Referer |
| `toonily` | [toonily.com](https://toonily.com) | Madara theme | Manhwa. Page CDN needs a Referer; search pages with `&paged=` only |
| `manhuaplus` | [manhuaplus.com](https://manhuaplus.com) | Madara theme | Manhua |
| `manhuatop` | [manhuatop.org](https://manhuatop.org) | Madara theme | Manhua. Series at `/manhua/`, listing at `/manga/` |
| `manhwatop` | [manhwatop.com](https://manhwatop.com) | Madara theme | Manhwa. Genre slugs are SEO-mangled and read live |
| `mangaread` | [mangaread.org](https://www.mangaread.org) | Madara theme | Mixed manga/manhwa/manhua. Genres at `/genres/` |
| `witchscans` | [witchscans.com](https://witchscans.com) | HTML + `ts_reader` JSON | Manhua. Genre slugs contain percent-encoded emoji |
| `writerscans` | [writerscans.com](https://writerscans.com) | HTML, client-side catalogue | 27-title group. Pages rebuilt from `uid` attributes |
| `setsuscans` | [setsuscans.com](https://setsuscans.com) | Madara theme | **Needs FlareSolverr** — 403 on every request without it |
| `webtoons` | [webtoons.com](https://www.webtoons.com) | HTML scraping | Official site; covers are proxied (hotlink-protected CDN) |
| `mangadass` | [mangadass.com](https://mangadass.com) | HTML scraping | **18+** · use `/search?q=`, `/?s=` ignores the query |
| `manhwa18` | [manhwa18.cc](https://manhwa18.cc) | HTML scraping | **18+** |
| `manga18club` | [manga18.club](https://manga18.club) | HTML + base64 page list | **18+** · pages decoded from `slides_p_path` |
| `hentaiakane` | [hentaiakane.com](https://hentaiakane.com) | HTML + `ts_reader` JSON | **18+** |
| `nhentai` | [nhentai.to](https://nhentai.to) | HTML scraping | **18+** · one gallery = one chapter |

Adult sources are stamped `content_rating: pornographic` and tagged `Adult`, so
**Safe mode** in Settings removes them, and each can be disabled individually.

**A note on the name "Madara".** Two unrelated things share it. `madarascans`
is *Madara Scans*, a site you can search and download from. The **Madara
WordPress theme** is an engine that six *other* sites run; it lives in
`mangadl/sources/madara.py`, is not a source, and deliberately never appears
in Settings or `mangadl sources`. Confusingly, Madara Scans does not run the
Madara theme.

Six of these run the **Madara** WordPress theme, so they share one scraper in
`mangadl/sources/madara.py` and each site file only declares what differs — the
series path, the genre prefix and the listing path. All three vary per install
and a wrong guess is a hard 404, so each was measured rather than assumed.

Sites behind Cloudflare (`weebcentral`, `setsuscans`) need
[FlareSolverr](https://github.com/FlareSolverr/FlareSolverr). Without it they
now fail in milliseconds instead of stalling a multi-source search — see the
v1.4.15 changelog entry.

Three requested sites were deliberately left out:

* **Comick** (`comick.io`) — the API returns an empty `md_images` array for
  every title, so no pages can be read.
* **Comix** (`comix.to`) — every `/api/v1/` call answers
  `403 {"message":"Missing token."}`, including from inside a real browser
  session with `cf_clearance` set, and the SPA renders nothing without it.

```bash
mangadl sources                        # list them with their capabilities
mangadl search "berserk"               # search all of them at once
mangadl search "berserk" -s mangadex   # search just one
mangadl <any-supported-url>            # source detected automatically
```

The source is inferred from the URL, so pasting a link is always enough.
`-s/--source` only matters when searching or when you want to override detection.

### MangaDex specifics

MangaDex is the richest source, and a few of its API behaviours are worth
knowing because they are easy to get wrong.

**Covers.** A manga's cover is only a *reference* in the API response, so the
cover filename has to be pulled in with reference expansion
(`includes[]=cover_art`) or it comes back as a bare id you cannot build a URL
from. The URL is:

```
https://uploads.mangadex.org/covers/{manga-id}/{filename}
```

Two thumbnails exist, and the size suffix is appended **after the complete
filename, extension included**:

```
{filename}.256.jpg     # small,  grid thumbnails
{filename}.512.jpg     # medium, detail view
```

So `abc.png` becomes `abc.png.512.jpg` — not `abc.512.jpg`. Stripping the
original extension first returns a 404, which is the usual cause of missing
MangaDex covers. MangaDL resolves all three sizes up front: thumbnails for the
UI grid, the original for the `cover.jpg` saved next to your downloads.
`get_covers()` additionally lists every per-volume and localised cover.

**Externally hosted chapters.** Licensed series (One Piece and friends) list
chapters that live on MangaPlus or Azuki: they carry an `externalUrl` and
report `pages: 0`. They cannot be downloaded, so MangaDL filters them out
rather than "succeeding" with zero pages. A title whose chapters are *all*
external will correctly report that nothing is downloadable.

**Multiple releases.** The same chapter number is often uploaded by several
scanlation groups. MangaDL keeps one release per number — preferring
`--scanlator` if you set one, otherwise the most complete upload — and records
the rest as alternatives.

**Language.** `-l/--language` picks the translation (default `en`).

### Adding a new source

Sources are plugins. Create `mangadl/sources/<name>.py`:

```python
from .base import Source

class MySource(Source):
    id = "mysite"
    name = "My Site"
    base_url = "https://mysite.com"
    domains = ("mysite.com",)

    def search(self, query, limit=32, **filters): ...
    def get_manga_info(self, url): ...
    def get_chapters(self, url): ...        # oldest first
    def get_chapter_images(self, chapter): ...
```

Then add it to `SOURCE_CLASSES` in `mangadl/sources/__init__.py`. Retries,
backoff, rate-limit handling, Cloudflare fallback and atomic image writes come
from the base class. The CLI, GUI and TUI discover it automatically.

---

## Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/                         # offline unit tests
MANGADL_NETWORK_TESTS=1 python -m pytest tests/ # also hit the live sites
```

The GUI dropdown component is covered by Playwright tests that drive real
headless Chromium. They skip automatically if it is not installed:

```bash
pip install playwright && python -m playwright install chromium
python -m pytest tests/test_dropdown.py
```

## Python API

The engine is usable as a library:

```python
from mangadl.downloader import DownloadEngine, DownloadOptions
from mangadl.sources import get_source, search_all, source_for_url

# search every site at once
for hit in search_all("berserk", limit=5):
    print(hit["source_name"], hit["title"], hit["url"])

# or drive one source directly
source = source_for_url("https://mangadex.org/title/<uuid>")
chapters = source.get_chapters("https://mangadex.org/title/<uuid>")

options = DownloadOptions(
    url="https://mangadex.org/title/<uuid>",
    selection="1-50",     # same syntax as the CLI
    output_dir="downloads",
    format="cbz",         # cbz | pdf | epub | images
    bundle=10,            # 0 = single file, N = N chapters per file
    source="",            # "" = detect from the URL; or "mangadex", "mangakatana", ...
    language="en",        # MangaDex translation language
    data_saver=False,     # MangaDex: smaller compressed pages
)

def on_event(event):      # structured progress events
    print(event["type"], event)

result = DownloadEngine(options, on_event).run()
print(result["outputs"])
```

---

## Cloudflare / FlareSolverr

Direct requests work most of the time. Weeb Central in particular sits behind
Cloudflare; if a site raises a challenge, the downloader falls back to a local
[FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) instance.

```bash
# easiest: docker
docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest

# or use the bundled helper (downloads and starts FlareSolverr)
python start_flaresolverr.py
```

You only need this if downloads start failing with Cloudflare errors.

---

## Project layout

```
mangadl/
├── cli.py              # rich-powered CLI (download / search / info / gui / tui)
├── tui.py              # full-screen Textual terminal UI
├── downloader.py       # DownloadEngine: orchestration, bundling, events
├── library.py          # JSON library + bookmarks (~/.mangadl/*.json)
├── scraper.py          # thin backwards-compatible facade over sources/
├── sources/            # one module per site — add a file to add a site
│   ├── base.py         # Source ABC: retries, backoff, atomic image writes
│   ├── mangadex.py     # official JSON API (covers, at-home page server)
│   ├── mangakatana.py  # HTML + obfuscated JS page arrays
│   ├── natomanga.py    # HTML + JSON chapter endpoint
│   └── weebcentral.py  # the original scraper
├── robust.py           # retries, circuit breaker, TTL caches, safe calling
├── config.py           # per-source ranking, exclusion and overrides
├── passlock.py         # optional app passcode
├── tracking.py         # read progress, watchlist, notes, disk maintenance
├── features.py         # history, queue, stats, filters, export, snapshots
├── packager.py         # CBZ / PDF / EPUB creation
├── flaresolverr.py     # optional Cloudflare bypass client
├── utils.py            # chapter parsing, natural sort, sanitising
└── gui/
    ├── __init__.py     # pywebview app + JS API bridge
    └── web/            # index.html, style.css, app.js, dropdown.js
```

## Standalone executable

Build an all-inclusive exe (GUI + TUI + CLI in one binary, no Python needed)
with PyInstaller and the provided [`MangaDL.spec`](MangaDL.spec):

```bash
pip install pyinstaller
pyinstaller MangaDL.spec            # one-folder -> dist/MangaDL/
pyinstaller MangaDL.spec -- --onefile   # single file
```

Double-clicking the exe opens the GUI; `MangaDL tui`, `MangaDL <url>`,
`MangaDL search ...` and `MangaDL resume` all work from a terminal.
Full per-platform instructions: **[PACKAGING.md](PACKAGING.md)**.

## Landing page (GitHub Pages)

`docs/index.html` is a ready-made landing page with the same ambient design as
the app (gradient orbs, dot matrix, feature grid, GUI/TUI screenshot tabs, CLI
demo terminal). To publish it:

1. GitHub repo → **Settings → Pages**
2. Source: **Deploy from a branch**, branch `main`, folder **`/docs`**
3. Your page appears at `https://<user>.github.io/WeebDL/`

## Data files

Everything lives in `~/.mangadl/`:

| File | Purpose |
|---|---|
| `config.json` | Everything configurable: app settings (theme, accent, workers, output dir) under `settings`, and per-source ranking/exclusion under `sources`. Written atomically under one lock. A pre-1.4.11 `settings.json` is migrated in automatically. |
| `library.json` | every downloaded chapter per manga: name, pages, date, output files |
| `bookmarks.json` | bookmarked manga (title, URL, cover) |
| `job.json` | journal of the current download; enables crash resume |
| `logs/mangadl.log` | rotating application log (exportable from Settings) |

The library is what powers the green "downloaded" highlighting in the GUI's
chapter list and the **New only** selection shortcut — re-open a manga later
and instantly see what you're missing.

## Troubleshooting

| Problem | Fix |
|---|---|
| `429 Too Many Requests` | Raise `--delay`, lower `--workers`. The engine also backs off automatically. |
| Cloudflare "Just a moment..." | Start FlareSolverr (see above). |
| GUI window doesn't open on Linux | Install a webview backend: `sudo apt install gir1.2-webkit2-4.1` or `pip install pywebview[qt]`. |
| GUI crashes or closes immediately on open | Since v2.6.3 the app retries alternative browser backends and shows the real error instead of dying. Check `~/.mangadl/logs/mangadl.log` and `crash.log`. On Windows, install/update the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) and make sure `pip install -U pywebview pythonnet` are current. |
| Console spam: `Error while processing window.native...` / `maximum recursion depth exceeded` (Windows) | Harmless pywebview/WebView2 bridge noise — fixed in v2.6.1 (the `window.native` bridge is removed at load and the messages are filtered from logs). Seeing `E_NOINTERFACE` / `ICoreWebView2Controller4` too? Your **WebView2 Runtime is outdated** — update it from Microsoft or via Windows Update. |
| Interrupted download | Re-run the same command — completed chapters are skipped via the verified `.checkpoint` and already-downloaded images are not re-fetched. |
| Crash / power outage | Launch the GUI (a Resume banner appears) or run `mangadl resume` — the job journal restarts the download where it left off. |
| Diagnosing problems | Export the log from Settings → Logs, or read `~/.mangadl/logs/mangadl.log`. |
| A few chapters failed | The summary lists them; re-run with `-c <numbers>` to fetch just those. |
| `ImportError: attempted relative import with no known parent package` | You ran a package file directly (e.g. `python mangadl/tui.py` or PyCharm's "Run file"). Fixed in v2.6.2 — files now self-bootstrap. Preferred launches: `mangadl tui`, `python -m mangadl tui`, or the root `python tui.py` / `python gui.py`. In PyCharm, set the run configuration to **module** `mangadl` with parameter `tui`. |

## Legal

This tool is for personal archival of content you have the right to access.
Support the official releases of the manga you enjoy.

## License

[MIT](LICENSE)
