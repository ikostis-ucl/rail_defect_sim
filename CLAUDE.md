# tsv-twin

Procedural railway track renderer that generates synthetic, annotated video sequences for AI training. Built on Blender's Python API (`bpy`).

## Critical: execution model

This project runs **inside Blender's Python interpreter**, not standalone Python. Never run `python run_video_gen.py` directly — it will fail because `bpy` is only available inside Blender.

The canonical invocation pattern is:

```bash
blender --background --python run_video_gen.py -- [args]
```

Use `BLENDER_BIN` to point at a non-default Blender binary:

```bash
BLENDER_BIN=/opt/blender/blender ./runtime/draft_quick.sh
```

## Running the pipeline

Use the preset scripts in `runtime/` — pick based on what you need:

| Script | Resolution | Duration | Use for |
|---|---|---|---|
| `draft_quick.sh` | 640×360 | 2 s | Fast iteration, checking geometry |
| `draft_preview.sh` | 960×540 | 20 s | Previewing a full sequence |
| `final_fullhd.sh` | 1920×1080 | 60 s | Production Full HD |
| `final_4k.sh` | 3840×2160 | 60 s | Production 4K |

All scripts accept extra `--` args that are forwarded to `config.py` (e.g. `--output-filename my_test.mp4`).

Output lands in `data/output/<run_name>/`.

## Architecture

```
run_video_gen.py          entrypoint (Blender calls this)
config.py                 CLI arg parsing → PipelineSettings
app/
  config/settings.py      PipelineSettings frozen dataclass
  core/pipeline.py        RailwayVideoPipeline — orchestrates everything
  geometry/               track geometry: sections, defects, builder, cache
  camera/                 camera setup and animation
  materials/              material factory
  render/                 render settings + PNG→MP4 fallback via ffmpeg
  scene/                  scene/world/lighting setup
```

`RailwayVideoPipeline.run()` is the single execution path: clean scene → world → render settings → build track → lighting → camera → render → finalize output.

## Configuration

Settings flow: CLI args (or `TSV_TWIN_*` env vars) → `config.py` → `PipelineSettings` dataclass → passed into pipeline. All settings have defaults in `PipelineSettings`; CLI args only override when explicitly provided.

A config file (yaml/ini/key=value) can be passed with `--config <path>` (requires `configargparse`, which is installed).

## Output

If the Blender build lacks a video codec, the render falls back to a PNG frame sequence and assembles it to MP4 via `ffmpeg`. If `ffmpeg` is not installed, the PNG sequence is kept as-is.
