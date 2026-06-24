---
description: Step-by-step checklist for adding a new railway track defect type to the pipeline.
---

## Current defect types
!`grep -rn "class.*Defect\|ALL_DEFECTS" app/geometry/defects/`

## Checklist

Work through these steps in order. Mark each done before moving to the next.

### 1. Define the defect class (`app/geometry/track_defects.py`)

- Subclass `Defect`
- Set `NAME: str` — snake_case, unique, used as the cache key
- Implement `variants()` — return a list of `DefectVariant` objects, one per fixed parameter combination
- Implement `apply(cls, section, params)` — mutate the `TrackSection` objects /lin(rails, ballast pieces, fasteners) to represent the defect

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

### 2. Register it (`app/geometry/track_defects.py`)

Add the new class to `ALL_DEFECTS`:

```python
ALL_DEFECTS: List[type[Defect]] = [
    SkewedBallastDefect,
    MissingFastenerPairDefect,
    MyNewDefect,  # ← add here
]
```

### 3. Cache invalidation (automatic — nothing to do)

Cache versioning is automatic: the defective cache fingerprints the defect
source files, so adding/editing a defect module invalidates stale cached
variants on the next run. There is no `CACHE_VERSION` to bump. (See the
`bump-cache` skill for details.)

### 4. Verify available `TrackSection` attributes

Check `track_section.py` for what `apply()` can mutate:
- `section.left_rail`, `section.right_rail` — rail mesh objects
- `section.left_ballast`, `section.middle_ballast`, `section.right_ballast` — ballast pieces
- `section.fasteners` — list of fastener objects (remove with `bpy.data.objects.remove(..., do_unlink=True)` then `.pop()`)

### 5. Test with draft_quick

```bash
./runtime/draft_quick.sh
```

Check the printed summary line — it reports defect count and percentage. A new defect type increases the total variant pool, so the effective rate per variant drops slightly (all variants are equally likely within the 10% window).
