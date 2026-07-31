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

## Background mode and crash safety (v1.4.19)

64. **Minimise to system tray** — closing the window keeps downloads running
65. Tray context menu shows live **transfer rate** and **ETA**
66. Tray menu shows **chapters remaining** and how many jobs are **queued**
67. Per-job lines in the menu, so concurrent downloads are distinguishable
68. **Open MangaDL** brings the window back; **Quit** really exits
69. Pause/resume the queue from the tray without stopping a running chapter
70. Tray icon changes colour while downloading, with an activity dot
71. Desktop notification when a download finishes (optional)
72. Rolling-window rate meter, so the speed reflects now, not the average
73. ETA projects chapters whose page lists have not been fetched yet
74. ETA reports `--` honestly when it genuinely cannot be known
75. `pystray` is optional; a machine with no tray degrades gracefully
76. **Crash resume now survives concurrent jobs** — one journal file per job
77. A finishing job no longer erases a still-running job's resume record
78. Journal writes are atomic and fsynced, so a crash cannot truncate them
79. A corrupt journal file is dropped rather than breaking every future read
80. Legacy single-file `job.json` is migrated automatically
81. `mangadl resume` lists every interrupted job

## Cover rebuilder (v1.4.20)

82. **Tools → Rebuild covers**: give every CBZ folder a `cover.jpg`
83. Walks a folder tree recursively, finding every `.cbz`/`.cbr`/`.cb7`
84. Recovers the series title from the filename, stripping chapter markers
85. Handles MangaDL's own names: `Chapters 001`, `001-050`, `001-003, 007-008`
86. Handles third-party names: `[Group]`, `(2024)`, `v03`, `c045`, `#12`, `Ep 200`
87. Keeps numbers that belong to a title (`Kingdom 2`) while dropping indexes
88. Non-latin titles survive intact
89. Searches every enabled source and ranks candidates, exact matches first
90. You choose the cover — nothing is applied automatically
91. Saves `cover.jpg` **beside the archive**, never in a shared parent
92. Several series in one folder are each moved into their own folder first
93. A folder that is already tidy is never reorganised
94. Idempotent: a second run does not nest folders inside folders
95. Moving never overwrites; a name clash is suffixed
96. Skips folders that already have a cover, unless you ask to replace
97. `raw/` page folders are ignored
98. Every thumbnail is proxied, so cross-origin CDNs still preview
99. `mangadl covers` does the same from the CLI, `--urls` for a dry run

## Cover rebuilder: folder choice and bulk sorting (v1.4.21)

100. **Choose folder** in Tools → Rebuild covers: scan any folder, not just downloads
101. The chosen folder is shown, with a Reset back to the configured one
102. **Sort into folders**: split a flat folder of loose CBZs by series, no downloads
103. Multi-volume sets group together (`Ch.001-036` + `Ch.037-072` → one folder)
104. `Ch.001-036` style names recognised, with or without the dot or space
105. `Chs.`, `Chapt.`, `Cap.`, `Capitulo` and `~` ranges also recognised
106. Longest marker spelling matches first, so `Chs` does not leave a stray `s`
107. Titles containing marker words survive: Chainsaw Man, Case Closed, Eden's Zero
108. `mangadl covers --dry-run` prints the plan and changes nothing
109. `mangadl covers --sort-only` splits a flat folder without fetching covers
110. `mangadl covers --replace` overwrites covers that already exist

## Smart search: one-button covers (v1.4.22)

111. **Smart search** button: scan, choose and apply covers for a whole folder
112. Chooses using the **source ranking from Settings** — no picking by hand
113. Exact title match always beats a fuzzy one
114. Resolution check rejects list thumbnails (measured 6x-15x smaller)
115. Ranking still decides between two genuinely good covers
116. Live per-series progress: what it chose, from where, at what size
117. **Stop** halts cleanly after the current series
118. Loose archives are sorted into folders on the way
119. Runs on a background thread, so the UI never blocks
120. Refuses to start a second scan while one is running
121. Cover bytes are reused from the measuring pass, never downloaded twice
122. A source that blocks measuring is not penalised for it
123. `mangadl covers` uses the same rules and reports the chosen resolution

## Tray, startup and stats (v1.4.24)

548. Closing to the tray keeps the process alive, so downloads really continue
549. Tray Quit and an empty queue both release the app; it never hangs invisibly
550. Turning "minimise to tray" off takes effect immediately, no restart
551. The tray switches save when you flip them (they were never bound)
552. Packaged builds bundle pystray, so the tray works in the exe
553. The stylesheet loads before the font CDN: no unstyled page on a slow link
554. Icons stay hidden until their font arrives instead of showing raw names
555. The bouncing search icon is no longer clipped at the top of its bounce
556. Queue tiles follow the theme (--panel-2/--edge-c were never defined)
557. Queue sparkline no longer inherits the stats chart's flex layout
558. Overall progress and Stop live inside the queue card, not a floating one
559. A single download shows a tile (the card used to need two rows)
560. Collapsed tiles carry a cover thumbnail, source and live ETA
561. In-flight chapters are listed once, inside the expanded tile
562. Chapter rows update in place instead of being rebuilt every second
563. Advanced queue logging records every engine event, off by default
564. Recent activity is a GitHub-style contribution calendar, 53 weeks
565. Calendar squares are brighter the more you downloaded that day
566. Each source has a stable colour; day squares mix their sources' colours
567. Day tooltips name each source as a fraction of that day's chapters
568. Source carousel with per-source totals, share and a mini activity strip
569. Carousel tooltips show a source's chapters as a fraction of the library
570. Per-day per-source statistics are recorded for the calendar
571. Charts label sources by display name, not raw ids like `madara.toonily`
572. Calendar and carousel honour the square-corners and reduced-motion settings

## Queue redesign and animations (v1.4.23)

124. Download queue **grouped by manga**, one tile per book
125. Tiles are **collapsible**, collapsed by default
126. Collapsed tile shows a live **transfer-rate sparkline**
127. Collapsed tile shows a **chapter fraction pill** (e.g. 10/100)
128. The pill pulses when the count changes
129. Expanded tile adds a larger cover, the source and a progress bar
130. Expanded tile shows speed, ETA, bytes downloaded and the fraction
131. Expanded tile lists the chapters downloading right now, with progress
132. Grouping keys on the URL, so one book never splits into two tiles
133. Live refresh patches only what changed, so an open tile stays open
134. Rate polling stops by itself when nothing is downloading
135. Per-job snapshots carry formatted speed/ETA text and a rate history
136. Rate history is bounded and sampled at most every 0.4s
137. Tile, toast, card, button and chapter-chip animations
138. All motion respects `prefers-reduced-motion`

## Source ranking and exclusion

139. Drag-and-drop source ranking in the GUI
140. Move up / down buttons as a keyboard-friendly alternative
141. Rank order decides which copy wins when a series exists on several sites
142. Toggle a source off to exclude its results entirely
143. Excluded sources still work from a direct URL
144. `search_enabled` — keep a source usable but out of multi-source search
145. Per-source result limit override
146. Per-source weight for duplicate scoring
147. Per-source language override
148. Per-source extra delay for politeness
149. Free-text note per source
150. Ranking is shared by CLI, GUI and TUI
151. New sources are auto-appended, ranked last
152. Stale config entries are pruned automatically
153. `mangadl config` shows the full table
154. `mangadl config enable|disable <source>`
155. `mangadl config up|down <source>`
156. `mangadl config rank <a> <b> ...` to set the whole order
157. `mangadl config reset`
158. Sources tab in the TUI with the same controls

## Provider attribution

159. Provider shown directly beneath the manga title in the GUI
160. Colour-coded provider dot per source
161. "Open on source site" link next to the provider name
162. Provider line under the title in the TUI
163. Provider line in `mangadl info`
164. Source badges on GUI search result cards
165. Source column in CLI search results
166. Source tag in TUI search results
167. Source recorded on every library entry
168. Source recorded on every bookmark
169. Source stamped on download results and plan events

## Passcode lock

170. Optional app passcode
171. PBKDF2-HMAC-SHA256 with 240,000 rounds
172. Per-install random salt — identical passcodes hash differently
173. Constant-time comparison
174. Passcode never stored in plaintext
175. One-time recovery key issued at setup
176. Recovery key is case-insensitive and ignores spacing
177. Recovery flow built into the lock screen
178. Change passcode (requires the current one)
179. Disable lock (requires the passcode)
180. Attempt throttling after 5 failures
181. Escalating cooldown, capped at 15 minutes
182. Auto-lock after N idle minutes
183. Lock on app start
184. Optional cover blurring behind the lock screen
185. Optional passcode hint
186. Lock file written with owner-only permissions
187. `mangadl lock status|set|change|off` from the terminal

## Content filters

188. Blocked tags
189. Blocked title words
190. Blocked authors
191. Safe mode drops adult-rated results
192. Hide results with no cover
193. Minimum chapter count filter
194. Filters apply to both GUI and CLI search

## Duplicate handling

195. Cross-source duplicate detection by normalised title
196. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
197. Best-ranked copy survives a merge
198. `also_on` lists the other sources carrying the same series
199. Toggle merging on or off
200. Interleave mode round-robins sources instead of grouping them

## Reading progress

201. Mark individual chapters read or unread
202. Bulk mark a range
203. Percentage progress per series
204. Unread count per series
205. Jump to next unread chapter
206. Last-read chapter remembered
207. Clear progress per series or globally

## Update watching

208. Watch a series for new chapters
209. Watchlist with per-series known chapter count
210. Parallel update checking across all watched series
211. New-chapter counts per series
212. Acknowledge updates to reset the badge
213. Progress callback while checking
214. Failing sites are skipped, not fatal
215. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

216. Free-text note per series
217. 0–5 star rating, clamped
218. Custom tags per series
219. Filter by minimum rating
220. Named collections
221. Add / remove series in a collection
222. Duplicate-safe collection inserts

## Statistics and insights

223. Total chapters, pages, bytes and time
224. Per-source statistics
225. Per-day statistics
226. Average pages per second
227. Busiest day and top source
228. Human-readable sizes and durations
229. Library insights: series, chapters, pages, disk use
230. Largest and most recent series
231. Statistics recorded automatically after every download
232. Stat tiles in GUI settings
233. `mangadl stats` in the terminal
234. Reset statistics

## Search history

235. Every search recorded with source and hit count
236. Duplicate queries collapse to the newest
237. Type-ahead suggestions from history
238. Prefix matches ranked above substring matches
239. Remove a single entry or clear all
240. Capped at 500 entries
241. `mangadl history` / `mangadl history clear`

## Download queue

242. Persistent job queue
243. Reorder queued jobs
244. Per-job status: pending, running, done, failed, paused
245. Progress and error recorded per job
246. Fetch the next pending job
247. Remove one job or clear by status

## Import, export, backup

248. Export library as JSON
249. Export library as CSV
250. Export library as Markdown table
251. Import a previously exported library
252. Merge or replace on import
253. Snapshots of library + bookmarks + config
254. Restore any snapshot
255. Last 20 snapshots retained
256. `mangadl export <file> [format]`

## Disk maintenance

257. Per-series disk usage report
258. Duplicate file scan by SHA-256, size-bucketed for speed
259. Wasted-space total
260. Orphan detection for missing files and folders
261. Bulk delete chosen files
262. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

263. Correct cover URLs in three sizes
264. Per-volume and localised cover listing
265. Reference expansion so covers arrive in one request
266. Translation language selection
267. Preferred scanlation group
268. Automatic dedupe of multiple releases per chapter
269. Alternatives recorded on the chosen release
270. Data-saver mode
271. Externally hosted chapters filtered out
272. Paginated feed with the 10k offset cap handled
273. All content ratings requested explicitly

## Discovery: trending and genres

274. Pressing Search with an empty box shows trending instead of doing nothing
275. GUI opens on a trending feed rather than a blank page
276. TUI opens on a trending feed
277. `mangadl search` with no query lists trending
278. `mangadl trending` explicit discovery command
279. `mangadl trending <genre>` for per-genre trending
280. `mangadl genres` lists every genre and which sites offer it
281. `-g/--genre` filters any search by genre
282. Genre dropdown in the GUI filter row
283. Quick-pick genre chips for the ten most widely supported genres
284. Genre dropdown in the TUI beside the source picker
285. Genres merged across every enabled source
286. Case-insensitive genre matching across sites
287. Genres ordered by how widely they are supported
288. Per-source genre id mapping kept alongside the shared label
289. Genre list reflects only the sources you have enabled
290. Trending results interleave sources so the first screen is a mix
291. `Load more` pagination in the GUI
292. Per-source browse sort options exposed to the UI
293. MangaDex trending via follower count
294. MangaDex genre browsing by resolved tag UUID
295. MangaDex tag names resolved case-insensitively, with partial matching
296. Raw MangaDex tag UUIDs accepted directly
297. MangaDex tag list cached per process
298. Mangakatana genre browsing over 46 genre slugs
299. Mangakatana pagination via the site's real filter path
300. Natomanga hot / latest / new discovery feeds
301. Natomanga genre browsing with paging
302. Weeb Central trending via popularity sort
303. Weeb Central genre browsing over 26 tags
304. Sources that cannot browse are skipped, with a clear message
305. Type-ahead search suggestions drawn from history
306. Empty results explain what to try next instead of just saying "none"
307. Browse honours source ranking and exclusions
308. Browse results pass through content filters and duplicate merging

## Robust calling

309. Circuit breaker per source, with closed / open / half-open states
310. Repeated failures open the breaker so a dead site is skipped instantly
311. Half-open probe after cooldown, closing again on success
312. Cooldown doubles with each repeated trip, capped
313. Success resets the failure count
314. Bounded retries with exponential backoff
315. Proportional jitter so retries do not synchronise
316. `retry_if` hook to skip pointless retries such as 404s
317. `on_retry` callback for progress reporting
318. TTL cache for discovery listings, five minutes
319. TTL cache for genre lists, one hour
320. Cache eviction when full, with hit-rate statistics
321. `call_safely` runs anything and falls back instead of raising
322. `gather` runs many calls in parallel and keeps whatever succeeds
323. Overall timeout support in `gather`, keeping finished work
324. Rate-limit headers honoured, absolute and relative
325. Partial results always returned rather than failing the whole request
326. Every failure logged once with context
327. `mangadl health` shows breaker state and cache hit rates
328. Health diagnostics exposed to the GUI

## Custom dropdowns

329. Themed dropdowns replacing unstyleable native select popups
330. Native `<select>` kept in the DOM as the source of truth
331. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
332. `value` setter wrapped so programmatic assignment repaints the trigger
333. MutationObserver picks up rebuilt option lists automatically
334. Real `change` and `input` events dispatched on selection
335. No event fired when reselecting the current value
336. Panel portalled to `<body>`, so no ancestor can clip it
337. Flips above the trigger when there is no room below
338. Repositions on scroll and resize
339. Type-to-filter box appears automatically past eight options
340. "No matches" state when a filter excludes everything
341. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
342. Typeahead on the closed trigger, like a native select
343. Only one panel open at a time
344. Closes on outside click
345. ARIA combobox/listbox roles with active-descendant tracking
346. Checkmark and accent colour on the selected row
347. Follows every theme and accent via CSS custom properties
348. Honours `prefers-reduced-motion`
349. Disabled selects reflected on the trigger
350. Enhancement failures are caught so styling can never break the page
351. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

352. Updates tab: watchlist with per-series new-chapter counts
353. Rail badge showing how many watched series have updates
354. One-click "Check now" runs every watched series in parallel
355. Watch / unwatch button on the manga page
356. Insights tab: six headline metrics at a glance
357. Per-source bar chart of downloaded chapters
358. Fourteen-day activity sparkline
359. Biggest series and recently downloaded lists
360. Tools tab with five sub-panels
361. Disk usage per series, largest first
362. Duplicate file scan with wasted-space total
363. Orphan detection for library entries whose files vanished
364. Source health panel showing live circuit-breaker state
365. Searchable history panel; click an entry to re-run it
366. `callApi` wrapper so a missing endpoint cannot blank a tab
367. GitHub-style landing page built on Primer design tokens
368. Real light and dark modes, remembered in localStorage
369. Five deep-linkable page tabs with working back/forward
370. Screenshot gallery with GUI and TUI sub-tabs
371. Copy-to-clipboard install commands with success feedback
372. Language breakdown bar computed from the real repository
373. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

374. Omega Scans source via its JSON API
375. Omega Scans coin-locked chapters detected and skipped
376. ManhwaRead source, decoding base64 page data
377. ManhwaRead per-chapter Referer so its CDN serves images
378. Manhwa18 source, flagged adult-only
379. Adult sources tagged so Safe mode removes them automatically
380. `18+` chip on adult sources in the ranking list
381. Toggle switches render correctly (CSS selector matched no markup)
382. Both switch markup variants supported, markup normalised
383. Disabled source rows keep their toggle legible and clickable
384. Off-state switch has real contrast against the row
385. Settings text, number and password inputs themed
386. Focus ring on settings inputs
387. Number spinners removed for visual consistency
388. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

389. Output files are named by the chapters they contain
390. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
391. Bundled files name their own range, e.g. "Chapters 011-020"
392. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
393. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
394. Heavily fragmented picks truncate to "001-013 (7 chapters)"
395. New {chapters} and {count} filename placeholders
396. Legacy "{title}" templates migrated forward automatically
397. Custom templates are never overwritten by the migration
398. Bad templates fall back instead of crashing the download
399. Library verification reports entries whose files have gone
400. Moved folders detected by matching folder name under a root
401. Proposals are inert until confirmed, so a wrong guess is harmless
402. Re-linking rewrites both the directory and every output path
403. Download history, title and source survive a re-link
404. "Pick new downloads folder" adopts a new root and re-links in one step
405. Moved files panel in the Tools tab
406. `mangadl library verify|scan|move` from the terminal
407. Extra library search roots remembered in settings
408. Minimum and maximum chapter number filters
409. Filter chapters by name text
410. Sort chapters newest-first or oldest-first
411. Hide already-downloaded chapters
412. Count pill shows "visible / total" while filtering
413. A note reports how many chapters a filter is hiding
414. Bulk select buttons act only on visible chapters
415. "Latest" picks the highest-numbered visible chapter
416. Filters change only the display, never the selection keys
417. One-click reset for all chapter filters

## Stability and polish

418. Window close no longer crashes with "unhashable type: 'dict'"
419. Cover mirrors: a failing CDN host falls back to a sibling automatically
420. Covers walk every mirror before showing a fallback tile
421. Passcode gates the app before any data is fetched or painted
422. Boot pauses until the lock screen is dismissed
423. Corner radii snap to a four-step scale instead of 13 ad-hoc values
424. Download location saved to settings.json when chosen
425. Download location saved when typed directly
426. Both folder fields stay in sync

## Square mode, rail and lock polish

427. Square corners mode: turn off all rounding in one switch
428. Square mode flattens pills, fields, dropdowns and switches
429. True circles (spinner, lock badge) stay round in square mode
430. Corner preference saved and restored
431. Side rail is narrower by default
432. Expand button widens the rail and reveals labels
433. Rail state remembered between runs
434. Lock overlay paints on the very first frame
435. Remembered lock state avoids a needless overlay flash
436. Fail-safe timer means the overlay can never strand the app
437. Show/hide passcode button
438. Remaining-attempts counter with warning colours
439. Wrong passcode shakes the panel
440. Live cooldown countdown that disables the field
441. Enter reliably submits a search
442. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

443. Empty-but-200 throttle responses are retried instead of accepted
444. Multi-source search no longer loses sources silently
445. Minimum chapter-count filter
446. Maximum chapter-count filter
447. Chapter counts read from count, last_chapter or the newest label
448. Unknown chapter counts are never filtered out
449. Webtoons source with episode paging
450. Webtoons per-chapter Referer for its hotlink-protected CDN
451. nhentai source, flagged adult-only
452. nhentai thumbnails resolved to full-size pages
453. Twenty-three sources total
454. nhentai browses `/popular` (the site root lists no galleries at all)
455. nhentai genre slugs verified against the live site
456. nhentai covers follow the site's own `data-fallbacks` chain
457. Cover proxy for hotlink-protected CDNs, inlined as data URIs
458. Webtoons covers load in the GUI despite the global `no-referrer`
459. Natomanga cover host is never rewritten (shards, not mirrors)
460. Transient cover failures retry the same URL instead of another host
461. Mangadass source, flagged adult-only
462. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
463. Mangadass chapters sorted numerically, not by document order
464. Manga18.club source, flagged adult-only
465. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
466. Manga18.club pages decoded from the base64 `slides_p_path` array
467. HentaiAkane source, flagged adult-only
468. HentaiAkane pages read from the `ts_reader.run` payload
469. ManhwaRead decodes base64 page lists that ship without padding
470. Connection pool sized to the worker count (no discarded connections)
471. Download cart: queue several manga and keep browsing
472. Concurrent downloads of different manga, configurable 1-5
473. Every progress event is stamped with its job, so chapters never mix
474. Chapter rows show the owning manga when several downloads run
475. Queue panel with per-job status and removable pending entries
476. Stop one download without touching the others
477. A cancelled job reports "stopped", not "failed"
478. Multi-genre search: combine genres with AND or OR
479. Genre chips toggle, building a selection instead of replacing it
480. Picked genres shown as removable chips with a Clear button
481. Genre intersection computed per source, never across sites
482. Library keys normalised (scheme, www, query, fragment)
483. Downloaded chapters matched by number, tolerating changed dates
484. Downloaded pill and highlighted rows can no longer disagree
485. URLs with tracking parameters no longer return zero chapters
486. Manhwa18 genre browsing fixed (/webtoon-genre/)
487. nhentai falls back to search for genres it does not have as tags
488. Content fills the window instead of a fixed centred column
489. Keyboard shortcuts with a searchable `?` help overlay
490. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
491. Shortcuts ignored while typing and while the lock screen is up
492. Invert chapter selection, on visible rows only
493. Copy title and link, with a clipboard fallback for WebView2
494. Refresh the current view with `r`
495. Bookmark and library covers load through the proxy (hotlinked CDNs)
496. Bookmarks store an openable URL, not the normalised key
497. Download queue visible before any job starts
498. Series type classified from origin language and tags
499. Type filter (Manga / Manhwa / Manhua) actually narrows results
500. Per-source default type for sites with a single-type catalogue
501. Square corners reach progress bars, the search box and every pill
502. Strict chapter range option, for hiding unknown chapter counts
503. Source picker removed from search filters (it lives in Settings)
504. Advanced info panel: year, status, type, language, demographic, authors
505. Custom result column count, 0 = fit the window
506. Bookmark folders with create, rename and delete
507. File bookmarks by dragging them onto a folder
508. Folder picker when bookmarking, or save straight to the root
509. Optional per-folder lock and blurred covers
510. Folder cover is the first book added to it
511. Deleting a folder keeps its bookmarks, moving them back to the root
512. Text-input modal that distinguishes cancel from an empty value
513. Keyboard shortcuts listed in Settings, not only in a popup
514. Overlay buttons bind reliably (markup declared before the script)
515. Dialog text inputs themed to match the rest of the app
516. Lock screen and recovery fields use the app font
517. Bookmark covers no longer hijack the drag gesture
518. Floating drop zones appear while dragging a bookmark
519. Drop a bookmark back to All bookmarks, or straight into a new folder
520. Drop highlight survives the pointer crossing child elements
521. A missed drop never navigates the app away
522. All configuration in one `config.json` (settings + sources)
523. Settings written atomically, so a crash cannot reset them
524. Concurrent saves cannot clobber each other
525. Pre-1.4.11 `settings.json` migrated automatically
526. Every bridge endpoint returns errors as data, never raises
527. A malformed queue entry cannot kill the download worker thread
528. Download options coerced from UI values instead of trusted
529. Cover cache bounded by bytes with LRU eviction
530. Global JS error handlers clear spinners and surface a message
531. Search/browse failures show a retry instead of a dead screen
532. `mangadl menu` — progressive numbered interface, no extra dependencies
533. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
534. Menu covers search, trending, URLs, library, bookmarks, settings, tools
535. Menu exits cleanly on EOF or a non-terminal stdin
536. `mangadl search --type` narrows by manga / manhwa / manhua
537. `mangadl search --status` narrows by publication status
538. `mangadl search -n/--limit` caps the number of results
539. `mangadl search --sort` by title, source, chapters or year, `--reverse`
540. `mangadl search --urls` prints one URL per line for pipes
541. `mangadl search --json` prints machine-readable results
542. `mangadl search --open N` shows details for a numbered result
543. `mangadl search --download N` downloads a numbered result
544. `mangadl tui` explains itself instead of a traceback without Textual
545. Every module runs directly (`py menu.py`) without an import error
546. Redesigned landing page with an original identity, not a code-host clone
547. Landing page ships light and dark themes, remembered between visits

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
