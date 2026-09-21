# IPLapse — Outputs

## Location

`default_output_dir()` resolves to:

```
<user home>/Videos/IPLapse
```

(uses `os.path.expanduser("~")`, so it is platform-appropriate everywhere). The
folder is created automatically on first recording.

## Naming

Videos are named after the **save time** — the moment recording stops and the
file is finalized:

```
timelapse_20260918_160350.mp4
```

The file is written under a temporary start-time name and renamed to the
save-time name on completion. If the name already exists, a counter is
appended — recordings never overwrite:

```
timelapse_20260918_160350.mp4
timelapse_20260918_160350 (2).mp4
```

## Format

Files are written as MP4. The codec fallback chain in `make_writer()`:

1. `avc1` → `.mp4` — H.264 (widest playback support)
2. `mp4v` → `.mp4` — MPEG-4 Part 2 (VLC-compatible)
3. `MJPG` → `.avi` — motion JPEG (last resort)

> Note: on a `python-opencv` pip wheel (bundled FFmpeg without `libx264`) the
> H.264 attempt fails and output falls back to `mp4v`. Distro `python-opencv`
> on Arch links system FFmpeg with `libx264`, so `avc1` works there
> (see `building-linux.md`).

## Verification

On completion, `record()` prints the final path and frame count to stdout, e.g.:

```
Saved /home/user/Videos/IPLapse/2026-09-18.mp4
120 frames recorded over 3600s at 30 fps -> 600x timelapse
```