# h.267-video-test

Benchmark of the video stream limits of a Raspberry Pi Zero 2 W with Camera Module 3 (IMX708):
frame rate, CPU load, and bitrate received over a UDP socket on another machine.

## Scripts
- `local_bench.py` — run **on the Pi** (`python3 local_bench.py`): fps / CPU / RSS per mode, output to `/dev/null`.
- `udp_bench.py` — run **on the receiving host**: opens a UDP socket per test, starts `remote_bench.py` on the Pi over ssh
  (`rpicam-vid -o udp://HOST:PORT`) and measures received Mbit/s in a steady 8 s window (after 5 s warm-up).

```
LOCAL_IP=192.168.x.y PI_TARGET=user@pi-host [PI_PASS=...] python3 udp_bench.py
```
Without `PI_PASS`, ssh keys are used. Requires `sshpass` only when `PI_PASS` is set.

## Findings (see `results/results.txt`)
- Hardware H.264 encoder (`bcm2835-codec`) accepts at most 1920x1920, so 2304x1296 and up fail to start. Practical limit: 1080p30 (or 720p60), ~7-9 % total CPU, ~10 Mbit/s.
- YUV420 is raw ISP output (no codec): negligible CPU, but gigabits/s. Over Wi-Fi it collapses to ~53 Mbit/s and 0.4-3.4 fps.
- MJPEG is encoded in software: 57-87 % total CPU; 4608x2592 reaches only ~12 fps.
- The name is as requested; the actual codec under test is H.264.
