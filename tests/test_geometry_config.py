"""Unit tests for TrackGeometryConfig and RailConfig."""
import dataclasses
import pytest
from app.config.geometry import RailConfig, TrackGeometryConfig


# ── RailConfig defaults ───────────────────────────────────────────────────────

def test_rail_config_defaults():
    rc = RailConfig()
    assert rc.width == pytest.approx(0.06)
    assert rc.height == pytest.approx(0.16)
    assert rc.lift == pytest.approx(0.0)
    assert rc.angle == pytest.approx(0.0)


def test_rail_config_frozen():
    rc = RailConfig()
    with pytest.raises(Exception):
        rc.angle = 5.0  # type: ignore[misc]


def test_rail_config_overrides():
    rc = RailConfig(width=0.08, angle=3.5)
    assert rc.width == pytest.approx(0.08)
    assert rc.angle == pytest.approx(3.5)
    assert rc.height == pytest.approx(0.16)  # default kept


# ── TrackGeometryConfig defaults ──────────────────────────────────────────────

def test_default_rail_spacing():
    assert TrackGeometryConfig().rail_spacing == pytest.approx(1.435)


def test_default_left_rail_is_rail_config():
    cfg = TrackGeometryConfig()
    assert isinstance(cfg.left_rail, RailConfig)
    assert cfg.left_rail.width == pytest.approx(0.06)
    assert cfg.left_rail.height == pytest.approx(0.16)
    assert cfg.left_rail.lift == pytest.approx(0.0)
    assert cfg.left_rail.angle == pytest.approx(0.0)


def test_default_right_rail_is_rail_config():
    cfg = TrackGeometryConfig()
    assert isinstance(cfg.right_rail, RailConfig)
    assert cfg.right_rail == RailConfig()


def test_default_left_and_right_rail_equal():
    cfg = TrackGeometryConfig()
    assert cfg.left_rail == cfg.right_rail


def test_default_sleeper_length():
    assert TrackGeometryConfig().sleeper_length == pytest.approx(0.108)


def test_default_sleeper_height():
    assert TrackGeometryConfig().sleeper_height == pytest.approx(0.12)


def test_default_sleeper_pitch_ratio():
    assert TrackGeometryConfig().sleeper_pitch_ratio == pytest.approx(0.60)


def test_default_screw_radius():
    assert TrackGeometryConfig().screw_radius == pytest.approx(0.015)


def test_default_screw_length():
    assert TrackGeometryConfig().screw_length == pytest.approx(0.05)


# ── Independent per-rail angles ───────────────────────────────────────────────

def test_independent_left_right_rail_angles():
    cfg = TrackGeometryConfig(
        left_rail=RailConfig(angle=5.0),
        right_rail=RailConfig(angle=-3.0),
    )
    assert cfg.left_rail.angle == pytest.approx(5.0)
    assert cfg.right_rail.angle == pytest.approx(-3.0)


def test_independent_left_right_rail_widths():
    cfg = TrackGeometryConfig(
        left_rail=RailConfig(width=0.06),
        right_rail=RailConfig(width=0.08),
    )
    assert cfg.left_rail.width == pytest.approx(0.06)
    assert cfg.right_rail.width == pytest.approx(0.08)


# ── derived section_pitch ──────────────────────────────────────────────────────

def test_section_pitch_default_reproduces_prior_hardcoded_value():
    # Prior code used section_spacing = 0.18 (hardcoded).
    # 0.108 / 0.60 = 0.18 exactly — no visual regression.
    assert TrackGeometryConfig().section_pitch == pytest.approx(0.18)


def test_section_pitch_formula():
    cfg = TrackGeometryConfig(sleeper_length=0.13, sleeper_pitch_ratio=0.72)
    assert cfg.section_pitch == pytest.approx(0.13 / 0.72)


def test_section_pitch_changes_with_sleeper_length():
    cfg1 = TrackGeometryConfig(sleeper_length=0.10)
    cfg2 = TrackGeometryConfig(sleeper_length=0.20)
    assert cfg2.section_pitch > cfg1.section_pitch


def test_section_pitch_changes_with_ratio():
    cfg_tight = TrackGeometryConfig(sleeper_pitch_ratio=0.90)
    cfg_loose = TrackGeometryConfig(sleeper_pitch_ratio=0.50)
    assert cfg_loose.section_pitch > cfg_tight.section_pitch


def test_section_pitch_is_always_larger_than_sleeper_length():
    for ratio in [0.4, 0.6, 0.72, 0.9]:
        cfg = TrackGeometryConfig(sleeper_pitch_ratio=ratio)
        assert cfg.section_pitch > cfg.sleeper_length


# ── immutability ──────────────────────────────────────────────────────────────

def test_frozen():
    cfg = TrackGeometryConfig()
    with pytest.raises(Exception):
        cfg.rail_spacing = 2.0  # type: ignore[misc]


# ── to_dict ───────────────────────────────────────────────────────────────────

def test_to_dict_contains_all_fields():
    cfg = TrackGeometryConfig()
    d = cfg.to_dict()
    for f in dataclasses.fields(cfg):
        assert f.name in d


def test_to_dict_values_match():
    cfg = TrackGeometryConfig(rail_spacing=1.6, sleeper_length=0.12)
    d = cfg.to_dict()
    assert d["rail_spacing"] == pytest.approx(1.6)
    assert d["sleeper_length"] == pytest.approx(0.12)


def test_to_dict_does_not_include_derived_section_pitch():
    d = TrackGeometryConfig().to_dict()
    assert "section_pitch" not in d


def test_to_dict_left_rail_is_nested_dict():
    d = TrackGeometryConfig().to_dict()
    assert isinstance(d["left_rail"], dict)
    assert "angle" in d["left_rail"]
    assert d["left_rail"]["angle"] == pytest.approx(0.0)


def test_to_dict_right_rail_is_nested_dict():
    cfg = TrackGeometryConfig(right_rail=RailConfig(angle=7.0))
    d = cfg.to_dict()
    assert isinstance(d["right_rail"], dict)
    assert d["right_rail"]["angle"] == pytest.approx(7.0)


def test_to_dict_no_ballast_keys():
    d = TrackGeometryConfig().to_dict()
    for key in d:
        assert "ballast" not in key


# ── from_yaml ─────────────────────────────────────────────────────────────────

def test_from_yaml_full_override(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text(
        "rail_spacing: 1.520\n"
        "sleeper_length: 0.115\n"
        "sleeper_pitch_ratio: 0.62\n"
    )
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.rail_spacing == pytest.approx(1.520)
    assert cfg.sleeper_length == pytest.approx(0.115)
    assert cfg.sleeper_pitch_ratio == pytest.approx(0.62)


def test_from_yaml_partial_keeps_defaults(tmp_path):
    yml = tmp_path / "partial.yml"
    yml.write_text("rail_spacing: 1.000\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.rail_spacing == pytest.approx(1.000)
    assert cfg.sleeper_height == pytest.approx(TrackGeometryConfig().sleeper_height)


def test_from_yaml_unknown_keys_are_ignored(tmp_path):
    yml = tmp_path / "unk.yml"
    yml.write_text("unknown_field: 999\nrail_spacing: 1.3\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.rail_spacing == pytest.approx(1.3)


def test_from_yaml_empty_file_uses_defaults(tmp_path):
    yml = tmp_path / "empty.yml"
    yml.write_text("")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg == TrackGeometryConfig()


def test_from_yaml_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        TrackGeometryConfig.from_yaml("/nonexistent/path/geo.yml")


def test_from_yaml_left_rail_angle(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("left_rail:\n  angle: 7.5\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.left_rail.angle == pytest.approx(7.5)
    assert cfg.right_rail.angle == pytest.approx(0.0)  # right rail unchanged


def test_from_yaml_independent_rail_angles(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("left_rail:\n  angle: 5.0\nright_rail:\n  angle: -3.0\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.left_rail.angle == pytest.approx(5.0)
    assert cfg.right_rail.angle == pytest.approx(-3.0)


def test_from_yaml_partial_rail_config_keeps_rail_defaults(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("left_rail:\n  angle: 2.0\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.left_rail.angle == pytest.approx(2.0)
    assert cfg.left_rail.width == pytest.approx(RailConfig().width)   # default kept
    assert cfg.left_rail.height == pytest.approx(RailConfig().height) # default kept


def test_from_yaml_section_pitch_recomputed_after_load(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("sleeper_length: 0.12\nsleeper_pitch_ratio: 0.6\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.section_pitch == pytest.approx(0.12 / 0.6)
