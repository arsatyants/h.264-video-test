#!/bin/bash
# Runs the h.264-video-test benchmarks and stores the output in results/run_<timestamp>/.
#
#   LOCAL_IP=192.168.10.222 PI_TARGET=admin@192.168.10.85 [PI_PASS=...] ./run_tests.sh <test>...
#
# Tests:
#   bench          fps / CPU / RSS per codec and resolution, run on the Pi (no network)
#   udp            received Mbit/s over a UDP socket (yuv420 / h264 / mjpeg)
#   matrix         H.264: resolution x fps x target bitrate (36 runs, ~12 min)
#   latency        sensor timestamp -> UDP receive: default vs --flush vs low-latency flags
#   latency-flags  --buffer-count / --denoise / GOP variants
#   latency-exp    manual exposure, Wi-Fi power save off (needs sudo on the Pi), repeated twice
#   visual         decode the stream with ffmpeg and save a JPEG per second (visual_out/)
#   g2g            glass-to-glass: needs a display on this host and the camera pointed at its screen
#   cleanup        kill leftover ffmpeg / rpicam-vid and restore Wi-Fi power save
#   all            bench udp matrix latency latency-flags   (g2g, visual and latency-exp are interactive/intrusive: run them by name)
#   help           this text (also -h, --help)
#
# Environment:
#   LOCAL_IP     IP of this host as seen by the Pi (receiver of the UDP stream)   [required]
#   PI_TARGET    ssh target of the Pi, e.g. admin@192.168.10.85                    [required]
#   PI_PASS      ssh/sudo password; if unset, ssh keys are used (sshpass needed with PI_PASS)
#
# Examples:
#   ./run_tests.sh latency                  one test
#   ./run_tests.sh bench udp latency        several in a row
#   ./run_tests.sh all                      the main non-interactive set
set -u
cd "$(dirname "$(readlink -f "$0")")"

usage() { awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "$0"; }
[ $# -eq 0 ] && { usage; exit 1; }
case "$1" in help|-h|--help) usage; exit 0;; esac

: "${LOCAL_IP:?set LOCAL_IP to the IP of this host as seen by the Pi}"
: "${PI_TARGET:?set PI_TARGET, e.g. user@pi-host}"
export LOCAL_IP PI_TARGET
[ -n "${PI_PASS:-}" ] && export PI_PASS
SSH=(ssh -o ConnectTimeout=10); [ -n "${PI_PASS:-}" ] && SSH=(sshpass -p "$PI_PASS" ssh -o ConnectTimeout=10)
[ -n "${PI_PASS:-}" ] && ! command -v sshpass >/dev/null && { echo "sshpass not installed (needed with PI_PASS)"; exit 1; }
command -v ffmpeg >/dev/null || echo "warning: ffmpeg not found (needed for visual / g2g)"

OUT="results/run_$(date +%Y%m%d_%H%M%S)"; mkdir -p "$OUT"
echo "output: $OUT"

cleanup() {
  echo "== cleanup"
  pkill -9 -f '^ffmpeg.*udp://0.0.0.0:5990' 2>/dev/null
  "${SSH[@]}" "$PI_TARGET" 'pkill -x rpicam-vid; true' >/dev/null 2>&1
  # restore the Wi-Fi power-save default (on) in case latency-exp was interrupted
  [ -n "${PI_PASS:-}" ] && "${SSH[@]}" "$PI_TARGET" "echo '$PI_PASS' | sudo -S -p '' iw dev wlan0 set power_save on" >/dev/null 2>&1
  return 0
}

run() { # name command...
  local name=$1; shift
  echo "== $name  ($(date +%T))"
  "$@" 2>&1 | grep -v setlocale | tee "$OUT/$name.txt"
}

wanted=("$@"); [ "$1" = all ] && wanted=(bench udp matrix latency latency-flags)
cleanup >/dev/null
for t in "${wanted[@]}"; do
  case "$t" in
    bench)         run bench "${SSH[@]}" "$PI_TARGET" python3 - < local_bench.py ;;
    udp)           run udp python3 -I udp_bench.py ;;
    matrix)        run matrix python3 -I h264_matrix.py ;;
    latency)       run latency python3 -I latency_test.py ;;
    latency-flags) LAT_SET=flags run latency-flags python3 -I latency_test.py ;;
    latency-exp)   LAT_SET=exp REPEAT=2 run latency-exp python3 -I latency_test.py ;;
    visual)        run visual ./visual_test.sh 1280x720 60 8000000 "$OUT/visual" ;;
    g2g)           export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}
                   B="--flush --buffer-count 4 --denoise cdn_off"
                   run g2g-base python3 -I glass2glass.py base 16 $B; cleanup >/dev/null; sleep 2
                   run g2g-lowlat python3 -I glass2glass.py lowlat 16 $B --intra 30 --inline --profile baseline
                   echo "screenshots + clock log: g2g_out/ (read the nested clock by eye; see README)" ;;
    cleanup)       cleanup ;;
    *)             echo "unknown test: $t"; usage; exit 1 ;;
  esac
  cleanup >/dev/null
done
echo "done -> $OUT"
