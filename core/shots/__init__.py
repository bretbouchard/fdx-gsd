"""Shot Layer module for screenplay shot suggestion and export.

This module provides shot suggestion functionality for screenplay analysis,
following the Issue/BaseValidator pattern from the validation layer.

Main Components:
    - ShotSuggester: Orchestrator that processes ScriptGraph and generates shots
    - ShotDetector: Heuristic engine for detecting shot opportunities
    - ShotListExporter: Exports shot lists to CSV and JSON formats

Data Models:
    - Shot: Individual shot suggestion with evidence linking
    - ShotList: Container for all shots with serialization methods

Enums:
    - ShotType: WS, MS, MCU, CU, ECU, INSERT, OTS, POV, TWO
    - CameraAngle: eye-level, high, low, dutch
    - CameraMovement: Static, Pan, Tilt, Dolly, Tracking, Handheld

Usage:
    from core.shots import ShotSuggester, ShotListExporter

    suggester = ShotSuggester(build_path=Path("build"))
    result = suggester.suggest()

    if result.success:
        shot_list = suggester.get_shot_list()
        exporter = ShotListExporter(shot_list)
        exporter.export_csv(Path("exports/shotlist.csv"))
"""

from .types import CameraAngle, CameraMovement, ShotType
from .models import Shot, ShotList

__all__ = [
    # Types
    "ShotType",
    "CameraAngle",
    "CameraMovement",
    # Models
    "Shot",
    "ShotList",
]
