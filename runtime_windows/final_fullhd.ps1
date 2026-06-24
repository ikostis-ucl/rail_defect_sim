$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent $PSScriptRoot

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --fps 30 `
    --duration-seconds 60 `
    --resolution-x 1920 `
    --resolution-y 1080 `
    --render-engine BLENDER_EEVEE `
    --track-length 100000 `
    --base-speed-units-per-frame 2.5 `
    @args
