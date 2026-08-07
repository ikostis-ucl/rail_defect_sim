"""Unit tests for TrackGeometryConfig and RailConfig."""
import dataclasses
import pytest
from app.config.geometry import RailConfig, TrackGeometryConfig


# ── RailConfig defaults ───────────────────────────────────────────────────────

def test_rail_config_defaults():
    rc = RailConfig()
    assert rc.head_width == pytest.approx(0.070)
    assert rc.foot_width == pytest.approx(0.140)
    assert rc.height == pytest.approx(0.159)
    assert rc.pad_thickness == pytest.approx(0.007)


def test_rail_config_frozen():
    rc = RailConfig()
    with pytest.raises(Exception):
        rc.head_width = 0.08  # type: ignore[misc]


def test_rail_config_overrides():
    rc = RailConfig(head_width=0.08, pad_thickness=0.009)
    assert rc.head_width == pytest.approx(0.08)
    assert rc.pad_thickness == pytest.approx(0.009)
    assert rc.height == pytest.approx(0.159)  # default kept


# ── TrackGeometryConfig defaults ──────────────────────────────────────────────

def test_default_rail_spacing():
    assert TrackGeometryConfig().rail_spacing == pytest.approx(1.000)


def test_default_left_rail_is_rail_config():
    cfg = TrackGeometryConfig()
    assert isinstance(cfg.left_rail, RailConfig)
    assert cfg.left_rail.head_width == pytest.approx(0.070)
    assert cfg.left_rail.foot_width == pytest.approx(0.140)
    assert cfg.left_rail.height == pytest.approx(0.159)
    assert cfg.left_rail.pad_thickness == pytest.approx(0.007)


def test_default_right_rail_is_rail_config():
    cfg = TrackGeometryConfig()
    assert isinstance(cfg.right_rail, RailConfig)
    assert cfg.right_rail == RailConfig()


def test_default_left_and_right_rail_equal():
    cfg = TrackGeometryConfig()
    assert cfg.left_rail == cfg.right_rail


def test_default_sleeper_depth():
    assert TrackGeometryConfig().sleeper_depth == pytest.approx(0.200)


def test_default_sleeper_height():
    assert TrackGeometryConfig().sleeper_height == pytest.approx(0.200)


def test_default_section_pitch():
    """Stated in metres: the Camrail mid-range spacing."""
    assert TrackGeometryConfig().section_pitch == pytest.approx(0.625)


def test_default_screw_radius():
    assert TrackGeometryConfig().screw_radius == pytest.approx(0.0065)


def test_default_screw_length():
    assert TrackGeometryConfig().screw_length == pytest.approx(0.035)


# ── Independent per-rail dimensions ───────────────────────────────────────────

def test_independent_left_right_rail_heights():
    """Defects often affect one rail only, so the two must be separable."""
    cfg = TrackGeometryConfig(
        left_rail=RailConfig(height=0.159),
        right_rail=RailConfig(height=0.172),
    )
    assert cfg.left_rail.height == pytest.approx(0.159)
    assert cfg.right_rail.height == pytest.approx(0.172)


def test_independent_left_right_rail_head_widths():
    cfg = TrackGeometryConfig(
        left_rail=RailConfig(head_width=0.065),
        right_rail=RailConfig(head_width=0.080),
    )
    assert cfg.left_rail.head_width == pytest.approx(0.065)
    assert cfg.right_rail.head_width == pytest.approx(0.080)


# ── section_pitch as a configured distance ─────────────────────────────────────

def test_section_pitch_default_value():
    # Camrail UIC54: 625 mm, mid-range of the 600-660 mm standard.
    assert TrackGeometryConfig().section_pitch == pytest.approx(0.625)


def test_section_pitch_is_taken_verbatim():
    """No arithmetic: what you write in metres is what you get."""
    assert TrackGeometryConfig(section_pitch=0.55).section_pitch == pytest.approx(0.55)


def test_section_pitch_is_independent_of_sleeper_depth():
    """Changing the sleeper body no longer silently moves the spacing."""
    a = TrackGeometryConfig(sleeper_depth=0.10)
    b = TrackGeometryConfig(sleeper_depth=0.20)
    assert a.section_pitch == b.section_pitch
    assert a.sleeper_clear_gap > b.sleeper_clear_gap


def test_sleepers_can_now_be_configured_to_overlap():
    """A ratio made overlap impossible; a distance does not.

    The pitch constraints (#17) are what must reject this, not the type.
    """
    cfg = TrackGeometryConfig(sleeper_depth=0.200, section_pitch=0.150)
    assert cfg.sleeper_clear_gap < 0


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
    cfg = TrackGeometryConfig(rail_spacing=1.6, sleeper_depth=0.12)
    d = cfg.to_dict()
    assert d["rail_spacing"] == pytest.approx(1.6)
    assert d["sleeper_depth"] == pytest.approx(0.12)


def test_to_dict_includes_section_pitch():
    d = TrackGeometryConfig().to_dict()
    assert d["section_pitch"] == pytest.approx(0.625)


def test_to_dict_left_rail_is_nested_dict():
    d = TrackGeometryConfig().to_dict()
    assert isinstance(d["left_rail"], dict)
    assert d["left_rail"]["head_width"] == pytest.approx(0.070)


def test_to_dict_right_rail_is_nested_dict():
    cfg = TrackGeometryConfig(right_rail=RailConfig(head_width=0.074))
    d = cfg.to_dict()
    assert isinstance(d["right_rail"], dict)
    assert d["right_rail"]["head_width"] == pytest.approx(0.074)


def test_to_dict_no_ballast_keys():
    d = TrackGeometryConfig().to_dict()
    for key in d:
        assert "ballast" not in key


# ── from_yaml ─────────────────────────────────────────────────────────────────

def test_from_yaml_full_override(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text(
        "rail_spacing: 1.520\n"
        "sleeper_depth: 0.115\n"
        "section_pitch: 0.185\n"
    )
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.rail_spacing == pytest.approx(1.520)
    assert cfg.sleeper_depth == pytest.approx(0.115)
    assert cfg.section_pitch == pytest.approx(0.185)


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


def test_from_yaml_left_rail_only(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("left_rail:\n  height: 0.175\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.left_rail.height == pytest.approx(0.175)
    assert cfg.right_rail.height == pytest.approx(RailConfig().height)  # unchanged


def test_from_yaml_independent_rail_dimensions(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("left_rail:\n  height: 0.159\nright_rail:\n  height: 0.172\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.left_rail.height == pytest.approx(0.159)
    assert cfg.right_rail.height == pytest.approx(0.172)


def test_from_yaml_partial_rail_config_keeps_rail_defaults(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("left_rail:\n  foot_width: 0.150\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.left_rail.foot_width == pytest.approx(0.150)
    assert cfg.left_rail.head_width == pytest.approx(RailConfig().head_width)   # default kept
    assert cfg.left_rail.height == pytest.approx(RailConfig().height)           # default kept


def test_from_yaml_section_pitch_loads_verbatim(tmp_path):
    yml = tmp_path / "geo.yml"
    yml.write_text("sleeper_depth: 0.12\nsection_pitch: 0.60\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.section_pitch == pytest.approx(0.60)
