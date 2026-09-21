# IPlapse

A small command-line tool that records time-lapses from an IP camera that
serves an **MJPEG stream over HTTP** — like the Android *IP Webcam* app. You
give it a URL and a speed, and it samples frames in the background and writes
them into an MP4 file.

There's no GUI and no live preview. It's meant to be run from a terminal on
Linux, and it keeps recording until you tell it to stop.

## Why

IP Webcam and similar apps can record video, but they don't do time-lapses.
IPlapse is for long, boring recordings: point it at your camera, leave it
running, and come back later to a short video that summarizes hours of footage.

## Requirements

- Python 3.12+ with `numpy` and OpenCV (`cv2`)
- A camera that exposes an MJPEG-over-HTTP stream, e.g. the IP Webcam app on
  your phone at `http://<phone-ip>:8080/video` (your actual port may differ)
- Your computer and camera on the same network

On Arch Linux you can install the dependencies with:

```bash
sudo pacman -S python-numpy python-opencv
```

(If you build from the pip wheel instead, H.264 output isn't available, so
videos fall back to MPEG-4 video in an MP4 — still plays fine.)

## Running from source

```bash
python -m venv .venv
.venv/bin/pip install numpy opencv-python-headless
.venv/bin/python timelapse.py --url http://192.168.1.5:8080/video --speed 600
```

## Install as a command

If you want an `iplapse` command that works from any directory:

```bash
# build a standalone binary (PyInstaller)
python -m venv .venv-build --system-site-packages
.venv-build/bin/pip install pyinstaller
.venv-build/bin/pyinstaller --noconfirm --onefile --name IPLapse timelapse.py

# put it on your PATH
cp dist/IPLapse ~/.local/bin/iplapse
```

## Usage

```bash
iplapse --url http://192.168.1.5:8080/video --speed 600
```

- `--url` — the MJPEG stream URL
- `--speed` — time-lapse multiplier. 600 means one second of video per ten
  minutes of real time (an hour becomes a 6-second clip)
- `--fps` — output frames per second (default 30)
- `--duration` — stop automatically after N seconds (default: run until stopped)
- `--output` — where to save videos (default: `~/Videos/IPLapse`)

A few examples:

```bash
# one second of output per ten minutes, stop after one hour
iplapse --url http://192.168.1.5:8080/video --speed 600 --duration 3600

# faster: one second per five minutes
iplapse --url http://192.168.1.5:8080/video --speed 300
```

## Stopping

- Press `q` in the terminal to stop and save. `Ctrl+C` works too.
- While recording, a blinking `● REC` line shows the frame count and elapsed
  time. Closing the terminal window stops the recording.
- Videos are saved as `timelapse_YYYYMMDD_HHMMSS.mp4` in `~/Videos/IPLapse`
  (named by the date and time the recording was saved).

## Notes

- The app reads the stream with a small HTTP reader, not a video player, so
  it works with cheap camera apps and keeps up with bursts of frames.
- Brief stream interruptions are handled automatically — it waits a few
  seconds and reconnects — so short Wi-Fi hiccups don't end the recording.
- If the stream never shows up, you'll get a clear error: the device isn't
  reachable, the URL isn't actually an MJPEG stream, or the camera app isn't
  running. On phones, keep the app in the foreground; some apps stop streaming
  when the screen locks.

## What it doesn't do

- No GUI, no live preview
- No audio
- One camera per run — no multiplexing
- It runs only as long as the terminal is open; there's no background service