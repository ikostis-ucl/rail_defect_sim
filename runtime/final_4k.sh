#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

exec "$BLENDER_BIN" \
  --background \
  --python "$PROJECT_ROOT/run_video_gen.py" \
  -- \
  --fps 30 \
  --duration-seconds 60 \
  --resolution-x 3840 \
  --resolution-y 2160 \
  --render-engine BLENDER_EEVEE \
  --speed-kmh 270 \
  "$@"

