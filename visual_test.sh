#!/bin/bash
# Visual test: Pi -> UDP -> ffmpeg (low-delay decode) on this host; saves a JPEG per second and prints decoded-frame stats.
# Usage: LOCAL_IP=... PI_TARGET=user@pi [PI_PASS=...] ./visual_test.sh [WxH] [fps] [bitrate_bps] [outdir]
set -u
EXP_FLAGS=${EXP_FLAGS---shutter 8000 --gain 3.7}   # manual exposure = auto exposure off; EXP_FLAGS="" restores auto exposure
RES=${1:-1280x720}; FPS=${2:-60}; BR=${3:-8000000}; OUT=${4:-visual_out}; PORT=5990
W=${RES%x*}; H=${RES#*x}; mkdir -p "$OUT"; rm -f "$OUT"/*.jpg
SSH=(ssh); [ -n "${PI_PASS:-}" ] && SSH=(sshpass -p "$PI_PASS" ssh)
timeout -k 2 12 ffmpeg -hide_banner -loglevel info -fflags nobuffer -flags low_delay -probesize 32768 -analyzeduration 0 \
  -f h264 -i "udp://0.0.0.0:$PORT?fifo_size=5000000&overrun_nonfatal=1" \
  -vf fps=1 -q:v 3 "$OUT/f_%02d.jpg" -f null - 2> "$OUT/ffmpeg.log" &
sleep 1
"${SSH[@]}" "$PI_TARGET" "rpicam-vid -n -t 8000 --codec h264 --width $W --height $H --framerate $FPS --bitrate $BR \
  --flush --buffer-count 4 --denoise cdn_off $EXP_FLAGS --intra 30 --inline --profile baseline -o udp://$LOCAL_IP:$PORT" >/dev/null 2>&1
wait
echo "--- ffmpeg stats"; grep -E "Stream #0|error|corrupt|concealment|non-existing|frame=" "$OUT/ffmpeg.log" | tail -6 | tr '\r' '\n' | tail -6
ls "$OUT"/*.jpg
