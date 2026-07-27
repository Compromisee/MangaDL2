#!/usr/bin/env python3
"""Launch the WeebCentral Downloader TUI (no install needed)."""

import sys

from weebcentral.tui import run_tui

if __name__ == "__main__":
    sys.exit(run_tui())
