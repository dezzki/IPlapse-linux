# IPLapse — Reference

## Entry points

| Function | Role |
|---|---|
| `main()` | Always runs `record(parse_args())` |
| `parse_args()` | CLI definition |
| `default_output_dir()` | Where videos are saved (`~/Videos/IPLapse`) |
| `open_stream(url, timeout, fallback, need_first_frame)` | Opens MJPEG/RTSP/file source; returns `("raw", stream, first_frame, url)` or `("cv", cap, first_frame, url)`, with Content-Type validation, Basic-auth support, and `Accept-Encoding: identity` |
| `_silence_stderr()` | Context manager that quiets OpenCV/FFmpeg/libjpeg warnings during decode and codec fallback |
| `_extract_multipart_frame(data, boundary)` | Parses one `--boundary` part by Content-Length → returns `(frame, consumed)` |
| `_extract_soi_eoi_frame(data)` | Raw `FF D8…FF D9` frame extraction (fallback when no boundary) |
| `make_writer(path, fps, w, h)` | Creates a `VideoWriter` with codec fallback |
| `record(args)` | The recorder (stream → threads → MP4, key watcher, status line, reconnect) |

## Key constants / state

| Symbol | Meaning |
|---|---|
| `DEFAULT_URL` | Default stream URL placeholder |
| `capture_interval` | `speed / fps` — real seconds between saved frames |
| `latest` / `frame_lock` | Freshest decoded frame + guard (shared across threads) |
| `stop_event` | Signals reader/writer threads to stop (also set by signal handler) |
| `rstate` | Writer handle, final path, and frame count |
| `stream_ok` | Becomes `False` when the reader gives up after reconnect attempts |
| `stop_info` | `{"stream": ...}` = why the stream ended; `{"stop": ...}` = stop reason printed as `Stopped: ...` |
| `stdin_watcher` | Single-key `q` reader (termios cbreak on POSIX, `msvcrt` on Windows); only active when stdin is a TTY |
| `status_loop` | Rewrites a blinking `●`/`○` REC line each second; prints a fuller status every 30 s (TTY only) |

## Entry sequence

```
main()
 └─ record(parse_args())
     ├─ open_stream() → reader thread + writer thread + stdin watcher
     ├─ reader reconnects on brief drops (3 × 3 s, raw mode)
     ├─ stop on: 'q' | duration | stream loss (after reconnect) | SIGTERM/SIGINT
     └─ writer.release() finalizes the MP4
```