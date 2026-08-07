#!/usr/bin/env bash
# Cameroon metre-gauge · drone three-quarter view · 10 s @ 10 fps · slow pass
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

exec "$BLENDER_BIN" \
  --background \
  --python "$PROJECT_ROOT/run_video_gen.py" \
  -- \
  --config "$PROJECT_ROOT/configs/camera/drone_three_quarter.yml" \
  --fps 10 \
  --duration-seconds 1 \
  --resolution-x 960 \
  --resolution-y 540 \
  --render-engine BLENDER_EEVEE \
  --speed-kmh 5.4 \
  --camera-accel-seconds 0 \
  "$@"
