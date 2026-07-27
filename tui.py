#!/usr/bin/env python3
"""Launch the MangaDL TUI (no install needed)."""

import sys

from mangadl.tui import run_tui

if __name__ == "__main__":
    sys.exit(run_tui())
