# runtime/windows/smoke_test.ps1
#
# Renders a short, slow-speed clip for visual sanity checking.
# 5 fps x 3 s = 15 frames at 640x360, camera speed 0.6 units/frame.
#
# Output: data/output/smoke_test/smoke_test.mp4
#
# Usage:
#   .\runtime\windows\smoke_test.ps1
#   $env:BLENDER_BIN = "C:\path\to\blender.exe"; .\runtime\windows\smoke_test.ps1
#   .\runtime\windows\smoke_test.ps1 --geometry-config configs/geometry/wide_gauge.yml
$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --fps 5 `
    --duration-seconds 3 `
    --resolution-x 640 `
    --resolution-y 360 `
    --render-engine BLENDER_EEVEE `
    --track-length 5000 `
    --base-speed-units-per-frame 0.6 `
    --output-filename smoke_test.mp4 `
    @args
