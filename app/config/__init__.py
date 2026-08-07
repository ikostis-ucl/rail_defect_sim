"""Configuration layer — pure data, no ``bpy``.

Every config here is a frozen dataclass describing *what* to build. The
matching builders (which import ``bpy``) live under their own packages:

    TrackGeometryConfig  ->  app.geometry.TrackSection
    CameraConfig         ->  app.camera.CameraAnimator
    EnvironmentConfig    ->  app.scene.SceneSetup
    AppearanceConfig     ->  app.materials.MaterialFactory
    RenderConfig         ->  app.render.RenderSetup

Keeping this split means a run can be fully described and validated before
Blender is ever launched.
"""

from app.config.appearance import (
    AppearanceConfig,
    NoiseSurfaceAppearance,
    SurfaceAppearance,
)
from app.config.camera import CameraConfig
from app.config.environment import (
    EnvironmentConfig,
    GroundConfig,
    SunConfig,
    WorldConfig,
)
from app.config.geometry import RailConfig, TrackGeometryConfig
from app.config.render import RenderConfig
from app.config.settings import PipelineSettings

__all__ = [
    "PipelineSettings",
    "RenderConfig",
    "CameraConfig",
    "EnvironmentConfig",
    "WorldConfig",
    "SunConfig",
    "GroundConfig",
    "AppearanceConfig",
    "SurfaceAppearance",
    "NoiseSurfaceAppearance",
    "TrackGeometryConfig",
    "RailConfig",
]
