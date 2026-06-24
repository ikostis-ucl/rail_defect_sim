"""Automatic cache versioning via source-code fingerprints.

The cache key (the 16-char hash in a ``.blend`` filename) identifies a
*geometry configuration* — it is derived purely from parameters and stays
stable across code changes.  The *fingerprint* defined here identifies the
*build logic* that turns those parameters into geometry: it is the SHA-256 of
the source files responsible for the build.

Together they replace the old hand-maintained ``CACHE_VERSION`` integers:
changing any relevant source file changes the fingerprint, which marks every
cached asset built by the old code as stale — no manual bump required.

Content hashing (rather than a git SHA) is deliberate: it invalidates the
cache on *uncommitted* edits too, which is exactly what you want while
iterating on geometry.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

# Bump ONLY when the cache *infrastructure* changes in a way that source
# hashing cannot capture — e.g. the .blend serialisation strategy or the
# manifest schema.  Never bump this for geometry or defect-logic changes;
# those are captured automatically by hashing their source files.
CACHE_FORMAT_VERSION = 1

_FINGERPRINT_LENGTH = 12


def _identity(path: Path) -> str:
    """Location-independent identifier: the file's parent dir + name.

    Using ``parent/name`` (rather than the bare name) disambiguates files that
    share a base name in different packages — e.g. ``cache/base.py`` vs
    ``defects/base.py`` — without baking the absolute checkout path into the
    fingerprint value.
    """
    return f"{path.parent.name}/{path.name}"


def source_fingerprint(
    paths: Iterable[Path],
    *,
    format_version: int = CACHE_FORMAT_VERSION,
) -> str:
    """Return a short, deterministic fingerprint of *paths*' contents.

    The result depends on each file's bytes and ``parent/name`` identity, plus
    ``format_version``.  It is deterministic across processes and machines:
    inputs are sorted by a total order (so set/hash-seed iteration order never
    leaks in), and a missing file is folded in as an explicit marker so the
    fingerprint stays stable instead of raising mid-render.
    """
    hasher = hashlib.sha256()
    hasher.update(f"format={format_version}".encode("utf-8"))

    # Sort by (identity, full path): identity gives a stable, location-
    # independent primary order; the full path breaks any identity ties so the
    # ordering is total and never depends on set iteration order.
    unique_sorted = sorted(
        {Path(p) for p in paths}, key=lambda p: (_identity(p), str(p))
    )
    for path in unique_sorted:
        hasher.update(b"\x00")
        hasher.update(_identity(path).encode("utf-8"))
        hasher.update(b"\x00")
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(b"<missing>")

    return hasher.hexdigest()[:_FINGERPRINT_LENGTH]
