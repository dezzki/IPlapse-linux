# IPLapse — Building (Linux)

CLI-only on Linux: there is no GUI. `iplapse` is a global terminal command like
`fastfetch` — it records only while the terminal running it stays open. There is
**no background service** and nothing runs at login.

## Runtime dependencies (Arch Linux)

| Package | Purpose |
|---|---|
| `python` | Python 3.12+ runtime |
| `python-numpy` | Frame buffers, JPEG byte decoding |
| `python-opencv` | MJPEG decode, `cv2.VideoWriter` (H.264) |

These are only needed to run from source or to build the binary. The built
binary is self-contained.

```bash
sudo pacman -S --needed python-numpy python-opencv
python -c "import cv2, numpy; print('ok')"
```

> **H.264 note:** `python-opencv` links against system FFmpeg (with `libx264`),
> so `avc1` output works. The `opencv-python` pip wheel bundles its own FFmpeg
> **without** `libx264`, so on that build the writer silently falls back to
> `mp4v` (still MP4, VLC-compatible). The codec fallback chain is
> `avc1` → `mp4v` → `MJPG`.

## Run from source

```bash
python timelapse.py --url http://<phone-ip>:8080/video --speed 600   # until you stop it
python timelapse.py --url http://<phone-ip>:8080/video --speed 600 --duration 3600
python timelapse.py --help
```

Videos are saved to `~/Videos/IPLapse` (override with `--output`).

## Build the binary (PyInstaller)

```bash
python -m venv --system-site-packages .venv-build   # Arch blocks pip by default (PEP 668)
.venv-build/bin/pip install pyinstaller
.venv-build/bin/pyinstaller --noconfirm --onefile --name IPLapse timelapse.py
```

Output: `dist/IPLapse` — self-contained (Python, OpenCV, numpy bundled), no
runtime install needed. A console build is used on Linux (no `--windowed`); it
prints useful output and the exit code reflects success/failure.

## Install as a global command

Install to `~/.local/bin` (already on your `PATH` in most setups) so it works
from any directory:

```bash
mkdir -p ~/.local/bin
cp dist/IPLapse ~/.local/bin/iplapse
chmod +x ~/.local/bin/iplapse
```

Check it: `type iplapse` should print `iplapse is /home/<you>/.local/bin/iplapse`.

Optional: for all users on the machine, copy to a system bin instead:

```bash
sudo cp dist/IPLapse /usr/local/bin/iplapse
```

## Usage

```bash
iplapse --url http://<phone-ip>:8080/video --speed 600
```

- **`--speed`** — timelapse multiplier (600 = 1 output second per 10 real
  minutes; 30 = fast).
- **`--fps`** — output frames per second (default 30).
- **`--duration`** — seconds to record before stopping (default: run until
  stopped).
- **`--output`** — save folder (default `~/Videos/IPLapse`).
- **Press `q`** (single key, no Enter) to stop and save. `Ctrl+C`/`SIGTERM`
  also stop it cleanly. Closing the terminal kills the process — recording
  happens only while the terminal is open.

While recording, a blinking `●`/`○` REC line shows the frame count and elapsed
time (updated every second, plus a fuller status line every 30 s). The output
file is finalized cleanly on any stop.

```bash
iplapse --help
iplapse --url http://192.168.1.5:8080/video --speed 600 --duration 3600
```

## Bad links

An unreachable or invalid stream URL prints:

```
Could not open stream: http://<url>
```

and exits non-zero (exit code 1).