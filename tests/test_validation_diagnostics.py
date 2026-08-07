"""Issues carry their data as fields, not only as prose.

A finished English sentence is all a person needs and all a program cannot use.
These pin the machine-readable half: a stable code to match on, the numbers that
produced the problem, and a serialisable shape for the whole report.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import PipelineSettings, TrackGeometryConfig
from app.validation import Policy, Resolver, Severity
from app.validation.constraints.geometry import RailsDoNotOverlap, SleeperNotTooTall
from app.validation.context import ValidationContext
from app.validation.issue import ValidationIssue, error, warning

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def overlapping():
    return PipelineSettings(geometry=TrackGeometryConfig(rail_spacing=0.2))


# ── The code is the stable handle ─────────────────────────────────────────────

def test_issue_carries_the_constraint_name_as_its_code():
    """Matched on like an exception type, rather than by searching the text."""
    ctx = ValidationContext.from_settings(overlapping())
    issue = RailsDoNotOverlap().check(ctx)[0]
    assert issue.code == "rails_do_not_overlap"
    assert issue.code == RailsDoNotOverlap.NAME


def test_a_caller_can_act_on_the_code_without_reading_english():
    report = Resolver().resolve(overlapping())
    codes = {i.code for i in report.unresolved}
    assert "rails_do_not_overlap" in codes


def test_every_shipped_constraint_declares_a_code():
    """A rule without one cannot be acted on, only printed."""
    from app.validation import all_constraints

    for constraint in all_constraints():
        assert constraint.NAME, f"{type(constraint).__name__} has no NAME"


def test_codes_are_unique_across_the_registry():
    """Two rules sharing a code would be indistinguishable to a caller."""
    from app.validation import all_constraints

    names = [c.NAME for c in all_constraints()]
    assert len(names) == len(set(names))


# ── The numbers come through as data ──────────────────────────────────────────

def test_interval_rules_report_value_and_bounds():
    ctx = ValidationContext.from_settings(overlapping())
    issue = RailsDoNotOverlap().check(ctx)[0]
    assert issue.value == pytest.approx(0.2)
    assert issue.expected_min == pytest.approx(0.28, abs=1e-6)
    assert issue.unit == "m"


def test_an_upper_bound_reports_as_a_maximum():
    settings = PipelineSettings(geometry=TrackGeometryConfig(sleeper_height=0.5))
    issue = SleeperNotTooTall().check(ValidationContext.from_settings(settings))[0]
    assert issue.value == pytest.approx(0.5)
    assert issue.expected_max == pytest.approx(0.3)
    assert issue.expected_min is None


def test_the_message_still_reads_as_a_sentence():
    """The human half must not regress while the machine half is added."""
    ctx = ValidationContext.from_settings(overlapping())
    message = RailsDoNotOverlap().check(ctx)[0].message
    assert "overlap" in message and "0.200" in message


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_issue_serialises_to_plain_data():
    issue = error("a.b", "went wrong", code="my_code", value=1.5, expected_max=1.0, unit="m")
    assert issue.as_dict() == {
        "code": "my_code", "severity": "error", "field": "a.b",
        "message": "went wrong", "value": 1.5,
        "expected_min": None, "expected_max": 1.0, "unit": "m",
    }


def test_report_serialises_whole():
    payload = Resolver().resolve(overlapping()).as_dict()
    assert payload["ok"] is False
    assert payload["unresolved"][0]["code"] == "rails_do_not_overlap"
    json.dumps(payload)   # must be serialisable, not merely dict-shaped


def test_repairs_are_inspectable_without_being_applied():
    """What the resolver *would* change, as data."""
    settings = PipelineSettings(geometry=TrackGeometryConfig(screw_radius=0.09))
    payload = Resolver().resolve(settings).as_dict()
    repair = payload["repairs"][0]
    assert repair["constraint"] == "fastener_fits_under_rail"
    assert repair["field"] == "geometry.screw_radius"
    assert repair["before"] != repair["after"]


def test_strict_policy_reports_the_same_codes_without_repairing():
    settings = PipelineSettings(geometry=TrackGeometryConfig(screw_radius=0.09))
    payload = Resolver(policy=Policy.STRICT).resolve(settings).as_dict()
    assert payload["repairs"] == []
    assert any(i["code"] == "fastener_fits_under_rail" for i in payload["issues"])


# ── Defaults keep existing constructions working ──────────────────────────────

def test_an_issue_without_structured_data_is_still_valid():
    issue = warning("some.field", "unusual but fine")
    assert issue.code == "" and issue.value is None
    assert issue.severity == Severity.WARNING


# ── The preflight seam ────────────────────────────────────────────────────────

def _preflight(*args):
    return subprocess.run(
        [sys.executable, "tools/preflight.py", *args],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )


def test_preflight_json_is_parseable_and_carries_codes():
    result = _preflight("--json", "--", "--geometry-config", "configs/geometry/default.yml")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "measurements" in payload


def test_preflight_json_reports_measurements_as_numbers():
    payload = json.loads(_preflight("--json").stdout)
    m = payload["measurements"]
    assert m["speed_kmh"] == 80.0
    assert m["track_length_m"] > m["travel_distance_m"]
    assert m["section_count"] > 0


def test_preflight_json_accepted_on_either_side_of_the_separator():
    before = json.loads(_preflight("--json", "--", "--fps", "24").stdout)
    after = json.loads(_preflight("--", "--fps", "24", "--json").stdout)
    assert before == after


def test_preflight_human_output_is_unchanged_without_the_flag():
    out = _preflight().stdout
    assert out.startswith("Configuration summary:")
    assert "Configuration OK." in out
