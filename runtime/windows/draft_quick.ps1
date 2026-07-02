$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --fps 10 `
    --duration-seconds 2 `
    --resolution-x 640 `
    --resolution-y 360 `
    --render-engine BLENDER_EEVEE `
    --track-length 8000 `
    --base-speed-units-per-frame 2.0 `
    @args
