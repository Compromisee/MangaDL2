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
