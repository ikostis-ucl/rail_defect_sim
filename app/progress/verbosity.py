"""How much detail the console account carries.

A run prints two very different kinds of thing: a handful of lines saying which
phase is running, and a line per cached asset saying it was found on disk. The
first is what somebody watching a headless VM wants. The second is a few hundred
lines of noise unless you are debugging the cache.

Quiet is the default, so the console stays readable. ``--verbose`` restores the
per-asset detail. Neither affects the machine stream, which always carries
everything.
"""

from __future__ import annotations

_verbose = False


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = bool(value)


def is_verbose() -> bool:
    return _verbose


def detail(message: str) -> None:
    """Print only when detail was asked for."""
    if _verbose:
        print(message)
