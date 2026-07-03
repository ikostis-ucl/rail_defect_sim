# Cameroon metre-gauge · birds-eye view · 10 s @ 10 fps · slow pass
$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --config "$ProjectRoot\configs\camera\birds_eye.yml" `
    --fps 10 `
    --duration-seconds 10 `
    --resolution-x 960 `
    --resolution-y 540 `
    --render-engine BLENDER_EEVEE `
    --track-length 1000 `
    --base-speed-units-per-frame 0.15 `
    --camera-accel-seconds 0 `
    @args
