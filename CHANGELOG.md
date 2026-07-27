# Changelog

All notable changes to **MangaDL**, newest first.

This changelog starts fresh at v1.0.0 for the [Compromisee/WeebDL](https://github.com/Compromisee/WeebDL)
fork. Earlier upstream history is not carried over.

---

## v1.1.0 — Cover, crash, search and performance fixes

### Fixed — MangaDex covers showed a placeholder

MangaDex serves a "You can read this at MangaDex" graphic instead of the real
artwork when the `Referer` is a `file://` URL, which is exactly what the
packaged GUI loads from. Measured against the live CDN: a 59,480-byte
placeholder (600x642) in place of the 143,403-byte cover (512x728). The page
now sends `<meta name="referrer" content="no-referrer">`, which restores the
real artwork. The URLs were never wrong — every one returned HTTP 200.

### Fixed — freeze and crash 0xCFFFFFFF during downloads

The engine emitted one progress event per downloaded image, and each event
became its own `evaluate_js` call: a JSON dump interpolated into a JS string
and marshalled across the native bridge. A 700-chapter job at ~60 pages each
is over 43,000 bridge crossings, which pins a core and takes WebView2 down
with `0xCFFFFFFF`.

Progress events are now coalesced per chapter and flushed on a 120 ms timer as
a single batch, while lifecycle events (start, done, packaged, finished) are
never dropped and terminal events flush immediately. Measured on the crash
scenario: 2,480 events became **one** bridge call.

### Fixed — search results not loading

Startup was a chain of unguarded `await` calls. A single rejecting bridge call
threw out of the whole handler, so everything after it silently never ran —
including the initial trending load. Reproduced: one failing endpoint left
**zero** results rendered. Each startup step is now isolated, so a failure is
logged and the rest still runs; the same scenario now renders results
normally.

### Changed — lower resource usage

- Images stream to disk in 64 KB chunks instead of being buffered whole in
  memory, which previously meant dozens of multi-MB blobs resident at once
- One shared image thread pool per job, replacing a new pool per chapter on
  top of the chapter pool; in-flight requests are capped at 16
- Background dot matrix: capped to 30 fps, dot count bounded, device pixel
  ratio clamped, resize debounced, and it now pauses when the window is
  hidden or the lock screen is up
- The dot colour is cached per theme rather than read via `getComputedStyle`
  on every animation frame, which was forcing a style recalc 60 times a second
- Flush timer, cached sessions and sockets are released when the window closes

### Added — interface polish

- Skeleton placeholder tiles while a search is in flight, replacing a bare
  spinner
- Covers reserve their aspect ratio up front, so the grid no longer reflows as
  each image decodes, and fade in once decoded
- Series with a missing or broken cover get a titled fallback tile instead of
  an empty gap
- Empty and error states now explain what happened and offer recovery actions
  (Retry, Clear genre, Show trending)
- Reduced-motion preferences are respected throughout

### Testing

- 211 offline tests plus 14 live-site tests

## v1.0.0 — Multi-source MangaDL

The first release of the fork under its own name. MangaDL downloads manga from
four sites through a pluggable source layer, with a CLI, a full-screen TUI and
a desktop GUI sharing the same engine.

### Sources

- **MangaDex** via the official JSON API — languages, scanlation groups,
  data-saver mode, correct cover art in three sizes, per-volume covers
- **Mangakatana** — HTML scraping, including its obfuscated JavaScript page
  arrays
- **Natomanga** (Manganato / Mangakakalot successor) — HTML plus the site's
  JSON chapter endpoint
- **Weeb Central** — the original source, with FlareSolverr fallback
- The source is detected automatically from any pasted URL; `-s/--source`
  forces one
- Cross-source search fans out in parallel and merges the results
- Adding a site is one file in `mangadl/sources/` plus one registry line

### Discovery: trending and genres

- **Pressing Search with an empty box shows trending titles** instead of doing
  nothing — the GUI, TUI and CLI all open on a discovery feed
- Genre browsing and genre-filtered search on every source
- 99 genres merged across sites, deduplicated case-insensitively, ordered by
  how widely each one is supported
- Quick-pick genre chips in the GUI, a genre dropdown in the TUI
- Trending results interleave sources so the first screen shows a mix
- `Load more` pagination in the GUI
- Type-ahead search suggestions drawn from your history
- `mangadl trending [genre]`, `mangadl genres`, `mangadl search -g <genre>`

### Robust calling

- Circuit breaker per source: a site that fails repeatedly is skipped
  instantly instead of costing a full timeout on every request, then probed
  again after an escalating cooldown
- Bounded retries with exponential backoff and jitter, and a `retry_if` hook
  so hopeless failures (404s) are not retried
- TTL caches for discovery listings and genre lists — repeat browsing is
  served from memory
- `gather()` runs many calls in parallel and keeps whatever succeeds
- Rate-limit headers (`Retry-After`, `X-RateLimit-Retry-After`) are honoured
- One dead site can never break a search, a browse or a genre listing
- `mangadl health` reports breaker state and cache hit rates

### Provider attribution

- The site a manga came from is shown **directly beneath its title**, with a
  coloured dot and a link back to the original page
- Provider shown in the GUI, the TUI and `mangadl info`
- Source badges on GUI result cards, a source column in CLI results
- Source recorded on library entries, bookmarks and download results

### Source ranking and exclusion

- Drag-and-drop source ranking in GUI settings, with move up/down buttons
- Ranking decides which copy wins when a series exists on several sites
- Exclude a source entirely, or only from multi-source search
- Excluded sources still work from a direct URL, so a shared link never breaks
- Per-source limit, weight, language and delay overrides
- Sources tab in the TUI, and `mangadl config` in the terminal

### Passcode lock

- Optional app passcode: PBKDF2-HMAC-SHA256, 240,000 rounds, per-install
  random salt, constant-time comparison
- The passcode is never stored in plaintext
- One-time recovery key, attempt throttling with escalating cooldown,
  auto-lock on idle, lock on start, optional cover blurring and a hint
- Full-screen lock overlay in the GUI with a built-in recovery flow
- Gates the interface only — downloaded files remain readable on disk

### Tracking

- Per-chapter read state, progress percentages and next-unread jump
- Watchlist with parallel update checking across every watched series
- Free-text notes and 0–5 star ratings

### Library and maintenance

- Search history with suggestions, a persistent download queue, and download
  statistics recorded automatically
- Content filters: blocked tags, titles and authors, safe mode, hide
  cover-less results
- Cross-source duplicate merging that strips decorations such as "(Colored)"
  and reports which other sites carry the same series
- Collections, snapshots, and library import/export as JSON, CSV or Markdown
- Disk usage per series, SHA-256 duplicate scanning with wasted-space totals,
  and orphan detection

### Core engine

- CBZ, PDF, EPUB and raw image output, with multiple formats in one run
- Flexible bundling: one file for everything, per chapter, or per N chapters
- Crash-safe resume with verified checkpoints and atomic image writes
- Parallel chapter and image downloads with configurable workers
- Filename templates with `{title}`, `{chapter}`, `{start}`, `{end}`

### Notable fixes made while building this

- **MangaDex covers**: the thumbnail suffix must follow the *complete*
  filename including its original extension (`abc.png.512.jpg`, not
  `abc.512.jpg`). The naive form returns 404 — the usual cause of missing
  MangaDex cover art
- **Externally hosted MangaDex chapters**: licensed titles on MangaPlus and
  Azuki report `pages: 0` and cannot be downloaded; they are filtered out
  rather than producing empty chapters
- **Mangakatana page arrays**: each chapter ships a decoy single-entry
  JavaScript array alongside the real page list, and both variable names are
  randomised per request, so the longest array is selected
- **Mangakatana listings**: a bare `div.item` selector matches sidebar cards
  that appear before the results grid, which broke pagination; `#book_list`
  now takes precedence
- **Mangakatana browse**: `/manga/page/N` ignores sorting and returns an
  alphabetical dump; the `?filter=1` form is the one the site itself uses
- **Weeb Central genres**: the search route expects `included_tag`, not
  `included_tag[]` — the bracketed form is silently ignored
- Images served as `application/octet-stream` are validated by magic bytes
  instead of being rejected
- Page ordering sorts numerically, so page 10 no longer lands before page 2

### Interface

- **Custom dropdowns** throughout the GUI. Native `<select>` popups are drawn
  by the OS and cannot be themed, so on a dark theme they appeared as bright
  system menus ignoring the accent colour. They are now themed listboxes with
  a type-to-filter box for long lists (the genre list has ~99 entries), full
  keyboard navigation, typeahead and ARIA roles.
- The real `<select>` stays in the DOM as the source of truth, so every
  existing `sel.value` / `innerHTML` / `appendChild` call site keeps working
  and real `change` events still fire.
- Fixed: closed dropdown panels were painted over the page because
  `display:flex` in author CSS overrides the user-agent `[hidden]` rule.
- Fixed: the GUI hero still carried the old pre-fork product name; it was split across
  `<span>`s so the rename missed it.

### Testing

- 182 offline tests plus 14 live-site tests behind `MANGADL_NETWORK_TESTS=1`
- Dropdown behaviour is covered by 27 Playwright tests driving real headless
  Chromium, since DOM, pointer and keyboard behaviour cannot be asserted from
  Python alone. They skip automatically when Playwright is unavailable.

### Not included

- **Comick** was evaluated and deliberately left out. Its `md_images` array
  comes back empty for every title and request variant tested — direct API,
  `tachiyomi=true`, browser headers and the web reader payload — so chapter
  pages cannot be resolved. Natomanga was added in its place. If Comick
  reopens that endpoint it drops in as a single new source module.
