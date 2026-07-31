# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for MangaDL — all-inclusive executable.

Build (from the repo root, inside your venv):

    pyinstaller MangaDL.spec              # one-folder build (recommended)
    pyinstaller MangaDL.spec -- --onefile # single-file build

Output lands in dist/MangaDL/ (or dist/MangaDL.exe for onefile).
See PACKAGING.md for full instructions per platform.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# "--onefile" after "--" switches to a single-file build
ONEFILE = "--onefile" in sys.argv

APP_NAME = "MangaDL"

# ----------------------------------------------------------------- data files
# The GUI's web assets must ship inside the bundle.
datas = [
    ("mangadl/gui/web", "mangadl/gui/web"),
]
# Textual ships css/tcss data files
datas += collect_data_files("textual")

# ------------------------------------------------------------- hidden imports
hiddenimports = [
    # pywebview platform backends (only the matching one loads at runtime)
    "webview.platforms.winforms",   # Windows
    "webview.platforms.edgechromium",
    "webview.platforms.cocoa",      # macOS
    "webview.platforms.gtk",        # Linux (WebKitGTK)
    "webview.platforms.qt",         # Linux fallback
    # System tray. pystray picks its backend at import time via a chain of
    # try/except imports, which PyInstaller's static analysis cannot follow
    # -- so without these the packaged exe silently had no tray at all and
    # "minimise to tray" did nothing.
    "pystray",
    "pystray._win32",
    "pystray._darwin",
    "pystray._appindicator",
    "pystray._gtk",
    "pystray._xorg",
    # The tray icon is drawn with Pillow at runtime.
    "PIL.Image",
    "PIL.ImageDraw",
    # stdlib/log bits PyInstaller sometimes misses
    "logging.handlers",
]
hiddenimports += collect_submodules("mangadl")
hiddenimports += collect_submodules("textual.widgets")

# ------------------------------------------------------------------- analysis
a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # trim things we never use to keep the exe smaller
        "tkinter", "unittest", "pydoc", "test",
        "numpy", "matplotlib", "scipy", "pandas",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ------------------------------------------------------------------ exe/build
# console=True so CLI/TUI subcommands work from a terminal; on Windows,
# double-clicking still opens the GUI (a console window appears alongside).
# For a console-free GUI-only exe, set console=False and build a second exe.
if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=True,
        icon="docs/icon.ico" if sys.platform == "win32" else None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        strip=False,
        upx=True,
        console=True,
        icon="docs/icon.ico" if sys.platform == "win32" else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=APP_NAME,
    )

# macOS app bundle (GUI double-click support)
if sys.platform == "darwin" and not ONEFILE:
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="io.github.mangadl.downloader",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
