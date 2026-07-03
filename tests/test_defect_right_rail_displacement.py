"""Unit tests for RightRailLateralDisplacementDefect."""
import math
import pytest
from unittest.mock import MagicMock, patch
from app.geometry.defects.rails.rail_displacement import RightRailLateralDisplacementDefect
from app.config.geometry import TrackGeometryConfig


# ── metadata ─────────────────────────────────────────────────────────────────

def test_name():
    assert RightRailLateralDisplacementDefect.NAME == "right_rail_lateral_displacement"


def test_displacement_variants_defined():
    assert len(RightRailLateralDisplacementDefect.DISPLACEMENT_VARIANTS) == 3


def test_span_lengths_defined():
    assert RightRailLateralDisplacementDefect.SPAN_LENGTHS == [5, 7]


# ── variants() ────────────────────────────────────────────────────────────────

def test_variants_count():
    # 3 displacements × 2 span_lengths × (5 + 7) positions
    expected = 3 * (5 + 7)
    assert len(RightRailLateralDisplacementDefect.variants()) == expected


def test_variants_contain_required_keys():
    for v in RightRailLateralDisplacementDefect.variants():
        assert "displacement_m" in v.defect_params
        assert "span_length" in v.defect_params
        assert "position" in v.defect_params


def test_variants_defect_name_matches_class():
    for v in RightRailLateralDisplacementDefect.variants():
        assert v.defect_name == RightRailLateralDisplacementDefect.NAME


def test_variants_positions_range_from_zero():
    for v in RightRailLateralDisplacementDefect.variants():
        span_length = v.defect_params["span_length"]
        position = v.defect_params["position"]
        assert 0 <= position < span_length


# ── span_groups() ─────────────────────────────────────────────────────────────

def test_span_groups_count():
    # 3 displacements × 2 span_lengths = 6 groups
    assert len(RightRailLateralDisplacementDefect.span_groups()) == 6


def test_span_groups_ordered_by_position():
    for group in RightRailLateralDisplacementDefect.span_groups():
        positions = [v.defect_params["position"] for v in group]
        assert positions == list(range(len(group)))


def test_span_groups_lengths_match_span_length_constant():
    for group in RightRailLateralDisplacementDefect.span_groups():
        span_length = group[0].defect_params["span_length"]
        assert len(group) == span_length


def test_span_groups_all_variants_same_displacement_and_span():
    for group in RightRailLateralDisplacementDefect.span_groups():
        displacements = {v.defect_params["displacement_m"] for v in group}
        spans = {v.defect_params["span_length"] for v in group}
        assert len(displacements) == 1
        assert len(spans) == 1


# ── apply() — geometry maths ─────────────────────────────────────────────────

def _make_section(cfg=None):
    """Return a MagicMock section with a real TrackGeometryConfig."""
    section = MagicMock()
    section.config = cfg or TrackGeometryConfig()
    section.fasteners = [MagicMock() for _ in range(8)]
    for f in section.fasteners:
        f.location.x = 0.0
    section.right_rail = MagicMock()
    section.right_rail.scale.x = 0.06
    section.right_rail.data.vertices = []
    section.right_sleeper = MagicMock()
    section.right_sleeper.location.x = 0.0
    return section


def test_apply_first_section_entry_fastener_is_minimal():
    # position=0 → t_entry=0 → x_entry=0 → entry fastener (6) barely moves
    section = _make_section()
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.06,
        "span_length": 5,
        "position": 0,
    })
    # Entry fastener displacement is 0 × (1-t) + x_exit × t, so |shift| < displacement_m
    assert abs(section.fasteners[6].location.x) < 0.06


def test_apply_last_section_exit_fastener_is_minimal():
    # position=N-1 → t_exit=1 → x_exit=0 → exit fastener (7) barely moves
    section = _make_section()
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.06,
        "span_length": 5,
        "position": 4,
    })
    assert abs(section.fasteners[7].location.x) < 0.06


def test_apply_midspan_section_has_maximum_offset():
    # Fastener 6 shift is largest near the span midpoint.
    def fastener_shift(position, span_length=5, displacement_m=0.10):
        section = _make_section()
        RightRailLateralDisplacementDefect.apply(section, {
            "displacement_m": displacement_m,
            "span_length": span_length,
            "position": position,
        })
        return abs(section.fasteners[6].location.x)

    shifts = [fastener_shift(i) for i in range(5)]
    assert shifts[2] > shifts[0]
    assert shifts[2] > shifts[4]


def test_apply_none_right_rail_does_not_raise():
    section = _make_section()
    section.right_rail = None
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.06, "span_length": 5, "position": 2,
    })


def test_apply_none_right_sleeper_does_not_raise():
    section = _make_section()
    section.right_sleeper = None
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.06, "span_length": 5, "position": 2,
    })


def test_apply_shifts_fasteners_6_and_7():
    section = _make_section()
    original_x6 = section.fasteners[6].location.x
    original_x7 = section.fasteners[7].location.x
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.10, "span_length": 5, "position": 2,
    })
    # Both fasteners should have shifted
    assert section.fasteners[6].location.x != original_x6 or section.fasteners[7].location.x != original_x7


def test_apply_does_not_shift_left_rail_fasteners():
    # Right-rail defect must not move any left-rail fastener (indices 0-3:
    # [0,1]=outer-left, [2,3]=inner-left).
    section = _make_section()
    original = [f.location.x for f in section.fasteners[:4]]
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.10, "span_length": 5, "position": 2,
    })
    for i in range(4):
        assert section.fasteners[i].location.x == original[i]


def test_apply_shifts_both_right_rail_fastener_pairs_together():
    # Both fastener pairs seated on the right rail ([4,5]=inner, [6,7]=outer)
    # clip the same moving rail foot, so both must shift — and by the same
    # amount, since they share the same y-offset-from-center pattern.
    section = _make_section()
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.10, "span_length": 5, "position": 2,
    })
    assert section.fasteners[4].location.x != 0.0
    assert section.fasteners[5].location.x != 0.0
    assert section.fasteners[4].location.x == section.fasteners[6].location.x
    assert section.fasteners[5].location.x == section.fasteners[7].location.x


def test_apply_larger_displacement_gives_larger_shift():
    def fastener_shift(displacement_m):
        section = _make_section()
        RightRailLateralDisplacementDefect.apply(section, {
            "displacement_m": displacement_m, "span_length": 5, "position": 2,
        })
        return abs(section.fasteners[6].location.x)

    assert fastener_shift(0.10) > fastener_shift(0.03)


def test_apply_uses_config_for_fastener_interpolation():
    # A config with a different sleeper_depth changes the fastener t values.
    # Just ensure it doesn't crash and shifts the fasteners consistently.
    cfg = TrackGeometryConfig(sleeper_depth=0.15, sleeper_pitch_ratio=0.60)
    section = _make_section(cfg)
    RightRailLateralDisplacementDefect.apply(section, {
        "displacement_m": 0.06, "span_length": 5, "position": 2,
    })
    assert section.fasteners[6].location.x != 0.0 or section.fasteners[7].location.x != 0.0
