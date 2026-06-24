#!/usr/bin/env bash
# Cameroon metre-gauge · birds-eye view · 10 s @ 24 fps · slow pass
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

exec "$BLENDER_BIN" \
  --background \
  --python "$PROJECT_ROOT/run_video_gen.py" \
  -- \
  --config "$PROJECT_ROOT/configs/camera/birds_eye.yml" \
  --fps 10 \
  --duration-seconds 10 \
  --resolution-x 960 \
  --resolution-y 540 \
  --render-engine BLENDER_EEVEE \
  --track-length 1000 \
  --base-speed-units-per-frame 0.15 \
  --camera-accel-seconds 0 \
  "$@"
