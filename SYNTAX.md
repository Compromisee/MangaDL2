# MangaDL — command syntax

Complete reference for the `mangadl` command line. Every example here was run
against the real build.

Four ways to drive the same engine:

| | Command | Best for |
|---|---|---|
| **CLI** | `mangadl …` | scripting, one-off downloads |
| **Menu** | `mangadl menu` | numbered prompts, nothing to memorise |
| **TUI** | `mangadl tui` | full-screen terminal app (needs `textual`) |
| **GUI** | `mangadl gui` | desktop window (needs `pywebview`) |

---

## Contents

- [The one-line version](#the-one-line-version)
- [Invocation](#invocation)
- [Downloading](#downloading)
  - [Chapter selection](#chapter-selection)
  - [Output format and bundling](#output-format-and-bundling)
  - [Filename templates](#filename-templates)
  - [Speed and politeness](#speed-and-politeness)
- [Searching and discovery](#searching-and-discovery)
- [Sources](#sources)
- [Library, watching and disk](#library-watching-and-disk)
- [Configuration and privacy](#configuration-and-privacy)
- [Colour and progress output](#colour-and-progress-output)
- [Exit codes](#exit-codes)
- [Recipes](#recipes)

---

## The one-line version

```bash
mangadl <url>
```

Paste any URL from a supported site. The source is detected, every chapter is
downloaded, and you get one CBZ. Nothing else is required.

---

## Invocation

```
mangadl [options] <url>
mangadl [options] <command> [arguments]
```

`mangadl` is the installed entry point. All three of these are equivalent:

```bash
mangadl search "berserk"           # installed script
python -m mangadl.cli search "berserk"
py cli.py search "berserk"         # run the file directly, from mangadl/
```

Running the files directly works on purpose — every module self-bootstraps its
package. `rich` is optional: without it the CLI still runs and still colours
its output, it just uses a simpler progress bar.

### Commands

| Command | What it does |
|---|---|
| *(a URL)* | download it |
| `search <query>` | search every enabled source at once |
| `info <url>` | title, cover, description, chapter count |
| `trending [genre]` | popular titles; alias `browse`, `popular` |
| `genres` | every genre, merged across sources |
| `sources` | list supported sites and capabilities |
| `config …` | enable, disable and rank sources |
| `library …` | verify, relocate and re-link downloads |
| `watch …` | track series for new chapters |
| `disk …` | usage, duplicates, orphaned files |
| `stats` | download statistics |
| `history` | recent searches |
| `lock …` | app passcode |
| `export <file>` | export the library |
| `health` | circuit-breaker state and cache hit rates |
| `resume` | resume an interrupted download |
| `menu` / `tui` / `gui` | launch an interface |

---

## Downloading

```bash
mangadl https://mangadex.org/title/<uuid>
mangadl https://asuracomic.net/series/emperor-of-solo-play
mangadl https://witchscans.com/manga/afterlife-diner/
```

A bare MangaDex UUID also works:

```bash
mangadl a1c7c817-4e59-43b7-9365-09675a149a6f
```

### Chapter selection

`-c` / `--chapters` (default `all`):

| Value | Meaning |
|---|---|
| `all` | every chapter (default) |
| `5` | just chapter 5 |
| `1-20` | chapters 1 through 20 |
| `1,5,10-20` | mix single chapters and ranges |
| `50-` | chapter 50 to the end |
| `latest` | the newest chapter only |
| `first` | the oldest chapter only |

```bash
mangadl <url> -c latest
mangadl <url> -c 1,5,10-20
mangadl <url> -c 50-
```

### Output format and bundling

```bash
mangadl <url> -f cbz          # default
mangadl <url> -f pdf
mangadl <url> -f epub
mangadl <url> -f images       # loose image files, no archive
```

`--per N` controls how chapters are grouped into files:

| Flag | Result |
|---|---|
| `--per 0` | everything in one file (default) |
| `--per 1` | one file per chapter |
| `--per 10` | one file per ten chapters |

```bash
mangadl <url> --per 10                 # one CBZ per 10 chapters
mangadl <url> -c 1-50 -f pdf           # chapters 1-50 as a single PDF
mangadl <url> --also epub              # CBZ *and* EPUB (repeatable)
mangadl <url> -f cbz --keep-images     # keep the raw pages too
mangadl <url> -o ~/Manga               # choose the output directory
```

### Filename templates

| Flag | Applies to | Default |
|---|---|---|
| `--name-single` | one-file bundles | `{title} - Chapters {chapters}` |
| `--name-chapter` | `--per 1` output | per-chapter name |
| `--name-range` | `--per N` output | chapter-range name |

Placeholders: `{title}`, `{chapters}`, `{chapter}`, `{source}`, `{start}`,
`{end}`.

```bash
mangadl <url> --per 1 --name-chapter "{title} Ch.{chapter}"
```

### Speed and politeness

| Flag | Default | Range |
|---|---|---|
| `-w`, `--workers` | 3 | 1–8 concurrent chapters |
| `--image-workers` | 6 | 1–10 concurrent pages per chapter |
| `--delay` | 0.5 | seconds between chapters |

```bash
mangadl <url> -w 6 --image-workers 10     # faster, heavier on the site
mangadl <url> -w 1 --delay 2              # gentle
```

Please leave the defaults alone unless you have a reason. They are set to be
polite to sites that are mostly run by volunteers.

### Other download flags

```bash
mangadl <url> -y            # skip the confirmation prompt
mangadl <url> --plain       # plain log lines, no progress UI (good for cron)
mangadl resume              # resume whatever was interrupted
```

---

## Searching and discovery

```bash
mangadl search "one piece"              # every enabled source, in parallel
mangadl search "berserk" -s mangadex    # one source
mangadl search                          # no query -> trending
```

### Filters

| Flag | Values | Notes |
|---|---|---|
| `--type` | `manga`, `manhwa`, `manhua`, `comic`, `novel`, `any` | lowercase |
| `--status` | `Ongoing`, `Completed`, … | |
| `-g`, `--genre` | any name from `mangadl genres` | comma-separate for several |
| `-n`, `--limit` | a number | results **per source** |
| `--sort` | `title`, `source`, `chapters`, `year` | |
| `--reverse` | | flip the sort |

`--type` is *derived*, not requested: almost no site accepts a type filter, so
MangaDL infers it from the origin language and tags. Results whose type cannot
be determined are **kept** — dropping them would erase whole sources from a
filtered search.

```bash
mangadl search "solo" --type manhwa
mangadl search "one piece" --status Ongoing
mangadl search "blue" -g Romance
mangadl search "blue" -g "Romance,Comedy"
mangadl search "berserk" --sort chapters --reverse
```

### Output modes

```bash
mangadl search "blue" --json      # machine-readable
mangadl search "blue" --urls      # URLs only, one per line
```

`--urls` is built for pipes:

```bash
mangadl search "murim" --type manhwa --urls | head -3 | xargs -n1 mangadl -c 1
```

### Acting on a result

```bash
mangadl search "berserk" --open 1        # show details for result 1
mangadl search "berserk" --download 1    # download result 1
```

### Browsing

```bash
mangadl trending                  # popular across every source
mangadl trending romance          # popular in one genre
mangadl trending -s mangadex      # one source
mangadl genres                    # every genre and who offers it
mangadl info <url>                # details for one series
```

---

## Sources

```bash
mangadl sources                   # every site, with capabilities
```

Force one with `-s`:

```bash
mangadl search "naruto" -s natomanga
```

MangaDex-only options:

```bash
mangadl <url> -l fr                       # translation language
mangadl <url> --scanlator "Group Name"    # preferred group
mangadl <url> --data-saver                # smaller, compressed pages
```

### Enabling, disabling and ranking

Rank decides which copy wins when a series exists on several sites; lower is
better.

```bash
mangadl config                                  # show the table
mangadl config disable natomanga                # skip it everywhere but URLs
mangadl config enable natomanga
mangadl config up mangakatana                   # move up one place
mangadl config down mangakatana
mangadl config rank mangadex asurascans flamecomics    # set the order outright
mangadl config reset
```

A **disabled** source is skipped everywhere except direct URLs, so a link
someone sends you still works.

### Cloudflare

Weeb Central and Setsu Scans sit behind Cloudflare and need
[FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) on
`localhost:8191`. Without it they fail in milliseconds and the rest of your
search continues — they will not hold it up.

---

## Library, watching and disk

```bash
mangadl library                      # verify every entry resolves on disk
mangadl library verify
mangadl library scan ~/Manga         # re-link folders you moved
mangadl library move <url> <folder>  # relocate one series
mangadl export out.json              # or: out.csv / out.md
```

```bash
mangadl watch add <url>              # track a series
mangadl watch list
mangadl watch check                  # check everything for new chapters
mangadl watch remove <url>
```

```bash
mangadl disk usage                   # size per series
mangadl disk dupes                   # duplicate files
mangadl disk orphans                 # files with no library entry
mangadl stats
mangadl health                       # breaker state, cache hit rates
```

---

## Configuration and privacy

Everything lives in `~/.mangadl/`:

| File | Contents |
|---|---|
| `config.json` | settings **and** per-source config, written atomically |
| `library.json` | what you have downloaded |
| `logs/` | rotating logs |

```bash
mangadl lock status
mangadl lock set        # set a passcode
mangadl lock change
mangadl lock off
mangadl history         # recent searches
```

---

## Colour and progress output

Colour is on when the output is a terminal and off when piped, so redirecting
to a file never produces escape-code soup.

| Variable | Effect |
|---|---|
| `NO_COLOR=1` | never colour |
| `FORCE_COLOR=1` | colour even when piped |
| `CLICOLOR_FORCE=1` | same as `FORCE_COLOR` |
| `TERM=dumb` | never colour |

```bash
NO_COLOR=1 mangadl sources
FORCE_COLOR=1 mangadl search "blue" | less -R
mangadl <url> --plain            # no progress bar at all; one line per event
```

On Windows, ANSI is enabled through the console API automatically. Windows 10
1511 and newer show colour; older hosts fall back to plain text rather than
printing raw escape codes.

With `rich` installed you get a spinner, a bar, `done/total`, a percentage,
elapsed time and an ETA. Without it you get a single-line bar with the same
counts. Use `--plain` in cron jobs and CI.

---

## Background mode

With **Settings → Background → Minimise to system tray** enabled, closing the
window hides it and downloads carry on. The tray icon's context menu shows:

* current transfer rate and ETA
* chapters remaining and how many jobs are queued
* one line per running download
* **Open MangaDL** to bring the window back, **Pause queue**, and **Quit**

The tray needs an optional dependency and a desktop session:

```bash
pip install "mangadl[tray]"
```

Without it the toggle is disabled and explains why; the window keeps its
ordinary close-quits behaviour.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | failure — nothing found, bad URL, download failed |
| `130` | cancelled with Ctrl-C |

```bash
mangadl <url> -y || echo "download failed"
```

---

## Recipes

**Grab only what is new, quietly, from cron**

```bash
mangadl watch check --plain
```

**One file per chapter, into a per-series folder**

```bash
mangadl <url> --per 1 -o ~/Manga
```

**Everything a source has for one genre, as URLs**

```bash
mangadl trending romance -s toonily --urls
```

**Search, pick, download in one line**

```bash
mangadl search "solo leveling" --type manhwa --download 1 -y
```

**Mirror a series as both CBZ and EPUB**

```bash
mangadl <url> -f cbz --also epub
```

**Slow, polite full-series archive**

```bash
mangadl <url> -w 1 --delay 2 --per 25 -o ~/Archive
```

**Check what a URL is before committing**

```bash
mangadl info <url>
```

---

## See also

- [`README.md`](README.md) — install, features, source table
- [`FEATURES.md`](FEATURES.md) — the full numbered feature list
- [`CHANGELOG.md`](CHANGELOG.md) — what changed, and why
- [`PACKAGING.md`](PACKAGING.md) — building a standalone executable
