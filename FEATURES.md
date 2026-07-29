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

## Source ranking and exclusion

82. Drag-and-drop source ranking in the GUI
83. Move up / down buttons as a keyboard-friendly alternative
84. Rank order decides which copy wins when a series exists on several sites
85. Toggle a source off to exclude its results entirely
86. Excluded sources still work from a direct URL
87. `search_enabled` — keep a source usable but out of multi-source search
88. Per-source result limit override
89. Per-source weight for duplicate scoring
90. Per-source language override
91. Per-source extra delay for politeness
92. Free-text note per source
93. Ranking is shared by CLI, GUI and TUI
94. New sources are auto-appended, ranked last
95. Stale config entries are pruned automatically
96. `mangadl config` shows the full table
97. `mangadl config enable|disable <source>`
98. `mangadl config up|down <source>`
99. `mangadl config rank <a> <b> ...` to set the whole order
100. `mangadl config reset`
101. Sources tab in the TUI with the same controls

## Provider attribution

102. Provider shown directly beneath the manga title in the GUI
103. Colour-coded provider dot per source
104. "Open on source site" link next to the provider name
105. Provider line under the title in the TUI
106. Provider line in `mangadl info`
107. Source badges on GUI search result cards
108. Source column in CLI search results
109. Source tag in TUI search results
110. Source recorded on every library entry
111. Source recorded on every bookmark
112. Source stamped on download results and plan events

## Passcode lock

113. Optional app passcode
114. PBKDF2-HMAC-SHA256 with 240,000 rounds
115. Per-install random salt — identical passcodes hash differently
116. Constant-time comparison
117. Passcode never stored in plaintext
118. One-time recovery key issued at setup
119. Recovery key is case-insensitive and ignores spacing
120. Recovery flow built into the lock screen
121. Change passcode (requires the current one)
122. Disable lock (requires the passcode)
123. Attempt throttling after 5 failures
124. Escalating cooldown, capped at 15 minutes
125. Auto-lock after N idle minutes
126. Lock on app start
127. Optional cover blurring behind the lock screen
128. Optional passcode hint
129. Lock file written with owner-only permissions
130. `mangadl lock status|set|change|off` from the terminal

## Content filters

131. Blocked tags
132. Blocked title words
133. Blocked authors
134. Safe mode drops adult-rated results
135. Hide results with no cover
136. Minimum chapter count filter
137. Filters apply to both GUI and CLI search

## Duplicate handling

138. Cross-source duplicate detection by normalised title
139. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
140. Best-ranked copy survives a merge
141. `also_on` lists the other sources carrying the same series
142. Toggle merging on or off
143. Interleave mode round-robins sources instead of grouping them

## Reading progress

144. Mark individual chapters read or unread
145. Bulk mark a range
146. Percentage progress per series
147. Unread count per series
148. Jump to next unread chapter
149. Last-read chapter remembered
150. Clear progress per series or globally

## Update watching

151. Watch a series for new chapters
152. Watchlist with per-series known chapter count
153. Parallel update checking across all watched series
154. New-chapter counts per series
155. Acknowledge updates to reset the badge
156. Progress callback while checking
157. Failing sites are skipped, not fatal
158. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

159. Free-text note per series
160. 0–5 star rating, clamped
161. Custom tags per series
162. Filter by minimum rating
163. Named collections
164. Add / remove series in a collection
165. Duplicate-safe collection inserts

## Statistics and insights

166. Total chapters, pages, bytes and time
167. Per-source statistics
168. Per-day statistics
169. Average pages per second
170. Busiest day and top source
171. Human-readable sizes and durations
172. Library insights: series, chapters, pages, disk use
173. Largest and most recent series
174. Statistics recorded automatically after every download
175. Stat tiles in GUI settings
176. `mangadl stats` in the terminal
177. Reset statistics

## Search history

178. Every search recorded with source and hit count
179. Duplicate queries collapse to the newest
180. Type-ahead suggestions from history
181. Prefix matches ranked above substring matches
182. Remove a single entry or clear all
183. Capped at 500 entries
184. `mangadl history` / `mangadl history clear`

## Download queue

185. Persistent job queue
186. Reorder queued jobs
187. Per-job status: pending, running, done, failed, paused
188. Progress and error recorded per job
189. Fetch the next pending job
190. Remove one job or clear by status

## Import, export, backup

191. Export library as JSON
192. Export library as CSV
193. Export library as Markdown table
194. Import a previously exported library
195. Merge or replace on import
196. Snapshots of library + bookmarks + config
197. Restore any snapshot
198. Last 20 snapshots retained
199. `mangadl export <file> [format]`

## Disk maintenance

200. Per-series disk usage report
201. Duplicate file scan by SHA-256, size-bucketed for speed
202. Wasted-space total
203. Orphan detection for missing files and folders
204. Bulk delete chosen files
205. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

206. Correct cover URLs in three sizes
207. Per-volume and localised cover listing
208. Reference expansion so covers arrive in one request
209. Translation language selection
210. Preferred scanlation group
211. Automatic dedupe of multiple releases per chapter
212. Alternatives recorded on the chosen release
213. Data-saver mode
214. Externally hosted chapters filtered out
215. Paginated feed with the 10k offset cap handled
216. All content ratings requested explicitly

## Discovery: trending and genres

217. Pressing Search with an empty box shows trending instead of doing nothing
218. GUI opens on a trending feed rather than a blank page
219. TUI opens on a trending feed
220. `mangadl search` with no query lists trending
221. `mangadl trending` explicit discovery command
222. `mangadl trending <genre>` for per-genre trending
223. `mangadl genres` lists every genre and which sites offer it
224. `-g/--genre` filters any search by genre
225. Genre dropdown in the GUI filter row
226. Quick-pick genre chips for the ten most widely supported genres
227. Genre dropdown in the TUI beside the source picker
228. Genres merged across every enabled source
229. Case-insensitive genre matching across sites
230. Genres ordered by how widely they are supported
231. Per-source genre id mapping kept alongside the shared label
232. Genre list reflects only the sources you have enabled
233. Trending results interleave sources so the first screen is a mix
234. `Load more` pagination in the GUI
235. Per-source browse sort options exposed to the UI
236. MangaDex trending via follower count
237. MangaDex genre browsing by resolved tag UUID
238. MangaDex tag names resolved case-insensitively, with partial matching
239. Raw MangaDex tag UUIDs accepted directly
240. MangaDex tag list cached per process
241. Mangakatana genre browsing over 46 genre slugs
242. Mangakatana pagination via the site's real filter path
243. Natomanga hot / latest / new discovery feeds
244. Natomanga genre browsing with paging
245. Weeb Central trending via popularity sort
246. Weeb Central genre browsing over 26 tags
247. Sources that cannot browse are skipped, with a clear message
248. Type-ahead search suggestions drawn from history
249. Empty results explain what to try next instead of just saying "none"
250. Browse honours source ranking and exclusions
251. Browse results pass through content filters and duplicate merging

## Robust calling

252. Circuit breaker per source, with closed / open / half-open states
253. Repeated failures open the breaker so a dead site is skipped instantly
254. Half-open probe after cooldown, closing again on success
255. Cooldown doubles with each repeated trip, capped
256. Success resets the failure count
257. Bounded retries with exponential backoff
258. Proportional jitter so retries do not synchronise
259. `retry_if` hook to skip pointless retries such as 404s
260. `on_retry` callback for progress reporting
261. TTL cache for discovery listings, five minutes
262. TTL cache for genre lists, one hour
263. Cache eviction when full, with hit-rate statistics
264. `call_safely` runs anything and falls back instead of raising
265. `gather` runs many calls in parallel and keeps whatever succeeds
266. Overall timeout support in `gather`, keeping finished work
267. Rate-limit headers honoured, absolute and relative
268. Partial results always returned rather than failing the whole request
269. Every failure logged once with context
270. `mangadl health` shows breaker state and cache hit rates
271. Health diagnostics exposed to the GUI

## Custom dropdowns

272. Themed dropdowns replacing unstyleable native select popups
273. Native `<select>` kept in the DOM as the source of truth
274. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
275. `value` setter wrapped so programmatic assignment repaints the trigger
276. MutationObserver picks up rebuilt option lists automatically
277. Real `change` and `input` events dispatched on selection
278. No event fired when reselecting the current value
279. Panel portalled to `<body>`, so no ancestor can clip it
280. Flips above the trigger when there is no room below
281. Repositions on scroll and resize
282. Type-to-filter box appears automatically past eight options
283. "No matches" state when a filter excludes everything
284. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
285. Typeahead on the closed trigger, like a native select
286. Only one panel open at a time
287. Closes on outside click
288. ARIA combobox/listbox roles with active-descendant tracking
289. Checkmark and accent colour on the selected row
290. Follows every theme and accent via CSS custom properties
291. Honours `prefers-reduced-motion`
292. Disabled selects reflected on the trigger
293. Enhancement failures are caught so styling can never break the page
294. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

295. Updates tab: watchlist with per-series new-chapter counts
296. Rail badge showing how many watched series have updates
297. One-click "Check now" runs every watched series in parallel
298. Watch / unwatch button on the manga page
299. Insights tab: six headline metrics at a glance
300. Per-source bar chart of downloaded chapters
301. Fourteen-day activity sparkline
302. Biggest series and recently downloaded lists
303. Tools tab with five sub-panels
304. Disk usage per series, largest first
305. Duplicate file scan with wasted-space total
306. Orphan detection for library entries whose files vanished
307. Source health panel showing live circuit-breaker state
308. Searchable history panel; click an entry to re-run it
309. `callApi` wrapper so a missing endpoint cannot blank a tab
310. GitHub-style landing page built on Primer design tokens
311. Real light and dark modes, remembered in localStorage
312. Five deep-linkable page tabs with working back/forward
313. Screenshot gallery with GUI and TUI sub-tabs
314. Copy-to-clipboard install commands with success feedback
315. Language breakdown bar computed from the real repository
316. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

317. Omega Scans source via its JSON API
318. Omega Scans coin-locked chapters detected and skipped
319. ManhwaRead source, decoding base64 page data
320. ManhwaRead per-chapter Referer so its CDN serves images
321. Manhwa18 source, flagged adult-only
322. Adult sources tagged so Safe mode removes them automatically
323. `18+` chip on adult sources in the ranking list
324. Toggle switches render correctly (CSS selector matched no markup)
325. Both switch markup variants supported, markup normalised
326. Disabled source rows keep their toggle legible and clickable
327. Off-state switch has real contrast against the row
328. Settings text, number and password inputs themed
329. Focus ring on settings inputs
330. Number spinners removed for visual consistency
331. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

332. Output files are named by the chapters they contain
333. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
334. Bundled files name their own range, e.g. "Chapters 011-020"
335. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
336. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
337. Heavily fragmented picks truncate to "001-013 (7 chapters)"
338. New {chapters} and {count} filename placeholders
339. Legacy "{title}" templates migrated forward automatically
340. Custom templates are never overwritten by the migration
341. Bad templates fall back instead of crashing the download
342. Library verification reports entries whose files have gone
343. Moved folders detected by matching folder name under a root
344. Proposals are inert until confirmed, so a wrong guess is harmless
345. Re-linking rewrites both the directory and every output path
346. Download history, title and source survive a re-link
347. "Pick new downloads folder" adopts a new root and re-links in one step
348. Moved files panel in the Tools tab
349. `mangadl library verify|scan|move` from the terminal
350. Extra library search roots remembered in settings
351. Minimum and maximum chapter number filters
352. Filter chapters by name text
353. Sort chapters newest-first or oldest-first
354. Hide already-downloaded chapters
355. Count pill shows "visible / total" while filtering
356. A note reports how many chapters a filter is hiding
357. Bulk select buttons act only on visible chapters
358. "Latest" picks the highest-numbered visible chapter
359. Filters change only the display, never the selection keys
360. One-click reset for all chapter filters

## Stability and polish

361. Window close no longer crashes with "unhashable type: 'dict'"
362. Cover mirrors: a failing CDN host falls back to a sibling automatically
363. Covers walk every mirror before showing a fallback tile
364. Passcode gates the app before any data is fetched or painted
365. Boot pauses until the lock screen is dismissed
366. Corner radii snap to a four-step scale instead of 13 ad-hoc values
367. Download location saved to settings.json when chosen
368. Download location saved when typed directly
369. Both folder fields stay in sync

## Square mode, rail and lock polish

370. Square corners mode: turn off all rounding in one switch
371. Square mode flattens pills, fields, dropdowns and switches
372. True circles (spinner, lock badge) stay round in square mode
373. Corner preference saved and restored
374. Side rail is narrower by default
375. Expand button widens the rail and reveals labels
376. Rail state remembered between runs
377. Lock overlay paints on the very first frame
378. Remembered lock state avoids a needless overlay flash
379. Fail-safe timer means the overlay can never strand the app
380. Show/hide passcode button
381. Remaining-attempts counter with warning colours
382. Wrong passcode shakes the panel
383. Live cooldown countdown that disables the field
384. Enter reliably submits a search
385. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

386. Empty-but-200 throttle responses are retried instead of accepted
387. Multi-source search no longer loses sources silently
388. Minimum chapter-count filter
389. Maximum chapter-count filter
390. Chapter counts read from count, last_chapter or the newest label
391. Unknown chapter counts are never filtered out
392. Webtoons source with episode paging
393. Webtoons per-chapter Referer for its hotlink-protected CDN
394. nhentai source, flagged adult-only
395. nhentai thumbnails resolved to full-size pages
396. Twenty-three sources total
397. nhentai browses `/popular` (the site root lists no galleries at all)
398. nhentai genre slugs verified against the live site
399. nhentai covers follow the site's own `data-fallbacks` chain
400. Cover proxy for hotlink-protected CDNs, inlined as data URIs
401. Webtoons covers load in the GUI despite the global `no-referrer`
402. Natomanga cover host is never rewritten (shards, not mirrors)
403. Transient cover failures retry the same URL instead of another host
404. Mangadass source, flagged adult-only
405. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
406. Mangadass chapters sorted numerically, not by document order
407. Manga18.club source, flagged adult-only
408. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
409. Manga18.club pages decoded from the base64 `slides_p_path` array
410. HentaiAkane source, flagged adult-only
411. HentaiAkane pages read from the `ts_reader.run` payload
412. ManhwaRead decodes base64 page lists that ship without padding
413. Connection pool sized to the worker count (no discarded connections)
414. Download cart: queue several manga and keep browsing
415. Concurrent downloads of different manga, configurable 1-5
416. Every progress event is stamped with its job, so chapters never mix
417. Chapter rows show the owning manga when several downloads run
418. Queue panel with per-job status and removable pending entries
419. Stop one download without touching the others
420. A cancelled job reports "stopped", not "failed"
421. Multi-genre search: combine genres with AND or OR
422. Genre chips toggle, building a selection instead of replacing it
423. Picked genres shown as removable chips with a Clear button
424. Genre intersection computed per source, never across sites
425. Library keys normalised (scheme, www, query, fragment)
426. Downloaded chapters matched by number, tolerating changed dates
427. Downloaded pill and highlighted rows can no longer disagree
428. URLs with tracking parameters no longer return zero chapters
429. Manhwa18 genre browsing fixed (/webtoon-genre/)
430. nhentai falls back to search for genres it does not have as tags
431. Content fills the window instead of a fixed centred column
432. Keyboard shortcuts with a searchable `?` help overlay
433. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
434. Shortcuts ignored while typing and while the lock screen is up
435. Invert chapter selection, on visible rows only
436. Copy title and link, with a clipboard fallback for WebView2
437. Refresh the current view with `r`
438. Bookmark and library covers load through the proxy (hotlinked CDNs)
439. Bookmarks store an openable URL, not the normalised key
440. Download queue visible before any job starts
441. Series type classified from origin language and tags
442. Type filter (Manga / Manhwa / Manhua) actually narrows results
443. Per-source default type for sites with a single-type catalogue
444. Square corners reach progress bars, the search box and every pill
445. Strict chapter range option, for hiding unknown chapter counts
446. Source picker removed from search filters (it lives in Settings)
447. Advanced info panel: year, status, type, language, demographic, authors
448. Custom result column count, 0 = fit the window
449. Bookmark folders with create, rename and delete
450. File bookmarks by dragging them onto a folder
451. Folder picker when bookmarking, or save straight to the root
452. Optional per-folder lock and blurred covers
453. Folder cover is the first book added to it
454. Deleting a folder keeps its bookmarks, moving them back to the root
455. Text-input modal that distinguishes cancel from an empty value
456. Keyboard shortcuts listed in Settings, not only in a popup
457. Overlay buttons bind reliably (markup declared before the script)
458. Dialog text inputs themed to match the rest of the app
459. Lock screen and recovery fields use the app font
460. Bookmark covers no longer hijack the drag gesture
461. Floating drop zones appear while dragging a bookmark
462. Drop a bookmark back to All bookmarks, or straight into a new folder
463. Drop highlight survives the pointer crossing child elements
464. A missed drop never navigates the app away
465. All configuration in one `config.json` (settings + sources)
466. Settings written atomically, so a crash cannot reset them
467. Concurrent saves cannot clobber each other
468. Pre-1.4.11 `settings.json` migrated automatically
469. Every bridge endpoint returns errors as data, never raises
470. A malformed queue entry cannot kill the download worker thread
471. Download options coerced from UI values instead of trusted
472. Cover cache bounded by bytes with LRU eviction
473. Global JS error handlers clear spinners and surface a message
474. Search/browse failures show a retry instead of a dead screen
475. `mangadl menu` — progressive numbered interface, no extra dependencies
476. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
477. Menu covers search, trending, URLs, library, bookmarks, settings, tools
478. Menu exits cleanly on EOF or a non-terminal stdin
479. `mangadl search --type` narrows by manga / manhwa / manhua
480. `mangadl search --status` narrows by publication status
481. `mangadl search -n/--limit` caps the number of results
482. `mangadl search --sort` by title, source, chapters or year, `--reverse`
483. `mangadl search --urls` prints one URL per line for pipes
484. `mangadl search --json` prints machine-readable results
485. `mangadl search --open N` shows details for a numbered result
486. `mangadl search --download N` downloads a numbered result
487. `mangadl tui` explains itself instead of a traceback without Textual
488. Every module runs directly (`py menu.py`) without an import error
489. Redesigned landing page with an original identity, not a code-host clone
490. Landing page ships light and dark themes, remembered between visits

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
