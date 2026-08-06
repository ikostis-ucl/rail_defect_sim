"""Uniform defect metadata.

Every defect answers the same questions about its physical size, regardless of
type. This is what lets constraint checks and annotation extents work against
*any* defect without knowing which one they hold — so adding a new defect type
requires no change to those callers.
"""

import pytest

from app.geometry.defects.base import Defect
from app.geometry.defects.registry import ALL_DEFECTS


@pytest.mark.parametrize("defect_class", ALL_DEFECTS, ids=lambda d: d.NAME)
def test_every_defect_answers_span_sections(defect_class):
    for variant in defect_class.variants():
        span = defect_class.span_sections(variant.defect_params)
        assert isinstance(span, int)
        assert span >= 1


@pytest.mark.parametrize("defect_class", ALL_DEFECTS, ids=lambda d: d.NAME)
def test_every_defect_answers_displacement(defect_class):
    for variant in defect_class.variants():
        magnitude = defect_class.displacement_m(variant.defect_params)
        assert isinstance(magnitude, float)
        assert magnitude >= 0.0


@pytest.mark.parametrize("defect_class", ALL_DEFECTS, ids=lambda d: d.NAME)
def test_span_sections_matches_span_group_length(defect_class):
    """A span group holds exactly as many variants as span_sections reports."""
    for group in defect_class.span_groups():
        reported = defect_class.span_sections(group[0].defect_params)
        assert reported == len(group)


def test_single_section_defects_report_span_of_one():
    for name in ("skewed_sleeper", "missing_fastener_pair"):
        cls = next(d for d in ALL_DEFECTS if d.NAME == name)
        assert cls.span_sections(cls.variants()[0].defect_params) == 1


def test_displacement_defects_report_their_magnitude():
    cls = next(d for d in ALL_DEFECTS if d.NAME == "right_rail_lateral_displacement")
    params = {"displacement_m": 0.03, "span_length": 5, "position": 0}
    assert cls.span_sections(params) == 5
    assert cls.displacement_m(params) == pytest.approx(0.03)


def test_rotation_only_defects_report_zero_displacement():
    """A skewed sleeper rotates without translating — honestly zero, not a lie."""
    cls = next(d for d in ALL_DEFECTS if d.NAME == "skewed_sleeper")
    assert cls.displacement_m({"angle_deg": 5.0}) == 0.0


def test_metadata_is_defined_on_the_base_class():
    """New defect types inherit the interface rather than reimplementing it."""
    assert hasattr(Defect, "span_sections")
    assert hasattr(Defect, "displacement_m")


def test_physical_length_is_computable_from_metadata_and_geometry():
    """The composition constraints need: span x pitch = length in metres."""
    from app.config import TrackGeometryConfig

    geometry = TrackGeometryConfig()
    cls = next(d for d in ALL_DEFECTS if d.NAME == "both_rails_gauge_widening")
    params = {"displacement_m": 0.05, "span_length": 7, "position": 0}
    length_m = cls.span_sections(params) * geometry.section_pitch
    assert length_m == pytest.approx(4.375)
