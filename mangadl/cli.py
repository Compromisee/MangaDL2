"""MangaDL command line interface.

Downloads manga from several sites (MangaDex, Mangakatana, Natomanga,
Weeb Central). The source is detected automatically from the URL.

Default behaviour: download every chapter and pack them into a single CBZ,
sorted into a per-manga folder inside the output directory.

    mangadl <manga-url>                    one CBZ with all chapters
    mangadl <manga-url> --per 10           one CBZ per 10 chapters
    mangadl <manga-url> -c 1-50 -f pdf     chapters 1-50 as a single PDF
    mangadl search "one piece"             search every source
    mangadl search "one piece" -s mangadex search one source
    mangadl sources                        list supported sites
    mangadl info <manga-url>               show manga details and chapters
"""

import argparse
import os
import sys
import threading

# Allow running this file directly (python mangadl/cli.py)
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import mangadl  # noqa: F401
    __package__ = "mangadl"

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
from .sources import (DEFAULT_SOURCE, SOURCES, detect_source, get_source,
                      list_sources, search_all, source_for_url)

console = Console(highlight=False)

ACCENT = "bright_cyan"
DIM = "grey58"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mangadl",
        description="Download manga from MangaDex, Mangakatana, Natomanga and Weeb Central as CBZ, PDF or EPUB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  mangadl https://mangadex.org/title/<uuid>\n"
            "  mangadl <url> --per 10               one CBZ per 10 chapters\n"
            "  mangadl <url> -c 1-50 -f pdf         chapters 1-50 as one PDF\n"
            "  mangadl <url> -c latest              only the newest chapter\n"
            "  mangadl search \"one piece\"          search all sources\n"
            "  mangadl search \"berserk\" -s mangadex\n"
            "  mangadl sources                          list supported sites\n"
            "  mangadl config disable natomanga         exclude a source\n"
            "  mangadl config up mangakatana            rank a source higher\n"
            "  mangadl stats                            download statistics\n"
            "  mangadl lock set                         set an app passcode\n"
            "  mangadl watch add <url>                  track a series for updates\n"
            "  mangadl watch check                      check every watched series\n"
            "  mangadl disk usage                       disk usage per series\n"
            "  mangadl info <url>\n"
            "  mangadl resume                       resume an interrupted download\n"
            "  mangadl tui                          full-screen terminal UI\n"
        ),
    )
    parser.add_argument("target", nargs="?",
                        help="manga URL, or a command: search | info | sources | config | "
                             "stats | history | lock | export | watch | disk | "
                             "gui | tui | resume")
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
    source_group = parser.add_argument_group("sources")
    source_group.add_argument("-s", "--source", default="", metavar="ID",
                              choices=[""] + list(SOURCES),
                              help="force a source: " + " | ".join(SOURCES)
                                   + " (default: detect from the URL)")
    source_group.add_argument("-l", "--language", default="en", metavar="LANG",
                              help="translation language, MangaDex only (default: en)")
    source_group.add_argument("--scanlator", default="", metavar="NAME",
                              help="preferred scanlation group, MangaDex only")
    source_group.add_argument("--data-saver", action="store_true",
                              help="download compressed pages, MangaDex only")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--plain", action="store_true", help="plain log output (no fancy progress UI)")
    return parser


# ------------------------------------------------------------------ commands

def cmd_sources():
    """List every supported site and what it can do."""
    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
    table.add_column("ID")
    table.add_column("Site")
    table.add_column("URL", style=DIM, overflow="fold")
    table.add_column("Notes", style=DIM)
    for meta in list_sources():
        notes = []
        if meta["supports_language"]:
            notes.append("languages")
        if meta["supports_scanlator"]:
            notes.append("scanlators")
        if meta["needs_flaresolverr"]:
            notes.append("needs FlareSolverr")
        table.add_row(meta["id"], meta["name"], meta["base_url"], ", ".join(notes) or "-")
    console.print(table)
    console.print(f"[{DIM}]Use with: mangadl search \"title\" -s <id>[/]")
    return 0


def cmd_config(args) -> int:
    """Show or change per-source ranking and exclusions."""
    from . import config as appconfig

    rest = [a for a in args.query]
    action = (rest[0].lower() if rest else "show")

    if action in ("enable", "disable", "include", "exclude"):
        if len(rest) < 2:
            console.print("[red]Usage: mangadl config enable|disable <source>[/]")
            return 1
        source_id = rest[1].lower()
        if source_id not in SOURCES:
            console.print(f"[red]Unknown source '{source_id}'[/]")
            return 1
        on = action in ("enable", "include")
        appconfig.set_enabled(source_id, on)
        console.print(f"{SOURCES[source_id].name}: "
                      f"[{ACCENT}]{'enabled' if on else 'excluded'}[/]")
    elif action in ("up", "down"):
        if len(rest) < 2:
            console.print(f"[red]Usage: mangadl config {action} <source>[/]")
            return 1
        appconfig.move(rest[1].lower(), -1 if action == "up" else 1)
    elif action == "rank":
        order = [s.lower() for s in rest[1:]]
        if not order:
            console.print("[red]Usage: mangadl config rank <source> <source> ...[/]")
            return 1
        appconfig.reorder(order)
        console.print("Ranking updated.")
    elif action == "reset":
        appconfig.reset_config()
        console.print("Source configuration reset.")
    elif action != "show":
        console.print(f"[red]Unknown action '{action}'[/]")
        console.print(f"[{DIM}]show | enable | disable | up | down | rank | reset[/]")
        return 1

    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
    table.add_column("#", style=DIM, justify="right")
    table.add_column("ID")
    table.add_column("Site")
    table.add_column("Search", justify="center")
    table.add_column("Status")
    for index, row in enumerate(appconfig.describe(), 1):
        enabled = row.get("enabled", True)
        table.add_row(
            str(index), row["id"], row.get("name", row["id"]),
            "yes" if row.get("search_enabled", True) else "no",
            f"[{ACCENT}]enabled[/]" if enabled else "[red]excluded[/]",
        )
    console.print(table)
    console.print(f"[{DIM}]mangadl config up|down <source>   "
                  f"mangadl config disable <source>[/]")
    return 0


def cmd_stats() -> int:
    from . import features

    stats = features.get_stats()
    totals = stats.get("totals", {})
    derived = stats.get("derived", {})
    if not totals:
        console.print("[yellow]No download statistics yet.[/]")
        return 0

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style=DIM)
    grid.add_column()
    grid.add_row("Downloads", str(totals.get("downloads", 0)))
    grid.add_row("Chapters", str(totals.get("chapters", 0)))
    grid.add_row("Pages", str(totals.get("pages", 0)))
    grid.add_row("Data", derived.get("human_bytes", "-"))
    grid.add_row("Time", derived.get("human_time", "-"))
    grid.add_row("Speed", f"{derived.get('avg_pages_per_second', 0)} pages/s")
    grid.add_row("Top source", derived.get("top_source", "-"))
    console.print(Panel(grid, title="[bold]Statistics[/]",
                        border_style=ACCENT, box=box.ROUNDED))

    per_source = stats.get("sources", {})
    if per_source:
        table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
        table.add_column("Source")
        table.add_column("Chapters", justify="right")
        table.add_column("Pages", justify="right")
        table.add_column("Data", justify="right")
        for name, row in sorted(per_source.items(),
                                key=lambda kv: -kv[1].get("chapters", 0)):
            table.add_row(name, str(row.get("chapters", 0)),
                          str(row.get("pages", 0)),
                          features.human_size(row.get("bytes", 0)))
        console.print(table)
    return 0


def cmd_history(args) -> int:
    from . import features

    rest = [a for a in args.query]
    if rest and rest[0].lower() == "clear":
        features.clear_history()
        console.print("History cleared.")
        return 0
    items = features.get_history(25)
    if not items:
        console.print("[yellow]No search history.[/]")
        return 0
    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
    table.add_column("Query")
    table.add_column("Source", style=DIM)
    table.add_column("Hits", justify="right", style=DIM)
    table.add_column("When", style=DIM)
    for item in items:
        table.add_row(item.get("query", ""), item.get("source", ""),
                      str(item.get("results", 0)), item.get("date", ""))
    console.print(table)
    return 0


def cmd_lock(args) -> int:
    """Manage the app passcode from the terminal."""
    import getpass

    from . import passlock

    rest = [a for a in args.query]
    action = (rest[0].lower() if rest else "status")

    if action == "status":
        status = passlock.status()
        console.print(Panel(
            f"Passcode: [{ACCENT}]{'on' if status['enabled'] else 'off'}[/]\n"
            f"Auto-lock: {status['auto_lock_minutes'] or 'never'}\n"
            f"Recovery key configured: {'yes' if status['has_recovery'] else 'no'}",
            title="[bold]Lock[/]", border_style=ACCENT, box=box.ROUNDED))
        return 0

    if action in ("set", "on", "enable"):
        code = getpass.getpass("New passcode: ")
        if code != getpass.getpass("Confirm passcode: "):
            console.print("[red]Passcodes do not match.[/]")
            return 1
        result = passlock.set_passcode(code)
        if not result.get("ok"):
            console.print(f"[red]{result['error']}[/]")
            return 1
        console.print(Panel(
            f"[bold]{result['recovery_key']}[/]\n\n"
            f"[{DIM}]Store this somewhere safe. It is shown once and is the only "
            f"way back in if you forget the passcode.[/]",
            title="[bold]Recovery key[/]", border_style=ACCENT, box=box.ROUNDED))
        return 0

    if action in ("off", "disable"):
        result = passlock.disable(getpass.getpass("Current passcode: "))
        console.print("Lock disabled." if result.get("ok")
                      else f"[red]{result['error']}[/]")
        return 0 if result.get("ok") else 1

    if action == "change":
        current = getpass.getpass("Current passcode: ")
        new = getpass.getpass("New passcode: ")
        result = passlock.change_passcode(current, new)
        console.print("Passcode changed." if result.get("ok")
                      else f"[red]{result['error']}[/]")
        return 0 if result.get("ok") else 1

    console.print(f"[{DIM}]Usage: mangadl lock status|set|change|off[/]")
    return 1


def cmd_export(args) -> int:
    from . import features

    rest = [a for a in args.query]
    if not rest:
        console.print("[red]Usage: mangadl export <file> [json|csv|md][/]")
        return 1
    path = rest[0]
    fmt = rest[1] if len(rest) > 1 else (
        os.path.splitext(path)[1].lstrip(".") or "json")
    try:
        features.export_library(path, fmt)
    except Exception as e:
        console.print(f"[red]Export failed:[/] {e}")
        return 1
    console.print(f"Exported library to [bold]{path}[/]")
    return 0


def cmd_watch(args) -> int:
    """Watch a series, or list / check the watchlist."""
    from . import tracking

    rest = list(args.query)
    action = (rest[0].lower() if rest else "list")

    if action == "list":
        entries = tracking.get_watchlist()
        if not entries:
            console.print("[yellow]Nothing is being watched.[/]")
            console.print(f"[{DIM}]Add one with: mangadl watch add <url>[/]")
            return 0
        table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
        table.add_column("Title")
        table.add_column("Source", style=DIM)
        table.add_column("Chapters", justify="right")
        table.add_column("New", justify="right")
        table.add_column("Checked", style=DIM)
        for entry in entries:
            new = entry.get("new_chapters", 0)
            table.add_row(
                entry.get("title", "?"), entry.get("source", "-"),
                str(entry.get("known_chapters", 0)),
                f"[{ACCENT}]+{new}[/]" if new else "-",
                entry.get("checked", "-"))
        console.print(table)
        return 0

    if action in ("add", "remove", "rm"):
        if len(rest) < 2:
            console.print(f"[red]Usage: mangadl watch {action} <url>[/]")
            return 1
        url = rest[1]
        if action == "add":
            try:
                source = source_for_url(url)
                info = source.get_manga_info(url)
                chapters = source.get_chapters(url)
                source.close()
            except Exception as e:
                console.print(f"[red]Error:[/] {e}")
                return 1
            tracking.watch(url, info["title"], len(chapters),
                           source=info.get("source"), cover=info.get("cover"))
            console.print(f"Watching [bold]{info['title']}[/] "
                          f"([{DIM}]{len(chapters)} chapters[/])")
        else:
            console.print("Removed." if tracking.unwatch(url)
                          else "[yellow]Not in the watchlist.[/]")
        return 0

    if action == "check":
        entries = tracking.get_watchlist()
        if not entries:
            console.print("[yellow]Nothing is being watched.[/]")
            return 0
        with console.status(f"Checking {len(entries)} series..."):
            updates = tracking.check_updates()
        if not updates:
            console.print("[green]Everything is up to date.[/]")
            return 0
        table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
        table.add_column("Title")
        table.add_column("New", justify="right")
        table.add_column("Total", justify="right")
        for update in updates:
            table.add_row(update["title"], f"[{ACCENT}]+{update['new']}[/]",
                          str(update["total"]))
        console.print(table)
        return 0

    console.print(f"[{DIM}]Usage: mangadl watch list|add|remove|check [url][/]")
    return 1


def cmd_disk(args) -> int:
    """Disk usage, duplicate files and orphaned library entries."""
    from . import features, tracking

    rest = list(args.query)
    action = (rest[0].lower() if rest else "usage")
    root = rest[1] if len(rest) > 1 else args.output

    if action == "usage":
        rows = tracking.disk_usage(root)
        if not rows:
            console.print(f"[yellow]Nothing found in {root}[/]")
            return 0
        table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
        table.add_column("Series")
        table.add_column("Files", justify="right", style=DIM)
        table.add_column("Size", justify="right")
        total = 0
        for row in rows[:30]:
            total += row["bytes"]
            table.add_row(row["name"], str(row["files"]),
                          features.human_size(row["bytes"]))
        console.print(table)
        console.print(f"[{DIM}]Total: {features.human_size(total)}[/]")
        return 0

    if action in ("dupes", "duplicates"):
        with console.status(f"Scanning {root}..."):
            groups = tracking.scan_duplicates(root)
        if not groups:
            console.print("[green]No duplicate files found.[/]")
            return 0
        wasted = sum(g["wasted"] for g in groups)
        for group in groups[:20]:
            console.print(f"[{ACCENT}]{features.human_size(group['size'])}[/] "
                          f"x{len(group['files'])}")
            for path in group["files"]:
                console.print(f"  [{DIM}]{path}[/]")
        console.print(f"\n[bold]{features.human_size(wasted)}[/] wasted "
                      f"across {len(groups)} groups")
        return 0

    if action == "orphans":
        orphans = tracking.find_orphans()
        if not orphans:
            console.print("[green]No orphaned library entries.[/]")
            return 0
        for orphan in orphans:
            console.print(f"[yellow]{orphan['title']}[/]")
            if orphan["directory_gone"]:
                console.print(f"  [{DIM}]folder missing: {orphan['directory']}[/]")
            for missing in orphan["missing"]:
                console.print(f"  [{DIM}]missing: {missing}[/]")
        return 0

    console.print(f"[{DIM}]Usage: mangadl disk usage|dupes|orphans [dir][/]")
    return 1


def cmd_search(query: str, source_id: str = "", language: str = "en"):
    if not query:
        console.print("[red]Provide a search query, e.g.: mangadl search \"one piece\"[/]")
        return 1

    if source_id:
        label = SOURCES[source_id].name
        with console.status(f"Searching [bold]{label}[/] for [bold]{query}[/]..."):
            source = get_source(source_id, language=language)
            try:
                results = source.search(query)
            finally:
                source.close()
    else:
        with console.status(f"Searching all sources for [bold]{query}[/]..."):
            results = search_all(query, limit=10)

    from . import features
    results = features.apply_filters(results)
    features.add_history(query, source_id or "all", len(results))

    if not results:
        console.print("[yellow]No results found.[/]")
        return 1

    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {ACCENT}")
    table.add_column("#", style=DIM, justify="right")
    table.add_column("Source", style=ACCENT)
    table.add_column("Title")
    table.add_column("URL", style=DIM, overflow="fold")
    for i, r in enumerate(results, 1):
        table.add_row(str(i), r.get("source_name") or r.get("source") or "?",
                      r["title"], r["url"])
    console.print(table)
    console.print(f"[{DIM}]Download with: mangadl <url>[/]")
    return 0


def cmd_info(url: str, source_id: str = "", language: str = "en"):
    if not url:
        console.print("[red]Provide a manga URL.[/]")
        return 1
    try:
        source = (get_source(source_id, language=language) if source_id
                  else source_for_url(url, language=language))
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        return 1
    with console.status("Fetching manga information..."):
        try:
            info = source.get_manga_info(url)
            chapters = source.get_chapters(url)
        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            return 1
        finally:
            source.close()

    provider = info.get("source_name") or source.name
    body = [f"[{DIM}]from[/] [{ACCENT}]{provider}[/]", ""]
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
        source=args.source,
        language=args.language,
        scanlator=args.scanlator,
        data_saver=args.data_saver,
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
    try:
        source = (get_source(options.source, language=options.language)
                  if options.source
                  else source_for_url(options.url, language=options.language))
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        return 1
    with console.status("Fetching manga information..."):
        try:
            info = source.get_manga_info(options.url)
            chapters = source.get_chapters(options.url)
        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            return 1
        finally:
            source.close()

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
    summary.add_row("Source", info.get("source_name") or source.name)
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
    if command in ("sources", "source"):
        return cmd_sources()
    if command == "config":
        return cmd_config(args)
    if command == "stats":
        return cmd_stats()
    if command == "history":
        return cmd_history(args)
    if command == "lock":
        return cmd_lock(args)
    if command == "export":
        return cmd_export(args)
    if command == "watch":
        return cmd_watch(args)
    if command == "disk":
        return cmd_disk(args)
    if command == "search":
        return cmd_search(" ".join(args.query), args.source, args.language)
    if command == "info":
        return cmd_info(args.query[0] if args.query else "",
                        args.source, args.language)
    if command == "gui":
        from .gui import run_gui
        return run_gui()
    if command == "tui":
        from .tui import run_tui
        return run_tui()
    if command == "resume":
        return cmd_resume(args)

    if not args.source and detect_source(args.target) is None:
        console.print(f"[red]No source recognises that URL:[/] {args.target}")
        console.print(f"[{DIM}]Supported sites:[/]")
        for meta in list_sources():
            console.print(f"  [{DIM}]{meta['name']:<14}{meta['base_url']}[/]")
        console.print(f"[{DIM}]Or search: mangadl search \"manga name\"[/]")
        return 1
    return cmd_download(args)


if __name__ == "__main__":
    sys.exit(main())
