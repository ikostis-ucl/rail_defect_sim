"""Derived geometry quantities and the profile/base-elevation config fields.

These are the values the validation layer and the camera datum depend on, so
they must be computable from config alone, without Blender.
"""

import dataclasses

import pytest

from app.config import TrackGeometryConfig
from app.config.geometry import RailConfig


# ── Profile provenance ────────────────────────────────────────────────────────

def test_config_declares_its_rail_profile():
    """Previously the profile lived only in YAML comments."""
    assert TrackGeometryConfig().profile == "UIC54"


def test_from_gauge_records_the_profile_it_used():
    cfg = TrackGeometryConfig.from_gauge(1435, profile="UIC60")
    assert cfg.profile == "UIC60"


def test_validate_against_profile_defaults_to_own_profile():
    """No profile argument needed — the config knows which standard it claims."""
    cfg = TrackGeometryConfig.from_gauge(1000, profile="UIC54")
    adjusted, issues = cfg.validate_against_profile()
    assert issues == []
    assert adjusted.profile == "UIC54"


def test_unknown_profile_accepts_values_as_is():
    cfg = TrackGeometryConfig(profile="NOT_A_REAL_PROFILE")
    adjusted, issues = cfg.validate_against_profile()
    assert adjusted is cfg
    assert issues == []


# ── Vertical datum ────────────────────────────────────────────────────────────

def test_base_elevation_is_configurable():
    assert TrackGeometryConfig().base_elevation == 0.1
    assert TrackGeometryConfig(base_elevation=0.25).base_elevation == 0.25


def test_sleeper_top_z():
    cfg = TrackGeometryConfig()  # 0.1 base + 0.200 sleeper
    assert cfg.sleeper_top_z == pytest.approx(0.300)


def test_rail_top_z_follows_the_contact_chain():
    """base + sleeper + pad + rail height = 0.1 + 0.200 + 0.007 + 0.159."""
    assert TrackGeometryConfig().rail_top_z == pytest.approx(0.466)


def test_rail_top_z_uses_the_higher_rail():
    """Camera clearance must clear the taller rail, not the average."""
    cfg = TrackGeometryConfig(
        left_rail=RailConfig(height=0.159),
        right_rail=RailConfig(height=0.200),
    )
    assert cfg.rail_top_z == pytest.approx(0.300 + 0.007 + 0.200)


def test_rail_top_z_moves_with_geometry():
    """Regression guard: the datum differs between profiles.

    The camera presets used to hardcode 0.466, which is wrong for any other
    geometry — that is exactly the coupling rail_top_z exists to remove.
    """
    default = TrackGeometryConfig().rail_top_z
    broad = TrackGeometryConfig(
        sleeper_height=0.130,
        left_rail=RailConfig(height=0.160),
        right_rail=RailConfig(height=0.160),
    ).rail_top_z
    assert default == pytest.approx(0.466)
    assert broad == pytest.approx(0.397)


# ── Sleeper spacing ───────────────────────────────────────────────────────────

def test_section_pitch_default():
    assert TrackGeometryConfig().section_pitch == pytest.approx(0.625)


def test_sleeper_clear_gap():
    """Pitch minus sleeper body: the free space between adjacent sleepers."""
    assert TrackGeometryConfig().sleeper_clear_gap == pytest.approx(0.425)


def test_sleepers_per_km():
    assert TrackGeometryConfig().sleepers_per_km == pytest.approx(1600.0)


def test_implausible_pitch_is_computable_even_though_unvalidated():
    """The wide_gauge.yml case: currently expressible and not yet rejected.

    Documents the gap that the sleeper-pitch constraints are meant to close.
    """
    cfg = TrackGeometryConfig(sleeper_depth=0.115, section_pitch=0.1855)
    assert cfg.section_pitch == pytest.approx(0.1855, abs=1e-4)
    assert cfg.sleepers_per_km > 5000
    assert cfg.validate() == []  # still passes — no pitch constraint exists yet


# ── Standards define spacing as a distance ────────────────────────────────────

def test_profiles_specify_spacing_in_millimetres():
    """Standards state a spacing, not a ratio — the catalog mirrors that."""
    from app.config.profiles import PROFILES

    assert PROFILES["UIC54"].section_pitch_mm == pytest.approx(625.0)
    assert PROFILES["UIC60"].section_pitch_mm == pytest.approx(650.0)
    assert PROFILES["115RE"].section_pitch_mm == pytest.approx(600.0)


def test_from_gauge_takes_spacing_from_the_standard():
    cfg = TrackGeometryConfig.from_gauge(1435, profile="UIC60")
    assert cfg.section_pitch == pytest.approx(0.650)
    assert cfg.sleepers_per_km == pytest.approx(1000 / 0.650)


def test_profile_check_flags_spacing_far_from_the_standard():
    """A 185 mm spacing cannot pass as UIC60's 650 mm."""
    cfg = TrackGeometryConfig.from_gauge(1520, profile="UIC60")
    bad = dataclasses.replace(cfg, section_pitch=0.185)
    adjusted, issues = bad.validate_against_profile()
    assert any(i.field == "section_pitch" for i in issues)
    assert adjusted.section_pitch == pytest.approx(0.650)   # clamped to standard


def test_profile_check_accepts_spacing_within_tolerance():
    cfg = TrackGeometryConfig.from_gauge(1000, profile="UIC54")
    near = dataclasses.replace(cfg, section_pitch=0.640)   # ~2% off 0.625
    _, issues = near.validate_against_profile()
    assert not any(i.field == "section_pitch" for i in issues)
