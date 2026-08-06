"""Seeding of defect placement: default value, CLI override, and determinism."""

from config import parse_pipeline_settings

from app.config.settings import PipelineSettings
from app.geometry.defects.selector import DefectSelector


def test_default_seed_is_42():
    assert PipelineSettings().seed == 42


def test_seed_absent_from_cli_falls_back_to_default():
    settings = parse_pipeline_settings(["--", "--fps", "24"])
    assert settings.seed == 42


def test_seed_cli_override():
    settings = parse_pipeline_settings(["--", "--seed", "7"])
    assert settings.seed == 7


def _sequence(seed: int, draws: int = 60) -> list[str | None]:
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


def test_forced_selector_accepts_seed():
    a = DefectSelector.forced("skewed_sleeper", seed=42)
    b = DefectSelector.forced("skewed_sleeper", seed=42)
    assert [a.select_variant().identifier for _ in range(20)] == [
        b.select_variant().identifier for _ in range(20)
    ]
