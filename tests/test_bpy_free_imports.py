"""The config and defect-metadata layers must import without Blender.

Constraint validation runs *before* Blender is launched, so anything it reads
has to be importable with no ``bpy`` available at all. These tests run in a
subprocess with ``bpy`` blocked outright — the in-process ``conftest.py`` stub
would mask exactly the coupling being tested.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_BLOCK_BPY = """
import sys
class _Blocker:
    def find_module(self, name, path=None):
        if name == "bpy" or name.startswith("bpy."):
            return self
    def load_module(self, name):
        raise ImportError("bpy is deliberately blocked")
sys.meta_path.insert(0, _Blocker())
sys.path.insert(0, {root!r})
"""


def _run_without_bpy(body: str) -> subprocess.CompletedProcess:
    script = _BLOCK_BPY.format(root=str(PROJECT_ROOT)) + textwrap.dedent(body)
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def test_config_layer_imports_without_bpy():
    result = _run_without_bpy(
        """
        import app.config
        from app.config import PipelineSettings, CameraConfig, TrackGeometryConfig
        from app.config import EnvironmentConfig, AppearanceConfig, RenderConfig
        PipelineSettings()
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_cli_parser_imports_without_bpy():
    result = _run_without_bpy(
        """
        from config import parse_pipeline_settings
        s = parse_pipeline_settings(["--", "--fps", "24"])
        assert s.render.fps == 24
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_validation_layer_imports_without_bpy():
    """The whole point of the validation layer: it runs before Blender exists."""
    result = _run_without_bpy(
        """
        from app.config import PipelineSettings
        from app.validation import Resolver, resolve_or_raise
        report = Resolver().resolve(PipelineSettings())
        assert report.ok, report.render()
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_derived_quantities_compute_without_bpy():
    """Constraints read these, so they must be reachable outside Blender too."""
    result = _run_without_bpy(
        """
        from app.config import PipelineSettings
        from app.validation.derived import frame_footprint, longest_defect_length
        settings = PipelineSettings()
        assert frame_footprint(settings)[0] > 0
        assert longest_defect_length(settings) > 0
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_preflight_tool_runs_without_bpy():
    """tools/preflight.py is the standalone gate — Blender must not be needed."""
    result = _run_without_bpy(
        """
        import runpy, sys
        sys.argv = ["preflight.py", "--", "--fps", "24"]
        try:
            runpy.run_path("tools/preflight.py", run_name="__main__")
        except SystemExit as exit_code:
            assert exit_code.code == 0, exit_code.code
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_defect_registry_imports_without_bpy():
    """Defect *metadata* must be readable outside Blender, unlike apply()."""
    result = _run_without_bpy(
        """
        from app.geometry.defects.registry import ALL_DEFECTS
        assert len(ALL_DEFECTS) == 13, len(ALL_DEFECTS)
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_defect_selector_imports_without_bpy():
    result = _run_without_bpy(
        """
        from app.geometry.defects import DefectSelector
        sel = DefectSelector.default(seed=42)
        assert len(sel.all_variants()) > 0
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_geometry_package_does_not_eagerly_import_builders():
    """app.geometry must not pull in bpy just by being imported."""
    result = _run_without_bpy(
        """
        import app.geometry
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_lazy_builder_access_still_raises_without_bpy():
    """The lazy export is real: touching TrackSection does need bpy."""
    result = _run_without_bpy(
        """
        import app.geometry
        try:
            app.geometry.TrackSection
        except ImportError:
            print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_unknown_lazy_attribute_raises_attribute_error():
    result = _run_without_bpy(
        """
        import app.geometry
        try:
            app.geometry.NoSuchThing
        except AttributeError:
            print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
