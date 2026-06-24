"""
Integration: verify that TrackSection geometry_payload() correctly reflects
TrackGeometryConfig, and that section_pitch is consistent with sleeper_length
and sleeper_pitch_ratio.
"""
import dataclasses
import pytest
from app.config.geometry import TrackGeometryConfig
from app.geometry.track_section import TrackSection


def test_geometry_payload_matches_config_fields():
    cfg = TrackGeometryConfig(rail_spacing=1.6, sleeper_length=0.12, sleeper_pitch_ratio=0.65)
    section = TrackSection(config=cfg)
    payload = section.geometry_payload()

    for fld in dataclasses.fields(cfg):
        assert fld.name in payload, f"Missing key: {fld.name}"
        val = getattr(cfg, fld.name)
        if dataclasses.is_dataclass(val):
            assert payload[fld.name] == dataclasses.asdict(val)
        else:
            assert payload[fld.name] == pytest.approx(val)


def test_geometry_payload_excludes_section_pitch():
    cfg = TrackGeometryConfig()
    payload = TrackSection(config=cfg).geometry_payload()
    assert "section_pitch" not in payload


def test_section_pitch_consistent_with_payload():
    cfg = TrackGeometryConfig(sleeper_length=0.13, sleeper_pitch_ratio=0.72)
    section = TrackSection(config=cfg)
    payload = section.geometry_payload()
    derived = payload["sleeper_length"] / payload["sleeper_pitch_ratio"]
    assert derived == pytest.approx(cfg.section_pitch)


def test_two_sections_with_different_configs_have_different_payloads():
    cfg_a = TrackGeometryConfig(rail_spacing=1.435)
    cfg_b = TrackGeometryConfig(rail_spacing=1.520)
    pa = TrackSection(config=cfg_a).geometry_payload()
    pb = TrackSection(config=cfg_b).geometry_payload()
    assert pa != pb


def test_default_section_payload_no_ballast_keys():
    payload = TrackSection().geometry_payload()
    for key in payload:
        assert "ballast" not in key, f"Unexpected ballast key: {key}"


def test_compute_layout_uses_config_rail_spacing():
    cfg = TrackGeometryConfig(rail_spacing=1.6)
    section = TrackSection(config=cfg)
    layout = section._compute_layout(0.0)
    assert layout.right_rail_x - layout.left_rail_x == pytest.approx(1.6)


def test_compute_layout_shifts_with_center_x():
    cfg = TrackGeometryConfig(rail_spacing=1.4)
    section = TrackSection(config=cfg)
    layout_a = section._compute_layout(0.0)
    layout_b = section._compute_layout(5.0)
    assert layout_b.left_rail_x - layout_a.left_rail_x == pytest.approx(5.0)
