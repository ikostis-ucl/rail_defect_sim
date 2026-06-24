import math
import pytest
from unittest.mock import MagicMock
from app.geometry.defects.skewed_sleeper import SkewedSleeperDefect


def test_name():
    assert SkewedSleeperDefect.NAME == "skewed_sleeper"


def test_variants_count():
    assert len(SkewedSleeperDefect.variants()) == len(SkewedSleeperDefect.ANGLE_VARIANTS)


def test_variants_are_four():
    assert len(SkewedSleeperDefect.variants()) == 4


def test_variant_names_match_class_name():
    for v in SkewedSleeperDefect.variants():
        assert v.defect_name == SkewedSleeperDefect.NAME


def test_variant_params_contain_angle_deg():
    for v in SkewedSleeperDefect.variants():
        assert "angle_deg" in v.defect_params


def test_variant_angles_match_constants():
    angles = [v.defect_params["angle_deg"] for v in SkewedSleeperDefect.variants()]
    assert sorted(angles) == sorted(SkewedSleeperDefect.ANGLE_VARIANTS)


def test_apply_rotates_all_three_sleeper_pieces():
    angle_deg = 5.0
    expected_rad = math.radians(angle_deg)

    left = MagicMock()
    left.rotation_euler = [0.0, 0.0, 0.0]
    middle = MagicMock()
    middle.rotation_euler = [0.0, 0.0, 0.0]
    right = MagicMock()
    right.rotation_euler = [0.0, 0.0, 0.0]

    section = MagicMock()
    section.left_sleeper = left
    section.middle_sleeper = middle
    section.right_sleeper = right

    SkewedSleeperDefect.apply(section, {"angle_deg": angle_deg})

    assert left.rotation_euler[2] == pytest.approx(expected_rad)
    assert middle.rotation_euler[2] == pytest.approx(expected_rad)
    assert right.rotation_euler[2] == pytest.approx(expected_rad)


def test_apply_handles_none_sleeper_pieces():
    section = MagicMock()
    section.left_sleeper = None
    section.middle_sleeper = None
    section.right_sleeper = None
    # Should not raise
    SkewedSleeperDefect.apply(section, {"angle_deg": 2.0})


def test_apply_negative_angle():
    left = MagicMock()
    left.rotation_euler = [0.0, 0.0, 0.0]
    section = MagicMock()
    section.left_sleeper = left
    section.middle_sleeper = None
    section.right_sleeper = None

    SkewedSleeperDefect.apply(section, {"angle_deg": -5.0})

    assert left.rotation_euler[2] == pytest.approx(math.radians(-5.0))


def test_variant_defect_class_is_skewed_sleeper():
    for v in SkewedSleeperDefect.variants():
        assert v.defect_class is SkewedSleeperDefect
