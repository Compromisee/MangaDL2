# Features

A complete feature reference for MangaDL.

## Sources

1. **MangaDex** — official JSON API
2. **Mangakatana** — HTML scraping with obfuscated JS page decoding
3. **Natomanga** — Manganato / Mangakakalot successor, JSON chapter endpoint
4. **Weeb Central** — the original source, FlareSolverr fallback
5. Source auto-detected from any pasted URL
6. `-s/--source` to force a source
7. `mangadl sources` lists every site and its capabilities
8. Cross-source search runs every site in parallel
9. Bare MangaDex UUIDs are accepted as URLs
10. Adding a site is one file plus one registry line
11. Per-source capability flags drive the UI (languages, scanlators, Cloudflare)
12. Shared base class: retries, backoff, rate limits, atomic writes
13. `Retry-After` / `X-RateLimit-Retry-After` honoured
14. Magic-byte image validation (accepts `application/octet-stream`)
15. Per-chapter `Referer` and header overrides for hotlink-protected CDNs

## Manhwa and manhua sources (v1.4.15)

16. **Asura Scans** — `api.asurascans.com` JSON API; the website is an SPA
    that returns one identical document for every URL, so the API is used
    instead
17. Asura paginates on `offset`; `page`, `p`, `skip`, `per_page` and `perPage`
    are all silently ignored and return page one
18. Asura search uses `&search=`; `&name=`, `&q=` and `&title=` are decoys that
    return the entire catalogue
19. **Flame Comics** — parsed from the Next.js `__NEXT_DATA__` payload, which
    carries types, tags, countries and page manifests the DOM never shows
20. Flame's whole 167-title catalogue arrives in one request, so search and
    browse need no further calls
21. Flame page manifests are dicts keyed by stringified index and are sorted
    numerically, not in dictionary order
22. **Demonic Scans** (MangaDemon) — `search.php` HTML-fragment backend
23. Demonic genre filtering is POST-only with numeric ids; over GET the site
    returns the unfiltered catalogue
24. **Witch Scans** — `ts_reader` JSON page lists, per-card series type
25. Witch Scans genre slugs carry percent-encoded emoji; four genres are
    reachable only through the encoded form
26. **Writers' Scans** — client-side catalogue, matched locally exactly as the
    site's own filter does, including alternative titles
27. Writers' Scans pages are rebuilt from `uid` attributes; every `src` on the
    page is a placeholder SVG
28. Writers' Scans coin-locked chapters are skipped
29. **Toonily** — manhwa; page CDN requires a Referer, covers do not
30. **Manhua Plus**, **Manhua Top**, **Manhwa Top**, **MangaRead** — four more
    catalogues across manhua, manhwa and mixed
31. **Setsu Scans** — Cloudflare-gated, registered behind FlareSolverr
32. Shared **Madara** theme scraper backs six sites; each declares only its
    series path, genre prefix and listing path
33. Madara genre slugs are read off each site's own search form rather than
    guessed, so SEO-mangled installs work
34. Madara chapter AJAX is sent with an explicit empty body — a bare POST
    answers 400 with zero bytes
35. Madara search pages with `&paged=`, the only form that works everywhere
36. Cloudflare sources fail in milliseconds when no solver is running instead
    of sleeping through five exponential backoffs

## CLI polish and startup safety (v1.4.16)

37. Rich is an **optional** dependency: the CLI and menu run, and stay
   coloured, when it is not installed
38. ANSI fallback renderer for tables, panels, rules and progress
39. `NO_COLOR`, `FORCE_COLOR` and `CLICOLOR_FORCE` honoured
40. Colour switches off automatically when output is piped
41. Windows ANSI enabled through the console API, with a plain-text fallback
   on hosts that do not support it
42. Download progress adds a percentage and an ETA column
43. `SYNTAX.md`: full command reference, every flag verified against the parser
44. `genres_all()` runs sources in parallel under a deadline
45. A slow source can no longer freeze the GUI on open
46. Sources that time out contribute their offline genre list rather than
    disappearing from the picker
47. Partial genre results are never cached
48. The CLI description is derived from the registry, so it cannot go stale

## Source ranking and exclusion

49. Drag-and-drop source ranking in the GUI
50. Move up / down buttons as a keyboard-friendly alternative
51. Rank order decides which copy wins when a series exists on several sites
52. Toggle a source off to exclude its results entirely
53. Excluded sources still work from a direct URL
54. `search_enabled` — keep a source usable but out of multi-source search
55. Per-source result limit override
56. Per-source weight for duplicate scoring
57. Per-source language override
58. Per-source extra delay for politeness
59. Free-text note per source
60. Ranking is shared by CLI, GUI and TUI
61. New sources are auto-appended, ranked last
62. Stale config entries are pruned automatically
63. `mangadl config` shows the full table
64. `mangadl config enable|disable <source>`
65. `mangadl config up|down <source>`
66. `mangadl config rank <a> <b> ...` to set the whole order
67. `mangadl config reset`
68. Sources tab in the TUI with the same controls

## Provider attribution

69. Provider shown directly beneath the manga title in the GUI
70. Colour-coded provider dot per source
71. "Open on source site" link next to the provider name
72. Provider line under the title in the TUI
73. Provider line in `mangadl info`
74. Source badges on GUI search result cards
75. Source column in CLI search results
76. Source tag in TUI search results
77. Source recorded on every library entry
78. Source recorded on every bookmark
79. Source stamped on download results and plan events

## Passcode lock

80. Optional app passcode
81. PBKDF2-HMAC-SHA256 with 240,000 rounds
82. Per-install random salt — identical passcodes hash differently
83. Constant-time comparison
84. Passcode never stored in plaintext
85. One-time recovery key issued at setup
86. Recovery key is case-insensitive and ignores spacing
87. Recovery flow built into the lock screen
88. Change passcode (requires the current one)
89. Disable lock (requires the passcode)
90. Attempt throttling after 5 failures
91. Escalating cooldown, capped at 15 minutes
92. Auto-lock after N idle minutes
93. Lock on app start
94. Optional cover blurring behind the lock screen
95. Optional passcode hint
96. Lock file written with owner-only permissions
97. `mangadl lock status|set|change|off` from the terminal

## Content filters

98. Blocked tags
99. Blocked title words
100. Blocked authors
101. Safe mode drops adult-rated results
102. Hide results with no cover
103. Minimum chapter count filter
104. Filters apply to both GUI and CLI search

## Duplicate handling

105. Cross-source duplicate detection by normalised title
106. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
107. Best-ranked copy survives a merge
108. `also_on` lists the other sources carrying the same series
109. Toggle merging on or off
110. Interleave mode round-robins sources instead of grouping them

## Reading progress

111. Mark individual chapters read or unread
112. Bulk mark a range
113. Percentage progress per series
114. Unread count per series
115. Jump to next unread chapter
116. Last-read chapter remembered
117. Clear progress per series or globally

## Update watching

118. Watch a series for new chapters
119. Watchlist with per-series known chapter count
120. Parallel update checking across all watched series
121. New-chapter counts per series
122. Acknowledge updates to reset the badge
123. Progress callback while checking
124. Failing sites are skipped, not fatal
125. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

126. Free-text note per series
127. 0–5 star rating, clamped
128. Custom tags per series
129. Filter by minimum rating
130. Named collections
131. Add / remove series in a collection
132. Duplicate-safe collection inserts

## Statistics and insights

133. Total chapters, pages, bytes and time
134. Per-source statistics
135. Per-day statistics
136. Average pages per second
137. Busiest day and top source
138. Human-readable sizes and durations
139. Library insights: series, chapters, pages, disk use
140. Largest and most recent series
141. Statistics recorded automatically after every download
142. Stat tiles in GUI settings
143. `mangadl stats` in the terminal
144. Reset statistics

## Search history

145. Every search recorded with source and hit count
146. Duplicate queries collapse to the newest
147. Type-ahead suggestions from history
148. Prefix matches ranked above substring matches
149. Remove a single entry or clear all
150. Capped at 500 entries
151. `mangadl history` / `mangadl history clear`

## Download queue

152. Persistent job queue
153. Reorder queued jobs
154. Per-job status: pending, running, done, failed, paused
155. Progress and error recorded per job
156. Fetch the next pending job
157. Remove one job or clear by status

## Import, export, backup

158. Export library as JSON
159. Export library as CSV
160. Export library as Markdown table
161. Import a previously exported library
162. Merge or replace on import
163. Snapshots of library + bookmarks + config
164. Restore any snapshot
165. Last 20 snapshots retained
166. `mangadl export <file> [format]`

## Disk maintenance

167. Per-series disk usage report
168. Duplicate file scan by SHA-256, size-bucketed for speed
169. Wasted-space total
170. Orphan detection for missing files and folders
171. Bulk delete chosen files
172. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

173. Correct cover URLs in three sizes
174. Per-volume and localised cover listing
175. Reference expansion so covers arrive in one request
176. Translation language selection
177. Preferred scanlation group
178. Automatic dedupe of multiple releases per chapter
179. Alternatives recorded on the chosen release
180. Data-saver mode
181. Externally hosted chapters filtered out
182. Paginated feed with the 10k offset cap handled
183. All content ratings requested explicitly

## Discovery: trending and genres

184. Pressing Search with an empty box shows trending instead of doing nothing
185. GUI opens on a trending feed rather than a blank page
186. TUI opens on a trending feed
187. `mangadl search` with no query lists trending
188. `mangadl trending` explicit discovery command
189. `mangadl trending <genre>` for per-genre trending
190. `mangadl genres` lists every genre and which sites offer it
191. `-g/--genre` filters any search by genre
192. Genre dropdown in the GUI filter row
193. Quick-pick genre chips for the ten most widely supported genres
194. Genre dropdown in the TUI beside the source picker
195. Genres merged across every enabled source
196. Case-insensitive genre matching across sites
197. Genres ordered by how widely they are supported
198. Per-source genre id mapping kept alongside the shared label
199. Genre list reflects only the sources you have enabled
200. Trending results interleave sources so the first screen is a mix
201. `Load more` pagination in the GUI
202. Per-source browse sort options exposed to the UI
203. MangaDex trending via follower count
204. MangaDex genre browsing by resolved tag UUID
205. MangaDex tag names resolved case-insensitively, with partial matching
206. Raw MangaDex tag UUIDs accepted directly
207. MangaDex tag list cached per process
208. Mangakatana genre browsing over 46 genre slugs
209. Mangakatana pagination via the site's real filter path
210. Natomanga hot / latest / new discovery feeds
211. Natomanga genre browsing with paging
212. Weeb Central trending via popularity sort
213. Weeb Central genre browsing over 26 tags
214. Sources that cannot browse are skipped, with a clear message
215. Type-ahead search suggestions drawn from history
216. Empty results explain what to try next instead of just saying "none"
217. Browse honours source ranking and exclusions
218. Browse results pass through content filters and duplicate merging

## Robust calling

219. Circuit breaker per source, with closed / open / half-open states
220. Repeated failures open the breaker so a dead site is skipped instantly
221. Half-open probe after cooldown, closing again on success
222. Cooldown doubles with each repeated trip, capped
223. Success resets the failure count
224. Bounded retries with exponential backoff
225. Proportional jitter so retries do not synchronise
226. `retry_if` hook to skip pointless retries such as 404s
227. `on_retry` callback for progress reporting
228. TTL cache for discovery listings, five minutes
229. TTL cache for genre lists, one hour
230. Cache eviction when full, with hit-rate statistics
231. `call_safely` runs anything and falls back instead of raising
232. `gather` runs many calls in parallel and keeps whatever succeeds
233. Overall timeout support in `gather`, keeping finished work
234. Rate-limit headers honoured, absolute and relative
235. Partial results always returned rather than failing the whole request
236. Every failure logged once with context
237. `mangadl health` shows breaker state and cache hit rates
238. Health diagnostics exposed to the GUI

## Custom dropdowns

239. Themed dropdowns replacing unstyleable native select popups
240. Native `<select>` kept in the DOM as the source of truth
241. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
242. `value` setter wrapped so programmatic assignment repaints the trigger
243. MutationObserver picks up rebuilt option lists automatically
244. Real `change` and `input` events dispatched on selection
245. No event fired when reselecting the current value
246. Panel portalled to `<body>`, so no ancestor can clip it
247. Flips above the trigger when there is no room below
248. Repositions on scroll and resize
249. Type-to-filter box appears automatically past eight options
250. "No matches" state when a filter excludes everything
251. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
252. Typeahead on the closed trigger, like a native select
253. Only one panel open at a time
254. Closes on outside click
255. ARIA combobox/listbox roles with active-descendant tracking
256. Checkmark and accent colour on the selected row
257. Follows every theme and accent via CSS custom properties
258. Honours `prefers-reduced-motion`
259. Disabled selects reflected on the trigger
260. Enhancement failures are caught so styling can never break the page
261. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

262. Updates tab: watchlist with per-series new-chapter counts
263. Rail badge showing how many watched series have updates
264. One-click "Check now" runs every watched series in parallel
265. Watch / unwatch button on the manga page
266. Insights tab: six headline metrics at a glance
267. Per-source bar chart of downloaded chapters
268. Fourteen-day activity sparkline
269. Biggest series and recently downloaded lists
270. Tools tab with five sub-panels
271. Disk usage per series, largest first
272. Duplicate file scan with wasted-space total
273. Orphan detection for library entries whose files vanished
274. Source health panel showing live circuit-breaker state
275. Searchable history panel; click an entry to re-run it
276. `callApi` wrapper so a missing endpoint cannot blank a tab
277. GitHub-style landing page built on Primer design tokens
278. Real light and dark modes, remembered in localStorage
279. Five deep-linkable page tabs with working back/forward
280. Screenshot gallery with GUI and TUI sub-tabs
281. Copy-to-clipboard install commands with success feedback
282. Language breakdown bar computed from the real repository
283. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

284. Omega Scans source via its JSON API
285. Omega Scans coin-locked chapters detected and skipped
286. ManhwaRead source, decoding base64 page data
287. ManhwaRead per-chapter Referer so its CDN serves images
288. Manhwa18 source, flagged adult-only
289. Adult sources tagged so Safe mode removes them automatically
290. `18+` chip on adult sources in the ranking list
291. Toggle switches render correctly (CSS selector matched no markup)
292. Both switch markup variants supported, markup normalised
293. Disabled source rows keep their toggle legible and clickable
294. Off-state switch has real contrast against the row
295. Settings text, number and password inputs themed
296. Focus ring on settings inputs
297. Number spinners removed for visual consistency
298. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

299. Output files are named by the chapters they contain
300. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
301. Bundled files name their own range, e.g. "Chapters 011-020"
302. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
303. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
304. Heavily fragmented picks truncate to "001-013 (7 chapters)"
305. New {chapters} and {count} filename placeholders
306. Legacy "{title}" templates migrated forward automatically
307. Custom templates are never overwritten by the migration
308. Bad templates fall back instead of crashing the download
309. Library verification reports entries whose files have gone
310. Moved folders detected by matching folder name under a root
311. Proposals are inert until confirmed, so a wrong guess is harmless
312. Re-linking rewrites both the directory and every output path
313. Download history, title and source survive a re-link
314. "Pick new downloads folder" adopts a new root and re-links in one step
315. Moved files panel in the Tools tab
316. `mangadl library verify|scan|move` from the terminal
317. Extra library search roots remembered in settings
318. Minimum and maximum chapter number filters
319. Filter chapters by name text
320. Sort chapters newest-first or oldest-first
321. Hide already-downloaded chapters
322. Count pill shows "visible / total" while filtering
323. A note reports how many chapters a filter is hiding
324. Bulk select buttons act only on visible chapters
325. "Latest" picks the highest-numbered visible chapter
326. Filters change only the display, never the selection keys
327. One-click reset for all chapter filters

## Stability and polish

328. Window close no longer crashes with "unhashable type: 'dict'"
329. Cover mirrors: a failing CDN host falls back to a sibling automatically
330. Covers walk every mirror before showing a fallback tile
331. Passcode gates the app before any data is fetched or painted
332. Boot pauses until the lock screen is dismissed
333. Corner radii snap to a four-step scale instead of 13 ad-hoc values
334. Download location saved to settings.json when chosen
335. Download location saved when typed directly
336. Both folder fields stay in sync

## Square mode, rail and lock polish

337. Square corners mode: turn off all rounding in one switch
338. Square mode flattens pills, fields, dropdowns and switches
339. True circles (spinner, lock badge) stay round in square mode
340. Corner preference saved and restored
341. Side rail is narrower by default
342. Expand button widens the rail and reveals labels
343. Rail state remembered between runs
344. Lock overlay paints on the very first frame
345. Remembered lock state avoids a needless overlay flash
346. Fail-safe timer means the overlay can never strand the app
347. Show/hide passcode button
348. Remaining-attempts counter with warning colours
349. Wrong passcode shakes the panel
350. Live cooldown countdown that disables the field
351. Enter reliably submits a search
352. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

353. Empty-but-200 throttle responses are retried instead of accepted
354. Multi-source search no longer loses sources silently
355. Minimum chapter-count filter
356. Maximum chapter-count filter
357. Chapter counts read from count, last_chapter or the newest label
358. Unknown chapter counts are never filtered out
359. Webtoons source with episode paging
360. Webtoons per-chapter Referer for its hotlink-protected CDN
361. nhentai source, flagged adult-only
362. nhentai thumbnails resolved to full-size pages
363. Twenty-three sources total
364. nhentai browses `/popular` (the site root lists no galleries at all)
365. nhentai genre slugs verified against the live site
366. nhentai covers follow the site's own `data-fallbacks` chain
367. Cover proxy for hotlink-protected CDNs, inlined as data URIs
368. Webtoons covers load in the GUI despite the global `no-referrer`
369. Natomanga cover host is never rewritten (shards, not mirrors)
370. Transient cover failures retry the same URL instead of another host
371. Mangadass source, flagged adult-only
372. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
373. Mangadass chapters sorted numerically, not by document order
374. Manga18.club source, flagged adult-only
375. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
376. Manga18.club pages decoded from the base64 `slides_p_path` array
377. HentaiAkane source, flagged adult-only
378. HentaiAkane pages read from the `ts_reader.run` payload
379. ManhwaRead decodes base64 page lists that ship without padding
380. Connection pool sized to the worker count (no discarded connections)
381. Download cart: queue several manga and keep browsing
382. Concurrent downloads of different manga, configurable 1-5
383. Every progress event is stamped with its job, so chapters never mix
384. Chapter rows show the owning manga when several downloads run
385. Queue panel with per-job status and removable pending entries
386. Stop one download without touching the others
387. A cancelled job reports "stopped", not "failed"
388. Multi-genre search: combine genres with AND or OR
389. Genre chips toggle, building a selection instead of replacing it
390. Picked genres shown as removable chips with a Clear button
391. Genre intersection computed per source, never across sites
392. Library keys normalised (scheme, www, query, fragment)
393. Downloaded chapters matched by number, tolerating changed dates
394. Downloaded pill and highlighted rows can no longer disagree
395. URLs with tracking parameters no longer return zero chapters
396. Manhwa18 genre browsing fixed (/webtoon-genre/)
397. nhentai falls back to search for genres it does not have as tags
398. Content fills the window instead of a fixed centred column
399. Keyboard shortcuts with a searchable `?` help overlay
400. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
401. Shortcuts ignored while typing and while the lock screen is up
402. Invert chapter selection, on visible rows only
403. Copy title and link, with a clipboard fallback for WebView2
404. Refresh the current view with `r`
405. Bookmark and library covers load through the proxy (hotlinked CDNs)
406. Bookmarks store an openable URL, not the normalised key
407. Download queue visible before any job starts
408. Series type classified from origin language and tags
409. Type filter (Manga / Manhwa / Manhua) actually narrows results
410. Per-source default type for sites with a single-type catalogue
411. Square corners reach progress bars, the search box and every pill
412. Strict chapter range option, for hiding unknown chapter counts
413. Source picker removed from search filters (it lives in Settings)
414. Advanced info panel: year, status, type, language, demographic, authors
415. Custom result column count, 0 = fit the window
416. Bookmark folders with create, rename and delete
417. File bookmarks by dragging them onto a folder
418. Folder picker when bookmarking, or save straight to the root
419. Optional per-folder lock and blurred covers
420. Folder cover is the first book added to it
421. Deleting a folder keeps its bookmarks, moving them back to the root
422. Text-input modal that distinguishes cancel from an empty value
423. Keyboard shortcuts listed in Settings, not only in a popup
424. Overlay buttons bind reliably (markup declared before the script)
425. Dialog text inputs themed to match the rest of the app
426. Lock screen and recovery fields use the app font
427. Bookmark covers no longer hijack the drag gesture
428. Floating drop zones appear while dragging a bookmark
429. Drop a bookmark back to All bookmarks, or straight into a new folder
430. Drop highlight survives the pointer crossing child elements
431. A missed drop never navigates the app away
432. All configuration in one `config.json` (settings + sources)
433. Settings written atomically, so a crash cannot reset them
434. Concurrent saves cannot clobber each other
435. Pre-1.4.11 `settings.json` migrated automatically
436. Every bridge endpoint returns errors as data, never raises
437. A malformed queue entry cannot kill the download worker thread
438. Download options coerced from UI values instead of trusted
439. Cover cache bounded by bytes with LRU eviction
440. Global JS error handlers clear spinners and surface a message
441. Search/browse failures show a retry instead of a dead screen
442. `mangadl menu` — progressive numbered interface, no extra dependencies
443. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
444. Menu covers search, trending, URLs, library, bookmarks, settings, tools
445. Menu exits cleanly on EOF or a non-terminal stdin
446. `mangadl search --type` narrows by manga / manhwa / manhua
447. `mangadl search --status` narrows by publication status
448. `mangadl search -n/--limit` caps the number of results
449. `mangadl search --sort` by title, source, chapters or year, `--reverse`
450. `mangadl search --urls` prints one URL per line for pipes
451. `mangadl search --json` prints machine-readable results
452. `mangadl search --open N` shows details for a numbered result
453. `mangadl search --download N` downloads a numbered result
454. `mangadl tui` explains itself instead of a traceback without Textual
455. Every module runs directly (`py menu.py`) without an import error
456. Redesigned landing page with an original identity, not a code-host clone
457. Landing page ships light and dark themes, remembered between visits

## Core engine

- Download any series from a supported site by URL
- Chapter selection syntax: `all`, `5`, `23.5`, `1-20`, `1,5,10-20`, `50-`, `-10`, `latest`, `first`
- Output formats: **CBZ**, **PDF** (pages sized exactly to each image), **EPUB** (chapter TOC), raw **images**
- Produce multiple formats in one run (`--also`)
- **Bundling**: everything in one file (default), one file per chapter, or one file per every N chapters
- Output sorted into a per-manga folder inside the output directory; cover image saved alongside
- **Naming templates** with `{title}`, `{chapter}`, `{start}`, `{end}` placeholders for single / per-chapter / range files
- Parallel chapter downloads (1-8 workers) and parallel image downloads per chapter (1-10 workers)
- Configurable retries per image (1-10) with exponential backoff and jitter
- Adaptive rate-limit handling (429-aware delays)
- **Crash-safe resume**: page-count-verified checkpoints, atomic `.part` image
  writes, and a job journal — resume an interrupted download from the GUI
  banner or `mangadl resume`; completed chapters skipped, partial chapters
  continue from the exact page they stopped at
- Rotating `.log` file (`~/.mangadl/logs/`) shared by GUI/TUI/CLI, with
  export and clear actions in GUI Settings
- Automatic **FlareSolverr** fallback when Cloudflare challenges appear
- Structured event stream consumed by all three front ends

## Library & bookmarks (JSON, in the user folder)

- `~/.mangadl/library.json` records every downloaded chapter per manga:
  chapter name, page count, date, output files, book title, folder
- `~/.mangadl/bookmarks.json` stores bookmarked manga
- Downloaded chapters are **highlighted green** in the GUI chapter list
- "New only" selection shortcut for incremental updates
- Multi-part downloads are tracked and each part is listed with its file size
- Missing output files are detected and flagged

## CLI (`mangadl`)

- Default action: download **all chapters as one CBZ**
- `search "query"` with results table, `info <url>` with details panel
- Download-plan confirmation panel, live per-chapter progress bars (rich)
- `--per N` bundling, `--name-*` templates, `--plain` mode for scripts/CI
- `gui` and `tui` launcher subcommands

## TUI (`mangadl tui`)

- Full-screen Textual app, works over SSH
- Tabs: Search / Manga / Downloads / Settings (`F1`-`F4`)
- Chapter multi-select with All / None / Latest and quick-range input
- Format and bundling selectors, live overall + per-chapter progress, colored log
- Shares settings and library with the GUI

## GUI (`mangadl gui`)

### Search
- Animated hero title with gradient shine, floating icon and staggered word entrance
- Search bar vertically centered; flies to the top when a search runs, title fades away
- **Filters**: sort (Best Match / Popularity / Subscribers / Recently Added / Latest Updates / Alphabet), ascending/descending order, status (Ongoing / Complete / Hiatus / Canceled), type (Manga / Manhwa / Manhua / OEL), official-only
- Filter changes re-run the search automatically; active-filter indicator dot
- Cover-art result grid with staggered entrance animations
- Paste a mangadl URL to skip straight to the manga page

### Manga page
- Cover, title, author, status, tags, description, bookmark toggle
- Downloaded chapters glow green with check marks and a counter pill
- All / None / New only / Latest shortcuts, quick-range box (`1-20, 25, 30-40`)
- Format picker, bundling picker (single / per chapter / every N), save-to path

### Downloads queue
- Overall progress bar with shimmer, live per-chapter bars with image counters
- Timestamped activity log, stop button, open-folder button
- Optional auto-open folder when a download finishes

### Bookmarks
- Cover grid of saved manga, hover-to-remove, click to open

### Library
- Every downloaded manga: chapter/page counts, last download time
- Parts badge; expandable list of parts with file sizes and missing-file flags
- **Read** buttons open books in your configured reader (e.g. Readest)
- Open folder, jump to manga page, remove entry

### Settings
- **Appearance**: 6 themes (Midnight, Mocha, Forest, Plum, Ocean, Light), 6 accent colors, animations toggle, dot-matrix toggle
- **Downloads**: output directory, default format, keep raw images, open folder when done, confirm-large-downloads guard with threshold
- **File naming**: three templates with live preview
- **Reader**: path to reader executable (file picker); empty = system default
- **Performance**: chapter workers, image workers, delay, retries per image
- **Data**: clear library / clear bookmarks

### Design
- Solid pastel-dark backgrounds with drifting circular gradient orbs
- Animated dot-matrix canvas backdrop (toggleable)
- Google Material Symbols exclusively - no emojis
- Confirm modal for destructive/large actions, toasts, staggered card animations

## Landing page

- `docs/index.html` - GitHub Pages-ready landing page with the same ambient design
- Feature grid, GUI/TUI screenshot tabs, CLI terminal demo, copyable install command

## Packaging

- `MangaDL.spec` + `launcher.py`: build a standalone executable with
  PyInstaller — GUI on double-click, TUI/CLI/search/resume via arguments
- One-folder and one-file modes; per-platform guide in `PACKAGING.md`

## Python API

```python
from mangadl.downloader import DownloadEngine, DownloadOptions
result = DownloadEngine(DownloadOptions(url="...", bundle=10)).run()
```
