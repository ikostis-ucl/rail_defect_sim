---
description: Inspect the section cache — fingerprints, manifests, and how automatic versioning works. Use when geometry/defect logic changes and you want to confirm the cache will invalidate, or to audit what is cached on disk.
---

## How versioning works now (automatic)

There is **no `CACHE_VERSION` integer to bump**. Each cache fingerprints the
source files that define its build logic. Editing any of them changes the
fingerprint, so assets built by the old code are detected as stale, pruned, and
rebuilt on the next run.

| Changed | Effect |
|---|---|
| `TrackSection` geometry (`app/geometry/track_section.py`) | prototype **and** defective caches invalidate |
| A defect's `apply()` / params (`app/geometry/defects/*.py`) | defective cache invalidates |
| Cache build/serialisation (`cache/base.py`, `prototype.py`, `defective.py`) | the relevant cache invalidates |

The only manual knob is `CACHE_FORMAT_VERSION` in
`app/geometry/cache/fingerprint.py` — bump it **only** for cache-infrastructure
or serialisation-format changes that source hashing cannot capture.

## Source files in each fingerprint
!`grep -rn "SOURCE_PATHS\|_SOURCE_FILES\|CACHE_FORMAT_VERSION" app/geometry/cache/`

## Current cache inventory (manifests)
!`for f in assets/track_section_cache/cache_index.json assets/track_section_cache/defective/cache_index.json; do echo "=== $f ==="; cat "$f" 2>/dev/null || echo "(none yet)"; done`

## Cache files on disk
!`ls assets/track_section_cache/ 2>/dev/null && echo "---" && ls assets/track_section_cache/defective/ 2>/dev/null || echo "No cache files yet"`

## Instructions

Read the manifests and source-file lists above. To force a full rebuild, delete
the cache dirs (they are gitignored and regenerable) or bump
`CACHE_FORMAT_VERSION`. Stale files are pruned automatically on the next run;
"orphan" `.blend` files (not in a manifest) are logged and safe to delete.
