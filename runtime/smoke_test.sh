#!/usr/bin/env bash
# runtime/smoke_test.sh
#
# Renders a short, slow-speed clip for visual sanity checking.
# 5 fps × 3 s = 15 frames at 640×360, camera speed 0.6 units/frame.
#
# Output: data/output/smoke_test/smoke_test.mp4
#
# Usage:
#   ./runtime/smoke_test.sh
#   BLENDER_BIN=/opt/blender/blender ./runtime/smoke_test.sh
#   ./runtime/smoke_test.sh --geometry-config configs/geometry/wide_gauge.yml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

exec "$BLENDER_BIN" \
  --background \
  --python "$PROJECT_ROOT/run_video_gen.py" \
  -- \
  --fps 5 \
  --duration-seconds 3 \
  --resolution-x 640 \
  --resolution-y 360 \
  --render-engine BLENDER_EEVEE \
  --track-length 5000 \
  --base-speed-units-per-frame 0.6 \
  --output-filename smoke_test.mp4 \
  "$@"
