# h.264-video-test

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

## H.264 matrix: resolution x fps x target bitrate (UDP, `h264_matrix.py`)

Steady 8 s window after 5 s warm-up; recv = UDP payload at the receiver. Static scene, so the encoder undershoots the target at low fps/resolution.

| Resolution | req fps | target Mbit/s | fps | CPU total % | rpicam-vid % (of 400) | recv Mbit/s |
|---|---|---|---|---|---|---|
| 1920x1080 | 60 | 8 | 36.3 | 8 | 29 | 4.82 |
| 1920x1080 | 60 | 4 | 36.5 | 9 | 31 | 2.40 |
| 1920x1080 | 60 | 2 | 36.5 | 8 | 31 | 1.21 |
| 1920x1080 | 30 | 8 | 29.1 | 9 | 31 | 7.73 |
| 1920x1080 | 30 | 4 | 30.0 | 9 | 31 | 3.98 |
| 1920x1080 | 30 | 2 | 28.3 | 8 | 29 | 1.90 |
| 1920x1080 | 15 | 8 | 15.0 | 5 | 18 | 4.26 |
| 1920x1080 | 15 | 4 | 15.0 | 5 | 17 | 4.21 |
| 1920x1080 | 15 | 2 | 15.0 | 4 | 17 | 2.07 |
| 1280x720 | 60 | 8 | 59.0 | 11 | 38 | 7.86 |
| 1280x720 | 60 | 4 | 58.3 | 10 | 36 | 3.88 |
| 1280x720 | 60 | 2 | 58.4 | 9 | 34 | 1.95 |
| 1280x720 | 30 | 8 | 30.0 | 6 | 24 | 6.06 |
| 1280x720 | 30 | 4 | 30.0 | 6 | 23 | 4.02 |
| 1280x720 | 30 | 2 | 30.0 | 6 | 22 | 2.01 |
| 1280x720 | 15 | 8 | 15.0 | 3 | 11 | 1.14 |
| 1280x720 | 15 | 4 | 15.0 | 3 | 11 | 1.14 |
| 1280x720 | 15 | 2 | 15.0 | 3 | 11 | 1.15 |
| 960x540 | 60 | 8 | 60.1 | 9 | 34 | 7.99 |
| 960x540 | 60 | 4 | 60.1 | 9 | 32 | 4.03 |
| 960x540 | 60 | 2 | 60.1 | 9 | 32 | 2.00 |
| 960x540 | 30 | 8 | 30.0 | 6 | 21 | 2.58 |
| 960x540 | 30 | 4 | 30.0 | 5 | 20 | 2.62 |
| 960x540 | 30 | 2 | 30.0 | 5 | 20 | 1.99 |
| 960x540 | 15 | 8 | 15.0 | 3 | 10 | 0.58 |
| 960x540 | 15 | 4 | 15.0 | 3 | 10 | 0.65 |
| 960x540 | 15 | 2 | 15.0 | 3 | 10 | 0.66 |
| 640x480 | 60 | 8 | 60.1 | 9 | 31 | 7.93 |
| 640x480 | 60 | 4 | 60.1 | 8 | 30 | 4.01 |
| 640x480 | 60 | 2 | 60.1 | 8 | 30 | 2.00 |
| 640x480 | 30 | 8 | 30.0 | 5 | 19 | 1.60 |
| 640x480 | 30 | 4 | 30.0 | 5 | 19 | 1.65 |
| 640x480 | 30 | 2 | 30.0 | 5 | 19 | 1.64 |
| 640x480 | 15 | 8 | 15.0 | 2 | 9 | 0.20 |
| 640x480 | 15 | 4 | 15.0 | 3 | 9 | 0.20 |
| 640x480 | 15 | 2 | 15.0 | 3 | 9 | 0.20 |

## Local and UDP tables (all codecs)

```
Raspberry Pi Zero 2 W + Camera Module 3 (IMX708), libcamera v0.7.2, rpicam-vid, 15 s/test, window 5-13 s
Local (no network), 4 cores:
codec  res         req    fps  sysCPU%  proc%(of 400)  RSS_MB  temp
yuv420 1536x864    120   62.2        7             31      62  40.2
yuv420 2304x1296    56   31.5        7             26      62  40.8
yuv420 4608x2592    14   14.0        9             34      29  41.9
h264   1280x720     60   59.5        9             34      60  42.4
h264   1728x972     30   30.0        7             27      58  42.9
h264   1920x1080    30   29.0        7             28      60  43.5
h264   1920x1080    60   36.5        8             29      61  44.0
mjpeg  1536x864    120   61.8       57            226      62  47.2
mjpeg  2304x1296    56   30.9       62            244      62  49.4
mjpeg  4608x2592    14   12.1       84            336      47  51.0
h264 2304x1296 and 1536x864@120: fail to start (bcm2835-codec max 1920x1920)

Over UDP via Wi-Fi to a LAN host (udp_bench.py):
codec  res         req    fps  sysCPU%  proc%  recv_Mbit/s  pkts/s
yuv420 1536x864    120    3.4        7      9         53.7     104
yuv420 2304x1296    56    1.5        6      7         53.1     102
yuv420 4608x2592    14    0.4        5      6         54.8     105
h264   1280x720     60   59.8       12     39         10.0      60
h264   1728x972     30   30.0        9     31         10.0      30
h264   1920x1080    30   29.0        9     32          9.5      29
h264   1920x1080    60   36.4        9     33          6.0      37
mjpeg  1536x864    120   59.9       59    225         35.5     120
mjpeg  2304x1296    56   30.9       64    246         34.5      92
mjpeg  4608x2592    14   12.0       87    335         22.2      48
```
