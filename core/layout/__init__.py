"""Layout brief generation module for Blender integration.

Generates layout briefs from ScriptGraph + ShotGraph for 3D previz.
Follows the ShotSuggester pattern from core/shots/suggester.py.

Key Components:
- Models: LayoutBrief, SceneLayout, CameraSetup, CharacterPosition, PropPosition
- Camera Math: calculate_camera_position() for shot type to 3D coordinates
- Generator: LayoutBriefGenerator orchestrates brief generation
- Exporter: LayoutBriefExporter writes JSON files for Blender

Output Format:
- blender/<scene_id>/layout_brief.json - Per-scene layout files
- build/layout_brief.json - Combined brief with all scenes
"""

from .models import (
    LayoutBrief,
    SceneLayout,
    CameraSetup,
    CharacterPosition,
    PropPosition,
)
from .camera_math import (
    calculate_camera_position,
    CameraPosition,
    CameraRotation,
    get_camera_setup_dict,
    SHOT_TYPE_DISTANCES,
)
from .generator import (
    LayoutBriefGenerator,
    generate_layout_brief,
    LayoutGenerationResult,
)
from .exporter import (
    LayoutBriefExporter,
    export_layout_brief,
)

__all__ = [
    # Models
    "LayoutBrief",
    "SceneLayout",
    "CameraSetup",
    "CharacterPosition",
    "PropPosition",
    # Camera math
    "calculate_camera_position",
    "CameraPosition",
    "CameraRotation",
    "get_camera_setup_dict",
    "SHOT_TYPE_DISTANCES",
    # Generator
    "LayoutBriefGenerator",
    "generate_layout_brief",
    "LayoutGenerationResult",
    # Exporter
    "LayoutBriefExporter",
    "export_layout_brief",
]
