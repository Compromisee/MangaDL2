# Changelog

All notable changes to **MangaDL**, newest first.

This changelog starts fresh at v1.0.0 for the [Compromisee/WeebDL](https://github.com/Compromisee/WeebDL)
fork. Earlier upstream history is not carried over.

---

## v1.4.13 — Interactive menu, richer CLI search

### Added — `mangadl menu`

A progressive, numbered interface. Every prompt is a list you answer with a
number; `b` goes back and `q` quits from **any** depth, so it is impossible to
get stranded in a submenu. It covers search, trending, pasting a URL, the
library, bookmarks, settings (folders, formats, sources, filters) and tools.

It deliberately needs nothing beyond `rich`, which is already a hard
dependency. The full-screen `mangadl tui` needs Textual, an optional extra
that in practice is often not installed — so the menu is the interface that
always works.

Edge cases that would otherwise look like crashes are handled: a closed stdin
(a pipe that ran out) and Ctrl-C both unwind cleanly, and running it without a
terminal prints guidance instead of blocking forever on a read that will never
return.

### Added — search syntax

    --type manga|manhwa|manhua|comic|novel   narrow by series type
    --status Ongoing|Completed|...           narrow by publication status
    -n, --limit N                            cap the results
    --sort title|source|chapters|year        sort, with --reverse
    --urls                                   one URL per line, for pipes
    --json                                   machine-readable output
    --open N                                 show details for result N
    --download N                             download result N

`--open` and `--download` act on the numbers just printed, so finding
something and acting on it is one command instead of a copy-paste of a URL.

`--type` is derived rather than requested, for the same reason the GUI filter
is: only one of the twelve sources accepts a type parameter. The type is
classified from origin language and tags, with a per-source default for
single-type catalogues, and results whose type cannot be determined are kept —
dropping them would erase whole sources from a filtered search. Sorting by
chapters puts unknown counts last rather than treating them as zero.

### Fixed — `mangadl tui` crashed instead of explaining itself

Textual was imported at module scope while the "Textual is not installed"
message lived in `run_tui()` further down. With Textual absent the module
failed *while it was still being imported*, so the friendly message never ran
and the command died with a raw `ModuleNotFoundError` traceback. The import is
now guarded, and the message points at `mangadl menu`, which needs nothing.

### Fixed — the landing page was quoting stale numbers

Six counters had drifted, three of them contradicting each other on the same
page: 330 vs 408 features, 376 vs 255 tests, and 9 sources when there are 12.
The genre metric said 99 where the live merge produces 116. All now match the
repository.

### Tests

609 offline (up from 583) + 21 live.

---

## v1.4.12 — GUI crash hardening

The GUI was described as very prone to crashing. Four measured causes, plus
one plain bug the audit turned up.

### Fixed — 87 of 102 bridge endpoints could raise into pywebview

Every public method on the API object is called from JavaScript. An exception
gets marshalled across the native bridge, which surfaces as a rejected promise
at best and can tear the view down at worst -- and the JS side cannot tell
"the endpoint blew up" from "the endpoint returned nothing". Only 15 methods
guarded themselves.

A metaclass now wraps every public method, so failures come back as
``{"ok": false, "error": ...}`` -- the shape ``callApi()`` already understands.
Measured after: 102 of 102 guarded, and 0 of 8 hostile-argument calls raise.
Doing it by hand is what decayed to 15 in the first place, so a method added
later is protected automatically.

### Fixed — a bad queue entry killed the download thread

``_start_queued()`` runs in the *finally* of a finished job's thread. A cart
entry with a non-numeric option (``retries: "not-an-int"``) made ``int()``
raise out of ``_spawn`` on that thread, with no handler: the job reported
done, the worker died, and the queue silently stalled. Verified with
``threading.excepthook`` -- before, one escaped exception; after, none.

Download options are now coerced and clamped rather than trusted, and a
malformed entry is dropped with an error event instead of taking the queue
with it.

### Fixed — the cover cache was bounded by count, not bytes

A proxied cover is a base64 data URI: 116 KB measured for one Webtoons cover.
The 240-entry cap therefore held ~28 MB, and scaled without any ceiling for a
source with larger art. It is now capped at 24 MB with proper LRU eviction --
the old code called ``clear()``, throwing away every cover the moment it
filled. Oversized items are served but not retained.

### Fixed — a rejected call left the UI hung and silent

There were no ``unhandledrejection`` or ``error`` handlers. Measured with a
failing endpoint: the loading spinner ran forever, **no message was shown at
all**, and the failure escaped to the console. There are now global handlers
that clear stranded spinners and surface a message, and the hot paths --
``search``, ``browse``, ``get_manga``, ``get_sources`` -- go through the
guarded wrapper. A failed search shows a retry action instead of a dead
screen. Measured after: 0 unhandled rejections, spinner cleared, message
shown.

### Fixed — Invert never worked

The audit found ``renderChapters()`` being called although no such function
exists; the real name is ``renderChapterList()``. Invert has thrown a
``ReferenceError`` on every click since it was added in v1.4.6 -- the
selection changed in state but the rows never repainted and the handler
aborted before updating the download button. A test now scans for any helper
that is called but never defined.

### Tests

583 offline (up from 552) + 21 live.

---

## v1.4.11 — One config.json, and the settings-loss bug behind it

### Fixed — settings resetting themselves

Theme, accent, sources, passcode preferences and the output directory would
all revert at once. The cause was not the individual settings screens, which
work: it was the store underneath them.

`settings.json` was the **only** store in the app that wrote without a lock
and without an atomic replace -- every other file (`config.json`,
`library.json`, `filters.json`, `progress.json`, `lock.json`) already used
tmp+`os.replace`. That lost data two ways:

* **An interrupted write** left truncated JSON on disk. `load_settings()`
  caught the `ValueError` and quietly returned the defaults, so a single bad
  shutdown reset every preference with no error anywhere.
* **Concurrent saves clobbered each other.** `set_settings()` did
  read-modify-write outside any lock, and so did the download-folder picker.
  Whichever landed last wrote back the state it had read, erasing the other's
  change. Measured on the old code, four threads saving at once destroyed the
  theme, accent and output directory in **5 of 5** runs; after the fix,
  **0 of 5**.

The Save button only posts 17 of the 35 keys, so any save at all could take
the appearance settings with it. That is now covered by a test.

### Changed — everything lives in config.json

`config.json` already held the per-source ranking and exclusion. It now also
holds the app settings, in two clearly separated sections::

    { "settings": { "theme": ..., "output_dir": ... },
      "sources":  { "mangadex": { "enabled": true, "rank": 0 } } }

Both sections share one `RLock` and one atomic write. `save_config()` also
refuses to drop the settings section, since its callers only ever build the
sources half.

An existing `settings.json` is folded in on first read and then left alone;
the per-source config already in `config.json` is preserved. Verified with
both files present, and with a corrupt legacy file.

### Note

While reproducing this I first wrote a browser probe that injected the
pywebview bridge after page load. `whenReady()` waits for the
`pywebviewready` event, so boot never ran and the probe "reproduced" dead
themes and an empty source list. That was the harness, not the app -- firing
the event correctly showed the UI working. The real defect was in the
persistence layer, which is what the measurements above cover.

### Tests

552 offline (up from 534) + 21 live.

---

## v1.4.10 — Bookmark drag-and-drop actually works

Dragging a bookmark did nothing. The HTML5 wiring itself was fine -- a real
mouse drag from the card body onto a folder tile did fire `dragstart` ->
`dragover` -> `drop` and call `move_bookmark`. The v1.4.7 test that "passed"
had dispatched a synthetic `drop` event, which skips the whole drag gesture,
so it never exercised the paths that were broken. Four real blockers:

**The cover swallowed the gesture.** An `<img>` is natively draggable, so
starting the drag on the artwork -- which is most of the card's surface, and
where anyone would naturally grab -- dragged the *picture* instead of the
card. Measured payload: `text/uri-list, text/html, Files`, none of which the
folder tile accepts. The cover is now `draggable = false`.

**There was often nothing to drop onto.** The folder grid is hidden when no
folders exist, so on a fresh install the drag had no target anywhere on
screen. Dragging genuinely did nothing, and there was no way to tell why.
Two floating drop zones now appear *while* a drag is in progress: **All
bookmarks** and **new folder**.

**A filed bookmark could not come back.** Once inside a folder there was no
root drop target, so filing was one-way.

**The highlight flickered off mid-drag.** `dragleave` fires when the pointer
crosses onto a *child* element, so the naive handler cleared the drop state
while the pointer was still over the tile. Enter/leave pairs are now counted.

One more, found while verifying: the first version of the drop zones toggled
`display` on an in-flow element, which reflowed the grid and **shifted the
cards out from under the pointer** the instant the drag began -- it hung the
test harness. The zones are now `position: fixed` and fade in, so the class
alone causes zero layout change (measured: card Y identical before/after).

A missed drop is also swallowed now; the browser would otherwise treat it as
"open this link" and navigate the whole app away.

### Tests

534 offline (up from 529) + 21 live. The drag tests now use real mouse
gestures rather than synthetic events, which is what let the original bug
through.

---

## v1.4.9 — Dialog inputs themed

### Fixed — the folder name field was unstyled

The themed-input rule is scoped to `.settings-card` / `.setting-row`. The
folder-name field and the prompt modal live in overlays, so nothing matched
them and they fell back to the browser default. Measured against a correctly
styled settings input:

| | settings input | dialog input (before) |
|---|---|---|
| background | `rgb(38,38,50)` | `rgb(255,255,255)` |
| text | `rgb(230,230,240)` | `rgb(0,0,0)` |
| border | `1px solid` | `2px inset` |
| radius | `12px` | `0px` |
| font | Inter 13px | Arial 13.3px |

White box, black text and an inset border on a dark panel. This is the same
bug the settings inputs had in v1.3.0, one layer up.

Rather than write a second near-duplicate block, the dialog inputs were added
to the existing rule — base, `:hover`, `:focus` and `::placeholder` — so the
two can never drift apart.

### Fixed — lock screen fields rendered in Arial

Sweeping every text input for browser defaults turned up a smaller related
issue: `.lock-input` never set `font-family`, so the passcode field and both
recovery fields used Arial while everything around them used Inter. Their
colours were already correct, which is why it read as slightly-off rather
than broken. Zero inputs now fall back to browser defaults.

### Tests

529 offline (up from 523) + 21 live, including a sweep that maps every text
input to the rule styling it.

---

## v1.4.8 — Overlay buttons fixed, shortcuts moved into Settings

### Fixed — the shortcuts X button, and every exit from the folder picker

`app.js` binds its listeners as it runs. Both overlays were declared *after*
the `<script>` tag, so at bind time `$("shortcutsClose")` and
`$("fpCancel")` were `null` and no handler was ever attached. There was no
console error, and the buttons were fully hit-testable, which is why this
looked like a styling or z-index problem rather than a missing listener.

Confirmed with CDP `DOMDebugger.getEventListeners`:

    shortcutsClose   listeners=NONE
    fpCancel         listeners=NONE
    modalCancel      listeners=['click']     <- declared above the script

The reported X button was the visible half of it. The folder picker was
worse: **Cancel, "Just bookmark it", Create and the backdrop were all dead**,
so once that dialog opened there was no way out of it. Both overlays now sit
above the script tags; all five exits verified working.

A test now enforces the rule generally — every id that `app.js` attaches a
listener to must appear before the script — so a future overlay cannot
reintroduce this.

### Changed — shortcuts live in Settings

The full list is rendered into a **Keyboard shortcuts** card in Settings,
from the same array the key handler uses, so the two cannot drift apart.
Pressing `?` still opens the quick overlay from anywhere. The rail's "Keys"
button was removed, since it was a second home for the same thing.

### Tests

523 offline (up from 517) + 21 live.

---

## v1.4.7 — Bookmark folders, type filter, cover and corner fixes

### Fixed — covers missing in Bookmarks and Library

Both views built their tile with a raw `<img src="...">`. This document sends
`no-referrer` (MangaDex serves a placeholder otherwise), so hotlink-protected
CDNs answer **403** from a bare `<img>` and sharded hosts get no mirror walk.
Search results already went through `attachCover()`, which proxies those
through Python — bookmarks and library rows did not, so covers from Webtoons
and friends were permanently blank there.

Bookmarks were also storing the *normalised* library key as their `url`.
That key has no scheme, so every bookmark linked nowhere. They now keep the
URL as given, plus any `cover_mirrors`.

### Fixed — the download queue was invisible

The queue card was nested inside `#dlActive`, which starts hidden and is only
revealed once a job is running — so a queue built up *before* pressing
Download could never be seen. It now sits outside that container and renders
whenever the Downloads view opens.

### Fixed — the Type filter did nothing

Searching "one piece" restricted to **Manhwa** returned 62 results, all of
them manga. Only one of the twelve sources (Weeb Central) implemented a
`series_type` parameter; every other source silently ignored it.

Type is now derived rather than requested: `classify_type()` maps origin
language (`ja` → Manga, `ko` → Manhwa, `zh` → Manhua) with explicit tags
taking priority, and sites with a single-type catalogue declare a
`default_series_type` fallback. Measured after: "one piece" as Manhwa returns
**0**, as Manga **41**; "solo leveling" as Manhwa returns 2, as Manga 3.

Results whose type genuinely cannot be determined are **kept** — dropping
them would erase whole sources from every filtered search.

### Fixed — square corners missed the most visible shapes

The setting flattens the radius variables, but the search box, both progress
bars and a dozen pills hardcoded `999px`, which no variable can reach. 26
such rules existed. Measured: `.searchbar` stayed at 999px in square mode
before, now 0px.

### Fixed — chapter min/max appeared to do nothing

The filter worked; the data did not exist. Only **5 of 22** results carried a
chapter count, because MangaDex leaves `lastChapter` empty for every ongoing
series and Weeb Central's search is JS-rendered. Unknown counts are kept by
design, so a `min_chapters` of 500 still showed them and the setting looked
ignored.

MangaDex now surfaces `lastChapter` where it exists (coverage 5/22 → 9/22),
and a new **Strict chapter range** option hides unknown counts for anyone who
wants a hard filter. The default stays lenient.

### Added — bookmark folders

* Create, rename and delete folders; deleting keeps the bookmarks and moves
  them back to the root, so nothing is lost by accident.
* File a bookmark by **dragging it onto a folder tile**, or pick a folder
  from a popup when bookmarking (offered only when folders exist, so the
  first bookmark is still one click).
* Optional per-folder **lock** and **blurred covers**.
* A folder's cover is the first book added to it.
* A bookmark pointing at a deleted folder falls back to the root rather than
  disappearing.

### Added — advanced info, custom columns, tidier filters

* **Advanced info** (opt-in) shows year, status, type, original language,
  demographic, last chapter/volume, authors and artists on the manga page.
  Every field is optional and omitted when a source does not report it.
* **Result columns** setting: 0 keeps the responsive fit, 1–14 pins a count.
* The **source picker was removed** from the search filter row — enabling and
  ranking sources already lives in Settings.

### Tests

517 offline (up from 464) + 21 live. The new suite gets its own isolated
`HOME` per test; without it, folder state leaked between cases.

---

## v1.4.6 — Multi-genre search, full-width layout, shortcuts, count fixes

### Fixed — "downloaded" on the manga page was wrong

Three separate causes, all measured:

* **URL variants missed the library.** The key only stripped a trailing
  slash, so of seven realistic variants of one URL, **five missed** —
  `http://` vs `https://`, a `www.` prefix, a `?query`, a `#fragment` and a
  different case. Reaching a manga by a slightly different link made an
  already-downloaded series look untouched. Keys are now normalised, and old
  entries are found and migrated rather than orphaned.
* **Chapter labels drift.** Several sources append the release date to the
  label (`Chapter 02 21/02/2026`). When a site edits that date the recorded
  name stops matching the listed one, so a downloaded chapter showed as
  missing — *while still counting toward the total*, which is why the
  "N downloaded" pill and the highlighted rows disagreed. Matching is now on
  the chapter **number**, and the pill is derived from the same match.
* **`get_library_entry` indexed the library with a raw URL**, which the
  normalised keys broke. Replaced with a tolerant `library.get_entry()`.

The stored entry keeps the URL as given — the key has no scheme, so using it
for display would have produced links that do not open.

### Fixed — URLs with tracking parameters returned zero chapters

Four sources filtered chapter links by "does this href start with the series
path?" and built that prefix from the **full** URL, query string included.
Pasting a link with `?ref=` or `utm_*` made the prefix unmatchable, so every
chapter was rejected and the manga silently showed **no chapters at all**.
Measured on ManhwaRead: 36 chapters clean, **0** with `?ref=x`. Now a shared
`Source.series_path()` strips the query and fragment; all three affected
sources return identical counts with and without parameters.

### Fixed — two genre endpoints that always 404'd

* **Manhwa18** used `/genres/<slug>`; the site serves `/webtoon-genre/<slug>`
  (`/genres/`, `/genre/` and `/manga-genre/` are all 404). Verified 24 cards
  per genre, paginated.
* **nhentai** was handed shared genre labels like "action" that are not
  nhentai tags and 404, burning four retries and logging an error each time.
  Unknown labels now fall back to its search index.

A multi-source genre browse that previously logged four 404s now logs none.

### Added — multi-genre search

Genres combine instead of replacing each other:

* Chips and the dropdown **toggle**, building a selection.
* **Match: all / any** — intersection or union — appears once two are picked.
* Picked genres show as removable chips with a Clear button.

No source accepts more than one genre per request, so each is fetched
separately and combined. The intersection is computed **per source**: the
same title has different URLs on different sites, so pairing a hit from one
with a hit from another would invent matches neither site agrees with.
Verified the AND result is exactly the set intersection (22 of 40 each for
Action ∩ Romance on MangaDex), and that every returned row lists both genres.

With a text query the extra genres are applied to result tags instead.
Results that carry no tags are kept — dropping them would silently hide whole
sources that omit them.

### Changed — content fills the window

Views sat in a fixed 1080px column and centred themselves. Measured before:

| viewport | grid | unused | columns |
|---|---|---|---|
| 1280px | 1080px | 11% | 6 |
| 1920px | 1080px | **42%** | 6 |
| 2560px | 1080px | **57%** | 6 |

After, at 1920px: 1780px wide, **4% unused, 10 columns**. The caps are now
ceilings rather than fixed widths, so wide screens gain columns while an
ultra-wide monitor does not stretch covers into one unreadable row. Settings
forms deliberately stay narrower so they remain scannable.

### Added — keyboard shortcuts and QOL

18 shortcuts with a `?` help overlay generated from the same list the handler
uses, so the two cannot drift apart.

* `/` focus search · `?` help · `Esc` close/clear · `r` refresh
* `g` then `s d b l u ,` to navigate
* On a manga: `a` all · `n` new only · `c` clear · `i` invert · `d` download
  · `q` queue · `b` bookmark · `y` copy title and link

Shortcuts are ignored while typing in any field and while the lock screen is
up, and modifier combos are left to the browser. One subtlety: Chromium
reports `Shift+/` as key `/` with `shiftKey` set, which matched "focus
search" before the help overlay could ever open — shifted keys are now
matched explicitly.

Also added: **Invert** chapter selection (acting on visible rows only, like
the other bulk buttons) and **copy title + link** with an `execCommand`
fallback, because WebView2 does not always grant clipboard-write.

### Tests

464 offline (up from 424) + 21 live.

---

## v1.4.5 — ManhwaRead bulk fix, download cart, concurrent downloads

### Fixed — ManhwaRead bulk downloads lost chapters

Downloading a range from ManhwaRead reliably dropped chapters with
`Could not decode chapterData ...: Incorrect padding`.

The reader's page list is base64-encoded JSON, and the site **strips the `=`
padding** whenever the encoded length is not a multiple of four. Python's
`base64.b64decode` is strict about padding, so those chapters raised and were
skipped. Measured over twelve consecutive chapters of one series: chapter 03
had `len % 4 == 2` and failed while the other eleven decoded fine.

That ~8% hit rate is exactly why a single chapter usually worked and a bulk
range did not — the longer the range, the likelier it contained a bad one.
Re-padding to the next multiple of four fixes it. A 1–6 range that previously
finished 5/6 with one failure now completes 6/6.

### Fixed — connection pool smaller than the worker count

Every bulk download logged `Connection pool is full, discarding connection`.
urllib3 pools ten connections per host by default while the engine runs up to
sixteen image threads, so the surplus connections were closed and reopened for
every page. The pool is now sized to the worker ceiling: measured 0 warnings
after, on a job that produced them continuously before.

### Added — download cart and concurrent downloads

Several manga can now download at the same time.

* **Add to queue** next to the download button queues a manga and lets you
  keep browsing; anything past the limit waits for a free slot and starts
  automatically when one opens.
* **Download queue** panel lists running and pending jobs with per-job status,
  and pending entries can be removed individually or cleared.
* **Concurrent manga** setting (1–5, default 2).
* Stopping is per-job: `stop_download(job_id)` stops one download and leaves
  the others running. Verified live — stopping one of two in-flight jobs let
  the other finish a full 300-page download.
* A cancelled job now reports **stopped** rather than **failed**.

### Fixed — concurrent downloads mixed up chapters

This was the real hazard in running jobs side by side, and it existed in the
event layer rather than on disk.

Progress events were coalesced into a map keyed on the **chapter name alone**,
and the UI's progress rows used the same key. Chapter names are not unique
across manga, so two series both reporting "Chapter 01" collapsed into one
entry: one series' progress silently overwrote the other's, and they shared a
single progress bar.

Every engine event is now stamped with a job id, and both the coalescing map
and the UI rows are keyed on `(job, chapter)`. Aggregate counters are summed
across jobs instead of being overwritten, and a chapter row shows its owning
manga only when more than one download is running, so a single download looks
exactly as it always has.

Verified end-to-end with three concurrent jobs including two colliding
"Chapter 01"s: 0 unstamped events, correct per-job chapter counts (5/3/2), and
each series' Chapter 01 byte-distinct (31 vs 38 pages, different hashes) — no
cross-contamination. Output paths were already per-manga, so files on disk
were never at risk.

### Tests

424 offline (up from 393) + 21 live.

---

## v1.4.4 — nhentai, Webtoons and Natomanga covers; three new sources

### Fixed — nhentai returned nothing

Two separate faults, both measured against the live site:

* **Browse was always empty.** It fetched the site root, which is a landing
  page carrying **zero** `.gallery` cards. `/popular` is the real listing and
  returns 25 per page. The `Trending` sort mapped to `/popular-today`, a 404.
* **7 of the 12 genres were invented.** The list was generic manga genres
  rather than nhentai tag slugs; `romance`, `drama`, `fantasy`, `school-life`,
  `vanilla`, `historical` and `sci-fi` all answered **404**, so those genre
  browses failed outright. Replaced with slugs verified to return results
  (`big-breasts`, `sole-female`, `nakadashi`, `full-color`, …).

Covers now also follow the ordered `data-fallbacks` list the site puts on each
card — thumbnail, then `.webp`, then the first page — instead of the single
`src`, which is not always present on the CDN.

### Fixed — Webtoons covers did not load

`webtoon-phinf.pstatic.net` answers **403 to any request whose Referer is not
webtoons.com** (measured: 403 with no Referer, with `file://` and with
`example.com`; 200 with `https://www.webtoons.com/`).

The GUI sends `<meta name="referrer" content="no-referrer">` because MangaDex
serves a "read this at MangaDex" placeholder otherwise, so the two demands are
mutually exclusive in one document and no `<img>` tag can satisfy both.

Sources can now declare `cover_needs_referer`, and those covers are fetched by
Python with the correct header and handed to the page as a `data:` URI through
a new `proxy_cover` API (bounded cache, 240 entries). Verified in Chromium: six
Webtoons covers decoded at 480×623, none blank. Of the twelve sources only
Webtoons needs this — every other cover CDN answered 200 with no Referer.

### Fixed — Natomanga covers (re-researched)

v1.4.1 treated `img-r1` / `img-r2` / `imgs-2` as interchangeable mirrors and
rewrote a failing cover onto each sibling. **Re-measuring disproved that.**
Over ten consecutive search covers, each requested from all three hosts:

| host | 200s |
|---|---|
| the host named in the page markup | **10/10** |
| `img-r1.2xstorage.com` | 3/10 |
| `img-r2.2xstorage.com` | 1/10 |
| `imgs-2.2xstorage.com` | 6/10 |

They are content shards, not mirrors: `/thumb/naruto.webp` is 200 on `img-r1`
and a hard **404** on `img-r2`. Every rewritten fallback was a likely 404, so
the failure was being made worse. The URL from the markup is now the only
candidate, and the real failure mode — a transient 429/503 on the correct
host — is handled by retrying the *same* URL once.

### Added — three sources (twelve total)

| Source | Site | Notes |
|---|---|---|
| `mangadass` | mangadass.com | 18+ |
| `manga18club` | manga18.club | 18+ |
| `hentaiakane` | hentaiakane.com | 18+ |

Findings worth recording:

* **Mangadass** — `/?s=<term>` is a decoy: it returns the homepage grid
  unchanged (identical 24 titles for `naruto`, `daddy` and no query at all).
  `/search?q=` is the real endpoint. Chapters also needed a numeric sort: the
  "Read First"/"Read Last" buttons sit above the list and point at real
  chapters, so document order yielded 2, 3, 4, 5, 6, 7, 8, **1**.
* **Manga18.club** — both `/?s=` and `/list-manga?q=` are decoys returning the
  same 20 rows for every query; the form posts `search`. The reader ships no
  usable `<img>` tags — one placeholder and an obfuscated script — with the
  pages held in `slides_p_path`, an array of base64-encoded CDN URLs. Decoding
  it in Python reproduces exactly the 11 URLs a real Chromium run requested,
  so no browser is needed. Its series cover also had to be read from
  `.detail_avatar`; the previous selector fell through to the "you may also
  like" sidebar and returned a different series' artwork.
* **HentaiAkane** — the request said "hentaikane", which does not resolve
  (`.com`, `.net`, `.org`, `.xyz`, `.to` are all NXDOMAIN); `hentaiakane.com`
  is the live site. Pages come from its `ts_reader.run({...})` payload. Cards
  are scoped to `.bs` because `a.series` on the same page is the sidebar
  popular list, which would inject unrelated titles.

All three are stamped `content_rating: pornographic` and tagged `Adult`, so
Safe mode filters them and the UI shows the `18+` chip. End-to-end verified: a
real CBZ built from HentaiAkane came to 13,279,316 bytes across 14 pages.

### Not added

* **Comix** (`comix.to`) — every `/api/v1/` endpoint answers
  `403 {"message":"Missing token."}`. The token is produced by an obfuscated
  anti-bot chunk; the call still 403s from inside a real browser session
  holding `cf_clearance`, and the SPA renders a blank page headless (0 images,
  0 API responses observed). Nothing could be read reliably.
* **Comick** — unchanged from v1.0: `md_images` is empty for every title.

### Tests

393 offline (up from 355) + 21 live. Two v1.4.1 tests that asserted the
disproven Natomanga mirror behaviour were rewritten to assert the measured
behaviour instead.

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
