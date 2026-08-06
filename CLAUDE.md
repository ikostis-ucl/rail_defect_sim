# tsv-twin

Procedural railway track renderer that generates synthetic video sequences of defective track for training defect-detection AI. Built on Blender's Python API (`bpy`).

Goal: cover **track-geometry deviations**, which are effectively absent from public railway datasets (those skew heavily toward rail-surface defects). Part of the Track Sentry Vision (TSV) project — see `docs/project_description.pdf`. Annotated output is the intended end state but is **not implemented yet** (see Output).

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

Alongside the quality presets, `runtime/` also holds:

| Script | Use for |
|---|---|
| `smoke_test.sh` | Minimal end-to-end run |
| `smoke_displacement.sh` | Forces `right_rail_lateral_displacement` at 100 %, slow camera — verifying a defect renders |
| `cameroon_birds_eye.sh`, `cameroon_windshield.sh`, `cameroon_roof_far.sh`, `cameroon_low_inspection.sh`, `cameroon_drone_three_quarter.sh` | Camera-angle demos on Cameroon metre gauge; each loads a `configs/camera/*.yml` |
| `camera_demos.sh` | Runs the whole camera-angle set in one go |

Every `.sh` has a PowerShell mirror in `runtime/windows/*.ps1`.

All scripts accept extra `--` args forwarded to `config.py` (e.g. `--output-filename my_test.mp4`).

Output lands in `data/output/<run_name>/`.

## Architecture

### The core split: config (data) vs builder (bpy)

Every domain is modelled twice — as a **frozen, `bpy`-free config dataclass**
describing *what* to build, and a **builder** that turns it into Blender objects:

| Domain | Config (no `bpy`) | Builder (`bpy`) |
|---|---|---|
| Track geometry | `TrackGeometryConfig` | `TrackSection` / `TrackBuilder` |
| Camera | `CameraConfig` | `CameraAnimator` |
| Environment | `EnvironmentConfig` (world, sun, ground) | `SceneSetup` / `TrackBuilder` |
| Surfaces | `AppearanceConfig` | `MaterialFactory` |
| Render | `RenderConfig` | `RenderSetup` |

`PipelineSettings` is the **composition root**: it owns one config per domain plus
run-level values (`track_length`, `seed`, `output_filename`, …).

**This split is load-bearing, not stylistic.** Constraint validation runs *before*
Blender launches, so anything it reads must import without `bpy`. Two rules keep
that true, both enforced by `tests/test_bpy_free_imports.py` (which blocks `bpy`
outright in a subprocess — the `conftest.py` stub would mask the coupling):

- **`app/config/` must never import `bpy`.**
- **Defect *metadata* must never import `bpy`.** `app/geometry/__init__.py` exports
  its builders lazily (PEP 562) and the defect modules import `TrackSection` only
  under `TYPE_CHECKING`, so `ALL_DEFECTS` is readable outside Blender. Only
  `Defect.apply()` needs Blender, and `fasteners` imports `bpy` inside the method.

### Expansibility rule

Write constraints and annotation logic against **derived quantities, never config
identities**. One `TrackInFrame` check reads `CameraConfig` and covers every camera
preset; one observability check reads `Defect.span_sections()` / `displacement_m()`
and covers every defect. `Defect` exposes that metadata uniformly on the base class,
so a 14th defect type needs no change to any consumer.

```
run_video_gen.py          entrypoint (Blender calls this)
config.py                 flat CLI args → nested per-domain configs
app/
  config/                 pure data, no bpy:
    settings.py             PipelineSettings — composition root
    render.py               RenderConfig (resolution, fps, duration, engine)
    camera.py               CameraConfig (pose, lens, sensor, height datum)
    environment.py          EnvironmentConfig (WorldConfig, SunConfig, GroundConfig)
    appearance.py           AppearanceConfig (per-surface colour/metallic/roughness)
    geometry.py             TrackGeometryConfig (+ RailConfig, derived quantities)
    profiles.py             RailProfileSpec catalog (YAML-overridable)
  core/pipeline.py        RailwayVideoPipeline — orchestrates everything
  geometry/
    track_section.py      TrackSection: builds one H-shaped section (rails + sleepers + fasteners)
    layout.py / utils.py  geometry helpers TrackSection.build() depends on
    cache/                section cache package:
      base.py               SectionCacheBase — shared get-or-create + prune flow
      fingerprint.py        automatic source-fingerprint versioning (no CACHE_VERSION)
      manifest.py           CacheManifest — cache_index.json inventory
      prototype.py          TrackSectionCache (healthy prototypes)
      defective.py          DefectiveSectionCache (defect variants)
    defects/              Defect system (package, bpy-free metadata): base, variant, registry, selector, plus per-component subpackages (rails/, fasteners/, sleepers/, ground/, ballast/)
    track_builder.py      Builds the full track by instantiating cached sections
  camera/                 CameraAnimator — builds/animates the camera from CameraConfig
  materials/              builders for surfaces:
    base.py                 Material ABC + PrincipledMaterial + NoiseBlendMaterial
    rail.py / sleeper.py / fastener.py / clip.py / grass.py   named types (NAME only)
    factory.py              MaterialFactory — pairs each type with its appearance
  render/                 render settings + PNG→MP4 fallback via ffmpeg
  scene/                  SceneSetup — world, units, lighting from EnvironmentConfig
configs/
  camera/                 camera pose presets (birds_eye, windshield, roof_far,
                          low_inspection, drone_three_quarter) — pass with --config
  geometry/               track geometry presets (default, cameroon_uic54, wide_gauge)
                          — pass with --geometry-config
  profiles/               rail profile specs (uic54, uic60, 115re) — auto-loaded at
                          import by app/config/profiles.py, overriding the built-in
                          dicts; no flag needed
assets/
  track_section_cache/          healthy section prototypes (.blend files)
  track_section_cache/defective/  defective section prototypes (.blend files)
```

`RailwayVideoPipeline.run()` is the single execution path: clean scene → world → render settings → build track → lighting → camera → render → finalize output.

## Defect system

Defects live in the `app/geometry/defects/` package, each as a subclass of `Defect` (`base.py`). Each declares a fixed set of `DefectVariant`s (pure data) and an `apply()` classmethod that mutates a `TrackSection`. Subclasses are collected in `registry.py` (`ALL_DEFECTS`).

Defects are grouped by physical **component** first, then by **family** (mechanism) within a component:

```
defects/
  rails/                 11 defects — the only component with more than one family so far
    rail_displacement/   base.py + defects.py — 8 lateral/inward bends
    rail_vertical/        base.py + defects.py — 3 vertical bumps
  fasteners/              1 defect — flat: defect.py directly (single mechanism)
  sleepers/               1 defect — flat: defect.py directly (single mechanism)
  ground/                 0 defects — placeholder package, no matching geometry in TrackSection yet
  ballast/                0 defects — placeholder package, no matching geometry in TrackSection yet
```

A single-mechanism component skips family-level nesting (`fasteners/defect.py`, not `fasteners/missing_fastener/defect.py`); it only grows a family subpackage once a second, genuinely different mechanism needs one. Each component's `__init__.py` re-exports everything under it, so `registry.py` imports through the component (e.g. `app.geometry.defects.rails`) rather than the family module directly.

Current defect types (the string is the `NAME`, used as the cache key and to force a defect):

| `NAME` | Class | Component | Effect |
|---|---|---|---|
| `skewed_sleeper` | `SkewedSleeperDefect` | sleepers | sleeper rotated ±2° or ±5° out of perpendicular |
| `missing_fastener_pair` | `MissingFastenerPairDefect` | fasteners | one of four fastener pairs removed |
| `right_rail_lateral_displacement` | `RightRailLateralDisplacementDefect` | rails | right rail bent outward (gauge widens right) |
| `left_rail_lateral_displacement` | `LeftRailLateralDisplacementDefect` | rails | left rail bent outward (gauge widens left) |
| `left_rail_inward_displacement` | `LeftRailInwardDisplacementDefect` | rails | left rail bent inward (toward centre) |
| `right_rail_inward_displacement` | `RightRailInwardDisplacementDefect` | rails | right rail bent inward (toward centre) |
| `both_rails_gauge_widening` | `BothRailsGaugeWideningDefect` | rails | both rails bend apart (gauge widens) |
| `both_rails_gauge_narrowing` | `BothRailsGaugeNarrowingDefect` | rails | both rails bend together (gauge narrows) |
| `both_rails_shift_left` | `BothRailsShiftLeftDefect` | rails | whole track bends left |
| `both_rails_shift_right` | `BothRailsShiftRightDefect` | rails | whole track bends right |
| `left_rail_vertical_bump` | `LeftRailVerticalBumpDefect` | rails | left rail bumps upward (lifts off sleeper) |
| `right_rail_vertical_bump` | `RightRailVerticalBumpDefect` | rails | right rail bumps upward (lifts off sleeper) |
| `both_rails_vertical_bump` | `BothRailsVerticalBumpDefect` | rails | both rails bump upward together |

The rail-displacement defects share a `RailDisplacementDefect` base (`rails/rail_displacement/base.py`): the rail mesh is sheared along a half-sine arch over a **span** of consecutive sections (5 or 7) so the bend is continuous; the sleeper is translated rigidly (stays straight) and the outer fastener pair follows. A `(side, sign)` `BENDS` list drives which rail(s) bend and in which direction — one tuple = single rail, two tuples = both rails. Lateral magnitude variants: 1.5 cm / 3 cm / 5 cm. The shear helper `_bend_mesh(obj, entry, exit, axis)` takes the target axis, so the **vertical bump** defects (`rails/rail_vertical/`) reuse the same machinery, bending in **+Z** instead of X — there the rail lifts off its seat (sleeper stays put) while the fasteners follow upward. Vertical magnitude variants are tuned independently (own `DISPLACEMENT_VARIANTS` on `RailVerticalDisplacementDefect`, not inherited): 3 cm / 6 cm / 10 cm.

`DefectSelector.default()` probabilistically injects defects: **10% of sections** *start* a defect (`DEFECT_PROBABILITY`); multi-section spans then queue their follower positions automatically. To add a new defect type, subclass `Defect` (or `RailDisplacementDefect`) and add it to `ALL_DEFECTS` in `registry.py` — the defective cache invalidates automatically (it fingerprints the `defects/` sources; see Section caching).

### Forcing a specific defect

Pass `--force-defect <NAME>` using a `NAME` from the table above. Every section then
receives that defect (100 % rate), with multi-section spans queued so the profile stays
continuous:

```bash
./runtime/draft_quick.sh --force-defect both_rails_gauge_widening
```

Omit the flag to restore the random mix at `DEFECT_PROBABILITY` (10 %). At 100 % the
displacement spans run back-to-back with no healthy track between occurrences.

### Defect rate

`--defect-rate <0..1>` sets the fraction of sections that *start* a defect
(**default 0.10**). This is the main dial for dataset composition — the balance of
healthy to faulty examples. Note multi-section spans then occupy their follower
sections too, so the share of *defective* sections lands several times higher
(~30 % at the default rate).

### Reproducibility

Defect placement is seeded: `--seed <int>`, **default 42**. The same seed and the same
settings always produce the same sequence of defects along the track. Vary the seed to
generate distinct datasets from otherwise identical settings:

```bash
./runtime/draft_quick.sh --seed 7
```

The seed is echoed at build time (`Defect placement seed: 42`) so a render's layout can be
traced back from its log. It governs *defect placement only*; camera vibration is driven
by Blender's own NOISE f-curve modifiers, which are configured separately in
`app/camera/camera_animator.py`.

## Section caching

The first render builds section prototypes (healthy + one per defect variant) and writes them as `.blend` files under `assets/`. Subsequent renders load from disk.

**Cache key** (the 16-char hash in a filename) is a SHA-256 of the geometry payload — it identifies a *geometry configuration* and is stable across code changes.

**Versioning is automatic.** Each cache fingerprints the source files that define its build logic (`SOURCE_PATHS` in `cache/prototype.py` / `cache/defective.py`) via `cache/fingerprint.py`. Editing any of those files changes the fingerprint, which marks every asset built by the old code as stale — there is **no `CACHE_VERSION` integer to bump by hand**. The only manual knob is `CACHE_FORMAT_VERSION` in `cache/fingerprint.py`, bumped *only* for cache-infrastructure/serialisation changes that source hashing can't capture.

**Manifest.** Each cache dir holds a `cache_index.json` (`cache/manifest.py`) recording every asset's key, fingerprint, params, and creation time. On construction each cache **auto-prunes** entries whose fingerprint no longer matches (deleting the stale `.blend`), drops entries whose `.blend` vanished, and logs any unmanaged orphan `.blend` files. Cached collections also embed their provenance as custom properties; on load the embedded fingerprint is re-checked against the manifest, so a `.blend` is self-describing and self-validating.

**Concurrency.** The cache assumes one render process per cache directory (the runtime scripts launch a single `blender --background` each). Two concurrent runs sharing `assets/track_section_cache/` can race on the manifest (last-writer-wins); the worst case is a regenerable `.blend` becoming an orphan and being rebuilt on next access — no corruption or data loss. Don't run parallel renders against the same cache dir without separate `cache_dir`s.

## Configuration

Settings flow: CLI args (or `TSV_TWIN_*` env vars) → `config.py` → `PipelineSettings` dataclass. All settings have defaults; CLI args only override when explicitly provided. A config file (yaml/ini/key=value) can be passed with `--config <path>` (requires `configargparse`, which is installed).

There are **two independent config channels** — don't confuse them:

- `--config <path>` → runtime settings (camera pose, fps, resolution). Presets in `configs/camera/`.
- `--geometry-config <path>` → track dimensions, parsed by `TrackGeometryConfig.from_yaml()`, never touched by `config.py`. Presets in `configs/geometry/`.

Both can be used in the same run:

```bash
./runtime/draft_quick.sh --config configs/camera/windshield.yml \
                        --geometry-config configs/geometry/cameroon_uic54.yml
```

## Output

A run produces **video only** — `data/output/<run_name>/<run_name>.mp4`. There is no
annotation/label sidecar yet: `TrackBuilder` knows each section's index, Y position, and
`DefectVariant`, but discards that after building. Emitting it is what turns these renders
into a trainable dataset (see the project proposal in `docs/project_description.pdf`).

If the Blender build lacks a video codec, the render falls back to a PNG frame sequence and assembles it to MP4 via `ffmpeg`. If `ffmpeg` is not installed, the PNG sequence is kept as-is.

## Tests

```bash
pytest              # 380 tests, ~0.5 s
```

Tests run in **plain Python, not Blender**: `tests/conftest.py` installs a `MagicMock` stub
for `bpy` before any app import, so geometry maths, config, defects, and cache logic are all
testable without launching Blender. Tests needing specific `bpy` behaviour patch the stub.
