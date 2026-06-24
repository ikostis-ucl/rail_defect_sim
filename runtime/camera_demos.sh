#!/usr/bin/env bash
#
# Render a 10-second demo clip for every camera placement in configs/camera/,
# with a very slow, near-constant camera glide (no acceleration ramp).
#
# Each clip lands in data/output/demo_<view>/demo_<view>.mp4.
#
# Usage:
#   BLENDER_BIN=/path/to/blender ./runtime/camera_demos.sh
# Tunable via env vars, e.g.:
#   BASE_SPEED=0.1 RES_X=1280 RES_Y=720 ./runtime/camera_demos.sh
# Extra args are forwarded to every run (and override config values), e.g.:
#   ./runtime/camera_demos.sh --force-defect both_rails_vertical_bump
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

# Demo parameters — slow, smooth, near-constant glide.
FPS="${FPS:-24}"
DURATION="${DURATION:-10}"
BASE_SPEED="${BASE_SPEED:-0.15}"      # Blender units/frame — very slow
ACCEL="${ACCEL:-0}"                   # seconds of ease-in; 0 = constant velocity
RES_X="${RES_X:-960}"
RES_Y="${RES_Y:-540}"
TRACK_LENGTH="${TRACK_LENGTH:-1000}"  # long enough that the far end stays a vanishing point

CAMERA_DIR="$PROJECT_ROOT/configs/camera"

shopt -s nullglob
configs=("$CAMERA_DIR"/*.yml)
if [ ${#configs[@]} -eq 0 ]; then
  echo "No camera configs found in $CAMERA_DIR" >&2
  exit 1
fi

echo "Rendering ${#configs[@]} camera demos: ${DURATION}s each, ${FPS}fps, "
echo "speed=${BASE_SPEED} u/frame, accel=${ACCEL}s, ${RES_X}x${RES_Y}."

for cfg in "${configs[@]}"; do
  name="$(basename "${cfg%.yml}")"
  echo ""
  echo "=================================================================="
  echo "  Camera demo: ${name}"
  echo "=================================================================="
  "$BLENDER_BIN" \
    --background \
    --python "$PROJECT_ROOT/run_video_gen.py" \
    -- \
    --config "$cfg" \
    --fps "$FPS" \
    --duration-seconds "$DURATION" \
    --resolution-x "$RES_X" \
    --resolution-y "$RES_Y" \
    --render-engine BLENDER_EEVEE \
    --track-length "$TRACK_LENGTH" \
    --base-speed-units-per-frame "$BASE_SPEED" \
    --camera-accel-seconds "$ACCEL" \
    --output-filename "demo_${name}.mp4" \
    "$@"
done

echo ""
echo "Done. Clips are under data/output/demo_<view>/."
