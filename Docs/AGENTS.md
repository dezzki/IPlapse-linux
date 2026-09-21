# IPLapse — Agent Guide (index)

OS-universal documentation for agents, contributors, and reviewers.

This file is a short index and quick start. Detailed docs live in the files
mapped below. **Keep this file under 100 lines** — add new content to a
sub-document instead.

## What is IPLapse?

A background time-lapse recorder for a camera exposing an **MJPEG-over-HTTP**
stream (e.g. the Android *IP Webcam* app). The user supplies a stream URL and a
speed multiplier (600x = 1 output second per 10 real minutes). The app samples
frames at that cadence and writes an MP4 (H.264 first, MPEG-4 fallback), with
**no live preview**. It is CLI-only — recording stops on duration, stream loss,
or `SIGTERM`/`SIGINT` (which finalize the file cleanly).

## Documentation map

| If you need... | Read |
|---|---|
| Dependencies, Python version, camera source | [`requirements.md`](requirements.md) |
| Architecture, recording flow, threads, stream reading, stop logic, design decisions, limitations | [`design.md`](design.md) |
| CLI arguments, mode selection, timelapse math | [`cli.md`](cli.md) |
| GUI elements and recorder subprocess orchestration | [`gui.md`](gui.md) (removed — historical record) |
| Output location, naming, codec fallback | [`outputs.md`](outputs.md) |
| Project layout, building the EXE / installer | [`building.md`](building.md) |
| Building on Arch Linux / other Linux (packages, PyInstaller, global `iplapse` command) | [`building-linux.md`](building-linux.md) |
| Entry points and function reference | [`reference.md`](reference.md) |

## Quick start

```bash
pip install -r requirements.txt
python timelapse.py --url <url> --speed 600          # CLI, records in background
python timelapse.py --url <url> --speed 600 --duration 3600  # stop after 1 h
```

On Arch Linux see [`building-linux.md`](building-linux.md) (PEP 668, venv,
PyInstaller, installing `iplapse` as a global command).

## Conventions

- The entire app is a single file: `timelapse.py`.
- Platform-specific behavior is called out explicitly in each document.
- Never grow `AGENTS.md` past 100 lines — put detail in a sub-document and
  map it here.