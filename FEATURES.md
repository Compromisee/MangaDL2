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

## Source ranking and exclusion

100. Drag-and-drop source ranking in the GUI
101. Move up / down buttons as a keyboard-friendly alternative
102. Rank order decides which copy wins when a series exists on several sites
103. Toggle a source off to exclude its results entirely
104. Excluded sources still work from a direct URL
105. `search_enabled` — keep a source usable but out of multi-source search
106. Per-source result limit override
107. Per-source weight for duplicate scoring
108. Per-source language override
109. Per-source extra delay for politeness
110. Free-text note per source
111. Ranking is shared by CLI, GUI and TUI
112. New sources are auto-appended, ranked last
113. Stale config entries are pruned automatically
114. `mangadl config` shows the full table
115. `mangadl config enable|disable <source>`
116. `mangadl config up|down <source>`
117. `mangadl config rank <a> <b> ...` to set the whole order
118. `mangadl config reset`
119. Sources tab in the TUI with the same controls

## Provider attribution

120. Provider shown directly beneath the manga title in the GUI
121. Colour-coded provider dot per source
122. "Open on source site" link next to the provider name
123. Provider line under the title in the TUI
124. Provider line in `mangadl info`
125. Source badges on GUI search result cards
126. Source column in CLI search results
127. Source tag in TUI search results
128. Source recorded on every library entry
129. Source recorded on every bookmark
130. Source stamped on download results and plan events

## Passcode lock

131. Optional app passcode
132. PBKDF2-HMAC-SHA256 with 240,000 rounds
133. Per-install random salt — identical passcodes hash differently
134. Constant-time comparison
135. Passcode never stored in plaintext
136. One-time recovery key issued at setup
137. Recovery key is case-insensitive and ignores spacing
138. Recovery flow built into the lock screen
139. Change passcode (requires the current one)
140. Disable lock (requires the passcode)
141. Attempt throttling after 5 failures
142. Escalating cooldown, capped at 15 minutes
143. Auto-lock after N idle minutes
144. Lock on app start
145. Optional cover blurring behind the lock screen
146. Optional passcode hint
147. Lock file written with owner-only permissions
148. `mangadl lock status|set|change|off` from the terminal

## Content filters

149. Blocked tags
150. Blocked title words
151. Blocked authors
152. Safe mode drops adult-rated results
153. Hide results with no cover
154. Minimum chapter count filter
155. Filters apply to both GUI and CLI search

## Duplicate handling

156. Cross-source duplicate detection by normalised title
157. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
158. Best-ranked copy survives a merge
159. `also_on` lists the other sources carrying the same series
160. Toggle merging on or off
161. Interleave mode round-robins sources instead of grouping them

## Reading progress

162. Mark individual chapters read or unread
163. Bulk mark a range
164. Percentage progress per series
165. Unread count per series
166. Jump to next unread chapter
167. Last-read chapter remembered
168. Clear progress per series or globally

## Update watching

169. Watch a series for new chapters
170. Watchlist with per-series known chapter count
171. Parallel update checking across all watched series
172. New-chapter counts per series
173. Acknowledge updates to reset the badge
174. Progress callback while checking
175. Failing sites are skipped, not fatal
176. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

177. Free-text note per series
178. 0–5 star rating, clamped
179. Custom tags per series
180. Filter by minimum rating
181. Named collections
182. Add / remove series in a collection
183. Duplicate-safe collection inserts

## Statistics and insights

184. Total chapters, pages, bytes and time
185. Per-source statistics
186. Per-day statistics
187. Average pages per second
188. Busiest day and top source
189. Human-readable sizes and durations
190. Library insights: series, chapters, pages, disk use
191. Largest and most recent series
192. Statistics recorded automatically after every download
193. Stat tiles in GUI settings
194. `mangadl stats` in the terminal
195. Reset statistics

## Search history

196. Every search recorded with source and hit count
197. Duplicate queries collapse to the newest
198. Type-ahead suggestions from history
199. Prefix matches ranked above substring matches
200. Remove a single entry or clear all
201. Capped at 500 entries
202. `mangadl history` / `mangadl history clear`

## Download queue

203. Persistent job queue
204. Reorder queued jobs
205. Per-job status: pending, running, done, failed, paused
206. Progress and error recorded per job
207. Fetch the next pending job
208. Remove one job or clear by status

## Import, export, backup

209. Export library as JSON
210. Export library as CSV
211. Export library as Markdown table
212. Import a previously exported library
213. Merge or replace on import
214. Snapshots of library + bookmarks + config
215. Restore any snapshot
216. Last 20 snapshots retained
217. `mangadl export <file> [format]`

## Disk maintenance

218. Per-series disk usage report
219. Duplicate file scan by SHA-256, size-bucketed for speed
220. Wasted-space total
221. Orphan detection for missing files and folders
222. Bulk delete chosen files
223. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

224. Correct cover URLs in three sizes
225. Per-volume and localised cover listing
226. Reference expansion so covers arrive in one request
227. Translation language selection
228. Preferred scanlation group
229. Automatic dedupe of multiple releases per chapter
230. Alternatives recorded on the chosen release
231. Data-saver mode
232. Externally hosted chapters filtered out
233. Paginated feed with the 10k offset cap handled
234. All content ratings requested explicitly

## Discovery: trending and genres

235. Pressing Search with an empty box shows trending instead of doing nothing
236. GUI opens on a trending feed rather than a blank page
237. TUI opens on a trending feed
238. `mangadl search` with no query lists trending
239. `mangadl trending` explicit discovery command
240. `mangadl trending <genre>` for per-genre trending
241. `mangadl genres` lists every genre and which sites offer it
242. `-g/--genre` filters any search by genre
243. Genre dropdown in the GUI filter row
244. Quick-pick genre chips for the ten most widely supported genres
245. Genre dropdown in the TUI beside the source picker
246. Genres merged across every enabled source
247. Case-insensitive genre matching across sites
248. Genres ordered by how widely they are supported
249. Per-source genre id mapping kept alongside the shared label
250. Genre list reflects only the sources you have enabled
251. Trending results interleave sources so the first screen is a mix
252. `Load more` pagination in the GUI
253. Per-source browse sort options exposed to the UI
254. MangaDex trending via follower count
255. MangaDex genre browsing by resolved tag UUID
256. MangaDex tag names resolved case-insensitively, with partial matching
257. Raw MangaDex tag UUIDs accepted directly
258. MangaDex tag list cached per process
259. Mangakatana genre browsing over 46 genre slugs
260. Mangakatana pagination via the site's real filter path
261. Natomanga hot / latest / new discovery feeds
262. Natomanga genre browsing with paging
263. Weeb Central trending via popularity sort
264. Weeb Central genre browsing over 26 tags
265. Sources that cannot browse are skipped, with a clear message
266. Type-ahead search suggestions drawn from history
267. Empty results explain what to try next instead of just saying "none"
268. Browse honours source ranking and exclusions
269. Browse results pass through content filters and duplicate merging

## Robust calling

270. Circuit breaker per source, with closed / open / half-open states
271. Repeated failures open the breaker so a dead site is skipped instantly
272. Half-open probe after cooldown, closing again on success
273. Cooldown doubles with each repeated trip, capped
274. Success resets the failure count
275. Bounded retries with exponential backoff
276. Proportional jitter so retries do not synchronise
277. `retry_if` hook to skip pointless retries such as 404s
278. `on_retry` callback for progress reporting
279. TTL cache for discovery listings, five minutes
280. TTL cache for genre lists, one hour
281. Cache eviction when full, with hit-rate statistics
282. `call_safely` runs anything and falls back instead of raising
283. `gather` runs many calls in parallel and keeps whatever succeeds
284. Overall timeout support in `gather`, keeping finished work
285. Rate-limit headers honoured, absolute and relative
286. Partial results always returned rather than failing the whole request
287. Every failure logged once with context
288. `mangadl health` shows breaker state and cache hit rates
289. Health diagnostics exposed to the GUI

## Custom dropdowns

290. Themed dropdowns replacing unstyleable native select popups
291. Native `<select>` kept in the DOM as the source of truth
292. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
293. `value` setter wrapped so programmatic assignment repaints the trigger
294. MutationObserver picks up rebuilt option lists automatically
295. Real `change` and `input` events dispatched on selection
296. No event fired when reselecting the current value
297. Panel portalled to `<body>`, so no ancestor can clip it
298. Flips above the trigger when there is no room below
299. Repositions on scroll and resize
300. Type-to-filter box appears automatically past eight options
301. "No matches" state when a filter excludes everything
302. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
303. Typeahead on the closed trigger, like a native select
304. Only one panel open at a time
305. Closes on outside click
306. ARIA combobox/listbox roles with active-descendant tracking
307. Checkmark and accent colour on the selected row
308. Follows every theme and accent via CSS custom properties
309. Honours `prefers-reduced-motion`
310. Disabled selects reflected on the trigger
311. Enhancement failures are caught so styling can never break the page
312. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

313. Updates tab: watchlist with per-series new-chapter counts
314. Rail badge showing how many watched series have updates
315. One-click "Check now" runs every watched series in parallel
316. Watch / unwatch button on the manga page
317. Insights tab: six headline metrics at a glance
318. Per-source bar chart of downloaded chapters
319. Fourteen-day activity sparkline
320. Biggest series and recently downloaded lists
321. Tools tab with five sub-panels
322. Disk usage per series, largest first
323. Duplicate file scan with wasted-space total
324. Orphan detection for library entries whose files vanished
325. Source health panel showing live circuit-breaker state
326. Searchable history panel; click an entry to re-run it
327. `callApi` wrapper so a missing endpoint cannot blank a tab
328. GitHub-style landing page built on Primer design tokens
329. Real light and dark modes, remembered in localStorage
330. Five deep-linkable page tabs with working back/forward
331. Screenshot gallery with GUI and TUI sub-tabs
332. Copy-to-clipboard install commands with success feedback
333. Language breakdown bar computed from the real repository
334. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

335. Omega Scans source via its JSON API
336. Omega Scans coin-locked chapters detected and skipped
337. ManhwaRead source, decoding base64 page data
338. ManhwaRead per-chapter Referer so its CDN serves images
339. Manhwa18 source, flagged adult-only
340. Adult sources tagged so Safe mode removes them automatically
341. `18+` chip on adult sources in the ranking list
342. Toggle switches render correctly (CSS selector matched no markup)
343. Both switch markup variants supported, markup normalised
344. Disabled source rows keep their toggle legible and clickable
345. Off-state switch has real contrast against the row
346. Settings text, number and password inputs themed
347. Focus ring on settings inputs
348. Number spinners removed for visual consistency
349. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

350. Output files are named by the chapters they contain
351. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
352. Bundled files name their own range, e.g. "Chapters 011-020"
353. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
354. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
355. Heavily fragmented picks truncate to "001-013 (7 chapters)"
356. New {chapters} and {count} filename placeholders
357. Legacy "{title}" templates migrated forward automatically
358. Custom templates are never overwritten by the migration
359. Bad templates fall back instead of crashing the download
360. Library verification reports entries whose files have gone
361. Moved folders detected by matching folder name under a root
362. Proposals are inert until confirmed, so a wrong guess is harmless
363. Re-linking rewrites both the directory and every output path
364. Download history, title and source survive a re-link
365. "Pick new downloads folder" adopts a new root and re-links in one step
366. Moved files panel in the Tools tab
367. `mangadl library verify|scan|move` from the terminal
368. Extra library search roots remembered in settings
369. Minimum and maximum chapter number filters
370. Filter chapters by name text
371. Sort chapters newest-first or oldest-first
372. Hide already-downloaded chapters
373. Count pill shows "visible / total" while filtering
374. A note reports how many chapters a filter is hiding
375. Bulk select buttons act only on visible chapters
376. "Latest" picks the highest-numbered visible chapter
377. Filters change only the display, never the selection keys
378. One-click reset for all chapter filters

## Stability and polish

379. Window close no longer crashes with "unhashable type: 'dict'"
380. Cover mirrors: a failing CDN host falls back to a sibling automatically
381. Covers walk every mirror before showing a fallback tile
382. Passcode gates the app before any data is fetched or painted
383. Boot pauses until the lock screen is dismissed
384. Corner radii snap to a four-step scale instead of 13 ad-hoc values
385. Download location saved to settings.json when chosen
386. Download location saved when typed directly
387. Both folder fields stay in sync

## Square mode, rail and lock polish

388. Square corners mode: turn off all rounding in one switch
389. Square mode flattens pills, fields, dropdowns and switches
390. True circles (spinner, lock badge) stay round in square mode
391. Corner preference saved and restored
392. Side rail is narrower by default
393. Expand button widens the rail and reveals labels
394. Rail state remembered between runs
395. Lock overlay paints on the very first frame
396. Remembered lock state avoids a needless overlay flash
397. Fail-safe timer means the overlay can never strand the app
398. Show/hide passcode button
399. Remaining-attempts counter with warning colours
400. Wrong passcode shakes the panel
401. Live cooldown countdown that disables the field
402. Enter reliably submits a search
403. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

404. Empty-but-200 throttle responses are retried instead of accepted
405. Multi-source search no longer loses sources silently
406. Minimum chapter-count filter
407. Maximum chapter-count filter
408. Chapter counts read from count, last_chapter or the newest label
409. Unknown chapter counts are never filtered out
410. Webtoons source with episode paging
411. Webtoons per-chapter Referer for its hotlink-protected CDN
412. nhentai source, flagged adult-only
413. nhentai thumbnails resolved to full-size pages
414. Twenty-three sources total
415. nhentai browses `/popular` (the site root lists no galleries at all)
416. nhentai genre slugs verified against the live site
417. nhentai covers follow the site's own `data-fallbacks` chain
418. Cover proxy for hotlink-protected CDNs, inlined as data URIs
419. Webtoons covers load in the GUI despite the global `no-referrer`
420. Natomanga cover host is never rewritten (shards, not mirrors)
421. Transient cover failures retry the same URL instead of another host
422. Mangadass source, flagged adult-only
423. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
424. Mangadass chapters sorted numerically, not by document order
425. Manga18.club source, flagged adult-only
426. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
427. Manga18.club pages decoded from the base64 `slides_p_path` array
428. HentaiAkane source, flagged adult-only
429. HentaiAkane pages read from the `ts_reader.run` payload
430. ManhwaRead decodes base64 page lists that ship without padding
431. Connection pool sized to the worker count (no discarded connections)
432. Download cart: queue several manga and keep browsing
433. Concurrent downloads of different manga, configurable 1-5
434. Every progress event is stamped with its job, so chapters never mix
435. Chapter rows show the owning manga when several downloads run
436. Queue panel with per-job status and removable pending entries
437. Stop one download without touching the others
438. A cancelled job reports "stopped", not "failed"
439. Multi-genre search: combine genres with AND or OR
440. Genre chips toggle, building a selection instead of replacing it
441. Picked genres shown as removable chips with a Clear button
442. Genre intersection computed per source, never across sites
443. Library keys normalised (scheme, www, query, fragment)
444. Downloaded chapters matched by number, tolerating changed dates
445. Downloaded pill and highlighted rows can no longer disagree
446. URLs with tracking parameters no longer return zero chapters
447. Manhwa18 genre browsing fixed (/webtoon-genre/)
448. nhentai falls back to search for genres it does not have as tags
449. Content fills the window instead of a fixed centred column
450. Keyboard shortcuts with a searchable `?` help overlay
451. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
452. Shortcuts ignored while typing and while the lock screen is up
453. Invert chapter selection, on visible rows only
454. Copy title and link, with a clipboard fallback for WebView2
455. Refresh the current view with `r`
456. Bookmark and library covers load through the proxy (hotlinked CDNs)
457. Bookmarks store an openable URL, not the normalised key
458. Download queue visible before any job starts
459. Series type classified from origin language and tags
460. Type filter (Manga / Manhwa / Manhua) actually narrows results
461. Per-source default type for sites with a single-type catalogue
462. Square corners reach progress bars, the search box and every pill
463. Strict chapter range option, for hiding unknown chapter counts
464. Source picker removed from search filters (it lives in Settings)
465. Advanced info panel: year, status, type, language, demographic, authors
466. Custom result column count, 0 = fit the window
467. Bookmark folders with create, rename and delete
468. File bookmarks by dragging them onto a folder
469. Folder picker when bookmarking, or save straight to the root
470. Optional per-folder lock and blurred covers
471. Folder cover is the first book added to it
472. Deleting a folder keeps its bookmarks, moving them back to the root
473. Text-input modal that distinguishes cancel from an empty value
474. Keyboard shortcuts listed in Settings, not only in a popup
475. Overlay buttons bind reliably (markup declared before the script)
476. Dialog text inputs themed to match the rest of the app
477. Lock screen and recovery fields use the app font
478. Bookmark covers no longer hijack the drag gesture
479. Floating drop zones appear while dragging a bookmark
480. Drop a bookmark back to All bookmarks, or straight into a new folder
481. Drop highlight survives the pointer crossing child elements
482. A missed drop never navigates the app away
483. All configuration in one `config.json` (settings + sources)
484. Settings written atomically, so a crash cannot reset them
485. Concurrent saves cannot clobber each other
486. Pre-1.4.11 `settings.json` migrated automatically
487. Every bridge endpoint returns errors as data, never raises
488. A malformed queue entry cannot kill the download worker thread
489. Download options coerced from UI values instead of trusted
490. Cover cache bounded by bytes with LRU eviction
491. Global JS error handlers clear spinners and surface a message
492. Search/browse failures show a retry instead of a dead screen
493. `mangadl menu` — progressive numbered interface, no extra dependencies
494. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
495. Menu covers search, trending, URLs, library, bookmarks, settings, tools
496. Menu exits cleanly on EOF or a non-terminal stdin
497. `mangadl search --type` narrows by manga / manhwa / manhua
498. `mangadl search --status` narrows by publication status
499. `mangadl search -n/--limit` caps the number of results
500. `mangadl search --sort` by title, source, chapters or year, `--reverse`
501. `mangadl search --urls` prints one URL per line for pipes
502. `mangadl search --json` prints machine-readable results
503. `mangadl search --open N` shows details for a numbered result
504. `mangadl search --download N` downloads a numbered result
505. `mangadl tui` explains itself instead of a traceback without Textual
506. Every module runs directly (`py menu.py`) without an import error
507. Redesigned landing page with an original identity, not a code-host clone
508. Landing page ships light and dark themes, remembered between visits

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
