# IPLapse — GUI

**The GUI was removed.** IPLapse is CLI-only (`timelapse.py` — see `cli.md` and
`building-linux.md`). The tkinter launcher, its recorder-subprocess
orchestration, and the `--parent-pid` / `--stop-file` mechanisms no longer
exist. This document is kept as a record of what was removed; do not restore
the GUI without updating `design.md` and `cli.md`.

Recording happens only while a terminal runs `iplapse` (see
`building-linux.md`); closing the terminal stops it. There is no background
service.