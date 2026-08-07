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

- **`app/config/` and `app/validation/` must never import `bpy`.**
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
  validation/             pre-render constraint checking, no bpy:
    context.py              ValidationContext — every config a rule may read
    derived.py              cross-config quantities (frame footprint, overlap, …)
    constraint.py           Constraint ABC + Interval + IntervalConstraint
    resolver.py             Resolver, Policy, ValidationReport, resolve_or_raise
    registry.py             CONSTRAINT_TYPES — the rules in force
    issue.py                Severity + ValidationIssue helpers
    constraints/            the rules themselves, one module per domain:
      geometry.py             impossible dimensions (migrated from validate())
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
tools/
  preflight.py            validate + summarise a config without launching Blender
assets/
  track_section_cache/          healthy section prototypes (.blend files)
  track_section_cache/defective/  defective section prototypes (.blend files)
```

`RailwayVideoPipeline.run()` is the single execution path: clean scene → world → render settings → build track → lighting → camera → render → finalize output.

## Validation

A run is checked **before Blender starts**, so an impossible or useless configuration
costs milliseconds instead of a full section-cache build plus render.

```bash
python tools/preflight.py -- --camera-height 6 --geometry-config configs/geometry/wide_gauge.yml
```

This is ordinary Python — no `blender` needed. It prints what the configuration
actually produces (frame footprint, frame overlap, longest defect, section count)
and exits 0 if usable, 1 if not, so a runtime script can gate a render on it.
`run_video_gen.run()` calls the same resolver as a safety net for direct
`blender --background --python` invocations; pass `validate=False` to skip it.

**How a rule is written.** Subclass `Constraint` (or `IntervalConstraint` when the
rule is "this quantity must lie in this range") and add it to `CONSTRAINT_TYPES` in
`app/validation/registry.py` — the same one-line pattern as `ALL_DEFECTS`. A rule
reads whatever it needs off `ValidationContext` (every config in one object) and
`app/validation/derived.py` (quantities that only exist *across* two configs, e.g.
frame footprint needs camera + render). Expressing a rule as an interval is what
makes automatic repair possible: the nearest legal value is just a clamp.

**Issues carry data, not just prose.** A `ValidationIssue` has a `message` for a
person and, alongside it, a **`code`** plus the numbers that produced it. The code is
the constraint's `NAME` — a stable identifier matched on like an exception type, so
rewording a message never breaks a caller:

```python
if issue.code == "rails_do_not_overlap":   # not: if "overlap" in issue.message
```

`IntervalConstraint` fills `code`, `value`, `expected_min`, `expected_max` and `unit`
automatically, so every interval rule reports its numbers for free. Codes are a
promise: renaming one is a breaking change.

`tools/preflight.py --json` prints the whole report plus the derived measurements as
data, which is what a UI or a CI job consumes.

**Policies.** `Policy.REPAIR` (default) adjusts the configuration to satisfy the
rules and reports every change; `Policy.STRICT` refuses without adjusting;
`Policy.WARN` reports and proceeds. Repair iterates to a fixpoint because one fix
can break another rule; if rules conflict, the resolver stops after `max_rounds`
and reports the conflict rather than spinning.

**Rules in force.** `constraints/geometry.py` holds the dimension checks that used
to sit unused in `TrackGeometryConfig.validate()` — positive rail and sleeper
heights, rails clearing both feet, fasteners that fit under the rail and inside the
sleeper, plus three "unusual but renderable" warnings. `validate()` now delegates
to them, so the standalone geometry view and the resolver cannot disagree. Still to
come: sleeper spacing, the camera rail-top datum, camera field of view, defect
observability, render budget.

Two rules of thumb the geometry module establishes:

- **Warnings never define `repair()`.** The resolver repairs anything repairable
  regardless of severity, so a repairable warning would let REPAIR quietly rewrite
  a configuration that was merely unusual.
- **Open bounds do not clamp.** "Height must be positive" has no nearest valid
  value — clamping gives an infinitesimal rail. Those repair to the dimension the
  *profile standard* specifies. Closed bounds (a clip radius with a largest
  acceptable value) clamp as normal.

`RailsDoNotOverlap` is deliberately **not** repairable: widening the gauge or
narrowing the rail feet each silently break a standard the config claims to
follow, so it fails the run and says why.

## Progress and cancellation

A run emits **events** (`app/progress/events.py`) once, and reporters render them for
whoever is watching. That split is why a headless VM and a UI can never disagree about
a run — they read the same events.

| Reporter | For |
|---|---|
| `ConsoleReporter` | a person, including over SSH: one line per phase, progress throttled to ~10 % steps |
| `JsonReporter` | a program: one JSON object per line, written to a **file** |
| `MultiReporter` | both at once |

```bash
./runtime/draft_quick.sh --progress-file /tmp/run.jsonl     # console + machine stream
./runtime/draft_quick.sh --quiet --progress-file /tmp/run.jsonl
./runtime/draft_quick.sh --verbose                          # per-asset cache detail
```

The machine stream goes to a file rather than stdout because **Blender writes copiously
to stdout** and a consumer cannot filter a stream it does not own. Console output is
deliberately quiet by default: per-asset cache lines are hundreds of lines on a large
track and are `--verbose` only.

**Phases, not just frames** — `scene`, `track`, `render`, `encode`. The first run of new
geometry builds hundreds of cached prototypes before a frame renders, so a frame-only
bar would sit at zero looking hung.

**Cancelling a run means killing the process.** A render runs as
`blender --background`, so whoever launched it — the UI, a shell, CI — stops it by
killing it. That works during the render itself, which nothing in-process can interrupt:
`bpy.ops.render.render(animation=True)` is a single blocking call.

Two things make killing safe, and they matter more than any graceful path:

- **Cache writes are atomic.** Prototypes are written to a temporary name and renamed
  into place, so a process dying mid-write leaves the cache consistent rather than
  leaving a truncated `.blend` the manifest still believes in.
- **A run clears its output directory before starting.** A killed run leaves numbered
  PNG frames behind, and ffmpeg assembles by pattern — so without this, leftovers from a
  longer previous run would be spliced onto the end of a later, shorter one. Clearing at
  the start covers every way a run can end, including `SIGKILL` and power loss, which no
  handler can catch.

`app/progress/cancel.py` additionally offers a **best-effort graceful stop**: SIGINT and
SIGTERM set a flag, checked at phase boundaries, which clears the output directory and
exits **130**. That is a courtesy for a console user pressing Ctrl-C between phases, not
the mechanism a UI should rely on.

## Defect system

**Vocabulary and scope live in `TAXONOMY.md`** — read it before naming a new defect
or arguing about what a term means. It fixes one English name per concept and records
which defects are in scope and which are deliberately not. Points that bite most often:

- **Gauge** is the distance between the **inner faces of the rail heads**, not
  centre-to-centre. `TrackGeometryConfig.rail_spacing` is currently centre-to-centre
  and so does not match the standard definition — reconciling it is tracked work.
- The standard geometry parameters are **longitudinal level, cross level, alignment,
  gauge, cant, twist**. Name defects after the parameter they deviate, whatever mesh
  operation produces them.
- Geometry defects are measured **against a chord**, over EN 13848 wavelength bands
  (**D1** = 3–25 m, D2 = 25–70 m, D3 = 70–150 m). **A span is not a wavelength**: the
  rail-bend waveform is a *half* sine, so our 5- and 7-section spans occupy ~3.1 m and
  ~4.4 m of track but have wavelengths of ~6.25 m and ~8.75 m. Span is also declared as
  a section *count*, so the physical wavelength silently changes with `section_pitch`.
- Foreign objects, signalling and safety equipment are **out of scope**; so are
  purely internal defects, until a non-optical sensor model exists.

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

### Units

A run is stated the way a person says it: **speed in km/h, duration in seconds,
resolution in pixels, distances in metres.**

```bash
./runtime/draft_quick.sh --speed-kmh 100 --duration-seconds 20
```

- `speed_kmh` is the only place a speed is stored. `speed_ms` and
  `metres_per_frame` are derived, never configured.
- **Frame rate does not change how fast the train moves.** It used to: speed was
  metres per *frame*, so raising fps from 12 to 25 for a smoother clip silently took
  the train from 108 km/h to 225 km/h. fps now changes only how finely the motion is
  sampled.
- **Track length is derived** from speed x duration plus a 10 % margin
  (`TRACK_LENGTH_MARGIN`), so the camera cannot be configured to run off the end of
  the built track. Override with `--track-length-m` / `--track-length-km` when a
  fixed-length track is wanted, typically for dataset generation.
- Every user-facing quantity carries its unit in its name (`_m`, `_km`, `_kmh`,
  `_deg`). Anything per-frame or in Blender units is internal and derived.

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
pytest              # 499 tests, ~1 s
```

Tests run in **plain Python, not Blender**: `tests/conftest.py` installs a `MagicMock` stub
for `bpy` before any app import, so geometry maths, config, defects, and cache logic are all
testable without launching Blender. Tests needing specific `bpy` behaviour patch the stub.
