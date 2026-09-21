# IPLapse — Requirements

## Runtime dependencies

| Requirement | Version / note | Purpose |
|---|---|---|
| Python | 3.12+ | Uses modern stdlib, `argparse` |
| opencv-python | latest | MJPEG decode, `cv2.VideoWriter` (H.264) |
| numpy | latest | Frame buffers, JPEG byte decoding |

Install with:

```bash
pip install -r requirements.txt
```

On Arch Linux prefer the distro packages `python-opencv` + `python-numpy`
(see [`building-linux.md`](building-linux.md)); `pip` is blocked by PEP 668
unless you use a venv.

## Camera source

Any **MJPEG-over-HTTP** endpoint. The documented target is the Android *IP
Webcam* app, which serves the stream at:

```
http://<phone-ip>:8080/video
```

Other sources `cv2.VideoCapture` can open (RTSP, local files) work via a
fallback path — see `design.md` → Stream reading strategy.

## Network

- PC and camera on the same network.
- The stream URL must be reachable from the machine running IPLapse.

## Platform notes

- The Python source is OS-agnostic; it is a **CLI-only** app (the GUI was
  removed).
- Packaging targets 64-bit Windows 10/11 (see `building.md`) and Arch
  Linux / other Linux (see `building-linux.md`); the code itself runs anywhere
  Python 3.12 + numpy + OpenCV run.