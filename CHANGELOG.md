# Changelog

All notable changes to **MangaDL**, newest first.

This changelog starts fresh at v1.0.0 for the [Compromisee/WeebDL](https://github.com/Compromisee/WeebDL)
fork. Earlier upstream history is not carried over.

---

## v1.4.3 — Aggregator fix, chapter-count filters, Webtoons and nhentai

### Fixed — multi-source search silently lost sources

Searching a popular title with several sources enabled returned far fewer
results than it should, and appeared to work only with a single source on.

Mangakatana soft-throttles by answering **HTTP 200 with a zero-length body**
instead of a 429. Measured: roughly 60% of rapid repeat searches came back
empty, while an immediate retry succeeded. `fetch()` treated that as success,
so the source contributed nothing and the aggregate looked broken. Empty
bodies are now retried with backoff — measured 6/6 successful searches after
the fix, against ~40% before.

This was a shared bug in the base class, so every source benefits. It also
explains the Natomanga symptoms: its searches and covers were fine in
isolation but dropped out under aggregate load.

Duplicate collapsing already keeps the highest-ranked source's copy and lists
the rest under `also_on`, which is now visible because the sources actually
report in. "One Piece" went from 25–29 unstable results to 54 across six
sources.

### Added — chapter-count filters

`min_chapters` was stored in settings but never applied. Both a minimum and a
maximum now work, in Settings under Content filters. Counts are read from an
explicit count, `last_chapter`, or the newest chapter label. Series whose
count cannot be determined are never filtered out — judging an unknown count
would make whole sources disappear from every filtered search.

### Added — two sources

- **Webtoons** (`webtoons`) — official site. Episodes are paged, and the
  viewer keeps real page URLs on `data-url` rather than `src`. Its CDN is
  hotlink-protected (403 without a Referer, 200 with), so chapters carry one.
- **nhentai** (`nhentai`) — **adult only**, tagged `pornographic` so Safe
  mode removes it and it shows an 18+ chip. Thumbnails are `t`-suffixed; the
  full page is the same path without it (21 KB vs 464 KB).

Both verified downloading real CBZs with zero empty pages.

### Not added

**HentaiRead** sits behind a Cloudflare interstitial (HTTP 403, "Just a
moment"). It would need FlareSolverr running to work at all, so shipping it
as a normal source would have produced a site that silently fails for most
people.

### Testing

- 355 offline tests plus 21 live-site tests

## v1.4.2 — Search fixed, square corners, thinner rail, better lock

### Fixed — search did nothing

Only genre/category browsing worked; typing a query and pressing Enter did
nothing. The search input carried a native `<datalist>`, and in WebView2 an
open datalist popup **consumes the Enter keypress**, so `keydown` never
reached the handler. The Search button worked, which is why category
browsing appeared fine.

The datalist is gone. Enter is handled on both `keydown` and `keyup`
(debounced so one press cannot fire twice), and suggestions now render into
a themed list that can actually be styled.

### Fixed — lock screen appeared too late

The overlay started hidden and was only shown once `lock_status` returned, so
a protected app was briefly readable. It now paints on the very first frame.

Two safeguards came with that, because covering the UI up-front is risky:

- the previous lock state is remembered, so an app with no passcode never
  flashes an overlay it does not need
- a fail-safe timer clears the overlay no matter what. Without it, a missing
  bridge or a hung call left the app permanently covered — caught when the
  existing dropdown tests started timing out against an unclickable page

### Added — square corners mode

A single switch in Settings turns off all rounding. It zeroes the radius
scale and flattens pills, fields, dropdowns and switches, while leaving
genuine circles (spinner, lock badge) round so controls stay recognisable.

### Added — thinner, expandable side rail

The rail is now 60px instead of 84px. An expand button widens it to 194px
and shows the labels inline; the state is remembered between runs.

### Improved — lock screen

Show/hide passcode button, a remaining-attempts counter that turns amber
then red, a shake on a wrong entry, and a live cooldown countdown that
disables the field while it runs.

### Testing

- 331 offline tests plus 17 live-site tests

## v1.4.1 — Crash on close, Natomanga covers, lock order, rounding, saved folder

### Fixed — crash on window close

Closing the window raised `unhashable type: 'dict'`. pywebview collects event
handler return values into a **set** (`return_values.add(value)` in
`webview/event.py`), and the `closed` handler added in v1.1.0 was
`api.shutdown`, which returns `{"ok": True}` for the JS bridge. A dict is not
hashable, so every close threw. The handler is now a thin wrapper that
discards the return value; `shutdown()` keeps its dict for the bridge.

### Fixed — Natomanga covers not showing

Natomanga mirrors each thumbnail across interchangeable CDN hosts, and any
one of them intermittently fails while the others serve the identical file.
Measured live: `storage.waitst.com` returned **429** and `img-r2` returned
**404** for images that came back **HTTP 200 with identical bytes** from the
sibling hosts.

Covers now carry a mirror list, and the UI walks it on error instead of
giving up on the first failure. Only when every mirror fails does the
fallback tile appear.

### Fixed — passcode did not gate startup

The lock check ran seven steps into boot, so settings, sources, genres,
filters, statistics and the trending feed were all fetched and painted
underneath the overlay before it appeared. The lock is now the first thing
boot does, and the rest waits for the unlock. Verified: only `lock_status`
is called before the passcode is accepted.

### Fixed — inconsistent corner rounding

Radii had drifted to 13 different ad-hoc values (6, 7, 8, 9, 10, 12, 13,
14px and more), which read as sloppy across the settings panels. Everything
now snaps to a four-step scale — `--radius-sm/md/lg/xl` — with pills and
circles deliberately left alone.

### Fixed — download location was not saved

Picking a folder only filled in the field; the choice was lost on restart.
It is now written to `settings.json` immediately, whether picked from the
folder dialog or typed directly, and both folder fields stay in sync.

### Testing

- 307 offline tests plus 17 live-site tests

## v1.4.0 — Chapter-range filenames, moved-folder recovery, chapter filters

### Changed — files are named by the chapters they contain

A "download all" archive was previously just `Naruto.cbz`, which said nothing
about what was inside. Output files now carry their chapter range:

    Naruto - Chapters 001-050.cbz      one file for everything
    Naruto - Chapters 011-020.cbz      bundled by 10
    Naruto - Chapter 007.cbz           one file per chapter

Non-contiguous selections collapse into runs (`001-003, 007-008, 020`), half
chapters stay inside a run (10, 10.5, 11 -> `010-011`), and a heavily
fragmented pick truncates to `001-013 (7 chapters)` so the filename cannot
grow unbounded. Two new placeholders, `{chapters}` and `{count}`, are
available in the naming templates.

Anyone carrying the old `{title}` template from a previous version is
migrated forward automatically — otherwise the stored value would keep
overriding the new default. Custom templates are left alone.

### Added — moved your downloads? nothing breaks

Moving a downloads folder used to orphan every library entry silently. Now:

- **Check library** reports entries whose folder or files have gone
- **Find moved folders** proposes matches by folder name. Proposals are
  inert until you confirm, so a wrong guess cannot rewrite anything
- **Pick new downloads folder** adopts a new root, saves it to settings and
  re-links everything under it in one step
- Re-linking rewrites the directory *and* each output path, and preserves
  download history, title and source
- New **Moved files** panel in Tools, plus
  `mangadl library verify|scan|move`

### Added — chapter min/max and sorting

The chapter list gained a minimum and maximum chapter number, a name filter,
newest/oldest sorting, and a "hide downloaded" toggle. The count pill shows
`visible / total` and a note reports how many rows a filter is hiding.

Filtering only changes what is displayed — selections are keyed by the real
chapter index, so hiding a row never silently drops it from a selection. The
bulk buttons deliberately act on *visible* chapters only: selecting rows you
have filtered out would mean downloading things you cannot see. "Latest" now
picks the highest-numbered visible chapter rather than the last array entry.

### Fixed

- The Tools tab's new panel did not load when its tab was clicked: the loader
  was wired into the view switcher but not the tool-tab handler.

### Testing

- 285 offline tests plus 17 live-site tests

## v1.3.0 — Three new sources, and the source toggles actually work

### Fixed — no way to turn a source off

The toggle existed but was invisible. The CSS targeted `.switch .track`
while most of the markup emits a bare `<span>` with no class, so **no rule
matched** and every switch in the app rendered zero-width. Measured before
the fix: `width: 0`, `matchesTrackRule: false`.

The markup was also inconsistent — 5 switches used `class="track"`, 7 did
not — so the CSS now matches both variants and the markup is normalised to
one shape. All 12 switches verified at 46x26.

Two related contrast problems went with it: the off-state track was almost
the same colour as the row behind it, and dimming a disabled row also dimmed
the control needed to re-enable it.

### Fixed — content filter inputs unstyled

The blocked-tags and blocked-titles fields matched no CSS rule at all, so
they fell back to the browser default: white background, black text, inset
border, Arial. Unreadable on every dark theme. Settings text, number and
password inputs are now themed, with a focus ring.

### Added — three sources

- **Omega Scans** (`omegascans`) — JSON API. Chapters come from
  `/chapter/query?series_id=`, not the series record, whose `seasons` array
  is always empty. Coin-locked chapters (`price > 0`) serve no images, so
  they are skipped rather than "downloaded" empty.
- **ManhwaRead** (`manhwaread`) — the reader renders pages as `blob:` URLs,
  so scraping `<img src>` yields nothing. The real list is base64 JSON in a
  `var chapterData` block. Its CDN also answers **403** without a Referer,
  so chapters carry one explicitly.
- **Manhwa18** (`manhwa18`) — **adult only.** Results are tagged
  `pornographic` so the existing Safe mode filter removes them, and the
  source shows an `18+` chip in Settings.

Verified end-to-end: all three search, list chapters and download real CBZ
files with zero empty pages.

### Cover art research

Unlike MangaDex, all three new CDNs return identical bytes with or without a
Referer, so no placeholder-swap workaround is needed for them. ManhwaRead's
page CDN is the exception and is handled per-chapter.

### Testing

- 254 offline tests plus 17 live-site tests
- Tests that hardcoded "4 sources" now count the registry, so adding a
  source no longer breaks them

## v1.2.0 — New GUI tabs and a GitHub-style landing page

### Added — three new GUI tabs

Nine backend features had no interface at all. They now do:

- **Updates** — the watchlist, with per-series new-chapter counts, a rail
  badge, and a "Check now" button that queries every source in parallel. A
  Watch button on the manga page feeds it.
- **Insights** — six headline metrics, a per-source bar chart, a fourteen-day
  activity sparkline, and biggest/most-recent series lists.
- **Tools** — five sub-panels: disk usage per series, SHA-256 duplicate
  scanning with a wasted-space total, orphan detection, live circuit-breaker
  health, and a clickable search history.

Every new view goes through a `callApi` wrapper, so a missing endpoint or a
Python-side exception logs a warning instead of blanking the tab.

### Added — GitHub-style landing page

`docs/index.html` is rebuilt on Primer design tokens as a repository page:
file listing, README pane, sidebar with topics, releases and a language
breakdown. Five deep-linkable tabs (Code, Features, Screenshots, CLI,
Sources) with working browser back/forward, real light and dark modes
remembered in localStorage, a screenshot gallery, and copy-to-clipboard
install commands.

The numbers on the page are computed from the repository — 228 features, 4
sources, the language split and the version badge. Star and fork counts were
deliberately left out: a static page cannot know them, and inventing them
would present made-up figures as fact.

### Fixed

- Bar chart fills rendered as empty tracks: `<span>` is `display: inline` by
  default, so width and height were ignored.
- Landing-page tabs did not respond to same-document hash changes, so
  in-page links and browser back/forward did nothing.

### Testing

- 241 offline tests plus 14 live-site tests

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
