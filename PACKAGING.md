# Packaging — building an all-inclusive executable

This guide produces a standalone **MangaDL** executable containing the
GUI, TUI and CLI in one binary — no Python installation needed on the target
machine.

| Command | Result |
|---|---|
| `MangaDL.exe` (double-click) | Desktop GUI |
| `MangaDL.exe tui` | Terminal UI |
| `MangaDL.exe <manga-url> --per 10` | CLI download |
| `MangaDL.exe search "one piece"` | CLI search |
| `MangaDL.exe resume` | Resume interrupted download |

The build is driven by **[`MangaDL.spec`](MangaDL.spec)** and the
unified entry point **[`launcher.py`](launcher.py)**.

---

## 1. Prerequisites

- Python **3.9 – 3.12** (PyInstaller support is best here; 3.13 usually works too)
- A clean **virtual environment** (strongly recommended — PyInstaller bundles
  everything importable, so a lean venv means a smaller exe)

```bash
git clone https://github.com/Yui007/mangadl_downloader.git
cd mangadl_downloader

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install pyinstaller
```

> Build on the OS you are targeting. PyInstaller does **not** cross-compile:
> a Windows exe must be built on Windows, a macOS app on macOS, etc.

---

## 2. Build

### One-folder build (recommended)

Fast startup, easy to debug, updates only changed files:

```bash
pyinstaller MangaDL.spec
```

Output: `dist/MangaDL/` — ship the whole folder. The executable is
`dist/MangaDL/MangaDL(.exe)`.

### One-file build

A single portable executable (slower startup — it unpacks to a temp dir):

```bash
pyinstaller MangaDL.spec -- --onefile
```

Output: `dist/MangaDL.exe` (or `dist/MangaDL` on macOS/Linux).

### Clean rebuild

```bash
pyinstaller MangaDL.spec --clean --noconfirm
```

---

## 3. What the spec bundles

- The whole `mangadl` package (CLI + TUI + GUI + engine)
- `mangadl/gui/web/` — the GUI's HTML/CSS/JS (the code auto-detects the
  PyInstaller location via `sys._MEIPASS`)
- Textual's data files (TUI styling)
- pywebview's platform backends as hidden imports (WinForms/EdgeChromium on
  Windows, Cocoa on macOS, GTK/Qt on Linux — only the matching one loads)
- Rotating-log handler (`logging.handlers`)

Excluded to keep size down: tkinter, numpy/matplotlib/etc. (unused).

Typical sizes: roughly 80–140 MB one-folder, 40–80 MB one-file (varies by OS and installed backends).

---

## 4. Platform notes

### Windows

- The exe uses **Microsoft Edge WebView2** for the GUI. Windows 11 and
  updated Windows 10 machines already have it; otherwise users can install
  the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).
- The spec sets `console=True` so `tui` / CLI subcommands work. Double-click
  still opens the GUI, but with a console window behind it. If you want a
  console-free GUI exe, build a second binary: copy the spec, set
  `console=False`, name it `MangaDLGUI`, and ship both.
- An icon is used automatically if `docs/icon.ico` exists.
- SmartScreen may warn on unsigned exes — sign the binary
  (`signtool sign /fd SHA256 ...`) or tell users to click "More info → Run
  anyway".

### macOS

- The one-folder build also produces **`dist/MangaDL.app`** for
  double-click launching; the CLI/TUI binary is inside
  `MangaDL.app/Contents/MacOS/`.
- Gatekeeper blocks unsigned apps: either
  `codesign --deep -s "Developer ID Application: ..." dist/MangaDL.app`
  and notarize, or instruct users to right-click → Open the first time.
- Build separate x86_64 / arm64 binaries on the corresponding Macs (or use
  `target_arch='universal2'` in the EXE section if all deps provide
  universal wheels).

### Linux

- The GUI needs WebKitGTK at runtime:
  `sudo apt install gir1.2-webkit2-4.1` (Debian/Ubuntu) or the distro
  equivalent. Alternatively `pip install pywebview[qt]` **before building**
  so the Qt backend is bundled.
- Build on the **oldest** distro you want to support (glibc compatibility).
- Mark the binary executable: `chmod +x dist/MangaDL/MangaDL`.

---

## 5. Testing the build

```bash
# GUI
dist/MangaDL/MangaDL

# CLI
dist/MangaDL/MangaDL --help
dist/MangaDL/MangaDL search "vinland saga"

# TUI (run from a real terminal)
dist/MangaDL/MangaDL tui
```

Smoke checklist:

- [ ] GUI opens, themes/orbs/dot-matrix render
- [ ] Search returns covers; manga page loads
- [ ] A 1-chapter download completes and packs a CBZ
- [ ] Library/bookmarks persist (`~/.mangadl/`)
- [ ] `search`, `info`, `resume`, `tui` subcommands work
- [ ] Log file appears in `~/.mangadl/logs/`

User data (settings, library, bookmarks, logs, job journal) always lives in
`~/.mangadl/`, never next to the exe — so upgrading is just replacing
the binary/folder.

---

## 6. Releasing on GitHub

```bash
# tag and build per platform, then:
gh release create v2.5.0 \
    dist/MangaDL-windows-x64.zip \
    dist/MangaDL-macos-arm64.zip \
    dist/MangaDL-linux-x64.tar.gz \
    --title "v2.5.0" --notes-file CHANGELOG.md
```

Suggested archive naming: `MangaDL-<os>-<arch>.<zip|tar.gz>` with the
one-folder build zipped inside.

### CI (GitHub Actions) sketch

```yaml
name: build
on: { push: { tags: ["v*"] } }
jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller MangaDL.spec --noconfirm
      - uses: actions/upload-artifact@v4
        with:
          name: MangaDL-${{ matrix.os }}
          path: dist/
```

---

## 7. Troubleshooting builds

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` at runtime | Add the module to `hiddenimports` in the spec and rebuild. |
| GUI opens blank / file not found | Web assets missing — confirm the `datas` entry and that `run_gui` resolves `sys._MEIPASS` (already handled). |
| Huge executable | Build in a clean venv; check `excludes`; avoid installing dev tools in the build env. |
| Antivirus flags the exe | Common with PyInstaller one-file. Prefer one-folder, sign the binary, or submit a false-positive report. |
| `webview` backend error on Linux | Install WebKitGTK (`gir1.2-webkit2-4.1`) or rebuild with `pywebview[qt]` installed. |
| Windows: console floods with `window.native` / recursion errors | Bridge noise from Edge's accessibility layer probing pywebview's .NET object; handled in-app since v2.6.1. If accompanied by `E_NOINTERFACE` COM errors, the target machine's **WebView2 Runtime is outdated** — install the current [Evergreen WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/). |
| TUI garbled on Windows | Use Windows Terminal (not legacy conhost). |
