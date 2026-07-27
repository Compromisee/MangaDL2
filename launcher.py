#!/usr/bin/env python3
"""Unified entry point for the packaged executable.

Behaviour:
    MangaDL.exe                 -> desktop GUI (default, no console needed)
    MangaDL.exe gui             -> desktop GUI
    MangaDL.exe tui             -> terminal UI
    MangaDL.exe <url> [...]     -> CLI download
    MangaDL.exe search "query"  -> CLI search
    MangaDL.exe resume          -> resume interrupted download
    MangaDL.exe --help          -> CLI help
"""

import multiprocessing
import sys


def main():
    # Required for PyInstaller: worker threads/processes must not re-launch app
    multiprocessing.freeze_support()

    args = sys.argv[1:]
    if not args or args[0] == "gui":
        from mangadl.gui import run_gui
        sys.exit(run_gui())

    from mangadl.cli import main as cli_main
    sys.exit(cli_main(args))


if __name__ == "__main__":
    main()
