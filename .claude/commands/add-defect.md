---
description: Step-by-step checklist for adding a new railway track defect type to the pipeline.
---

## Current defect types & cache version
!`grep -rn "NAME = \|CACHE_VERSION" app/geometry/defects/ app/geometry/cache/defective.py`

## Layout

Defects live in the `app/geometry/defects/` package. Each defect *family* is its
own sub-package: `base.py` (the family base class) + `defects.py` (concrete
subclasses) + `__init__.py` (re-exports). Examples: `rail_displacement/`,
`rail_vertical/`, `skewed_sleeper/`, `missing_fastener/`. The abstract `Defect`
base is in `defects/base.py`; the registry is `defects/registry.py`.

## Checklist

Work through these steps in order. Mark each done before moving to the next.

### 1. Define the defect

For a brand-new family, create `app/geometry/defects/<family>/` with `base.py`,
`defects.py`, `__init__.py`. For a variant of an existing family (e.g. another
rail bend), just add a subclass to that family's `defects.py`.

- Subclass `Defect` (`defects/base.py`) — or an existing family base such as
  `RailDisplacementDefect` to inherit its `variants()`/`span_groups()`/`apply()`.
- Set `NAME: str` — snake_case, unique, used as the cache key.
- Implement `variants()` — one `DefectVariant` per fixed parameter combination.
- Implement `apply(cls, section, params)` — mutate the `TrackSection`.
- For a **multi-section** defect (continuous over several sleepers), override
  `span_groups()` to return ordered position sequences; `DefectSelector` queues
  the follower positions automatically.

```python
class MyNewDefect(Defect):
    NAME = "my_new_defect"

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        return [DefectVariant(cls.NAME, {"param": value}, cls) for value in [...]]

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        # mutate section.left_rail, section.fasteners, etc.
        ...
```

Rail-bend families reuse `RailDisplacementDefect._bend_mesh(obj, entry, exit, axis)`
to shear a mesh continuously along its local Y (use `axis="x"` for lateral,
`axis="z"` for vertical); subclasses just set `NAME` and a `BENDS` list of
`(side, sign)` tuples.

### 2. Register it (`app/geometry/defects/registry.py`)

Import the class and add it to `ALL_DEFECTS`. Also re-export it from the family
`__init__.py` and (optionally) from `app/geometry/defects/__init__.py`.

```python
from app.geometry.defects.my_family import MyNewDefect

ALL_DEFECTS: List[type[Defect]] = [
    SkewedSleeperDefect,
    MissingFastenerPairDefect,
    ...,
    MyNewDefect,  # ← add here
]
```

### 3. Bump the cache version (`app/geometry/cache/defective.py`)

Increment `DefectiveSectionCache.CACHE_VERSION` by 1 so stale cached variants are
not reused.

### 4. Verify available `TrackSection` attributes

Check `track_section.py` for what `apply()` can mutate:
- `section.left_rail`, `section.right_rail` — rail mesh objects
- `section.left_sleeper`, `section.middle_sleeper`, `section.right_sleeper` — sleepers
- `section.fasteners` — list of fastener objects (indices 0,1 = outer-left pair;
  6,7 = outer-right pair). Remove with `bpy.data.objects.remove(..., do_unlink=True)`
  then `.pop()`.
- `section.config` — geometry config (`cfg.sleeper_length`, `cfg.section_pitch`,
  `cfg.sleeper_height`, rail config); use these instead of hard-coded dimensions.

### 5. Test with draft_quick

Force your defect onto every section for a quick visual check:

```bash
BLENDER_BIN=/home/crespina/blender-5.1.0-linux-x64/blender \
  ./runtime/draft_quick.sh -- --force-defect my_new_defect
```

Or run normally (10% random injection) and check the printed summary line — it
reports defect count and percentage. A new defect type increases the total
variant pool, so the effective rate per variant drops slightly (all variants are
equally likely within the 10% window).
