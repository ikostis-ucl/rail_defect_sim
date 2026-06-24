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

All scripts accept extra `--` args forwarded to `config.py` (e.g. `--output-filename my_test.mp4`).

Output lands in `data/output/<run_name>/`.

## Architecture

```
run_video_gen.py          entrypoint (Blender calls this)
config.py                 CLI arg parsing → PipelineSettings
app/
  config/settings.py      PipelineSettings frozen dataclass
  core/pipeline.py        RailwayVideoPipeline — orchestrates everything
  geometry/
    track_section.py      TrackSection: builds one H-shaped section (rails + ballast + fasteners)
    track_section_cache.py  SectionCacheBase + TrackSectionCache (healthy prototypes)
    track_defects.py      Defect system: variants, cache, probabilistic selector
    track_builder.py      Builds the full track by instantiating cached sections
  camera/                 camera setup and animation
  materials/
    material_factory.py   Material abstract base + concrete types + MaterialFactory coordinator
  render/                 render settings + PNG→MP4 fallback via ffmpeg
  scene/                  scene/world/lighting setup
assets/
  track_section_cache/          healthy section prototypes (.blend files)
  track_section_cache/defective/  defective section prototypes (.blend files)
```

`RailwayVideoPipeline.run()` is the single execution path: clean scene → world → render settings → build track → lighting → camera → render → finalize output.

## Defect system

Defects are defined in `track_defects.py` as subclasses of `Defect`. Each declares a fixed set of `DefectVariant`s (pure data) and an `apply()` classmethod that mutates a `TrackSection`.

Current defect types:
- `SkewedBallastDefect` — ballast rotated ±2° or ±5° out of perpendicular
- `MissingFastenerPairDefect` — one of four fastener pairs removed

`DefectSelector.default()` probabilistically injects defects: **10% of sections** receive a randomly chosen variant. To add a new defect type, subclass `Defect` and add it to `ALL_DEFECTS`.

## Section caching

The first render builds section prototypes (healthy + one per defect variant) and writes them as `.blend` files under `assets/`. Subsequent renders load from disk. Cache keys are SHA-256 hashes of the geometry payload; bump `CACHE_VERSION` on `TrackSectionCache` or `DefectiveSectionCache` to invalidate stale cache files.

## Configuration

Settings flow: CLI args (or `TSV_TWIN_*` env vars) → `config.py` → `PipelineSettings` dataclass. All settings have defaults; CLI args only override when explicitly provided. A config file (yaml/ini/key=value) can be passed with `--config <path>` (requires `configargparse`, which is installed).

## Output

If the Blender build lacks a video codec, the render falls back to a PNG frame sequence and assembles it to MP4 via `ffmpeg`. If `ffmpeg` is not installed, the PNG sequence is kept as-is.
