"""WeebCentral Downloader command line interface.

Default behaviour: download every chapter and pack them into a single CBZ,
sorted into a per-manga folder inside the output directory.

    weebcentral <manga-url>                    one CBZ with all chapters
    weebcentral <manga-url> --per 10           one CBZ per 10 chapters
    weebcentral <manga-url> -c 1-50 -f pdf     chapters 1-50 as a single PDF
    weebcentral search "one piece"             search WeebCentral
    weebcentral info <manga-url>               show manga details and chapters
"""

import argparse
import os
import sys
import threading

# Allow running this file directly (python weebcentral/cli.py)
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import weebcentral  # noqa: F401
    __package__ = "weebcentral"

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .downloader import DownloadEngine, DownloadOptions
from .scraper import WeebCentralScraper

console = Console(highlight=False)

ACCENT = "bright_cyan"
DIM = "grey58"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="weebcentral",
        description="Download manga from weebcentral.com as CBZ, PDF or EPUB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  weebcentral https://weebcentral.com/series/XXXX/name\n"
            "  weebcentral <url> --per 10               one CBZ per 10 chapters\n"
            "  weebcentral <url> -c 1-50 -f pdf         chapters 1-50 as one PDF\n"
            "  weebcentral <url> -c latest              only the newest chapter\n"
            "  weebcentral search \"one piece\"\n"
            "  weebcentral info <url>\n"
            "  weebcentral resume                       resume an interrupted download\n"
            "  weebcentral tui                          full-screen terminal UI\n"
        ),
    )
    parser.add_argument("target", nargs="?", help="manga URL, or a command: search | info | gui | tui | resume")
    parser.add_argument("query", nargs="*", help="arguments for search / info")
    parser.add_argument("-c", "--chapters", default="all", metavar="SEL",
                        help="chapter selection: all | 5 | 1-20 | 1,5,10-20 | 50- | latest | first (default: all)")
    parser.add_argument("-o", "--output", default="downloads", metavar="DIR",
                        help="output directory (default: downloads)")
    parser.add_argument("-f", "--format", default="cbz", choices=["cbz", "pdf", "epub", "images"],
                        help="output format (default: cbz)")
    parser.add_argument("--per", type=int, default=0, metavar="N",
                        help="chapters per output file: 0 = everything in one file, 1 = one file per chapter, N = N chapters per file (default: 0)")
    parser.add_argument("--also", action="append", default=[], choices=["cbz", "pdf", "epub", "images"],
                        metavar="FMT", help="produce an additional format (repeatable)")
    parser.add_argument("--keep-images", action="store_true",
                        help="keep the raw page images after packaging")
    parser.add_argument("-w", "--workers", type=int, default=3, metavar="N",
                        help="concurrent chapter downloads, 1-8 (default: 3)")
    parser.add_argument("--image-workers", type=int, default=6, metavar="N",
                        help="concurrent image downloads per chapter, 1-10 (default: 6)")
    parser.add_argument("--delay", type=float, default=0.5, metavar="S",
                        help="delay between chapters in seconds (default: 0.5)")
    parser.add_argument("--name-single", default="{title}", metavar="TPL",
                        help="filename template for single-file bundles (default: {title})")
    parser.add_argument("--name-chapter", default="{title} - Chapter {chapter}", metavar="TPL",
                        help="template for per-chapter files")
    parser.add_argument("--name-range", default="{title} - Chapters {start}-{end}", metavar="TPL",
                        help="template for chapter-range bundles")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--plain", action="store_true", help="plain log output (no fancy progress UI)")
    return parser


# ------------------------------------------------------------------ commands

def cmd_search(query: str):
    if not query:
        console.print("[red]Provide a search query, e.g.: weebcentral search \"one piece\"[/]")
        return 1
    with console.status(f"Searching for [bold]{query}[/]..."):
        results = WeebCentralScraper().search(query)
    if not results:
        console.print("[yellow]No results found.[/]")
        return 1

    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
    table.add_column("#", style=DIM, justify="right")
    table.add_column("Title")
    table.add_column("URL", style=DIM, overflow="fold")
    for i, r in enumerate(results, 1):
        table.add_row(str(i), r["title"], r["url"])
    console.print(table)
    console.print(f"[{DIM}]Download with: weebcentral <url>[/]")
    return 0


def cmd_info(url: str):
    if not url:
        console.print("[red]Provide a manga URL.[/]")
        return 1
    scraper = WeebCentralScraper()
    with console.status("Fetching manga information..."):
        info = scraper.get_manga_info(url)
        chapters = scraper.get_chapters(url)

    body = []
    if info.get("authors"):
        body.append(f"[{DIM}]Author[/]   {', '.join(info['authors'])}")
    if info.get("status"):
        body.append(f"[{DIM}]Status[/]   {info['status']}")
    if info.get("tags"):
        body.append(f"[{DIM}]Tags[/]     {', '.join(info['tags'])}")
    body.append(f"[{DIM}]Chapters[/] {len(chapters)}")
    if info.get("description"):
        body.append("")
        body.append(info["description"])
    console.print(Panel("\n".join(body), title=f"[bold]{info['title']}[/]",
                        border_style=ACCENT, box=box.ROUNDED))

    if chapters:
        first, last = chapters[0]["name"], chapters[-1]["name"]
        console.print(f"[{DIM}]First:[/] {first}    [{DIM}]Latest:[/] {last}")
    return 0


def cmd_resume(args) -> int:
    """Resume the last interrupted job recorded in the journal."""
    from .downloader import DownloadEngine, DownloadOptions
    from .logs import clear_journal, read_journal

    job = read_journal()
    if not job:
        console.print("[yellow]No interrupted download to resume.[/]")
        return 1
    title = job.get("title", "Unknown manga")
    started = job.get("started", "?")
    console.print(Panel(
        f"[bold]{title}[/]\n[{DIM}]Interrupted job from {started}. "
        f"Completed chapters will be skipped.[/]",
        title="[bold]Resume download[/]", border_style=ACCENT, box=box.ROUNDED))

    if not args.yes:
        try:
            answer = console.input(f"[{ACCENT}]Resume? \\[Y/n][/] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return 130
        if answer and answer not in ("y", "yes"):
            discard = console.input(f"[{DIM}]Discard this job? \\[y/N][/] ").strip().lower()
            if discard in ("y", "yes"):
                clear_journal()
                console.print("Discarded.")
            return 0

    options = DownloadOptions(**job["options"])
    if args.plain:
        return _run_plain(options)
    return _run_rich(options, skip_confirm=True)


def cmd_download(args) -> int:
    options = DownloadOptions(
        url=args.target,
        selection=args.chapters,
        output_dir=args.output,
        format=args.format,
        bundle=max(0, args.per),
        chapter_workers=max(1, min(8, args.workers)),
        image_workers=max(1, min(10, args.image_workers)),
        delay=max(0.0, args.delay),
        keep_images=args.keep_images or args.format == "images" or "images" in args.also,
        extra_formats=[f for f in args.also if f != "images"],
        name_single=args.name_single,
        name_chapter=args.name_chapter,
        name_range=args.name_range,
    )

    if args.plain:
        return _run_plain(options)
    return _run_rich(options, skip_confirm=args.yes)


def _run_plain(options) -> int:
    def on_event(event):
        t = event["type"]
        if t == "status":
            print(event["message"])
        elif t == "plan":
            print(f"{event['title']}: {event['total']} chapters -> {event['directory']}")
        elif t == "chapter_done":
            print(f"[{event['completed']}/{event['total']}] {event['chapter']} ({event['pages']} pages)")
        elif t == "chapter_failed":
            print(f"FAILED: {event['chapter']}")
        elif t == "packaged":
            print(f"Created: {event['file']}")
        elif t == "error":
            print(f"ERROR: {event['message']}", file=sys.stderr)

    result = DownloadEngine(options, on_event).run()
    return 0 if result.get("ok") else 1


def _run_rich(options, skip_confirm=False) -> int:
    scraper = WeebCentralScraper()
    with console.status("Fetching manga information..."):
        try:
            info = scraper.get_manga_info(options.url)
            chapters = scraper.get_chapters(options.url)
        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            return 1

    from .utils import parse_selection
    try:
        selected = parse_selection(options.selection, chapters)
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        return 1
    if not selected:
        console.print("[red]Selection matched no chapters.[/]")
        return 1

    if options.bundle == 0:
        bundle_desc = "everything in one file"
    elif options.bundle == 1:
        bundle_desc = "one file per chapter"
    else:
        bundle_desc = f"{options.bundle} chapters per file"

    fmt_desc = options.format.upper()
    if options.extra_formats:
        fmt_desc += " + " + " + ".join(f.upper() for f in options.extra_formats)

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style=DIM)
    summary.add_column()
    summary.add_row("Manga", f"[bold]{info['title']}[/]")
    summary.add_row("Chapters", f"{len(selected)} of {len(chapters)}  ({selected[0]['name']} to {selected[-1]['name']})")
    summary.add_row("Format", fmt_desc)
    summary.add_row("Bundling", bundle_desc)
    summary.add_row("Output", options.output_dir)
    console.print(Panel(summary, title="[bold]Download plan[/]", border_style=ACCENT, box=box.ROUNDED))

    if not skip_confirm:
        try:
            answer = console.input(f"[{ACCENT}]Proceed? \\[Y/n][/] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return 130
        if answer and answer not in ("y", "yes"):
            console.print("Cancelled.")
            return 0

    progress = Progress(
        SpinnerColumn(style=ACCENT),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30, complete_style=ACCENT),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    overall = progress.add_task("[bold]Overall", total=len(selected))
    chapter_tasks = {}
    lock = threading.Lock()
    result_holder = {}

    def on_event(event):
        t = event["type"]
        with lock:
            if t == "chapter_start":
                chapter_tasks[event["chapter"]] = progress.add_task(
                    f"  {event['chapter']}", total=None)
            elif t == "chapter_progress":
                task = chapter_tasks.get(event["chapter"])
                if task is not None:
                    progress.update(task, total=event["total"], completed=event["done"])
            elif t == "chapter_done":
                task = chapter_tasks.pop(event["chapter"], None)
                if task is not None:
                    progress.remove_task(task)
                progress.advance(overall)
                progress.console.print(
                    f"  [{ACCENT}]done[/] {event['chapter']} [{DIM}]({event['pages']} pages)[/]")
            elif t == "chapter_failed":
                task = chapter_tasks.pop(event["chapter"], None)
                if task is not None:
                    progress.remove_task(task)
                progress.advance(overall)
                progress.console.print(f"  [red]failed[/] {event['chapter']}")
            elif t == "packaging":
                progress.console.print(f"  [{DIM}]packing {event['file']}[/]")
            elif t == "packaged":
                progress.console.print(f"  [{ACCENT}]created[/] {event['file']}")
            elif t == "error":
                progress.console.print(f"[red]Error:[/] {event['message']}")

    engine = DownloadEngine(options, on_event)
    try:
        with progress:
            result = engine.run()
            result_holder.update(result)
    except KeyboardInterrupt:
        engine.stop()
        console.print("\n[yellow]Stopped by user.[/]")
        return 130

    if result_holder.get("ok"):
        lines = [f"Downloaded [bold]{result_holder['downloaded']}[/] chapters to "
                 f"[bold]{result_holder['directory']}[/]"]
        for out in result_holder.get("outputs", []):
            lines.append(f"[{DIM}]{out}[/]")
        if result_holder.get("failed"):
            lines.append(f"[red]{len(result_holder['failed'])} chapters failed:[/] "
                         + ", ".join(result_holder["failed"][:8]))
        console.print(Panel("\n".join(lines), title="[bold]Complete[/]",
                            border_style=ACCENT, box=box.ROUNDED))
        return 0
    return 1


# ---------------------------------------------------------------------- main

def main(argv=None):
    from .logs import setup_logging
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.target:
        parser.print_help()
        return 0

    command = args.target.lower()
    if command == "search":
        return cmd_search(" ".join(args.query))
    if command == "info":
        return cmd_info(args.query[0] if args.query else "")
    if command == "gui":
        from .gui import run_gui
        return run_gui()
    if command == "tui":
        from .tui import run_tui
        return run_tui()
    if command == "resume":
        return cmd_resume(args)

    if "weebcentral" not in args.target:
        console.print("[red]That does not look like a WeebCentral URL.[/]")
        console.print(f"[{DIM}]Try: weebcentral search \"manga name\"[/]")
        return 1
    return cmd_download(args)


if __name__ == "__main__":
    sys.exit(main())
