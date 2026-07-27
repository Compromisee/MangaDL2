#!/usr/bin/env python3
"""Unified entry point for the packaged executable.

Behaviour:
    WeebCentral.exe                 -> desktop GUI (default, no console needed)
    WeebCentral.exe gui             -> desktop GUI
    WeebCentral.exe tui             -> terminal UI
    WeebCentral.exe <url> [...]     -> CLI download
    WeebCentral.exe search "query"  -> CLI search
    WeebCentral.exe resume          -> resume interrupted download
    WeebCentral.exe --help          -> CLI help
"""

import multiprocessing
import sys


def main():
    # Required for PyInstaller: worker threads/processes must not re-launch app
    multiprocessing.freeze_support()

    args = sys.argv[1:]
    if not args or args[0] == "gui":
        from weebcentral.gui import run_gui
        sys.exit(run_gui())

    from weebcentral.cli import main as cli_main
    sys.exit(cli_main(args))


if __name__ == "__main__":
    main()
