$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& $BlenderBin `
    --background `
    --python "$ProjectRoot\run_video_gen.py" `
    -- `
    --fps 24 `
    --duration-seconds 20 `
    --resolution-x 960 `
    --resolution-y 540 `
    --render-engine BLENDER_EEVEE `
    --track-length 20000 `
    --base-speed-units-per-frame 2.5 `
    @args
