"""Determinism of defect placement under a fixed seed.

The seed's *plumbing* (default value, CLI flag) is covered by
test_config_settings.py and test_config_parsing.py; this file covers the
behaviour that actually matters — that a seed reproduces a track layout.
"""

from app.geometry.defects.selector import DefectSelector


def _sequence(seed: int, draws: int = 60) -> list:
    """Run a default selector for *draws* sections and record what it picked."""
    selector = DefectSelector.default(seed=seed)
    out = []
    for _ in range(draws):
        variant = selector.select_variant()
        out.append(variant.identifier if variant is not None else None)
    return out


def test_same_seed_reproduces_identical_defect_layout():
    assert _sequence(42) == _sequence(42)


def test_different_seeds_produce_different_layouts():
    # Guards against the seed being accepted but ignored.
    assert _sequence(42) != _sequence(1234)


def test_layout_contains_both_healthy_and_defective_sections():
    """A usable dataset needs negatives too; the default rate is 10%."""
    drawn = _sequence(42, draws=200)
    assert any(d is None for d in drawn)
    assert any(d is not None for d in drawn)


def test_forced_selector_accepts_seed():
    a = DefectSelector.forced("skewed_sleeper", seed=42)
    b = DefectSelector.forced("skewed_sleeper", seed=42)
    assert [a.select_variant().identifier for _ in range(20)] == [
        b.select_variant().identifier for _ in range(20)
    ]


def test_forced_selector_makes_every_section_defective():
    selector = DefectSelector.forced("skewed_sleeper", seed=42)
    assert all(selector.select_variant() is not None for _ in range(50))
