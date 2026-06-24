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
    track_section.py      TrackSection: builds one H-shaped section (rails + sleepers + fasteners)
    defects/              Defect system (package): base, variant, per-defect modules, registry, selector
    cache/                Section caches (package): base, prototype (healthy), defective
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

Defects live in the `app/geometry/defects/` package, each as a subclass of `Defect` (`base.py`). Each declares a fixed set of `DefectVariant`s (pure data) and an `apply()` classmethod that mutates a `TrackSection`. Subclasses are collected in `registry.py` (`ALL_DEFECTS`).

Current defect types (the string is the `NAME`, used as the cache key and to force a defect):

| `NAME` | Class | Effect |
|---|---|---|
| `skewed_sleeper` | `SkewedSleeperDefect` | sleeper rotated ±2° or ±5° out of perpendicular |
| `missing_fastener_pair` | `MissingFastenerPairDefect` | one of four fastener pairs removed |
| `right_rail_lateral_displacement` | `RightRailLateralDisplacementDefect` | right rail bent outward (gauge widens right) |
| `left_rail_lateral_displacement` | `LeftRailLateralDisplacementDefect` | left rail bent outward (gauge widens left) |
| `left_rail_inward_displacement` | `LeftRailInwardDisplacementDefect` | left rail bent inward (toward centre) |
| `right_rail_inward_displacement` | `RightRailInwardDisplacementDefect` | right rail bent inward (toward centre) |
| `both_rails_gauge_widening` | `BothRailsGaugeWideningDefect` | both rails bend apart (gauge widens) |
| `both_rails_gauge_narrowing` | `BothRailsGaugeNarrowingDefect` | both rails bend together (gauge narrows) |
| `both_rails_shift_left` | `BothRailsShiftLeftDefect` | whole track bends left |
| `both_rails_shift_right` | `BothRailsShiftRightDefect` | whole track bends right |

The rail-displacement defects share a `RailDisplacementDefect` base (`rail_displacement.py`): the rail mesh is sheared along a half-sine arch over a **span** of consecutive sections (5 or 7) so the bend is continuous; the sleeper is translated rigidly (stays straight) and the outer fastener pair follows. A `(side, sign)` `BENDS` list drives which rail(s) bend and in which direction — one tuple = single rail, two tuples = both rails. Magnitude variants: 3 cm / 6 cm / 10 cm.

`DefectSelector.default()` probabilistically injects defects: **10% of sections** *start* a defect (`DEFECT_PROBABILITY`); multi-section spans then queue their follower positions automatically. To add a new defect type, subclass `Defect` (or `RailDisplacementDefect`), add it to `ALL_DEFECTS` in `registry.py`, and bump `DefectiveSectionCache.CACHE_VERSION`.

### Forcing a specific defect

There is no CLI flag yet — edit `DefectSelector.default()` in `selector.py` to register only the defect you want and raise the rate:

```python
selector.DEFECT_PROBABILITY = 1.0                      # every eligible section
for defect_class in ALL_DEFECTS:
    if defect_class.NAME != "both_rails_gauge_widening":  # ← your NAME from the table
        continue
    for span_group in defect_class.span_groups():
        selector.register_span(span_group)
```

Revert both changes to restore the random mix. At `1.0` the displacement spans run back-to-back; lower the probability for healthy track between occurrences.

## Section caching

The first render builds section prototypes (healthy + one per defect variant) and writes them as `.blend` files under `assets/`. Subsequent renders load from disk. Cache keys are SHA-256 hashes of the geometry payload; bump `CACHE_VERSION` on `TrackSectionCache` or `DefectiveSectionCache` to invalidate stale cache files.

## Configuration

Settings flow: CLI args (or `TSV_TWIN_*` env vars) → `config.py` → `PipelineSettings` dataclass. All settings have defaults; CLI args only override when explicitly provided. A config file (yaml/ini/key=value) can be passed with `--config <path>` (requires `configargparse`, which is installed).

## Output

If the Blender build lacks a video codec, the render falls back to a PNG frame sequence and assembles it to MP4 via `ffmpeg`. If `ffmpeg` is not installed, the PNG sequence is kept as-is.
