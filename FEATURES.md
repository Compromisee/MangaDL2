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

## Madara aggregate and dedupe rewrite (v1.4.18)

49. **Madara Sites** — one source fanning out across ten Madara-theme sites
50. Members searched in parallel and interleaved, so the first screen is a mix
51. A dead or slow member is skipped; it never breaks the source
52. Per-site circuit breakers still apply to each member individually
53. Genre display names are translated back to each install's own slug
54. Series and chapter URLs delegate to the site that owns them
55. Downloads route through the owning member, so its Referer rules apply
56. Four new Madara sites: Coffee Manga, MangaSushi, MangaOwl, MangaGG
57. HTTP 404/410 is no longer retried — it is a definitive answer
58. Dedupe is Unicode-safe: CJK titles are no longer destroyed
59. Only recognised edition notes are stripped, so "(Season 2)" stays distinct
60. Untitled rows are never grouped together
61. Word-break variants merge: "Nano Machine" = "Nanomachine"
62. Leading articles ignored: "The Beginning After The End"
63. Merging backfills metadata the best-ranked copy is missing

## Source ranking and exclusion

64. Drag-and-drop source ranking in the GUI
65. Move up / down buttons as a keyboard-friendly alternative
66. Rank order decides which copy wins when a series exists on several sites
67. Toggle a source off to exclude its results entirely
68. Excluded sources still work from a direct URL
69. `search_enabled` — keep a source usable but out of multi-source search
70. Per-source result limit override
71. Per-source weight for duplicate scoring
72. Per-source language override
73. Per-source extra delay for politeness
74. Free-text note per source
75. Ranking is shared by CLI, GUI and TUI
76. New sources are auto-appended, ranked last
77. Stale config entries are pruned automatically
78. `mangadl config` shows the full table
79. `mangadl config enable|disable <source>`
80. `mangadl config up|down <source>`
81. `mangadl config rank <a> <b> ...` to set the whole order
82. `mangadl config reset`
83. Sources tab in the TUI with the same controls

## Provider attribution

84. Provider shown directly beneath the manga title in the GUI
85. Colour-coded provider dot per source
86. "Open on source site" link next to the provider name
87. Provider line under the title in the TUI
88. Provider line in `mangadl info`
89. Source badges on GUI search result cards
90. Source column in CLI search results
91. Source tag in TUI search results
92. Source recorded on every library entry
93. Source recorded on every bookmark
94. Source stamped on download results and plan events

## Passcode lock

95. Optional app passcode
96. PBKDF2-HMAC-SHA256 with 240,000 rounds
97. Per-install random salt — identical passcodes hash differently
98. Constant-time comparison
99. Passcode never stored in plaintext
100. One-time recovery key issued at setup
101. Recovery key is case-insensitive and ignores spacing
102. Recovery flow built into the lock screen
103. Change passcode (requires the current one)
104. Disable lock (requires the passcode)
105. Attempt throttling after 5 failures
106. Escalating cooldown, capped at 15 minutes
107. Auto-lock after N idle minutes
108. Lock on app start
109. Optional cover blurring behind the lock screen
110. Optional passcode hint
111. Lock file written with owner-only permissions
112. `mangadl lock status|set|change|off` from the terminal

## Content filters

113. Blocked tags
114. Blocked title words
115. Blocked authors
116. Safe mode drops adult-rated results
117. Hide results with no cover
118. Minimum chapter count filter
119. Filters apply to both GUI and CLI search

## Duplicate handling

120. Cross-source duplicate detection by normalised title
121. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
122. Best-ranked copy survives a merge
123. `also_on` lists the other sources carrying the same series
124. Toggle merging on or off
125. Interleave mode round-robins sources instead of grouping them

## Reading progress

126. Mark individual chapters read or unread
127. Bulk mark a range
128. Percentage progress per series
129. Unread count per series
130. Jump to next unread chapter
131. Last-read chapter remembered
132. Clear progress per series or globally

## Update watching

133. Watch a series for new chapters
134. Watchlist with per-series known chapter count
135. Parallel update checking across all watched series
136. New-chapter counts per series
137. Acknowledge updates to reset the badge
138. Progress callback while checking
139. Failing sites are skipped, not fatal
140. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

141. Free-text note per series
142. 0–5 star rating, clamped
143. Custom tags per series
144. Filter by minimum rating
145. Named collections
146. Add / remove series in a collection
147. Duplicate-safe collection inserts

## Statistics and insights

148. Total chapters, pages, bytes and time
149. Per-source statistics
150. Per-day statistics
151. Average pages per second
152. Busiest day and top source
153. Human-readable sizes and durations
154. Library insights: series, chapters, pages, disk use
155. Largest and most recent series
156. Statistics recorded automatically after every download
157. Stat tiles in GUI settings
158. `mangadl stats` in the terminal
159. Reset statistics

## Search history

160. Every search recorded with source and hit count
161. Duplicate queries collapse to the newest
162. Type-ahead suggestions from history
163. Prefix matches ranked above substring matches
164. Remove a single entry or clear all
165. Capped at 500 entries
166. `mangadl history` / `mangadl history clear`

## Download queue

167. Persistent job queue
168. Reorder queued jobs
169. Per-job status: pending, running, done, failed, paused
170. Progress and error recorded per job
171. Fetch the next pending job
172. Remove one job or clear by status

## Import, export, backup

173. Export library as JSON
174. Export library as CSV
175. Export library as Markdown table
176. Import a previously exported library
177. Merge or replace on import
178. Snapshots of library + bookmarks + config
179. Restore any snapshot
180. Last 20 snapshots retained
181. `mangadl export <file> [format]`

## Disk maintenance

182. Per-series disk usage report
183. Duplicate file scan by SHA-256, size-bucketed for speed
184. Wasted-space total
185. Orphan detection for missing files and folders
186. Bulk delete chosen files
187. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

188. Correct cover URLs in three sizes
189. Per-volume and localised cover listing
190. Reference expansion so covers arrive in one request
191. Translation language selection
192. Preferred scanlation group
193. Automatic dedupe of multiple releases per chapter
194. Alternatives recorded on the chosen release
195. Data-saver mode
196. Externally hosted chapters filtered out
197. Paginated feed with the 10k offset cap handled
198. All content ratings requested explicitly

## Discovery: trending and genres

199. Pressing Search with an empty box shows trending instead of doing nothing
200. GUI opens on a trending feed rather than a blank page
201. TUI opens on a trending feed
202. `mangadl search` with no query lists trending
203. `mangadl trending` explicit discovery command
204. `mangadl trending <genre>` for per-genre trending
205. `mangadl genres` lists every genre and which sites offer it
206. `-g/--genre` filters any search by genre
207. Genre dropdown in the GUI filter row
208. Quick-pick genre chips for the ten most widely supported genres
209. Genre dropdown in the TUI beside the source picker
210. Genres merged across every enabled source
211. Case-insensitive genre matching across sites
212. Genres ordered by how widely they are supported
213. Per-source genre id mapping kept alongside the shared label
214. Genre list reflects only the sources you have enabled
215. Trending results interleave sources so the first screen is a mix
216. `Load more` pagination in the GUI
217. Per-source browse sort options exposed to the UI
218. MangaDex trending via follower count
219. MangaDex genre browsing by resolved tag UUID
220. MangaDex tag names resolved case-insensitively, with partial matching
221. Raw MangaDex tag UUIDs accepted directly
222. MangaDex tag list cached per process
223. Mangakatana genre browsing over 46 genre slugs
224. Mangakatana pagination via the site's real filter path
225. Natomanga hot / latest / new discovery feeds
226. Natomanga genre browsing with paging
227. Weeb Central trending via popularity sort
228. Weeb Central genre browsing over 26 tags
229. Sources that cannot browse are skipped, with a clear message
230. Type-ahead search suggestions drawn from history
231. Empty results explain what to try next instead of just saying "none"
232. Browse honours source ranking and exclusions
233. Browse results pass through content filters and duplicate merging

## Robust calling

234. Circuit breaker per source, with closed / open / half-open states
235. Repeated failures open the breaker so a dead site is skipped instantly
236. Half-open probe after cooldown, closing again on success
237. Cooldown doubles with each repeated trip, capped
238. Success resets the failure count
239. Bounded retries with exponential backoff
240. Proportional jitter so retries do not synchronise
241. `retry_if` hook to skip pointless retries such as 404s
242. `on_retry` callback for progress reporting
243. TTL cache for discovery listings, five minutes
244. TTL cache for genre lists, one hour
245. Cache eviction when full, with hit-rate statistics
246. `call_safely` runs anything and falls back instead of raising
247. `gather` runs many calls in parallel and keeps whatever succeeds
248. Overall timeout support in `gather`, keeping finished work
249. Rate-limit headers honoured, absolute and relative
250. Partial results always returned rather than failing the whole request
251. Every failure logged once with context
252. `mangadl health` shows breaker state and cache hit rates
253. Health diagnostics exposed to the GUI

## Custom dropdowns

254. Themed dropdowns replacing unstyleable native select popups
255. Native `<select>` kept in the DOM as the source of truth
256. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
257. `value` setter wrapped so programmatic assignment repaints the trigger
258. MutationObserver picks up rebuilt option lists automatically
259. Real `change` and `input` events dispatched on selection
260. No event fired when reselecting the current value
261. Panel portalled to `<body>`, so no ancestor can clip it
262. Flips above the trigger when there is no room below
263. Repositions on scroll and resize
264. Type-to-filter box appears automatically past eight options
265. "No matches" state when a filter excludes everything
266. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
267. Typeahead on the closed trigger, like a native select
268. Only one panel open at a time
269. Closes on outside click
270. ARIA combobox/listbox roles with active-descendant tracking
271. Checkmark and accent colour on the selected row
272. Follows every theme and accent via CSS custom properties
273. Honours `prefers-reduced-motion`
274. Disabled selects reflected on the trigger
275. Enhancement failures are caught so styling can never break the page
276. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

277. Updates tab: watchlist with per-series new-chapter counts
278. Rail badge showing how many watched series have updates
279. One-click "Check now" runs every watched series in parallel
280. Watch / unwatch button on the manga page
281. Insights tab: six headline metrics at a glance
282. Per-source bar chart of downloaded chapters
283. Fourteen-day activity sparkline
284. Biggest series and recently downloaded lists
285. Tools tab with five sub-panels
286. Disk usage per series, largest first
287. Duplicate file scan with wasted-space total
288. Orphan detection for library entries whose files vanished
289. Source health panel showing live circuit-breaker state
290. Searchable history panel; click an entry to re-run it
291. `callApi` wrapper so a missing endpoint cannot blank a tab
292. GitHub-style landing page built on Primer design tokens
293. Real light and dark modes, remembered in localStorage
294. Five deep-linkable page tabs with working back/forward
295. Screenshot gallery with GUI and TUI sub-tabs
296. Copy-to-clipboard install commands with success feedback
297. Language breakdown bar computed from the real repository
298. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

299. Omega Scans source via its JSON API
300. Omega Scans coin-locked chapters detected and skipped
301. ManhwaRead source, decoding base64 page data
302. ManhwaRead per-chapter Referer so its CDN serves images
303. Manhwa18 source, flagged adult-only
304. Adult sources tagged so Safe mode removes them automatically
305. `18+` chip on adult sources in the ranking list
306. Toggle switches render correctly (CSS selector matched no markup)
307. Both switch markup variants supported, markup normalised
308. Disabled source rows keep their toggle legible and clickable
309. Off-state switch has real contrast against the row
310. Settings text, number and password inputs themed
311. Focus ring on settings inputs
312. Number spinners removed for visual consistency
313. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

314. Output files are named by the chapters they contain
315. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
316. Bundled files name their own range, e.g. "Chapters 011-020"
317. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
318. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
319. Heavily fragmented picks truncate to "001-013 (7 chapters)"
320. New {chapters} and {count} filename placeholders
321. Legacy "{title}" templates migrated forward automatically
322. Custom templates are never overwritten by the migration
323. Bad templates fall back instead of crashing the download
324. Library verification reports entries whose files have gone
325. Moved folders detected by matching folder name under a root
326. Proposals are inert until confirmed, so a wrong guess is harmless
327. Re-linking rewrites both the directory and every output path
328. Download history, title and source survive a re-link
329. "Pick new downloads folder" adopts a new root and re-links in one step
330. Moved files panel in the Tools tab
331. `mangadl library verify|scan|move` from the terminal
332. Extra library search roots remembered in settings
333. Minimum and maximum chapter number filters
334. Filter chapters by name text
335. Sort chapters newest-first or oldest-first
336. Hide already-downloaded chapters
337. Count pill shows "visible / total" while filtering
338. A note reports how many chapters a filter is hiding
339. Bulk select buttons act only on visible chapters
340. "Latest" picks the highest-numbered visible chapter
341. Filters change only the display, never the selection keys
342. One-click reset for all chapter filters

## Stability and polish

343. Window close no longer crashes with "unhashable type: 'dict'"
344. Cover mirrors: a failing CDN host falls back to a sibling automatically
345. Covers walk every mirror before showing a fallback tile
346. Passcode gates the app before any data is fetched or painted
347. Boot pauses until the lock screen is dismissed
348. Corner radii snap to a four-step scale instead of 13 ad-hoc values
349. Download location saved to settings.json when chosen
350. Download location saved when typed directly
351. Both folder fields stay in sync

## Square mode, rail and lock polish

352. Square corners mode: turn off all rounding in one switch
353. Square mode flattens pills, fields, dropdowns and switches
354. True circles (spinner, lock badge) stay round in square mode
355. Corner preference saved and restored
356. Side rail is narrower by default
357. Expand button widens the rail and reveals labels
358. Rail state remembered between runs
359. Lock overlay paints on the very first frame
360. Remembered lock state avoids a needless overlay flash
361. Fail-safe timer means the overlay can never strand the app
362. Show/hide passcode button
363. Remaining-attempts counter with warning colours
364. Wrong passcode shakes the panel
365. Live cooldown countdown that disables the field
366. Enter reliably submits a search
367. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

368. Empty-but-200 throttle responses are retried instead of accepted
369. Multi-source search no longer loses sources silently
370. Minimum chapter-count filter
371. Maximum chapter-count filter
372. Chapter counts read from count, last_chapter or the newest label
373. Unknown chapter counts are never filtered out
374. Webtoons source with episode paging
375. Webtoons per-chapter Referer for its hotlink-protected CDN
376. nhentai source, flagged adult-only
377. nhentai thumbnails resolved to full-size pages
378. Twenty-three sources total
379. nhentai browses `/popular` (the site root lists no galleries at all)
380. nhentai genre slugs verified against the live site
381. nhentai covers follow the site's own `data-fallbacks` chain
382. Cover proxy for hotlink-protected CDNs, inlined as data URIs
383. Webtoons covers load in the GUI despite the global `no-referrer`
384. Natomanga cover host is never rewritten (shards, not mirrors)
385. Transient cover failures retry the same URL instead of another host
386. Mangadass source, flagged adult-only
387. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
388. Mangadass chapters sorted numerically, not by document order
389. Manga18.club source, flagged adult-only
390. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
391. Manga18.club pages decoded from the base64 `slides_p_path` array
392. HentaiAkane source, flagged adult-only
393. HentaiAkane pages read from the `ts_reader.run` payload
394. ManhwaRead decodes base64 page lists that ship without padding
395. Connection pool sized to the worker count (no discarded connections)
396. Download cart: queue several manga and keep browsing
397. Concurrent downloads of different manga, configurable 1-5
398. Every progress event is stamped with its job, so chapters never mix
399. Chapter rows show the owning manga when several downloads run
400. Queue panel with per-job status and removable pending entries
401. Stop one download without touching the others
402. A cancelled job reports "stopped", not "failed"
403. Multi-genre search: combine genres with AND or OR
404. Genre chips toggle, building a selection instead of replacing it
405. Picked genres shown as removable chips with a Clear button
406. Genre intersection computed per source, never across sites
407. Library keys normalised (scheme, www, query, fragment)
408. Downloaded chapters matched by number, tolerating changed dates
409. Downloaded pill and highlighted rows can no longer disagree
410. URLs with tracking parameters no longer return zero chapters
411. Manhwa18 genre browsing fixed (/webtoon-genre/)
412. nhentai falls back to search for genres it does not have as tags
413. Content fills the window instead of a fixed centred column
414. Keyboard shortcuts with a searchable `?` help overlay
415. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
416. Shortcuts ignored while typing and while the lock screen is up
417. Invert chapter selection, on visible rows only
418. Copy title and link, with a clipboard fallback for WebView2
419. Refresh the current view with `r`
420. Bookmark and library covers load through the proxy (hotlinked CDNs)
421. Bookmarks store an openable URL, not the normalised key
422. Download queue visible before any job starts
423. Series type classified from origin language and tags
424. Type filter (Manga / Manhwa / Manhua) actually narrows results
425. Per-source default type for sites with a single-type catalogue
426. Square corners reach progress bars, the search box and every pill
427. Strict chapter range option, for hiding unknown chapter counts
428. Source picker removed from search filters (it lives in Settings)
429. Advanced info panel: year, status, type, language, demographic, authors
430. Custom result column count, 0 = fit the window
431. Bookmark folders with create, rename and delete
432. File bookmarks by dragging them onto a folder
433. Folder picker when bookmarking, or save straight to the root
434. Optional per-folder lock and blurred covers
435. Folder cover is the first book added to it
436. Deleting a folder keeps its bookmarks, moving them back to the root
437. Text-input modal that distinguishes cancel from an empty value
438. Keyboard shortcuts listed in Settings, not only in a popup
439. Overlay buttons bind reliably (markup declared before the script)
440. Dialog text inputs themed to match the rest of the app
441. Lock screen and recovery fields use the app font
442. Bookmark covers no longer hijack the drag gesture
443. Floating drop zones appear while dragging a bookmark
444. Drop a bookmark back to All bookmarks, or straight into a new folder
445. Drop highlight survives the pointer crossing child elements
446. A missed drop never navigates the app away
447. All configuration in one `config.json` (settings + sources)
448. Settings written atomically, so a crash cannot reset them
449. Concurrent saves cannot clobber each other
450. Pre-1.4.11 `settings.json` migrated automatically
451. Every bridge endpoint returns errors as data, never raises
452. A malformed queue entry cannot kill the download worker thread
453. Download options coerced from UI values instead of trusted
454. Cover cache bounded by bytes with LRU eviction
455. Global JS error handlers clear spinners and surface a message
456. Search/browse failures show a retry instead of a dead screen
457. `mangadl menu` — progressive numbered interface, no extra dependencies
458. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
459. Menu covers search, trending, URLs, library, bookmarks, settings, tools
460. Menu exits cleanly on EOF or a non-terminal stdin
461. `mangadl search --type` narrows by manga / manhwa / manhua
462. `mangadl search --status` narrows by publication status
463. `mangadl search -n/--limit` caps the number of results
464. `mangadl search --sort` by title, source, chapters or year, `--reverse`
465. `mangadl search --urls` prints one URL per line for pipes
466. `mangadl search --json` prints machine-readable results
467. `mangadl search --open N` shows details for a numbered result
468. `mangadl search --download N` downloads a numbered result
469. `mangadl tui` explains itself instead of a traceback without Textual
470. Every module runs directly (`py menu.py`) without an import error
471. Redesigned landing page with an original identity, not a code-host clone
472. Landing page ships light and dark themes, remembered between visits

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
