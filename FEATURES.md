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

## Source ranking and exclusion

37. Drag-and-drop source ranking in the GUI
38. Move up / down buttons as a keyboard-friendly alternative
39. Rank order decides which copy wins when a series exists on several sites
40. Toggle a source off to exclude its results entirely
41. Excluded sources still work from a direct URL
42. `search_enabled` — keep a source usable but out of multi-source search
43. Per-source result limit override
44. Per-source weight for duplicate scoring
45. Per-source language override
46. Per-source extra delay for politeness
47. Free-text note per source
48. Ranking is shared by CLI, GUI and TUI
49. New sources are auto-appended, ranked last
50. Stale config entries are pruned automatically
51. `mangadl config` shows the full table
52. `mangadl config enable|disable <source>`
53. `mangadl config up|down <source>`
54. `mangadl config rank <a> <b> ...` to set the whole order
55. `mangadl config reset`
56. Sources tab in the TUI with the same controls

## Provider attribution

57. Provider shown directly beneath the manga title in the GUI
58. Colour-coded provider dot per source
59. "Open on source site" link next to the provider name
60. Provider line under the title in the TUI
61. Provider line in `mangadl info`
62. Source badges on GUI search result cards
63. Source column in CLI search results
64. Source tag in TUI search results
65. Source recorded on every library entry
66. Source recorded on every bookmark
67. Source stamped on download results and plan events

## Passcode lock

68. Optional app passcode
69. PBKDF2-HMAC-SHA256 with 240,000 rounds
70. Per-install random salt — identical passcodes hash differently
71. Constant-time comparison
72. Passcode never stored in plaintext
73. One-time recovery key issued at setup
74. Recovery key is case-insensitive and ignores spacing
75. Recovery flow built into the lock screen
76. Change passcode (requires the current one)
77. Disable lock (requires the passcode)
78. Attempt throttling after 5 failures
79. Escalating cooldown, capped at 15 minutes
80. Auto-lock after N idle minutes
81. Lock on app start
82. Optional cover blurring behind the lock screen
83. Optional passcode hint
84. Lock file written with owner-only permissions
85. `mangadl lock status|set|change|off` from the terminal

## Content filters

86. Blocked tags
87. Blocked title words
88. Blocked authors
89. Safe mode drops adult-rated results
90. Hide results with no cover
91. Minimum chapter count filter
92. Filters apply to both GUI and CLI search

## Duplicate handling

93. Cross-source duplicate detection by normalised title
94. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
95. Best-ranked copy survives a merge
96. `also_on` lists the other sources carrying the same series
97. Toggle merging on or off
98. Interleave mode round-robins sources instead of grouping them

## Reading progress

99. Mark individual chapters read or unread
100. Bulk mark a range
101. Percentage progress per series
102. Unread count per series
103. Jump to next unread chapter
104. Last-read chapter remembered
105. Clear progress per series or globally

## Update watching

106. Watch a series for new chapters
107. Watchlist with per-series known chapter count
108. Parallel update checking across all watched series
109. New-chapter counts per series
110. Acknowledge updates to reset the badge
111. Progress callback while checking
112. Failing sites are skipped, not fatal
113. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

114. Free-text note per series
115. 0–5 star rating, clamped
116. Custom tags per series
117. Filter by minimum rating
118. Named collections
119. Add / remove series in a collection
120. Duplicate-safe collection inserts

## Statistics and insights

121. Total chapters, pages, bytes and time
122. Per-source statistics
123. Per-day statistics
124. Average pages per second
125. Busiest day and top source
126. Human-readable sizes and durations
127. Library insights: series, chapters, pages, disk use
128. Largest and most recent series
129. Statistics recorded automatically after every download
130. Stat tiles in GUI settings
131. `mangadl stats` in the terminal
132. Reset statistics

## Search history

133. Every search recorded with source and hit count
134. Duplicate queries collapse to the newest
135. Type-ahead suggestions from history
136. Prefix matches ranked above substring matches
137. Remove a single entry or clear all
138. Capped at 500 entries
139. `mangadl history` / `mangadl history clear`

## Download queue

140. Persistent job queue
141. Reorder queued jobs
142. Per-job status: pending, running, done, failed, paused
143. Progress and error recorded per job
144. Fetch the next pending job
145. Remove one job or clear by status

## Import, export, backup

146. Export library as JSON
147. Export library as CSV
148. Export library as Markdown table
149. Import a previously exported library
150. Merge or replace on import
151. Snapshots of library + bookmarks + config
152. Restore any snapshot
153. Last 20 snapshots retained
154. `mangadl export <file> [format]`

## Disk maintenance

155. Per-series disk usage report
156. Duplicate file scan by SHA-256, size-bucketed for speed
157. Wasted-space total
158. Orphan detection for missing files and folders
159. Bulk delete chosen files
160. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

161. Correct cover URLs in three sizes
162. Per-volume and localised cover listing
163. Reference expansion so covers arrive in one request
164. Translation language selection
165. Preferred scanlation group
166. Automatic dedupe of multiple releases per chapter
167. Alternatives recorded on the chosen release
168. Data-saver mode
169. Externally hosted chapters filtered out
170. Paginated feed with the 10k offset cap handled
171. All content ratings requested explicitly

## Discovery: trending and genres

172. Pressing Search with an empty box shows trending instead of doing nothing
173. GUI opens on a trending feed rather than a blank page
174. TUI opens on a trending feed
175. `mangadl search` with no query lists trending
176. `mangadl trending` explicit discovery command
177. `mangadl trending <genre>` for per-genre trending
178. `mangadl genres` lists every genre and which sites offer it
179. `-g/--genre` filters any search by genre
180. Genre dropdown in the GUI filter row
181. Quick-pick genre chips for the ten most widely supported genres
182. Genre dropdown in the TUI beside the source picker
183. Genres merged across every enabled source
184. Case-insensitive genre matching across sites
185. Genres ordered by how widely they are supported
186. Per-source genre id mapping kept alongside the shared label
187. Genre list reflects only the sources you have enabled
188. Trending results interleave sources so the first screen is a mix
189. `Load more` pagination in the GUI
190. Per-source browse sort options exposed to the UI
191. MangaDex trending via follower count
192. MangaDex genre browsing by resolved tag UUID
193. MangaDex tag names resolved case-insensitively, with partial matching
194. Raw MangaDex tag UUIDs accepted directly
195. MangaDex tag list cached per process
196. Mangakatana genre browsing over 46 genre slugs
197. Mangakatana pagination via the site's real filter path
198. Natomanga hot / latest / new discovery feeds
199. Natomanga genre browsing with paging
200. Weeb Central trending via popularity sort
201. Weeb Central genre browsing over 26 tags
202. Sources that cannot browse are skipped, with a clear message
203. Type-ahead search suggestions drawn from history
204. Empty results explain what to try next instead of just saying "none"
205. Browse honours source ranking and exclusions
206. Browse results pass through content filters and duplicate merging

## Robust calling

207. Circuit breaker per source, with closed / open / half-open states
208. Repeated failures open the breaker so a dead site is skipped instantly
209. Half-open probe after cooldown, closing again on success
210. Cooldown doubles with each repeated trip, capped
211. Success resets the failure count
212. Bounded retries with exponential backoff
213. Proportional jitter so retries do not synchronise
214. `retry_if` hook to skip pointless retries such as 404s
215. `on_retry` callback for progress reporting
216. TTL cache for discovery listings, five minutes
217. TTL cache for genre lists, one hour
218. Cache eviction when full, with hit-rate statistics
219. `call_safely` runs anything and falls back instead of raising
220. `gather` runs many calls in parallel and keeps whatever succeeds
221. Overall timeout support in `gather`, keeping finished work
222. Rate-limit headers honoured, absolute and relative
223. Partial results always returned rather than failing the whole request
224. Every failure logged once with context
225. `mangadl health` shows breaker state and cache hit rates
226. Health diagnostics exposed to the GUI

## Custom dropdowns

227. Themed dropdowns replacing unstyleable native select popups
228. Native `<select>` kept in the DOM as the source of truth
229. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
230. `value` setter wrapped so programmatic assignment repaints the trigger
231. MutationObserver picks up rebuilt option lists automatically
232. Real `change` and `input` events dispatched on selection
233. No event fired when reselecting the current value
234. Panel portalled to `<body>`, so no ancestor can clip it
235. Flips above the trigger when there is no room below
236. Repositions on scroll and resize
237. Type-to-filter box appears automatically past eight options
238. "No matches" state when a filter excludes everything
239. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
240. Typeahead on the closed trigger, like a native select
241. Only one panel open at a time
242. Closes on outside click
243. ARIA combobox/listbox roles with active-descendant tracking
244. Checkmark and accent colour on the selected row
245. Follows every theme and accent via CSS custom properties
246. Honours `prefers-reduced-motion`
247. Disabled selects reflected on the trigger
248. Enhancement failures are caught so styling can never break the page
249. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

250. Updates tab: watchlist with per-series new-chapter counts
251. Rail badge showing how many watched series have updates
252. One-click "Check now" runs every watched series in parallel
253. Watch / unwatch button on the manga page
254. Insights tab: six headline metrics at a glance
255. Per-source bar chart of downloaded chapters
256. Fourteen-day activity sparkline
257. Biggest series and recently downloaded lists
258. Tools tab with five sub-panels
259. Disk usage per series, largest first
260. Duplicate file scan with wasted-space total
261. Orphan detection for library entries whose files vanished
262. Source health panel showing live circuit-breaker state
263. Searchable history panel; click an entry to re-run it
264. `callApi` wrapper so a missing endpoint cannot blank a tab
265. GitHub-style landing page built on Primer design tokens
266. Real light and dark modes, remembered in localStorage
267. Five deep-linkable page tabs with working back/forward
268. Screenshot gallery with GUI and TUI sub-tabs
269. Copy-to-clipboard install commands with success feedback
270. Language breakdown bar computed from the real repository
271. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

272. Omega Scans source via its JSON API
273. Omega Scans coin-locked chapters detected and skipped
274. ManhwaRead source, decoding base64 page data
275. ManhwaRead per-chapter Referer so its CDN serves images
276. Manhwa18 source, flagged adult-only
277. Adult sources tagged so Safe mode removes them automatically
278. `18+` chip on adult sources in the ranking list
279. Toggle switches render correctly (CSS selector matched no markup)
280. Both switch markup variants supported, markup normalised
281. Disabled source rows keep their toggle legible and clickable
282. Off-state switch has real contrast against the row
283. Settings text, number and password inputs themed
284. Focus ring on settings inputs
285. Number spinners removed for visual consistency
286. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

287. Output files are named by the chapters they contain
288. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
289. Bundled files name their own range, e.g. "Chapters 011-020"
290. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
291. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
292. Heavily fragmented picks truncate to "001-013 (7 chapters)"
293. New {chapters} and {count} filename placeholders
294. Legacy "{title}" templates migrated forward automatically
295. Custom templates are never overwritten by the migration
296. Bad templates fall back instead of crashing the download
297. Library verification reports entries whose files have gone
298. Moved folders detected by matching folder name under a root
299. Proposals are inert until confirmed, so a wrong guess is harmless
300. Re-linking rewrites both the directory and every output path
301. Download history, title and source survive a re-link
302. "Pick new downloads folder" adopts a new root and re-links in one step
303. Moved files panel in the Tools tab
304. `mangadl library verify|scan|move` from the terminal
305. Extra library search roots remembered in settings
306. Minimum and maximum chapter number filters
307. Filter chapters by name text
308. Sort chapters newest-first or oldest-first
309. Hide already-downloaded chapters
310. Count pill shows "visible / total" while filtering
311. A note reports how many chapters a filter is hiding
312. Bulk select buttons act only on visible chapters
313. "Latest" picks the highest-numbered visible chapter
314. Filters change only the display, never the selection keys
315. One-click reset for all chapter filters

## Stability and polish

316. Window close no longer crashes with "unhashable type: 'dict'"
317. Cover mirrors: a failing CDN host falls back to a sibling automatically
318. Covers walk every mirror before showing a fallback tile
319. Passcode gates the app before any data is fetched or painted
320. Boot pauses until the lock screen is dismissed
321. Corner radii snap to a four-step scale instead of 13 ad-hoc values
322. Download location saved to settings.json when chosen
323. Download location saved when typed directly
324. Both folder fields stay in sync

## Square mode, rail and lock polish

325. Square corners mode: turn off all rounding in one switch
326. Square mode flattens pills, fields, dropdowns and switches
327. True circles (spinner, lock badge) stay round in square mode
328. Corner preference saved and restored
329. Side rail is narrower by default
330. Expand button widens the rail and reveals labels
331. Rail state remembered between runs
332. Lock overlay paints on the very first frame
333. Remembered lock state avoids a needless overlay flash
334. Fail-safe timer means the overlay can never strand the app
335. Show/hide passcode button
336. Remaining-attempts counter with warning colours
337. Wrong passcode shakes the panel
338. Live cooldown countdown that disables the field
339. Enter reliably submits a search
340. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

341. Empty-but-200 throttle responses are retried instead of accepted
342. Multi-source search no longer loses sources silently
343. Minimum chapter-count filter
344. Maximum chapter-count filter
345. Chapter counts read from count, last_chapter or the newest label
346. Unknown chapter counts are never filtered out
347. Webtoons source with episode paging
348. Webtoons per-chapter Referer for its hotlink-protected CDN
349. nhentai source, flagged adult-only
350. nhentai thumbnails resolved to full-size pages
351. Twenty-three sources total
352. nhentai browses `/popular` (the site root lists no galleries at all)
353. nhentai genre slugs verified against the live site
354. nhentai covers follow the site's own `data-fallbacks` chain
355. Cover proxy for hotlink-protected CDNs, inlined as data URIs
356. Webtoons covers load in the GUI despite the global `no-referrer`
357. Natomanga cover host is never rewritten (shards, not mirrors)
358. Transient cover failures retry the same URL instead of another host
359. Mangadass source, flagged adult-only
360. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
361. Mangadass chapters sorted numerically, not by document order
362. Manga18.club source, flagged adult-only
363. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
364. Manga18.club pages decoded from the base64 `slides_p_path` array
365. HentaiAkane source, flagged adult-only
366. HentaiAkane pages read from the `ts_reader.run` payload
367. ManhwaRead decodes base64 page lists that ship without padding
368. Connection pool sized to the worker count (no discarded connections)
369. Download cart: queue several manga and keep browsing
370. Concurrent downloads of different manga, configurable 1-5
371. Every progress event is stamped with its job, so chapters never mix
372. Chapter rows show the owning manga when several downloads run
373. Queue panel with per-job status and removable pending entries
374. Stop one download without touching the others
375. A cancelled job reports "stopped", not "failed"
376. Multi-genre search: combine genres with AND or OR
377. Genre chips toggle, building a selection instead of replacing it
378. Picked genres shown as removable chips with a Clear button
379. Genre intersection computed per source, never across sites
380. Library keys normalised (scheme, www, query, fragment)
381. Downloaded chapters matched by number, tolerating changed dates
382. Downloaded pill and highlighted rows can no longer disagree
383. URLs with tracking parameters no longer return zero chapters
384. Manhwa18 genre browsing fixed (/webtoon-genre/)
385. nhentai falls back to search for genres it does not have as tags
386. Content fills the window instead of a fixed centred column
387. Keyboard shortcuts with a searchable `?` help overlay
388. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
389. Shortcuts ignored while typing and while the lock screen is up
390. Invert chapter selection, on visible rows only
391. Copy title and link, with a clipboard fallback for WebView2
392. Refresh the current view with `r`
393. Bookmark and library covers load through the proxy (hotlinked CDNs)
394. Bookmarks store an openable URL, not the normalised key
395. Download queue visible before any job starts
396. Series type classified from origin language and tags
397. Type filter (Manga / Manhwa / Manhua) actually narrows results
398. Per-source default type for sites with a single-type catalogue
399. Square corners reach progress bars, the search box and every pill
400. Strict chapter range option, for hiding unknown chapter counts
401. Source picker removed from search filters (it lives in Settings)
402. Advanced info panel: year, status, type, language, demographic, authors
403. Custom result column count, 0 = fit the window
404. Bookmark folders with create, rename and delete
405. File bookmarks by dragging them onto a folder
406. Folder picker when bookmarking, or save straight to the root
407. Optional per-folder lock and blurred covers
408. Folder cover is the first book added to it
409. Deleting a folder keeps its bookmarks, moving them back to the root
410. Text-input modal that distinguishes cancel from an empty value
411. Keyboard shortcuts listed in Settings, not only in a popup
412. Overlay buttons bind reliably (markup declared before the script)
413. Dialog text inputs themed to match the rest of the app
414. Lock screen and recovery fields use the app font
415. Bookmark covers no longer hijack the drag gesture
416. Floating drop zones appear while dragging a bookmark
417. Drop a bookmark back to All bookmarks, or straight into a new folder
418. Drop highlight survives the pointer crossing child elements
419. A missed drop never navigates the app away
420. All configuration in one `config.json` (settings + sources)
421. Settings written atomically, so a crash cannot reset them
422. Concurrent saves cannot clobber each other
423. Pre-1.4.11 `settings.json` migrated automatically
424. Every bridge endpoint returns errors as data, never raises
425. A malformed queue entry cannot kill the download worker thread
426. Download options coerced from UI values instead of trusted
427. Cover cache bounded by bytes with LRU eviction
428. Global JS error handlers clear spinners and surface a message
429. Search/browse failures show a retry instead of a dead screen
430. `mangadl menu` — progressive numbered interface, no extra dependencies
431. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
432. Menu covers search, trending, URLs, library, bookmarks, settings, tools
433. Menu exits cleanly on EOF or a non-terminal stdin
434. `mangadl search --type` narrows by manga / manhwa / manhua
435. `mangadl search --status` narrows by publication status
436. `mangadl search -n/--limit` caps the number of results
437. `mangadl search --sort` by title, source, chapters or year, `--reverse`
438. `mangadl search --urls` prints one URL per line for pipes
439. `mangadl search --json` prints machine-readable results
440. `mangadl search --open N` shows details for a numbered result
441. `mangadl search --download N` downloads a numbered result
442. `mangadl tui` explains itself instead of a traceback without Textual
443. Every module runs directly (`py menu.py`) without an import error
444. Redesigned landing page with an original identity, not a code-host clone
445. Landing page ships light and dark themes, remembered between visits

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
