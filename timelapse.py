import argparse
import base64
import os
import re
import select
import signal
import sys
import threading
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime

import cv2
import numpy as np


DEFAULT_URL = "http://192.168.1.5:8080/video"


def default_output_dir():
    return os.path.join(os.path.expanduser("~"), "Videos", "IPLapse")


def _unique_path(path):
    base, ext = os.path.splitext(path)
    candidate = path
    n = 2
    while os.path.exists(candidate):
        candidate = f"{base} ({n}){ext}"
        n += 1
    return candidate


def parse_args():
    parser = argparse.ArgumentParser(
        description="Record a timelapse from an IP webcam in the background."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Stream URL (e.g. http://<phone-ip>:8080/video)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=600.0,
        help="Timelapse speed multiplier (600 = 1 output second per 10 real minutes).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Frames per second of the output video.",
    )
    parser.add_argument(
        "--output",
        default=default_output_dir(),
        help="Folder where videos are saved.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional: record for this many seconds, then stop.",
    )
    return parser.parse_args()


def open_stream(url, timeout=15, fallback=True, need_first_frame=True):
    headers = {"User-Agent": "IPLapse/1.0", "Accept-Encoding": "identity"}
    auth_header = None
    parts = urllib.parse.urlsplit(url)
    if parts.username is not None or parts.password is not None:
        user = urllib.parse.unquote(parts.username or "")
        pw = urllib.parse.unquote(parts.password or "")
        token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("ascii")
        auth_header = f"Basic {token}"
        netloc = parts.hostname or ""
        if parts.port is not None:
            netloc += f":{parts.port}"
        url = urllib.parse.urlunsplit(
            (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
        )
        headers["Authorization"] = auth_header
    try:
        req = urllib.request.Request(url, headers=headers)
        stream = urllib.request.urlopen(req, timeout=timeout)
        ct = (stream.headers.get("Content-Type") or "").lower()
        if ct.startswith("text/") or ct.startswith("video/") or "mpegurl" in ct:
            stream.close()
            raise SystemExit(
                f"Could not open stream: {url} - server returned {ct!r}, not a live "
                "MJPEG stream. Check that the URL points to the video endpoint "
                "(e.g. .../video) and that the camera app is running."
            )
        if not need_first_frame:
            return "raw", stream, None, url
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = stream.read(4096)
            if not chunk:
                break
            buf += chunk
            start = buf.find(b"\xff\xd8")
            end = buf.find(b"\xff\xd9", start + 2) if start != -1 else -1
            if start != -1 and end != -1:
                try:
                    frame = cv2.imdecode(
                        np.frombuffer(buf[start:end + 2], dtype=np.uint8),
                        cv2.IMREAD_COLOR,
                    )
                except Exception:
                    frame = None
                if frame is not None:
                    return "raw", stream, frame, url
        stream.close()
    except SystemExit:
        raise
    except Exception:
        pass
    if not fallback:
        raise SystemExit(f"Could not open stream: {url}")
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        ok, frame = cap.read()
        if ok and frame is not None:
            return "cv", cap, frame, url
    msg = f"Could not open stream: {url}"
    if auth_header:
        msg += " (credentials were supplied but the stream was still not readable)"
    raise SystemExit(msg)


@contextmanager
def _silence_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved = os.dup(2)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


def _frame_from_jpeg(jpg):
    with _silence_stderr():
        try:
            return cv2.imdecode(
                np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR
            )
        except Exception:
            return None


def _extract_soi_eoi_frame(data):
    """Raw fallback: slice the first complete SOI..EOI JPEG. Returns (frame, consumed)."""
    s = data.find(b"\xff\xd8")
    if s == -1:
        return None, 0
    e = data.find(b"\xff\xd9", s + 2)
    if e == -1:
        return None, 0
    return _frame_from_jpeg(data[s:e + 2]), e + 2


def _extract_multipart_frame(data, delim):
    """Multipart part parser (--boundary / headers / Content-Length body).

    Returns (frame or None, bytes_consumed). (None, 0) means 'need more data'.
    Falls back to SOI..EOI scanning inside a part when it has no Content-Length.
    """
    start = data.find(delim)
    if start == -1:
        return None, 0
    pos = start + len(delim)
    if data[pos:pos + 2] == b"--":
        return None, 0  # final delimiter (stream is ending)
    if data[pos:pos + 2] != b"\r\n":
        # malformed region after the delimiter - skip it to keep making progress
        return None, len(delim)
    pos += 2
    hdr_end = data.find(b"\r\n\r\n", pos)
    if hdr_end == -1:
        return None, 0
    headers = data[pos:hdr_end].decode("latin1", "replace")
    body_start = hdr_end + 4
    m = re.search(r"Content-Length:\s*(\d+)", headers, re.I)
    if m:
        cl = int(m.group(1))
        body_end = body_start + cl
        if len(data) < body_end:
            return None, 0  # body not fully buffered yet
        jpg = data[body_start:body_end]
        consumed = body_end + (2 if data[body_end:body_end + 2] == b"\r\n" else 0)
        if jpg[:2] != b"\xff\xd8" or jpg[-2:] != b"\xff\xd9":
            return None, consumed  # not a clean JPEG part; drop it, keep going
        return _frame_from_jpeg(jpg), consumed
    # No Content-Length: scan SOI..EOI within this part's body
    frame, rel = _extract_soi_eoi_frame(data[body_start:])
    if rel == 0:
        return None, 0
    return frame, body_start + rel


def make_writer(path, fps, width, height):
    attempts = [("avc1", ".mp4"), ("mp4v", ".mp4"), ("MJPG", ".avi")]
    for codec, ext in attempts:
        candidate = os.path.splitext(path)[0] + ext
        writer = None
        try:
            with _silence_stderr():
                writer = cv2.VideoWriter(
                    candidate, cv2.VideoWriter_fourcc(*codec), fps, (width, height)
                )
                opened = writer.isOpened()
        except Exception:
            opened = False
        if opened:
            return writer, candidate
        if writer is not None:
            writer.release()
    raise SystemExit("Could not create output video writer (no supported codec).")


def record(args):
    capture_interval = args.speed / args.fps
    mode, src, first_frame, url = open_stream(args.url)

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(
        args.output, f"timelapse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    )

    print(f"Recording started: {url}", flush=True)
    print(f"Output folder: {args.output}", flush=True)

    stop_event = threading.Event()
    frame_lock = threading.Lock()
    latest = first_frame
    stream_ok = True
    stop_info = {"stream": "", "stop": ""}
    rstate = {"writer": None, "path": None, "frames": 0}

    def reader():
        nonlocal latest, stream_ok, src
        if mode == "raw":
            def read_boundary():
                try:
                    ct = src.headers.get("Content-Type") or ""
                except Exception:
                    return None
                m = re.search(r"boundary=([^;\s]+)", ct)
                return ("--" + m.group(1).strip('"')).encode() if m else None

            boundary = read_boundary()
            buf = b""
            failures = 0
            stall = 0
            MAX_RECONNECT = 3
            while not stop_event.is_set():
                progress = False
                frame, consumed = (
                    _extract_multipart_frame(buf, boundary)
                    if boundary is not None
                    else _extract_soi_eoi_frame(buf)
                )
                while consumed:
                    progress = True
                    buf = buf[consumed:]
                    if frame is not None:
                        with frame_lock:
                            latest = frame
                    frame, consumed = (
                        _extract_multipart_frame(buf, boundary)
                        if boundary is not None
                        else _extract_soi_eoi_frame(buf)
                    )
                if not progress:
                    stall += 1
                    if boundary is not None and stall >= 40:
                        boundary = None  # malformed multipart - fall back to raw scan
                        stall = 0
                else:
                    stall = 0
                try:
                    chunk = src.read(65536)
                except Exception:
                    chunk = b""
                if not chunk:
                    failures += 1
                    if failures > MAX_RECONNECT:
                        stop_info["stream"] = "camera stream ended (reconnect failed)"
                        stream_ok = False
                        return
                    if stop_event.wait(timeout=3.0):
                        return
                    try:
                        rmode, new_src, f, _ = open_stream(
                            url, timeout=10, fallback=False, need_first_frame=False
                        )
                    except SystemExit:
                        continue
                    try:
                        src.close()
                    except Exception:
                        pass
                    src = new_src
                    boundary = read_boundary()
                    failures = 0
                    stall = 0
                    buf = b""
                    if rmode == "raw" and f is not None:
                        with frame_lock:
                            latest = f
                    continue
                buf += chunk
                if len(buf) > 8_000_000:
                    idx = buf.rfind(boundary) if boundary is not None else buf.rfind(b"\xff\xd8")
                    buf = buf[idx:] if idx != -1 else b""
        else:
            failures = 0
            while not stop_event.is_set():
                try:
                    ok, frame = src.read()
                except Exception:
                    ok = False
                if not ok:
                    failures += 1
                    if failures >= 50:
                        stop_info["stream"] = "camera stream ended (cv read failed)"
                        stream_ok = False
                        return
                    time.sleep(0.02)
                    continue
                failures = 0
                with frame_lock:
                    latest = frame

    def writer_loop():
        next_capture = None
        while not stop_event.is_set():
            with frame_lock:
                f = latest
            if f is None:
                time.sleep(0.05)
                continue
            now = time.time()
            if rstate["writer"] is None:
                height, width = f.shape[:2]
                rstate["writer"], rstate["path"] = make_writer(
                    out_path, args.fps, width, height
                )
                rstate["writer"].write(f)
                rstate["frames"] += 1
                next_capture = now + capture_interval
            elif now >= next_capture:
                rstate["writer"].write(f)
                rstate["frames"] += 1
                next_capture += capture_interval
            time.sleep(0.02)
        if rstate["writer"] is not None:
            rstate["writer"].release()

    def handle_signal(signum, frame):
        stop_info["stop"] = f"signal {signum} received"
        stop_event.set()

    if os.name == "posix":
        signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    stdin_tty = sys.stdin.isatty()

    def stdin_watcher():
        if os.name == "nt":
            try:
                import msvcrt
            except ImportError:
                return
            while not stop_event.is_set():
                ch = msvcrt.getch()
                if ch in (b"q", b"Q", b"\x03"):
                    stop_info["stop"] = "'q' pressed"
                    stop_event.set()
                    return
        else:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop_event.is_set():
                    readable, _, _ = select.select([sys.stdin], [], [], 1.0)
                    if not readable:
                        continue
                    ch = sys.stdin.read(1)
                    if ch in ("q", "Q", "\x03"):
                        stop_info["stop"] = "'q' pressed"
                        stop_event.set()
                        return
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def status_loop():
        blink = False
        last_status = time.time()
        while not stop_event.is_set():
            time.sleep(1.0)
            blink = not blink
            elapsed = time.time() - start
            mm, ss = divmod(int(elapsed), 60)
            sys.stdout.write(
                f"\r{'●' if blink else '○'} REC  {rstate['frames']:>6} frames  "
                f"{mm:02d}:{ss:02d}  (q to stop)  "
            )
            sys.stdout.flush()
            if elapsed - last_status >= 30:
                last_status = time.time()
                sys.stdout.write(
                    f"\nREC status: {rstate['frames']} frames in {int(elapsed)}s, "
                    f"capture every {capture_interval:.3g}s\n"
                )
                sys.stdout.flush()

    reader_thread = threading.Thread(target=reader, daemon=True)
    writer_thread = threading.Thread(target=writer_loop, daemon=True)
    reader_thread.start()
    writer_thread.start()

    watcher = None
    if stdin_tty:
        watcher = threading.Thread(target=stdin_watcher, daemon=True)
        watcher.start()
    else:
        print("stdin not a terminal - stop with Ctrl+C or SIGTERM.", flush=True)

    start = time.time()
    status_thread = None
    output_printed = False
    while not stop_event.is_set():
        if args.duration is not None and time.time() - start >= args.duration:
            stop_info["stop"] = "--duration elapsed"
            break
        if not stream_ok:
            if not stop_info["stop"]:
                stop_info["stop"] = stop_info["stream"] or "camera stream ended"
            break
        if not output_printed and rstate["writer"] is not None:
            output_printed = True
            h, w = first_frame.shape[:2]
            print(
                f"Output: {rstate['path']} ({w}x{h} @ {args.fps:g} fps, "
                f"capture every {capture_interval:.3g}s)",
                flush=True,
            )
            if stdin_tty:
                print("Press q to stop and save.", flush=True)
            if sys.stdout.isatty():
                status_thread = threading.Thread(target=status_loop, daemon=True)
                status_thread.start()
        time.sleep(0.1)

    stop_event.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=2)
    if status_thread is not None:
        status_thread.join(timeout=2)
    if watcher is not None and os.name != "nt":
        watcher.join(timeout=2)
    if status_thread is not None:
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
    if mode == "raw":
        try:
            src.close()
        except Exception:
            pass
    elif not reader_thread.is_alive():
        src.release()

    elapsed = max(time.time() - start, 1e-9)
    if rstate["frames"] == 0:
        if not stream_ok or stop_info["stream"]:
            reason = stop_info["stream"] or "camera stream ended"
            print(
                f"Failed: camera stream ended before any frame was captured "
                f"({reason}). Nothing was saved.",
                flush=True,
            )
            sys.exit(1)
        print("Stopped before any frame was captured. Nothing was saved.", flush=True)
        return
    if not stop_info["stop"]:
        stop_info["stop"] = "stopped"
    final_path = rstate["path"]
    if final_path and os.path.exists(final_path):
        ext = os.path.splitext(final_path)[1]
        saved_path = _unique_path(
            os.path.join(
                args.output,
                f"timelapse_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}",
            )
        )
        try:
            os.rename(final_path, saved_path)
            final_path = saved_path
        except OSError:
            pass
    print(f"Stopped: {stop_info['stop']}.", flush=True)
    print(f"Saved {final_path or out_path}")
    print(
        f"{rstate['frames']} frames recorded over {elapsed:.0f}s at {args.fps:g} fps "
        f"-> {args.speed:g}x timelapse"
    )


def main():
    record(parse_args())


if __name__ == "__main__":
    main()