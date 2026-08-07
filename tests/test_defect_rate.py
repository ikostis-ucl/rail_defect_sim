"""Defect rate is configurable.

How often defects appear sets the balance of healthy to faulty examples in the
generated dataset. It used to be a class constant reachable only by editing
source; it is now a normal setting.
"""

import pytest

from app.config import PipelineSettings
from app.geometry.defects.selector import DefectSelector
from config import parse_pipeline_settings


def parse(*args):
    return parse_pipeline_settings(["--", *args])


def _defect_share(probability: float, draws: int = 4000) -> float:
    """Fraction of sections that end up defective at the given start rate."""
    selector = DefectSelector.default(seed=42, probability=probability)
    hits = sum(selector.select_variant() is not None for _ in range(draws))
    return hits / draws


# ── Setting and flag ──────────────────────────────────────────────────────────

def test_default_rate_is_ten_percent():
    assert PipelineSettings().defect_rate == pytest.approx(0.10)


def test_rate_flag_overrides_the_default():
    assert parse("--defect-rate", "0.35").defect_rate == pytest.approx(0.35)


def test_rate_absent_falls_back_to_default():
    assert parse("--fps", "24").defect_rate == pytest.approx(0.10)


def test_rate_does_not_disturb_other_settings():
    s = parse("--defect-rate", "0.5")
    assert s.seed == 42
    assert s.render.fps == 12


# ── Selector honours it ───────────────────────────────────────────────────────

def test_zero_rate_yields_no_defects():
    selector = DefectSelector.default(seed=42, probability=0.0)
    assert all(selector.select_variant() is None for _ in range(200))


def test_full_rate_yields_only_defects():
    selector = DefectSelector.default(seed=42, probability=1.0)
    assert all(selector.select_variant() is not None for _ in range(200))


def test_higher_rate_produces_more_defects():
    assert _defect_share(0.05) < _defect_share(0.25) < _defect_share(0.6)


def test_omitting_probability_uses_the_class_default():
    """Existing callers that pass only a seed keep the 10% behaviour."""
    assert DefectSelector.default(seed=42)._probability == pytest.approx(
        DefectSelector.DEFECT_PROBABILITY
    )


def test_defective_share_exceeds_the_start_rate():
    """Multi-section spans occupy follower sections, so the share of defective
    sections is several times the rate at which defects *start*."""
    share = _defect_share(0.10)
    assert share > 0.10


def test_rate_is_still_reproducible_under_a_seed():
    """Changing the rate must not cost determinism."""
    first = DefectSelector.default(seed=7, probability=0.3)
    second = DefectSelector.default(seed=7, probability=0.3)
    assert [first.select_variant() for _ in range(50)] == [
        second.select_variant() for _ in range(50)
    ]
