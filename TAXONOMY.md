# Track defect taxonomy

The vocabulary this project uses for track defects, track geometry, and the
parts of the track itself. One name per concept, in English, so that defect
class names, annotation labels, config fields, and documentation all agree.

## Provenance and authority

The defect list originates in the TSV *Dossier de Spécifications Système*
(chapter 2.3), which enumerates 38 track defects observed on the target
networks. That document is written by railway practitioners and is **not a
normative standard** — it is a useful survey of what actually gets found in the
field, and this project treats it as such.

Where the two disagree, **international standards win**:

- **EN 13848** — track geometry quality: which parameters exist, how they are
  measured, and over what wavelengths.
- **UIC / EN rail profiles** — rail cross-section dimensions (already modelled
  in `app/config/profiles.py`).

The source document's French vocabulary is not used. Its defect numbering is
kept in the tables below purely so a claim can be traced back to it.

The source document also assigns each defect a criticality, a frequency, and a
priority category. **Those are not modelled here.** They describe maintenance
urgency for a specific operator's network, which is neither a property of a
rendered image nor something a simulator can know. They are used only to order
the project's own work.

## Scope

This is a *track geometry* simulator. In scope: anything that changes the
**shape, position, presence, or surface** of the track itself — rails, sleepers,
fastenings, ballast.

Out of scope, and deliberately so:

- **Foreign objects and clearance intrusion** — objects that are not track.
- **Signalling and safety equipment** — a separate asset domain, and an object
  detection problem rather than a track geometry one.
- **Purely internal defects** with no surface expression (internal cleavage,
  subsurface shelling, cracks that have not yet broken the surface). These are
  ultrasonic and eddy-current findings. They are well defined and a simulator
  could carry their geometry, but they produce no optical signal, so they are
  deferred until a non-optical sensor model exists. The surface-breaking stage
  of the same defect *is* in scope.

## Track components

| Term | Meaning | Where it lives |
|---|---|---|
| **rail head** | the crown; the running surface a wheel contacts | `RailConfig.head_width` |
| **rail web** | the vertical section joining head to foot | not modelled separately |
| **rail foot** | the base flange resting on the sleeper | `RailConfig.foot_width` |
| **rail pad** | elastomeric pad between rail foot and sleeper | `RailConfig.pad_thickness` |
| **sleeper** | transverse beam carrying both rails (*tie* in US usage) | `sleeper_depth`, `sleeper_height` |
| **fastening** | the clip and screw securing rail to sleeper | `screw_radius`, `screw_length` |
| **ballast** | the stone bed supporting and confining the sleepers | not modelled yet |
| **sleeper bay** | the span between two consecutive sleepers | `sleeper_clear_gap` |

Prefer *sleeper* over *tie* and *fastening* over *fastener assembly*, but treat
them as synonyms when reading external sources.

## Measurement conventions

**Gauge** is the distance between the **inner faces of the two rail heads**,
measured at a defined depth below the running surface (14 mm in EN 13848-1).
It is *not* the centre-to-centre distance between rail centrelines — those
differ by one head width, so the two are not interchangeable when comparing
against a standard's limits.

> `TrackGeometryConfig.rail_spacing` is currently centre-to-centre and therefore
> does not match this definition. Reconciling it is tracked work.

**Nominal gauges**: 1435 mm standard, 1067 mm Cape, 1000 mm metre.

**Geometry defects are measured against a chord**, not in absolute space — a
versine over a fixed baseline. EN 13848-1 defines the wavelength bands:

| Band | Wavelength range | Notes |
|---|---|---|
| **D1** | 3 m < λ ≤ 25 m | the everyday inspection band |
| **D2** | 25 m < λ ≤ 70 m | longer, slower deviations |
| **D3** | 70 m < λ ≤ 150 m | high speed lines only |

A defect spanning 5 sections at 0.625 m pitch is ~3.1 m — the very bottom of D1.
Anything in D2 would need roughly 40 or more sections.

**Longitudinal / lateral / vertical** always mean: along the track, across the
track, and perpendicular to the plane of the rails, respectively.

## The geometry parameters

The five standard track geometry parameters, plus twist. These are what a
measurement vehicle records and what the geometry defects deviate from.

| Parameter | Meaning |
|---|---|
| **longitudinal level** | vertical deviation of a rail along the track, against a chord |
| **cross level** | height difference between the two rails at one point |
| **alignment** | lateral deviation of the track from its intended line |
| **gauge** | distance between the inner faces of the rail heads |
| **cant** (superelevation) | designed height difference between rails through a curve |
| **twist** (warp) | rate of change of cross level over a fixed base, typically 3 m |

Twist is absent from the source document's defect table but is a first-class
EN 13848 parameter and a direct derailment mechanism, so it is modelled here.

## Defect classes

Grouped by what the simulator has to *do* to produce them, since that determines
what infrastructure each one needs. `#` is the source document's number.

### A. Track geometry deformation
Deforming rail and sleeper meshes across a span of sections.

| # | Name | Implemented as |
|---|---|---|
| 3 | alignment defect | `both_rails_shift_left` / `_right` |
| 4 | gauge defect | `both_rails_gauge_widening` / `_narrowing`, per-rail lateral / inward |
| 1 | longitudinal level defect | `*_rail_vertical_bump` |
| 2 | cross level defect | single-rail vertical bump |
| — | twist defect | not implemented |
| 5 | cant deficiency / excess | not implemented; needs curved track |

### B. Component presence and integrity
Removing, splitting, or displacing whole objects.

| # | Name | Implemented as |
|---|---|---|
| 25 | broken rail | not implemented |
| 16 | missing sleeper | not implemented |
| 19 | complete sleeper failure | not implemented |
| 16 | displaced sleeper | `skewed_sleeper` (rotation only) |
| 17 | missing fastening | `missing_fastener_pair` |
| 18 | bent sleeper | not implemented |

### C. Ballast body
All require ballast geometry, which does not exist yet.

| # | Name |
|---|---|
| 9 | ballast settlement |
| 23 | hanging sleeper (voided support) |
| 10 | ballast lateral displacement / shoulder loss |
| 11 | ballast erosion / washout |
| 13 | vegetation encroachment |
| 12 | ballast fouling |
| 15 | ballast breakdown / excessive fragmentation |

The source document defines *hanging sleeper* (#23) dynamically, as a sleeper
that moves under a passing train. Here it is modelled by its static cause: a
void between sleeper and ballast.

### D. Rail profile and wear
Modifying the rail cross-section itself.

| # | Name |
|---|---|
| 24 | rail head wear (vertical and gauge-face) |
| 38 | plastic flow / lipping |
| 30 | corrugation |

### E. Surface and texture defects
Require the texture system, and a sub-millimetre imaging modality to be
meaningful targets.

| # | Name |
|---|---|
| 33 | squat |
| 36 | head checking |
| 32 | wheel-flat impact mark |
| 37 | wheel burn |
| 28 | weld defect (surface-breaking) |
| 20, 21 | sleeper cracking, end splitting |
| 34, 35 | shelling, spalling (surface-breaking) |
| 31 | grinding burn |

### Deferred — no optical signature

| # | Name |
|---|---|
| 26 | transverse head crack (internal stage) |
| 27 | longitudinal head crack (internal stage) |
| 29 | heat-affected zone crack |
| 22 | internal shakes / cleavage |
| 14 | ballast clogging (internal to the bed) |

### Excluded — not track

| # | Name |
|---|---|
| 6 | loading gauge intrusion |
| 7 | safety equipment missing or degraded |
| 8 | signalling equipment missing or degraded |

## Naming rules

- Defect `NAME` values are `snake_case` English, describing **what changed**,
  not what caused it: `broken_rail`, not `fatigue_fracture`.
- Where a defect can affect one rail or both, name the variant explicitly:
  `left_rail_…`, `right_rail_…`, `both_rails_…`.
- Use the standard parameter name when one exists. A defect in longitudinal
  level is a `longitudinal_level` defect, whatever mesh operation produces it.
- Component packages under `app/geometry/defects/` are named for the physical
  component: `rails/`, `sleepers/`, `fasteners/`, `ballast/`.
