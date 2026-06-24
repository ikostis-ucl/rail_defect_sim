#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

exec "$BLENDER_BIN" \
  --background \
  --python "$PROJECT_ROOT/run_video_gen.py" \
  -- \
  --fps 10 \
  --duration-seconds 2 \
  --resolution-x 640 \
  --resolution-y 360 \
  --render-engine BLENDER_EEVEE \
  --track-length 8000 \
  --base-speed-units-per-frame 2.0 \
  "$@"

