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
    - ShotSuggestionResult: Result of shot suggestion operation

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
        exporter = ShotListExporter()
        exporter.export_csv(shot_list, Path("exports/shotlist.csv"))

CLI Usage:
    gsd suggest-shots  # Generates exports/shotlist.csv and build/shotgraph.json
"""

from .types import CameraAngle, CameraMovement, ShotType
from .models import Shot, ShotList
from .detector import ShotDetector
from .exporter import ShotListExporter
from .suggester import ShotSuggester, ShotSuggestionResult, suggest_shots

__all__ = [
    # Types
    "ShotType",
    "CameraAngle",
    "CameraMovement",
    # Models
    "Shot",
    "ShotList",
    # Components
    "ShotDetector",
    "ShotListExporter",
    "ShotSuggester",
    "ShotSuggestionResult",
    # Convenience functions
    "suggest_shots",
]
