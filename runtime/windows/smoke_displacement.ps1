# Smoke test - right-rail lateral displacement defect
#
# Forces 100% displacement defect coverage so the defect is guaranteed to
# appear on every section. Camera moves slowly so the lateral bend is easy
# to observe frame by frame.
#
# Usage:
#   .\runtime\windows\smoke_displacement.ps1 [extra args]
#   $env:BLENDER_BIN = "C:\path\to\blender.exe"; .\runtime\windows\smoke_displacement.ps1
$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --fps 10 `
    --duration-seconds 5 `
    --resolution-x 640 `
    --resolution-y 360 `
    --track-length 500 `
    --base-speed-units-per-frame 0.08 `
    --force-defect right_rail_lateral_displacement `
    --output-filename smoke_displacement.mp4 `
    @args
