#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

exec "$BLENDER_BIN" \
  --background \
  --python "$PROJECT_ROOT/run_video_gen.py" \
  -- \
  --fps 24 \
  --duration-seconds 20 \
  --resolution-x 960 \
  --resolution-y 540 \
  --render-engine BLENDER_EEVEE \
  --speed-kmh 216 \
  "$@"

