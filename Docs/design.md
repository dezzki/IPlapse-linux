# IPLapse — Design

## Architecture

A background CLI recorder with **no live preview**. The command line supplies
the stream URL and speed; `record()` does all the work in one process.

## Recording flow (`record()`)

1. **Open the stream** — `open_stream()` returns `("raw", stream, first_frame)`
   (raw HTTP MJPEG) or `("cv", capture, first_frame)` (fallback).
2. **Pick the output path** — timestamp-based name in the default output folder
   (`outputs.md`); the file is renamed to the **save-time** name on completion.
3. **Reader thread** — decodes frames continuously, keeps only the **latest**
   under a `frame_lock`.
4. **Writer thread** — samples `latest` on a 20 ms loop, writing a frame
   whenever wall-clock time reaches `next_capture`; advances
   `next_capture += capture_interval` after each write (drift-free).
5. **Main thread** — polls stop conditions every 100 ms, then coordinates
   shutdown (`stop_event`, writer release finalizes the MP4, reader joined
   best-effort).

Both threads are daemons; a blocked socket read is abandoned on process exit.

## Stream reading strategy

### Raw MJPEG reader (preferred)

Reads the HTTP body in chunks and extracts JPEG frames:

- **Multipart mode (default):** when the response declares
  `multipart/x-mixed-replace; boundary=...` (what the IP Webcam app serves),
  the reader parses parts by their `--boundary` + headers and slices each
  frame by its exact `Content-Length`. Decoding precise slices avoids the
  libjpeg `Corrupt JPEG data` chatter that naive marker-scanning causes.
- **SOI/EOI fallback:** servers that send raw concatenated JPEGs (no boundary)
  are handled by scanning for `FF D8`…`FF D9`, including per-part fallback when
  a multipart part lacks `Content-Length`. An 8 MB buffer cap drops stale data.

Decode warnings from libjpeg/OpenCV are silenced during `imdecode`, so they
can't spam the terminal or mangle the `● REC` status line.

**Resilience:** the reader is wrapped so any `read()` failure, EOF, or timeout
is treated as a recoverable blip: it waits 3 s, re-opens the same URL (raw
mode only — the cv fallback never reconnects), and continues writing to the
same MP4. Short camera or Wi-Fi interruptions no longer end the recording.

**Input validation:** `open_stream` sends `Accept-Encoding: identity`,
supports `user:pass@host` URLs (Basic auth), and rejects responses whose
`Content-Type` is `text/*` or `video/*` with an actionable error instead of
silently scanning garbage.

**Why not `cv2.VideoCapture` only?** FFMPEG's HTTP buffering adds latency and
frame-burst jitter on MJPEG streams; the raw reader always yields the freshest
frame with lower latency.

### `cv2.VideoCapture` fallback

Used when the raw reader can't fetch a first frame (RTSP, local files). The
`"cv"` reader branch calls `cap.read()`. If 50 consecutive reads fail (~1 s),
`stream_ok` is set to `False` and recording stops — the same stream-loss
behavior the raw reader already has.

## Why wall-clock sampling?

MJPEG-over-HTTP clients receive frames in **bursts** (a socket `read()` blocks
until a full buffer arrives), so sampling by frame count or read timing is
wrong. Sampling is always driven by wall-clock time in the writer thread.

## Stop mechanisms (checked in order)

1. **`q` key** — a single-key stdin watcher (termios cbreak on POSIX,
   `msvcrt` on Windows) sets `stop_event`; active only when stdin is a TTY.
2. `--duration` elapsed.
3. Stream ended (`stream_ok = False`) — the raw reader tolerates brief
   interruptions: on EOF/read-error/timeout it waits 3 s and re-opens the URL,
   up to 3 times (auto-reconnect), only giving up after that. The cv fallback
   stops after 50 consecutive failed reads.
4. `SIGTERM` / `SIGINT` — the signal handler sets `stop_event`; the main loop
   exits, the writer releases, and the MP4 is finalized. `SIGTERM` is what
   `systemctl stop` sends, so stopping the service never leaves a truncated
   file. (SIGTERM is registered only on POSIX; SIGINT works everywhere.)

A `Stopped: <reason>.` line is printed on every stop (e.g.
`--duration elapsed`, `'q' pressed`, `signal 2 received`, or
`camera stream ended (reconnect failed)`). If the stream ends **before any
frame is captured**, the app prints a clear `Failed: ...` message and exits
non-zero instead of reporting a phantom "Saved".

## Console feedback

A start message (`Recording started:` / `Output folder:`) prints as soon as the
stream opens, and the exact output path once the writer is created. A status
thread then rewrites a blinking `●`/`○` REC line every second (frames + elapsed,
plus a fuller line every 30 s); it is cleared before the final `Saved ...`
line. Codec-fallback warnings from OpenCV/FFmpeg are silenced with
`_silence_stderr()` so a missing H.264 encoder doesn't produce alarming output.

## Design decisions worth preserving

- No preview window — background-only by design.
- Single-file app (`timelapse.py`).
- Wall-clock sampling (see above).
- Latest-frame reader thread — never a lagging queue.
- Codec fallback chain — `avc1` (H.264) first, then `mp4v`, then `MJPG`.
- Graceful stop — files are always finalized (duration, stream loss, signals).

## Limitations / non-goals

- No live preview; only samples at the timelapse cadence.
- One URL → one timelapse; no multiplexing.
- No audio.
- Requires an MJPEG stream (or anything `cv2.VideoCapture` can open).
- No GUI and no Windows installer (removed when the app became CLI-only).