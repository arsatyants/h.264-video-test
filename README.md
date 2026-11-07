# h.264-video-test

Measurements of the real-time video streaming limits of a **Raspberry Pi Zero 2 W with Camera Module 3 (IMX708)**:
how many frames per second and which resolutions the board can produce, how much CPU each codec costs, how much bitrate gets
through a UDP socket over Wi-Fi, how to tune the pipeline for low latency, and the end-to-end (glass-to-glass) delay.

**Setup:** Pi Zero 2 W (Raspberry Pi OS, libcamera / `rpicam-vid`) sends video over Wi-Fi via UDP to a Raspberry Pi 5 on the same LAN.
Codecs under test: raw YUV420 (ISP output), hardware H.264 (`bcm2835-codec`) and software MJPEG.

## Key results
- Hardware H.264 works up to **1920x1080@30** (or 720p@60); wider than 1920 px fails to start. It costs only ~7-12 % total CPU and ~10 Mbit/s.
- Raw YUV420 is gigabits/s and collapses to ~53 Mbit/s and 0.4-3.4 fps over Wi-Fi. MJPEG is encoded on the CPU (57-87 % load).
- Pipeline latency (sensor timestamp -> UDP receive) is ~180 ms at 1080p30 by default and drops to ~45-90 ms with
  `--flush --buffer-count 3-4 --denoise cdn_off`; the camera then drops frames instead of buffering them.
- Glass-to-glass at 720p60: **179 ms** by default, **139 ms** with the low-latency flags.

## Files
| File | Where it runs | Purpose |
|---|---|---|
| `local_bench.py` | Pi Zero | fps / CPU / RSS per codec and resolution, output to `/dev/null` |
| `udp_bench.py` + `remote_bench.py` | receiving host (starts the Pi side over ssh) | received Mbit/s over a UDP socket per mode |
| `h264_matrix.py` | receiving host | H.264 matrix: resolution x fps x target bitrate |
| `latency_test.py` + `remote_latency.py` | receiving host | per-frame latency: sensor timestamp -> UDP receive (clock offset by UDP ping-pong) |
| `glass2glass.py` | host with a display (Pi 5) | on-screen stopwatch + live video; camera looks at the screen |
| `visual_test.sh` | receiving host | decodes the stream with ffmpeg low-delay and saves a JPEG per second |
| `results/` | | raw result tables and zoomed glass-to-glass evidence |

## Requirements
Pi Zero side: `rpicam-apps`, Python 3. Host side: Python 3, `ffmpeg`, `sshpass` (only if you use `PI_PASS`); `glass2glass.py` also needs `pygame`.
All host scripts read the environment: `LOCAL_IP` (host IP seen by the Pi), `PI_TARGET` (`user@pi-host`), optional `PI_PASS` (otherwise ssh keys).

```
LOCAL_IP=192.168.x.y PI_TARGET=user@pi-host [PI_PASS=...] python3 udp_bench.py
LOCAL_IP=... PI_TARGET=... python3 h264_matrix.py
LOCAL_IP=... PI_TARGET=... [LAT_SET=flags] python3 latency_test.py
LOCAL_IP=... PI_TARGET=... python3 glass2glass.py TAG SECONDS [rpicam-vid flags]   # run in a graphical session
```

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

## Low latency (`latency_test.py`, `visual_test.sh`)
`--low-latency` only affects the software libav encoder. For the hardware H.264 encoder the useful knobs are
`--flush`, a small `--buffer-count` (bounds the queue: the camera drops frames instead of buffering them),
`--denoise cdn_off`, `--intra 30 --inline --profile baseline`. Per-frame latency is measured sensor timestamp -> UDP receive
(clock offset to the Pi estimated by UDP ping-pong and subtracted). Full tables: `results/latency.txt`.

Findings (8 Mbit/s target):
- Default `--buffer-count` queues ~6 frames: 1080p30 = ~184 ms, 1080p60 (encoder overload, 36 fps) = ~153 ms, 720p60 = ~77 ms.
- `--buffer-count` trades fps for latency directly: at 1080p30 bc4 = 28 fps / 119 ms, bc3 = 22.5 fps / 107 ms, bc2 = 15 fps / 105 ms. Too small a value starves the ISP->encoder pipeline.
- `--denoise cdn_off` gives a further ~10-20 ms; GOP/baseline/inline barely changes latency (but gives fast recovery after loss).
- Best combos: 1080p60 request (36 fps real) with full low-latency flags = 67 ms; 720p60 bc4 = 57 ms @ 54 fps; 720p60 bc3+cdn_off = 48 ms @ 45 fps.
- Latency does not grow over time in any run (drift ~0), i.e. no unbounded buffer accumulation.
- Visual check: `./visual_test.sh 1280x720 60` decodes the stream with `ffmpeg -fflags nobuffer -flags low_delay` and saves a JPEG/s.
  Live view: `ffplay -fflags nobuffer -flags low_delay -framedrop -probesize 32 -analyzeduration 0 -f h264 udp://0.0.0.0:5990`.

### Latency on a scene with motion (`results/latency_motion.txt`)
Camera turned away from the wall (person, ceiling, chandelier in view), same `latency_test.py` "main" set, 8 Mbit/s target.
Latency (median, ms) static -> with motion: 1080p30 default 184 -> 175, lowlat 154 -> 90 (25 fps); 1080p60 default 153 -> 157, lowlat 67 -> 85;
720p60 default 77 -> 93, lowlat 44 -> 46 (46 fps); 640x480@60 31 ms for all configs. No unbounded drift. Latency barely depends on the scene;
bitrate does (the static dim scene was sensor-noise-heavy, so it was not a reliable motion indicator).

## Glass-to-glass (`glass2glass.py`, `results/glass2glass.txt`)
The Pi 5 screen shows a ms stopwatch (plus moving stripes/ball) and the live decoded video in a red frame; the camera looks at that
screen, so the video contains the stopwatch as it was at capture. latency = clock now - clock seen in the video (read from zoomed
screenshots, +-15 ms). 720p60, 8 Mbit/s, mean of 6 shots: **default 179 ms** (151-191), **low-latency flags 139 ms** (119-154).
The ~40 ms gain matches the sensor-timestamp -> UDP measurement. Includes exposure, encode, Wi-Fi, decode (ffmpeg low-delay),
scaling and drawing plus one panel latency; the last panel latency is not included. Zoomed evidence: `results/g2g_strips_*.png`.
Gotcha: kill leftover `ffmpeg` / remote `rpicam-vid` between runs (they hold UDP port 5990 / the camera).

## Experiments: manual exposure, Wi-Fi power save, MPEG-TS 188-byte packets (`results/low_latency_experiments.txt`)
720p60, 8 Mbit/s, base flags `--flush --buffer-count 4 --denoise cdn_off`.
- **Manual exposure** (`--shutter 8000 --gain 3.7`; auto exposure used the whole 16.2 ms frame period): sensor->UDP latency 47 ms either way;
  glass-to-glass 141 -> 139 ms, i.e. no gain resolvable within the +-15 ms reading error (digits are visibly sharper, less motion blur).
- **Wi-Fi power save off** (`iw dev wlan0 set power_save off`): median 47 ms both ways; p95 52-54 -> 52-54, max 65-89 ms. With a steady 60 pkt/s
  stream the radio is never idle, so power save does not add latency here. One base run had a 96 ms outlier (drift 50 ms) that did not repeat.
- **MPEG-TS, `pkt_size=1316` (7x188)** via `--codec libav --libav-format mpegts` (hardware encoder through libav): glass-to-glass
  **163 ms vs 141 ms** for raw H.264 over UDP, i.e. ~20 ms worse. This mode also writes no per-frame metadata, so only glass-to-glass could be measured.
Conclusion: the dominant levers remain `--buffer-count` and resolution/fps; the three tested options do not reduce latency further.

## Auto exposure off
Setting both `--shutter` and `--gain` disables auto exposure in `rpicam-vid` (verified on the Pi: 171 frames, exposure fixed at 7993 us,
gain 3.7, `AeState` 0). Recommended low-latency set with fixed exposure:
```
rpicam-vid -n -t 0 --codec h264 --width 1280 --height 720 --framerate 60 --bitrate 8000000 \
  --flush --buffer-count 4 --denoise cdn_off --shutter 8000 --gain 3.7 --intra 30 --inline --profile baseline -o udp://HOST:PORT
```
Pick `--shutter` <= one frame period (16.6 ms at 60 fps) and raise `--gain` as the light drops; fixed exposure never lowers the frame rate
in the dark, but the image will be darker or noisier instead. `visual_test.sh` uses these values by default (`EXP_FLAGS=""` restores auto exposure).
