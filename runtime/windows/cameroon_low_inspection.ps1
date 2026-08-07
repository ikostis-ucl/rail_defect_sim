# Cameroon metre-gauge · low inspection view · 10 s @ 10 fps · slow pass
$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --config "$ProjectRoot\configs\camera\low_inspection.yml" `
    --fps 10 `
    --duration-seconds 10 `
    --resolution-x 960 `
    --resolution-y 540 `
    --render-engine BLENDER_EEVEE `
    --speed-kmh 5.4 `
    --camera-accel-seconds 0 `
    @args
