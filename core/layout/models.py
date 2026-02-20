"""Layout brief data models for Blender integration.

Dataclasses for representing scene layouts, camera setups, and character positions.
Following the Shot/ShotList dataclass pattern from core/shots/models.py.

Blender Coordinate System (Z-up):
- X: right
- Y: forward (into screen)
- Z: up
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json


@dataclass
class CharacterPosition:
    """
    Character placement in a scene.

    Represents where a character stands, their facing direction,
    and blocking notes for 3D previz.
    """

    character_id: str
    name: str
    position: Dict[str, float]  # {"x": 0.0, "y": 0.0, "z": 0.0}
    facing: Dict[str, float]  # Direction vector {"x": 0, "y": 1, "z": 0}
    posture: str = "standing"
    blocking_notes: str = ""
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "position": self.position,
            "facing": self.facing,
            "posture": self.posture,
            "blocking_notes": self.blocking_notes,
            "evidence_ids": sorted(self.evidence_ids) if self.evidence_ids else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterPosition":
        """Create from dictionary."""
        return cls(
            character_id=data["character_id"],
            name=data["name"],
            position=data.get("position", {"x": 0.0, "y": 0.0, "z": 0.0}),
            facing=data.get("facing", {"x": 0, "y": 1, "z": 0}),
            posture=data.get("posture", "standing"),
            blocking_notes=data.get("blocking_notes", ""),
            evidence_ids=data.get("evidence_ids", []),
        )


@dataclass
class PropPosition:
    """
    Prop/object placement in a scene.

    Represents where a prop is located in 3D space.
    """

    prop_id: str
    name: str
    position: Dict[str, float]  # {"x": 0.0, "y": 0.0, "z": 0.0}
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "prop_id": self.prop_id,
            "name": self.name,
            "position": self.position,
            "evidence_ids": sorted(self.evidence_ids) if self.evidence_ids else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PropPosition":
        """Create from dictionary."""
        return cls(
            prop_id=data["prop_id"],
            name=data["name"],
            position=data.get("position", {"x": 0.0, "y": 0.0, "z": 0.0}),
            evidence_ids=data.get("evidence_ids", []),
        )


@dataclass
class CameraSetup:
    """
    Camera configuration for a shot.

    Contains camera position, rotation, lens settings, and
    links back to the source shot.
    """

    setup_id: str  # e.g., "CAM_shot_001_001"
    shot_id: str  # Links to Shot.shot_id
    shot_type: str  # WS, MS, CU, etc.
    camera: Dict[str, Any]  # position, rotation, lens_mm, sensor_width
    target: Dict[str, float]  # Look-at point {"x": 0, "y": 0, "z": 0}
    movement: str = "Static"
    description: str = ""
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "setup_id": self.setup_id,
            "shot_id": self.shot_id,
            "shot_type": self.shot_type,
            "camera": self.camera,
            "target": self.target,
            "movement": self.movement,
            "description": self.description,
            "evidence_ids": sorted(self.evidence_ids) if self.evidence_ids else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraSetup":
        """Create from dictionary."""
        return cls(
            setup_id=data["setup_id"],
            shot_id=data["shot_id"],
            shot_type=data["shot_type"],
            camera=data.get("camera", {}),
            target=data.get("target", {"x": 0, "y": 0, "z": 0}),
            movement=data.get("movement", "Static"),
            description=data.get("description", ""),
            evidence_ids=data.get("evidence_ids", []),
        )


@dataclass
class SceneLayout:
    """
    Complete layout for one scene.

    Contains characters, props, camera setups, and environment settings.
    """

    scene_id: str
    slugline: str
    location_id: str
    int_ext: str  # "INT" or "EXT"
    time_of_day: str  # "DAY", "NIGHT", etc.
    environment: Dict[str, Any]  # description, lighting_preset
    characters: List[CharacterPosition] = field(default_factory=list)
    props: List[PropPosition] = field(default_factory=list)
    camera_setups: List[CameraSetup] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        All nested lists are sorted by their id fields for determinism.
        """
        # Sort nested lists by id fields
        sorted_characters = sorted(self.characters, key=lambda c: c.character_id)
        sorted_props = sorted(self.props, key=lambda p: p.prop_id)
        sorted_cameras = sorted(self.camera_setups, key=lambda c: c.setup_id)

        return {
            "scene_id": self.scene_id,
            "slugline": self.slugline,
            "location_id": self.location_id,
            "int_ext": self.int_ext,
            "time_of_day": self.time_of_day,
            "environment": self.environment,
            "characters": [c.to_dict() for c in sorted_characters],
            "props": [p.to_dict() for p in sorted_props],
            "camera_setups": [c.to_dict() for c in sorted_cameras],
            "evidence_ids": sorted(self.evidence_ids) if self.evidence_ids else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneLayout":
        """Create from dictionary."""
        characters = [
            CharacterPosition.from_dict(c)
            for c in data.get("characters", [])
        ]
        props = [
            PropPosition.from_dict(p)
            for p in data.get("props", [])
        ]
        camera_setups = [
            CameraSetup.from_dict(c)
            for c in data.get("camera_setups", [])
        ]

        return cls(
            scene_id=data["scene_id"],
            slugline=data.get("slugline", ""),
            location_id=data.get("location_id", ""),
            int_ext=data.get("int_ext", "INT"),
            time_of_day=data.get("time_of_day", "DAY"),
            environment=data.get("environment", {}),
            characters=characters,
            props=props,
            camera_setups=camera_setups,
            evidence_ids=data.get("evidence_ids", []),
        )


@dataclass
class LayoutBrief:
    """
    Top-level container for all scene layouts.

    Contains all scene layouts with metadata for Blender consumption.
    """

    version: str = "1.0"
    project_id: str = ""
    scene_layouts: List[SceneLayout] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Scene layouts are sorted by scene_id for determinism.
        """
        sorted_layouts = sorted(self.scene_layouts, key=lambda s: s.scene_id)

        return {
            "version": self.version,
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "total_scenes": len(sorted_layouts),
            "scene_layouts": [s.to_dict() for s in sorted_layouts],
        }

    def save(self, path: Path) -> None:
        """Write layout brief to JSON file.

        Args:
            path: Output file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutBrief":
        """Create from dictionary."""
        scene_layouts = [
            SceneLayout.from_dict(s)
            for s in data.get("scene_layouts", [])
        ]

        return cls(
            version=data.get("version", "1.0"),
            project_id=data.get("project_id", ""),
            scene_layouts=scene_layouts,
            generated_at=(
                datetime.fromisoformat(data["generated_at"])
                if data.get("generated_at")
                else datetime.now()
            ),
        )

    @classmethod
    def load(cls, path: Path) -> "LayoutBrief":
        """Load layout brief from JSON file.

        Args:
            path: Path to layout brief JSON

        Returns:
            LayoutBrief instance
        """
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def get_layout_for_scene(self, scene_id: str) -> Optional[SceneLayout]:
        """Get layout for a specific scene.

        Args:
            scene_id: Scene identifier

        Returns:
            SceneLayout or None if not found
        """
        for layout in self.scene_layouts:
            if layout.scene_id == scene_id:
                return layout
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the layout brief.

        Returns:
            Dict with counts by scene
        """
        return {
            "total_scenes": len(self.scene_layouts),
            "total_characters": sum(len(s.characters) for s in self.scene_layouts),
            "total_props": sum(len(s.props) for s in self.scene_layouts),
            "total_cameras": sum(len(s.camera_setups) for s in self.scene_layouts),
        }
