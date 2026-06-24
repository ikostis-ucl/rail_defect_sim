---
description: Show all CACHE_VERSION constants in the codebase so you can bump them when geometry or defect logic changes. Use whenever TrackSection geometry, defect parameters, or cache serialisation logic changes.
---

## Current cache versions
!`grep -rn "CACHE_VERSION" app/`

## Cache directories
!`ls assets/track_section_cache/ 2>/dev/null && echo "---" && ls assets/track_section_cache/defective/ 2>/dev/null || echo "No cache files yet"`

## When to bump

| Changed | Bump |
|---|---|
| `TrackSection` geometry (dimensions, layout) | `TrackSectionCache.CACHE_VERSION` |
| `DefectVariant` params or `Defect.apply()` logic | `DefectiveSectionCache.CACHE_VERSION` |
| Both | Both |

## Instructions

Show the current version values from the grep output above. Ask which one(s) need bumping, then make the edit. Remind the user that old `.blend` files in `assets/` are harmless but can be deleted to reclaim disk space — the new versions will be rebuilt on the next run.
