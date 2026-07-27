"""Download engine: orchestrates scraping, image downloads and packaging.

Emits structured events through a callback so both the CLI and the GUI can
render progress however they like.
"""

import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from threading import Lock

from .packager import EXTENSIONS, PACKAGERS
from .scraper import WeebCentralScraper
from . import library
from .utils import (
    chapter_number,
    chunk,
    format_chapter_number,
    parse_selection,
    sanitize,
)

logger = logging.getLogger(__name__)


@dataclass
class DownloadOptions:
    url: str = ""
    selection: str = "all"          # chapter selection string, see utils.parse_selection
    output_dir: str = "downloads"
    format: str = "cbz"             # cbz | pdf | epub | images
    bundle: int = 0                 # 0 = everything in one file, N = N chapters per file
    chapter_workers: int = 3        # concurrent chapters
    image_workers: int = 6          # concurrent images per chapter
    delay: float = 0.5              # polite delay between chapters (seconds)
    keep_images: bool = False       # keep raw images after packaging
    retries: int = 5                # retries per image download
    extra_formats: list = field(default_factory=list)  # additional formats to produce
    # naming templates; placeholders: {title} {chapter} {start} {end}
    name_single: str = "{title}"
    name_chapter: str = "{title} - Chapter {chapter}"
    name_range: str = "{title} - Chapters {start}-{end}"


class DownloadEngine:
    """Runs one manga download job."""

    def __init__(self, options: DownloadOptions, on_event=None):
        self.opt = options
        self.on_event = on_event or (lambda event: None)
        self.scraper = WeebCentralScraper(delay=options.delay)
        self._stop = False
        self.failed = []

    # ----------------------------------------------------------------- api

    def stop(self):
        self._stop = True

    def emit(self, type_, **data):
        try:
            self.on_event({"type": type_, **data})
        except Exception:
            pass

    # ----------------------------------------------------------------- run

    def run(self) -> dict:
        """Execute the job. Returns a result summary dict."""
        opt = self.opt
        self.emit("status", message="Fetching manga information")

        info = self.scraper.get_manga_info(opt.url)
        title = sanitize(info["title"])
        self.emit("manga", info=info)

        chapters = self.scraper.get_chapters(opt.url)
        if not chapters:
            self.emit("error", message="No chapters found")
            return {"ok": False, "error": "No chapters found"}

        try:
            selected = parse_selection(opt.selection, chapters)
        except ValueError as e:
            self.emit("error", message=str(e))
            return {"ok": False, "error": str(e)}

        if not selected:
            self.emit("error", message="Selection matched no chapters")
            return {"ok": False, "error": "Selection matched no chapters"}

        manga_dir = os.path.join(opt.output_dir, title)
        raw_dir = os.path.join(manga_dir, "raw")
        os.makedirs(manga_dir, exist_ok=True)

        self.emit("plan", title=title, total=len(selected),
                  chapters=[c["name"] for c in selected], directory=manga_dir)

        # Cover
        if info.get("cover"):
            ext = os.path.splitext(info["cover"].split("?")[0])[1] or ".jpg"
            cover_path = os.path.join(manga_dir, f"cover{ext}")
            if not os.path.exists(cover_path):
                self.scraper.download_file(info["cover"], cover_path, referer=opt.url)

        # Checkpoint of completed chapters (crash-safe resume).
        # v2 format: "name<TAB>pages"; legacy lines (name only) still accepted.
        checkpoint = os.path.join(manga_dir, ".checkpoint")
        done_pages = {}   # chapter name -> expected page count (0 = unknown)
        if os.path.exists(checkpoint):
            with open(checkpoint, encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line.strip():
                        continue
                    name, _, pages = line.partition("\t")
                    try:
                        done_pages[name] = int(pages)
                    except ValueError:
                        done_pages[name] = 0

        def chapter_complete_on_disk(name):
            """True if a previous run fully downloaded this chapter."""
            expected = done_pages.get(name)
            if expected is None:
                return False
            target = os.path.join(raw_dir, sanitize(name))
            if not os.path.isdir(target):
                return False
            have = [f for f in os.listdir(target)
                    if not f.endswith(".part") and os.path.getsize(
                        os.path.join(target, f)) > 0]
            return len(have) >= expected > 0

        # Journal: mark this job as in progress so a crash can offer resume
        from . import logs as _logs
        _logs.write_journal(asdict(opt), {
            "title": info["title"], "directory": manga_dir,
            "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        # ------------------------------------------------------- download
        chapter_dirs = {}  # chapter name -> images dir
        completed = 0
        checkpoint_lock = Lock()

        def worker(chapter):
            if self._stop:
                return chapter, 0, None
            name = chapter["name"]
            target = os.path.join(raw_dir, sanitize(name))

            # Fast path: fully present from a previous (crashed) run
            if chapter_complete_on_disk(name):
                pages = done_pages.get(name, 0)
                self.emit("chapter_start", chapter=name)
                self.emit("chapter_progress", chapter=name, done=pages, total=pages)
                logger.info("Resuming: '%s' already complete (%d pages)", name, pages)
                return chapter, pages, target

            os.makedirs(target, exist_ok=True)
            self.emit("chapter_start", chapter=name)

            urls = self.scraper.get_chapter_images(chapter["url"])
            if not urls:
                return chapter, 0, None

            got = 0
            with ThreadPoolExecutor(max_workers=self.opt.image_workers) as pool:
                futures = {}
                for i, url in enumerate(urls, 1):
                    ext = os.path.splitext(url.split("?")[0])[1].lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                        ext = ".jpg"
                    path = os.path.join(target, f"{i:03d}{ext}")
                    if os.path.exists(path) and os.path.getsize(path) > 0:
                        got += 1
                        self.emit("chapter_progress", chapter=name, done=got, total=len(urls))
                        continue
                    futures[pool.submit(
                        self.scraper.download_file, url, path, chapter["url"],
                        self.opt.retries,
                    )] = url
                for future in as_completed(futures):
                    if self._stop:
                        break
                    if future.result():
                        got += 1
                        self.emit("chapter_progress", chapter=name, done=got, total=len(urls))

            # Only a COMPLETE chapter counts; partial ones will be resumed
            # next run (existing images are skipped, missing ones refetched).
            if got == len(urls):
                return chapter, got, target
            if got:
                logger.warning("Chapter '%s' incomplete: %d/%d pages "
                               "(will resume next run)", name, got, len(urls))
            return chapter, 0, None

        with ThreadPoolExecutor(max_workers=max(1, opt.chapter_workers)) as pool:
            futures = [pool.submit(worker, c) for c in selected]
            for future in as_completed(futures):
                if self._stop:
                    break
                chapter, got, target = future.result()
                name = chapter["name"]
                if target:
                    chapter_dirs[name] = target
                    completed += 1
                    if done_pages.get(name, 0) < got:
                        with checkpoint_lock:
                            done_pages[name] = got
                            with open(checkpoint, "a", encoding="utf-8") as f:
                                f.write(f"{name}\t{got}\n")
                                f.flush()
                                os.fsync(f.fileno())
                    try:
                        library.record_chapter(
                            opt.url, info["title"], name, pages=got,
                            cover=info.get("cover"), directory=manga_dir,
                        )
                    except Exception:
                        logger.debug("Failed to record chapter in library", exc_info=True)
                    self.emit("chapter_done", chapter=name, pages=got,
                              completed=completed, total=len(selected))
                elif not self._stop:
                    self.failed.append(chapter)
                    self.emit("chapter_failed", chapter=name)
                time.sleep(opt.delay)

        if self._stop:
            self.emit("stopped")
            _logs.clear_journal()
            return {"ok": False, "stopped": True}

        # -------------------------------------------------------- package
        ordered = [
            (chapter_dirs[c["name"]], c["name"])
            for c in sorted(selected, key=lambda c: chapter_number(c["name"]))
            if c["name"] in chapter_dirs
        ]

        outputs = []
        formats = [opt.format] + [f for f in opt.extra_formats if f != opt.format]
        formats = [f for f in dict.fromkeys(formats) if f in PACKAGERS or f == "images"]

        for fmt in formats:
            if fmt == "images":
                continue
            outputs += self._package(fmt, ordered, manga_dir, title)

        keep = opt.keep_images or "images" in formats or not outputs
        if not keep and os.path.isdir(raw_dir):
            shutil.rmtree(raw_dir, ignore_errors=True)
            try:
                os.remove(checkpoint)
            except OSError:
                pass

        if outputs:
            try:
                library.record_outputs(opt.url, outputs)
            except Exception:
                logger.debug("Failed to record outputs in library", exc_info=True)

        _logs.clear_journal()

        self.emit("done", downloaded=completed, failed=len(self.failed),
                  outputs=outputs, directory=manga_dir)
        return {
            "ok": True,
            "title": title,
            "directory": manga_dir,
            "downloaded": completed,
            "failed": [c["name"] for c in self.failed],
            "outputs": outputs,
        }

    # ------------------------------------------------------------- helpers

    def _package(self, fmt, ordered, manga_dir, title):
        """Package chapters into one or more volume files. Returns output paths."""
        if not ordered:
            return []
        packager = PACKAGERS[fmt]
        ext = EXTENSIONS[fmt]
        outputs = []

        def render(template, fallback, **kw):
            try:
                name = template.format(**kw).strip()
                return name or fallback.format(**kw)
            except (KeyError, IndexError, ValueError):
                return fallback.format(**kw)

        groups = chunk(ordered, self.opt.bundle)
        for group in groups:
            if len(groups) == 1:
                label = render(self.opt.name_single, "{title}", title=title)
            elif len(group) == 1:
                num = format_chapter_number(chapter_number(group[0][1]))
                label = render(self.opt.name_chapter, "{title} - Chapter {chapter}",
                               title=title, chapter=num)
            else:
                lo = format_chapter_number(chapter_number(group[0][1]))
                hi = format_chapter_number(chapter_number(group[-1][1]))
                label = render(self.opt.name_range, "{title} - Chapters {start}-{end}",
                               title=title, start=lo, end=hi)

            out_path = os.path.join(manga_dir, sanitize(label) + ext)
            self.emit("packaging", format=fmt, file=os.path.basename(out_path))
            result = packager(group, out_path, label)
            if result:
                outputs.append(result)
                self.emit("packaged", format=fmt, file=result)
        return outputs
