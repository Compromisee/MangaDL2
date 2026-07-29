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

## Source ranking and exclusion

16. Drag-and-drop source ranking in the GUI
17. Move up / down buttons as a keyboard-friendly alternative
18. Rank order decides which copy wins when a series exists on several sites
19. Toggle a source off to exclude its results entirely
20. Excluded sources still work from a direct URL
21. `search_enabled` — keep a source usable but out of multi-source search
22. Per-source result limit override
23. Per-source weight for duplicate scoring
24. Per-source language override
25. Per-source extra delay for politeness
26. Free-text note per source
27. Ranking is shared by CLI, GUI and TUI
28. New sources are auto-appended, ranked last
29. Stale config entries are pruned automatically
30. `mangadl config` shows the full table
31. `mangadl config enable|disable <source>`
32. `mangadl config up|down <source>`
33. `mangadl config rank <a> <b> ...` to set the whole order
34. `mangadl config reset`
35. Sources tab in the TUI with the same controls

## Provider attribution

36. Provider shown directly beneath the manga title in the GUI
37. Colour-coded provider dot per source
38. "Open on source site" link next to the provider name
39. Provider line under the title in the TUI
40. Provider line in `mangadl info`
41. Source badges on GUI search result cards
42. Source column in CLI search results
43. Source tag in TUI search results
44. Source recorded on every library entry
45. Source recorded on every bookmark
46. Source stamped on download results and plan events

## Passcode lock

47. Optional app passcode
48. PBKDF2-HMAC-SHA256 with 240,000 rounds
49. Per-install random salt — identical passcodes hash differently
50. Constant-time comparison
51. Passcode never stored in plaintext
52. One-time recovery key issued at setup
53. Recovery key is case-insensitive and ignores spacing
54. Recovery flow built into the lock screen
55. Change passcode (requires the current one)
56. Disable lock (requires the passcode)
57. Attempt throttling after 5 failures
58. Escalating cooldown, capped at 15 minutes
59. Auto-lock after N idle minutes
60. Lock on app start
61. Optional cover blurring behind the lock screen
62. Optional passcode hint
63. Lock file written with owner-only permissions
64. `mangadl lock status|set|change|off` from the terminal

## Content filters

65. Blocked tags
66. Blocked title words
67. Blocked authors
68. Safe mode drops adult-rated results
69. Hide results with no cover
70. Minimum chapter count filter
71. Filters apply to both GUI and CLI search

## Duplicate handling

72. Cross-source duplicate detection by normalised title
73. Decorations stripped when matching (Colored, Official, Doujinshi, brackets)
74. Best-ranked copy survives a merge
75. `also_on` lists the other sources carrying the same series
76. Toggle merging on or off
77. Interleave mode round-robins sources instead of grouping them

## Reading progress

78. Mark individual chapters read or unread
79. Bulk mark a range
80. Percentage progress per series
81. Unread count per series
82. Jump to next unread chapter
83. Last-read chapter remembered
84. Clear progress per series or globally

## Update watching

85. Watch a series for new chapters
86. Watchlist with per-series known chapter count
87. Parallel update checking across all watched series
88. New-chapter counts per series
89. Acknowledge updates to reset the badge
90. Progress callback while checking
91. Failing sites are skipped, not fatal
92. `mangadl watch list|add|remove|check`

## Notes, ratings, collections

93. Free-text note per series
94. 0–5 star rating, clamped
95. Custom tags per series
96. Filter by minimum rating
97. Named collections
98. Add / remove series in a collection
99. Duplicate-safe collection inserts

## Statistics and insights

100. Total chapters, pages, bytes and time
101. Per-source statistics
102. Per-day statistics
103. Average pages per second
104. Busiest day and top source
105. Human-readable sizes and durations
106. Library insights: series, chapters, pages, disk use
107. Largest and most recent series
108. Statistics recorded automatically after every download
109. Stat tiles in GUI settings
110. `mangadl stats` in the terminal
111. Reset statistics

## Search history

112. Every search recorded with source and hit count
113. Duplicate queries collapse to the newest
114. Type-ahead suggestions from history
115. Prefix matches ranked above substring matches
116. Remove a single entry or clear all
117. Capped at 500 entries
118. `mangadl history` / `mangadl history clear`

## Download queue

119. Persistent job queue
120. Reorder queued jobs
121. Per-job status: pending, running, done, failed, paused
122. Progress and error recorded per job
123. Fetch the next pending job
124. Remove one job or clear by status

## Import, export, backup

125. Export library as JSON
126. Export library as CSV
127. Export library as Markdown table
128. Import a previously exported library
129. Merge or replace on import
130. Snapshots of library + bookmarks + config
131. Restore any snapshot
132. Last 20 snapshots retained
133. `mangadl export <file> [format]`

## Disk maintenance

134. Per-series disk usage report
135. Duplicate file scan by SHA-256, size-bucketed for speed
136. Wasted-space total
137. Orphan detection for missing files and folders
138. Bulk delete chosen files
139. `mangadl disk usage|dupes|orphans`

## MangaDex specifics

140. Correct cover URLs in three sizes
141. Per-volume and localised cover listing
142. Reference expansion so covers arrive in one request
143. Translation language selection
144. Preferred scanlation group
145. Automatic dedupe of multiple releases per chapter
146. Alternatives recorded on the chosen release
147. Data-saver mode
148. Externally hosted chapters filtered out
149. Paginated feed with the 10k offset cap handled
150. All content ratings requested explicitly

## Discovery: trending and genres

151. Pressing Search with an empty box shows trending instead of doing nothing
152. GUI opens on a trending feed rather than a blank page
153. TUI opens on a trending feed
154. `mangadl search` with no query lists trending
155. `mangadl trending` explicit discovery command
156. `mangadl trending <genre>` for per-genre trending
157. `mangadl genres` lists every genre and which sites offer it
158. `-g/--genre` filters any search by genre
159. Genre dropdown in the GUI filter row
160. Quick-pick genre chips for the ten most widely supported genres
161. Genre dropdown in the TUI beside the source picker
162. Genres merged across every enabled source
163. Case-insensitive genre matching across sites
164. Genres ordered by how widely they are supported
165. Per-source genre id mapping kept alongside the shared label
166. Genre list reflects only the sources you have enabled
167. Trending results interleave sources so the first screen is a mix
168. `Load more` pagination in the GUI
169. Per-source browse sort options exposed to the UI
170. MangaDex trending via follower count
171. MangaDex genre browsing by resolved tag UUID
172. MangaDex tag names resolved case-insensitively, with partial matching
173. Raw MangaDex tag UUIDs accepted directly
174. MangaDex tag list cached per process
175. Mangakatana genre browsing over 46 genre slugs
176. Mangakatana pagination via the site's real filter path
177. Natomanga hot / latest / new discovery feeds
178. Natomanga genre browsing with paging
179. Weeb Central trending via popularity sort
180. Weeb Central genre browsing over 26 tags
181. Sources that cannot browse are skipped, with a clear message
182. Type-ahead search suggestions drawn from history
183. Empty results explain what to try next instead of just saying "none"
184. Browse honours source ranking and exclusions
185. Browse results pass through content filters and duplicate merging

## Robust calling

186. Circuit breaker per source, with closed / open / half-open states
187. Repeated failures open the breaker so a dead site is skipped instantly
188. Half-open probe after cooldown, closing again on success
189. Cooldown doubles with each repeated trip, capped
190. Success resets the failure count
191. Bounded retries with exponential backoff
192. Proportional jitter so retries do not synchronise
193. `retry_if` hook to skip pointless retries such as 404s
194. `on_retry` callback for progress reporting
195. TTL cache for discovery listings, five minutes
196. TTL cache for genre lists, one hour
197. Cache eviction when full, with hit-rate statistics
198. `call_safely` runs anything and falls back instead of raising
199. `gather` runs many calls in parallel and keeps whatever succeeds
200. Overall timeout support in `gather`, keeping finished work
201. Rate-limit headers honoured, absolute and relative
202. Partial results always returned rather than failing the whole request
203. Every failure logged once with context
204. `mangadl health` shows breaker state and cache hit rates
205. Health diagnostics exposed to the GUI

## Custom dropdowns

206. Themed dropdowns replacing unstyleable native select popups
207. Native `<select>` kept in the DOM as the source of truth
208. Existing code (`sel.value`, `innerHTML`, `appendChild`) keeps working
209. `value` setter wrapped so programmatic assignment repaints the trigger
210. MutationObserver picks up rebuilt option lists automatically
211. Real `change` and `input` events dispatched on selection
212. No event fired when reselecting the current value
213. Panel portalled to `<body>`, so no ancestor can clip it
214. Flips above the trigger when there is no room below
215. Repositions on scroll and resize
216. Type-to-filter box appears automatically past eight options
217. "No matches" state when a filter excludes everything
218. Full keyboard support: arrows, Home, End, Enter, Escape, Tab
219. Typeahead on the closed trigger, like a native select
220. Only one panel open at a time
221. Closes on outside click
222. ARIA combobox/listbox roles with active-descendant tracking
223. Checkmark and accent colour on the selected row
224. Follows every theme and accent via CSS custom properties
225. Honours `prefers-reduced-motion`
226. Disabled selects reflected on the trigger
227. Enhancement failures are caught so styling can never break the page
228. Opt out per element with `data-no-custom="true"`

## Interface: tabs and landing page

229. Updates tab: watchlist with per-series new-chapter counts
230. Rail badge showing how many watched series have updates
231. One-click "Check now" runs every watched series in parallel
232. Watch / unwatch button on the manga page
233. Insights tab: six headline metrics at a glance
234. Per-source bar chart of downloaded chapters
235. Fourteen-day activity sparkline
236. Biggest series and recently downloaded lists
237. Tools tab with five sub-panels
238. Disk usage per series, largest first
239. Duplicate file scan with wasted-space total
240. Orphan detection for library entries whose files vanished
241. Source health panel showing live circuit-breaker state
242. Searchable history panel; click an entry to re-run it
243. `callApi` wrapper so a missing endpoint cannot blank a tab
244. GitHub-style landing page built on Primer design tokens
245. Real light and dark modes, remembered in localStorage
246. Five deep-linkable page tabs with working back/forward
247. Screenshot gallery with GUI and TUI sub-tabs
248. Copy-to-clipboard install commands with success feedback
249. Language breakdown bar computed from the real repository
250. No fabricated star/fork counts — only verifiable numbers shown

## Added sources and UI fixes

251. Omega Scans source via its JSON API
252. Omega Scans coin-locked chapters detected and skipped
253. ManhwaRead source, decoding base64 page data
254. ManhwaRead per-chapter Referer so its CDN serves images
255. Manhwa18 source, flagged adult-only
256. Adult sources tagged so Safe mode removes them automatically
257. `18+` chip on adult sources in the ranking list
258. Toggle switches render correctly (CSS selector matched no markup)
259. Both switch markup variants supported, markup normalised
260. Disabled source rows keep their toggle legible and clickable
261. Off-state switch has real contrast against the row
262. Settings text, number and password inputs themed
263. Focus ring on settings inputs
264. Number spinners removed for visual consistency
265. Struck-through name on excluded sources

## Filenames, relocation and chapter filters

266. Output files are named by the chapters they contain
267. A single "download all" file reads e.g. "Naruto - Chapters 001-050"
268. Bundled files name their own range, e.g. "Chapters 011-020"
269. Non-contiguous selections collapse into runs: "001-003, 007-008, 020"
270. Half chapters stay inside a run: 10, 10.5, 11 -> "010-011"
271. Heavily fragmented picks truncate to "001-013 (7 chapters)"
272. New {chapters} and {count} filename placeholders
273. Legacy "{title}" templates migrated forward automatically
274. Custom templates are never overwritten by the migration
275. Bad templates fall back instead of crashing the download
276. Library verification reports entries whose files have gone
277. Moved folders detected by matching folder name under a root
278. Proposals are inert until confirmed, so a wrong guess is harmless
279. Re-linking rewrites both the directory and every output path
280. Download history, title and source survive a re-link
281. "Pick new downloads folder" adopts a new root and re-links in one step
282. Moved files panel in the Tools tab
283. `mangadl library verify|scan|move` from the terminal
284. Extra library search roots remembered in settings
285. Minimum and maximum chapter number filters
286. Filter chapters by name text
287. Sort chapters newest-first or oldest-first
288. Hide already-downloaded chapters
289. Count pill shows "visible / total" while filtering
290. A note reports how many chapters a filter is hiding
291. Bulk select buttons act only on visible chapters
292. "Latest" picks the highest-numbered visible chapter
293. Filters change only the display, never the selection keys
294. One-click reset for all chapter filters

## Stability and polish

295. Window close no longer crashes with "unhashable type: 'dict'"
296. Cover mirrors: a failing CDN host falls back to a sibling automatically
297. Covers walk every mirror before showing a fallback tile
298. Passcode gates the app before any data is fetched or painted
299. Boot pauses until the lock screen is dismissed
300. Corner radii snap to a four-step scale instead of 13 ad-hoc values
301. Download location saved to settings.json when chosen
302. Download location saved when typed directly
303. Both folder fields stay in sync

## Square mode, rail and lock polish

304. Square corners mode: turn off all rounding in one switch
305. Square mode flattens pills, fields, dropdowns and switches
306. True circles (spinner, lock badge) stay round in square mode
307. Corner preference saved and restored
308. Side rail is narrower by default
309. Expand button widens the rail and reveals labels
310. Rail state remembered between runs
311. Lock overlay paints on the very first frame
312. Remembered lock state avoids a needless overlay flash
313. Fail-safe timer means the overlay can never strand the app
314. Show/hide passcode button
315. Remaining-attempts counter with warning colours
316. Wrong passcode shakes the panel
317. Live cooldown countdown that disables the field
318. Enter reliably submits a search
319. Themed suggestion list replacing the native datalist

## Aggregator fix, chapter limits and two more sources

320. Empty-but-200 throttle responses are retried instead of accepted
321. Multi-source search no longer loses sources silently
322. Minimum chapter-count filter
323. Maximum chapter-count filter
324. Chapter counts read from count, last_chapter or the newest label
325. Unknown chapter counts are never filtered out
326. Webtoons source with episode paging
327. Webtoons per-chapter Referer for its hotlink-protected CDN
328. nhentai source, flagged adult-only
329. nhentai thumbnails resolved to full-size pages
330. Twelve sources total
331. nhentai browses `/popular` (the site root lists no galleries at all)
332. nhentai genre slugs verified against the live site
333. nhentai covers follow the site's own `data-fallbacks` chain
334. Cover proxy for hotlink-protected CDNs, inlined as data URIs
335. Webtoons covers load in the GUI despite the global `no-referrer`
336. Natomanga cover host is never rewritten (shards, not mirrors)
337. Transient cover failures retry the same URL instead of another host
338. Mangadass source, flagged adult-only
339. Mangadass real `/search?q=` endpoint (`/?s=` ignores the query)
340. Mangadass chapters sorted numerically, not by document order
341. Manga18.club source, flagged adult-only
342. Manga18.club `?search=` endpoint plus an autocomplete-JSON fallback
343. Manga18.club pages decoded from the base64 `slides_p_path` array
344. HentaiAkane source, flagged adult-only
345. HentaiAkane pages read from the `ts_reader.run` payload
346. ManhwaRead decodes base64 page lists that ship without padding
347. Connection pool sized to the worker count (no discarded connections)
348. Download cart: queue several manga and keep browsing
349. Concurrent downloads of different manga, configurable 1-5
350. Every progress event is stamped with its job, so chapters never mix
351. Chapter rows show the owning manga when several downloads run
352. Queue panel with per-job status and removable pending entries
353. Stop one download without touching the others
354. A cancelled job reports "stopped", not "failed"
355. Multi-genre search: combine genres with AND or OR
356. Genre chips toggle, building a selection instead of replacing it
357. Picked genres shown as removable chips with a Clear button
358. Genre intersection computed per source, never across sites
359. Library keys normalised (scheme, www, query, fragment)
360. Downloaded chapters matched by number, tolerating changed dates
361. Downloaded pill and highlighted rows can no longer disagree
362. URLs with tracking parameters no longer return zero chapters
363. Manhwa18 genre browsing fixed (/webtoon-genre/)
364. nhentai falls back to search for genres it does not have as tags
365. Content fills the window instead of a fixed centred column
366. Keyboard shortcuts with a searchable `?` help overlay
367. Two-key navigation chords (g s, g d, g b, g l, g u, g ,)
368. Shortcuts ignored while typing and while the lock screen is up
369. Invert chapter selection, on visible rows only
370. Copy title and link, with a clipboard fallback for WebView2
371. Refresh the current view with `r`
372. Bookmark and library covers load through the proxy (hotlinked CDNs)
373. Bookmarks store an openable URL, not the normalised key
374. Download queue visible before any job starts
375. Series type classified from origin language and tags
376. Type filter (Manga / Manhwa / Manhua) actually narrows results
377. Per-source default type for sites with a single-type catalogue
378. Square corners reach progress bars, the search box and every pill
379. Strict chapter range option, for hiding unknown chapter counts
380. Source picker removed from search filters (it lives in Settings)
381. Advanced info panel: year, status, type, language, demographic, authors
382. Custom result column count, 0 = fit the window
383. Bookmark folders with create, rename and delete
384. File bookmarks by dragging them onto a folder
385. Folder picker when bookmarking, or save straight to the root
386. Optional per-folder lock and blurred covers
387. Folder cover is the first book added to it
388. Deleting a folder keeps its bookmarks, moving them back to the root
389. Text-input modal that distinguishes cancel from an empty value
390. Keyboard shortcuts listed in Settings, not only in a popup
391. Overlay buttons bind reliably (markup declared before the script)
392. Dialog text inputs themed to match the rest of the app
393. Lock screen and recovery fields use the app font
394. Bookmark covers no longer hijack the drag gesture
395. Floating drop zones appear while dragging a bookmark
396. Drop a bookmark back to All bookmarks, or straight into a new folder
397. Drop highlight survives the pointer crossing child elements
398. A missed drop never navigates the app away
399. All configuration in one `config.json` (settings + sources)
400. Settings written atomically, so a crash cannot reset them
401. Concurrent saves cannot clobber each other
402. Pre-1.4.11 `settings.json` migrated automatically
403. Every bridge endpoint returns errors as data, never raises
404. A malformed queue entry cannot kill the download worker thread
405. Download options coerced from UI values instead of trusted
406. Cover cache bounded by bytes with LRU eviction
407. Global JS error handlers clear spinners and surface a message
408. Search/browse failures show a retry instead of a dead screen
409. `mangadl menu` — progressive numbered interface, no extra dependencies
410. Every menu prompt accepts a number; `b` = back, `q` = quit at any depth
411. Menu covers search, trending, URLs, library, bookmarks, settings, tools
412. Menu exits cleanly on EOF or a non-terminal stdin
413. `mangadl search --type` narrows by manga / manhwa / manhua
414. `mangadl search --status` narrows by publication status
415. `mangadl search -n/--limit` caps the number of results
416. `mangadl search --sort` by title, source, chapters or year, `--reverse`
417. `mangadl search --urls` prints one URL per line for pipes
418. `mangadl search --json` prints machine-readable results
419. `mangadl search --open N` shows details for a numbered result
420. `mangadl search --download N` downloads a numbered result
421. `mangadl tui` explains itself instead of a traceback without Textual
422. Every module runs directly (`py menu.py`) without an import error
423. Redesigned landing page with an original identity, not a code-host clone
424. Landing page ships light and dark themes, remembered between visits

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
