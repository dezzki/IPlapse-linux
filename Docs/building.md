# IPLapse — Building

> **CLI-only:** the GUI was removed, so no `--windowed` build. Windows and
> Linux build the same console executable. Linux-specific instructions live in
> [`building-linux.md`](building-linux.md) (packages, PEP 668, global `iplapse`
> command).

## Project layout

```
timelapse.py              # entire application (recorder + GUI) in one file
requirements.txt          # runtime dependencies
README.md                 # end-user documentation
AGENTS.md                 # agent docs index (this set of files)
requirements.md design.md cli.md gui.md outputs.md building.md reference.md
IPLapse.iss               # Inno Setup script (installer build)
IPWebcamTimelapse.spec    # PyInstaller spec
.gitignore                # ignores build/, dist/, installer/, timelapses/
```

## Run from source

```bash
pip install -r requirements.txt
python timelapse.py                           # GUI
python timelapse.py --url <url> --speed 600   # direct recording
```

## Portable executable (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --name IPWebcamTimelapse timelapse.py
```

Output: `dist/IPWebcamTimelapse.exe` — self-contained (Python, OpenCV, numpy
bundled), no runtime install needed. Built for 64-bit Windows 10/11. Runs
without a console window is *not* used: the app is CLI-only, so keep the
console build (removes `--windowed` from earlier versions).

## Installer (optional, Inno Setup)

```bash
ISCC.exe IPLapse.iss
```

Output: `installer/IPLapse-Setup.exe`. The installer is a wrapper that installs
the same portable executable plus Start Menu/desktop shortcuts; the EXE works
without it.