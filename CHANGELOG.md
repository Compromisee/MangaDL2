# Changelog

All notable changes to this fork, newest first.

## v2.6.2 — Direct-file launch fix

### Fixed
- `ImportError: attempted relative import with no known parent package` when
  running `weebcentral/tui.py` or `weebcentral/cli.py` directly as files
  (e.g. PyCharm's "Run file"). Both modules now self-bootstrap their package
  context, so `python weebcentral/tui.py` works from any working directory

### Added
- Root-level `tui.py` runner (`python tui.py`), matching the existing
  `gui.py`

## v2.6.1 — Windows WebView2 noise fix

### Fixed
- **Windows console/log spam**: pywebview's WinForms backend exposes a .NET
  object as `window.native`; Edge's accessibility/autofill layer enumerates
  it recursively (`AccessibilityObject.Bounds.Empty.Empty...`,
  `ModifierKeys.A.A...`) until Python's recursion limit, flooding the console
  with `[pywebview] Error while processing window.native...`. The app now
  deletes `window.native` on page load (it was never used) and a logging
  filter drops any remaining bridge noise from the console and the log file
  while keeping real pywebview errors
- Documented the related `E_NOINTERFACE` / `ICoreWebView2Controller4` COM
  errors: they mean the machine's WebView2 Runtime is outdated (README and
  PACKAGING troubleshooting tables)

## v2.6.0 — Standalone executable packaging

### Added
- **`WeebCentral.spec`**: PyInstaller spec building an all-inclusive
  executable (GUI + TUI + CLI in one binary); one-folder and `--onefile`
  modes, web assets and Textual data bundled, pywebview platform backends
  as hidden imports, macOS .app bundle, optional Windows icon
- **`launcher.py`**: unified entry point — double-click opens the GUI,
  `tui` / `<url>` / `search` / `resume` arguments route to the CLI
- **`PACKAGING.md`**: complete build guide — prerequisites, one-folder vs
  one-file, per-platform notes (WebView2, Gatekeeper/codesign, WebKitGTK),
  smoke-test checklist, GitHub release + CI workflow sketch, build
  troubleshooting table
- GUI asset loading now resolves `sys._MEIPASS` so the frozen exe finds
  its bundled HTML/CSS/JS
- Verified end-to-end: built with PyInstaller 6.21, ran live search and a
  real chapter download from the frozen binary

## v2.5.0 — Crash-safe resume & logging

### Added
- **Crash recovery**: a job journal (`~/.weebcentral/job.json`) records every
  in-progress download; after a crash/outage the GUI shows a "Resume" banner
  on launch and the CLI gains a `weebcentral resume` command — completed
  chapters are skipped, partial chapters continue where they left off
- **Verified checkpoints**: `.checkpoint` now stores the page count per
  chapter and files are verified on disk before skipping; incomplete chapters
  no longer count as done
- **Atomic image writes**: pages download to `.part` files and are renamed on
  success, so a crash mid-write can never leave corrupt images that resume
  would wrongly skip
- **Rotating file log** at `~/.weebcentral/logs/weebcentral.log` (2 MB x 3
  backups), enabled across GUI, TUI and CLI
- **Logs settings card**: shows log path/size, **Export log** (save-as dialog,
  concatenates rotated parts) and clear-log
- Checkpoint writes are fsynced and thread-safe

### Changed
- A chapter is only recorded as complete when *all* of its pages downloaded

## v2.4.0 — Search experience & filters

### Added
- **Search filters**: sort by Best Match / Popularity / Subscribers / Recently
  Added / Latest Updates / Alphabet, with ascending/descending order toggle
- Status filter (Ongoing / Complete / Hiatus / Canceled), type filter
  (Manga / Manhwa / Manhua / OEL) and official-only filter
- Filters re-run the current search automatically; active-filter dot on the
  filter button; reset button
- Scraper `search()` accepts `sort`, `order`, `official`, `status`,
  `series_type` parameters
- `FEATURES.md` (full feature reference) and this `CHANGELOG.md`

### Changed
- **Search redesign**: stylized three-part title (solid + gradient-shine +
  outline words) with floating icon and staggered entrance
- Search bar starts vertically centered; on search it glides to the top and
  the title fades away; clearing the input brings the hero back
- Stale search responses are discarded (rapid filter changes stay correct)
- Animations kept light: transform/opacity only, capped stagger delays

## v2.3.0 — Landing page, reader integration, naming templates

### Added
- **GitHub Pages landing page** (`docs/index.html`): ambient design matching
  the app - gradient orbs, dot matrix, feature grid, GUI/TUI screenshot tabs,
  CLI terminal demo, copyable install command
- **Open in reader**: `reader_path` setting (e.g. Readest executable) with a
  file picker; Library items get Read buttons; empty path = system default app
- **Library parts**: multi-part downloads expand to list every part with file
  size, per-part Read button and missing-file detection
- **Naming templates** for single-file / per-chapter / range bundles using
  `{title}`, `{chapter}`, `{start}`, `{end}`; Settings card with live preview;
  CLI flags `--name-single`, `--name-chapter`, `--name-range`
- New settings: open-folder-when-done, retries per image (now honored by the
  engine)

### Changed
- `DownloadOptions` gains `retries` and naming-template fields with safe
  fallback for invalid templates

## v2.2.0 — Bookmarks, library, ambient redesign

### Added
- **JSON library** (`~/.weebcentral/library.json`): every downloaded chapter
  recorded with pages, date, outputs and folder; engine writes it
  automatically from all front ends
- **Bookmarks** (`~/.weebcentral/bookmarks.json`) with a bookmark toggle on
  the manga page and a Bookmarks tab (cover grid, hover-to-remove)
- **Library tab**: chapter/page counts, last download, open folder, jump to
  manga, remove entry
- **Green highlighting** of already-downloaded chapters in the chapter list,
  plus a "New only" selection shortcut and downloaded-counter pill
- **6 themes** (Midnight, Mocha, Forest, Plum, Ocean, Light) and **6 accent
  colors**; theme selection moved into Settings
- Animated **dot-matrix** canvas backdrop and drifting **circular gradient
  orbs** over solid pastel-dark backgrounds (both toggleable)
- Confirm modal; confirm-large-downloads guard with threshold setting
- Clear-library / clear-bookmarks actions

### Changed
- Full visual redesign: glassy cards, gradient buttons with glow, shimmer
  progress bars, staggered card entrance animations

## v2.1.0 — Terminal UI

### Added
- **Full-screen TUI** built with Textual: `weebcentral tui` /
  `weebcentral-tui`
- Tabs: Search / Manga / Downloads / Settings with `F1`-`F4` shortcuts
- Chapter multi-select with All / None / Latest and quick-range input
- Format + bundling selectors, live overall and per-chapter progress bars,
  colored activity log, stop control
- Settings shared with the GUI (`~/.weebcentral/settings.json`)
- `[tui]` and `[all]` install extras

## v2.0.0 — Fork rewrite

### Added
- **New CLI** (`weebcentral`): default action downloads *all* chapters into a
  *single CBZ*, sorted into a per-manga folder
- `--per N` bundling: one file per N chapters (1 = per chapter)
- Formats: CBZ / PDF / EPUB / raw images; `--also` for extra formats
- `search` and `info` subcommands; rich progress UI; `--plain` mode
- **pywebview GUI** with Material Symbols (no emojis), light/dark themes,
  live per-chapter progress, chapter picker, settings
- Core split into a `weebcentral/` package: scraper, event-driven
  `DownloadEngine`, packagers, utils, FlareSolverr client
- Checkpoint resume, adaptive rate-limit backoff
- `pyproject.toml` packaging with `weebcentral` / `weebcentral-gui` scripts

### Removed
- Legacy PyQt6 GUI, monolithic `weebcentral_scraper.py` interactive script

---

*Versions before v2.0.0 correspond to the upstream project
([Yui007/weebcentral_downloader](https://github.com/Yui007/weebcentral_downloader)).*
