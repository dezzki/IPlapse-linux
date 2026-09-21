# IPLapse — CLI

## Mode selection

**CLI-only.** The app is always in record mode: `main()` calls
`record(parse_args())`. There is no GUI (removed) and no hidden orchestration
flags (`--record`, `--parent-pid`, `--stop-file` no longer exist).

## Arguments (`parse_args()`)

| Argument | Default | Purpose |
|---|---|---|
| `--url` | `http://192.168.1.5:8080/video` | MJPEG stream URL |
| `--speed` | `600.0` | Timelapse speed multiplier |
| `--fps` | `30.0` | Output video frames per second |
| `--output` | `~/Videos/IPLapse` | Save folder |
| `--duration` | `None` | Stop automatically after N seconds |

## Examples

```bash
python timelapse.py --url http://192.168.1.5:8080/video --speed 600
python timelapse.py --url <url> --speed 300 --fps 30 --output ~/clips --duration 3600
```

## Console feedback

When recording starts you see:

```
Recording started: http://192.168.1.5:8080/video
Output folder: /home/<you>/Videos/IPLapse
Output: /home/<you>/Videos/IPLapse/timelapse_20260918_171504.mp4 (640x480 @ 30 fps, capture every 6.67s)
Press q to stop and save.
```

While recording, a single line is rewritten every second with a blinking
`●`/`○` REC indicator, the frame count and elapsed time; every 30 s a fuller
`REC status:` line is printed. The indicator line is cleared before the final
`Saved ...` message, which reports the **save-time** name (the file is renamed
to the date+time when recording stops — see `outputs.md`).

## Stopping

The recorder stops and finalizes the MP4 when any of these happen:

1. Press **`q`** in the terminal (single key, no Enter) — the normal in-terminal
   stop.
2. `--duration` elapsed.
3. Stream ended permanently — brief interruptions are **auto-handled**: the
   reader waits 3 s and reconnects to the same URL, up to 3 times, continuing
   the same file. It only stops after the reconnects fail.
4. `SIGTERM` / `SIGINT` received (e.g. `systemctl stop` or Ctrl+C) — the
   signal handler sets the stop event so the file is finalized cleanly.

Every stop prints why it happened, e.g. `Stopped: --duration elapsed.`,
`Stopped: 'q' pressed.`, `Stopped: signal 2 received.`, or
`Stopped: camera stream ended (reconnect failed).`. If the stream ends before
any frame is captured, the app prints `Failed: camera stream ended before any
frame was captured (...)` and **exits non-zero** — no phantom "Saved".

If stdin is not a terminal (background/nohup), the key watcher is disabled and
a note is printed; stop then via `--duration` or signals.

An unreachable/invalid URL prints a clear `Could not open stream: <url>` (with
the reason, e.g. a non-MJPEG `Content-Type`) and exits non-zero (exit code 1).

## Timelapse math

```
capture_interval = speed / fps        # seconds of real time between saved frames
```

| Speed | capture interval | 1 s of video covers |
|---|---|---|
| 30 | 1.0 s | 30 s |
| 300 | 10.0 s | 5 min |
| 600 | 20.0 s | 10 min |
| 1200 | 40.0 s | 20 min |

The first frame is written immediately when the writer is created; subsequent
frames when wall-clock time passes `next_capture`, which advances by
`capture_interval` after each write (drift-free).