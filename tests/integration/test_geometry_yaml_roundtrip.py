"""
Integration: write a YAML file, load it, verify the config roundtrips cleanly
including section_pitch as a directly configured distance.
"""
import dataclasses
import pytest
import yaml
from app.config.geometry import RailConfig, TrackGeometryConfig


def test_roundtrip_all_fields(tmp_path):
    original = TrackGeometryConfig(
        rail_spacing=1.520,
        left_rail=RailConfig(head_width=0.07, height=0.18),
        right_rail=RailConfig(head_width=0.072, height=0.18),
        sleeper_depth=0.115,
        sleeper_height=0.13,
        section_pitch=0.185,
        screw_radius=0.016,
        screw_length=0.055,
    )
    yml = tmp_path / "test_geo.yml"
    yml.write_text(yaml.dump(original.to_dict()))

    loaded = TrackGeometryConfig.from_yaml(yml)

    assert loaded.rail_spacing == pytest.approx(original.rail_spacing)
    assert loaded.left_rail.height == pytest.approx(original.left_rail.height)
    assert loaded.right_rail.head_width == pytest.approx(original.right_rail.head_width)
    assert loaded.sleeper_depth == pytest.approx(original.sleeper_depth)
    assert loaded.section_pitch == pytest.approx(original.section_pitch)


def test_section_pitch_loads_directly_from_yaml(tmp_path):
    """Stated in metres, not inferred from a ratio."""
    yml = tmp_path / "geo.yml"
    yml.write_text("sleeper_depth: 0.18\nsection_pitch: 0.60\n")
    cfg = TrackGeometryConfig.from_yaml(yml)
    assert cfg.section_pitch == pytest.approx(0.60)
    assert cfg.sleeper_clear_gap == pytest.approx(0.42)


def test_default_yml_file_is_valid():
    """The checked-in default.yml must load without error and match defaults."""
    from pathlib import Path
    default_path = Path(__file__).parents[2] / "configs" / "geometry" / "default.yml"
    assert default_path.exists(), "configs/geometry/default.yml not found"
    cfg = TrackGeometryConfig.from_yaml(default_path)
    defaults = TrackGeometryConfig()
    assert cfg.rail_spacing == pytest.approx(defaults.rail_spacing)
    assert cfg.left_rail == defaults.left_rail
    assert cfg.right_rail == defaults.right_rail
    assert cfg.sleeper_depth == pytest.approx(defaults.sleeper_depth)
    assert cfg.section_pitch == pytest.approx(defaults.section_pitch)


def test_wide_gauge_yml_file_is_valid():
    """configs/geometry/wide_gauge.yml must load and have rail_spacing > default."""
    from pathlib import Path
    path = Path(__file__).parents[2] / "configs" / "geometry" / "wide_gauge.yml"
    assert path.exists(), "configs/geometry/wide_gauge.yml not found"
    cfg = TrackGeometryConfig.from_yaml(path)
    assert cfg.rail_spacing > TrackGeometryConfig().rail_spacing


def test_cache_key_differs_between_configs(tmp_path):
    """Two different configs must produce different cache keys."""
    from app.geometry.cache.base import SectionCacheBase

    cfg_a = TrackGeometryConfig(sleeper_depth=0.108)
    cfg_b = TrackGeometryConfig(sleeper_depth=0.130)

    key_a = SectionCacheBase._make_cache_key({"cv": 1, **cfg_a.to_dict()})
    key_b = SectionCacheBase._make_cache_key({"cv": 1, **cfg_b.to_dict()})
    assert key_a != key_b


def test_same_config_gives_same_cache_key():
    from app.geometry.cache.base import SectionCacheBase
    cfg = TrackGeometryConfig()
    k1 = SectionCacheBase._make_cache_key(cfg.to_dict())
    k2 = SectionCacheBase._make_cache_key(cfg.to_dict())
    assert k1 == k2


def test_cache_key_differs_for_different_rail_dimensions():
    """Different left_rail dimensions must produce different cache keys."""
    from app.geometry.cache.base import SectionCacheBase
    cfg_a = TrackGeometryConfig(left_rail=RailConfig(head_width=0.070))
    cfg_b = TrackGeometryConfig(left_rail=RailConfig(head_width=0.074))
    key_a = SectionCacheBase._make_cache_key(cfg_a.to_dict())
    key_b = SectionCacheBase._make_cache_key(cfg_b.to_dict())
    assert key_a != key_b


def test_cache_key_differs_for_left_vs_right_rail():
    """The same change on the left vs the right rail is a different track."""
    from app.geometry.cache.base import SectionCacheBase
    cfg_a = TrackGeometryConfig(left_rail=RailConfig(head_width=0.074))
    cfg_b = TrackGeometryConfig(right_rail=RailConfig(head_width=0.074))
    key_a = SectionCacheBase._make_cache_key(cfg_a.to_dict())
    key_b = SectionCacheBase._make_cache_key(cfg_b.to_dict())
    assert key_a != key_b
