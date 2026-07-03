# Render a 10-second demo clip for every camera placement in configs/camera/,
# with a very slow, near-constant camera glide (no acceleration ramp).
#
# Each clip lands in data/output/demo_<view>/demo_<view>.mp4.
#
# Usage:
#   .\runtime\windows\camera_demos.ps1
#   $env:BLENDER_BIN = "C:\path\to\blender.exe"; .\runtime\windows\camera_demos.ps1
# Tunable via env vars, e.g.:
#   $env:BASE_SPEED = "0.1"; $env:RES_X = "1280"; $env:RES_Y = "720"; .\runtime\windows\camera_demos.ps1
# Extra args are forwarded to every run (and override config values), e.g.:
#   .\runtime\windows\camera_demos.ps1 --force-defect both_rails_vertical_bump
$ErrorActionPreference = "Stop"
$BlenderBin = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Demo parameters - slow, smooth, near-constant glide.
$Fps         = if ($env:FPS)          { $env:FPS }          else { "24" }
$Duration    = if ($env:DURATION)     { $env:DURATION }     else { "10" }
$BaseSpeed   = if ($env:BASE_SPEED)   { $env:BASE_SPEED }   else { "0.15" }  # Blender units/frame - very slow
$Accel       = if ($env:ACCEL)        { $env:ACCEL }        else { "0" }     # seconds of ease-in; 0 = constant velocity
$ResX        = if ($env:RES_X)        { $env:RES_X }        else { "960" }
$ResY        = if ($env:RES_Y)        { $env:RES_Y }        else { "540" }
$TrackLength = if ($env:TRACK_LENGTH) { $env:TRACK_LENGTH } else { "1000" }  # long enough that the far end stays a vanishing point

$CameraDir = "$ProjectRoot\configs\camera"

$configs = @(Get-ChildItem -Path $CameraDir -Filter "*.yml" -File)
if ($configs.Count -eq 0) {
    Write-Error "No camera configs found in $CameraDir"
    exit 1
}

Write-Host "Rendering $($configs.Count) camera demos: ${Duration}s each, ${Fps}fps, "
Write-Host "speed=${BaseSpeed} u/frame, accel=${Accel}s, ${ResX}x${ResY}."

foreach ($cfg in $configs) {
    $name = $cfg.BaseName
    Write-Host ""
    Write-Host "=================================================================="
    Write-Host "  Camera demo: ${name}"
    Write-Host "=================================================================="
    & $BlenderBin `
        --background `
        --python "$ProjectRoot\run_video_gen.py" `
        -- `
        --config "$($cfg.FullName)" `
        --fps $Fps `
        --duration-seconds $Duration `
        --resolution-x $ResX `
        --resolution-y $ResY `
        --render-engine BLENDER_EEVEE `
        --track-length $TrackLength `
        --base-speed-units-per-frame $BaseSpeed `
        --camera-accel-seconds $Accel `
        --output-filename "demo_${name}.mp4" `
        @args
}

Write-Host ""
Write-Host "Done. Clips are under data/output/demo_<view>/."
