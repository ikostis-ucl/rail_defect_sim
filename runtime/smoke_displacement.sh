#!/usr/bin/env bash
# Smoke test — right-rail lateral displacement defect
#
# Forces 100% displacement defect coverage so the defect is guaranteed to
# appear on every section. Camera moves slowly so the lateral bend is easy
# to observe frame by frame.
#
# Usage:
#   ./runtime/smoke_displacement.sh [extra args]
#   BLENDER_BIN=/opt/blender/blender ./runtime/smoke_displacement.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER_BIN="${BLENDER_BIN:-blender}"

"${BLENDER_BIN}" --background --python "${SCRIPT_DIR}/../run_video_gen.py" -- \
  --fps 10 \
  --duration-seconds 5 \
  --resolution-x 640 \
  --resolution-y 360 \
  --track-length 500 \
  --base-speed-units-per-frame 0.08 \
  --force-defect right_rail_lateral_displacement \
  --output-filename smoke_displacement.mp4 \
  "$@"
