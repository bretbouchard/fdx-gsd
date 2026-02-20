"""Shot and ShotList data models for the Shot Layer.

Dataclasses for representing individual shots and shot lists,
following the Issue dataclass pattern from core/validation/base.py.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json

from .types import CameraAngle, CameraMovement, ShotType


@dataclass
class Shot:
    """
    Represents a single shot suggestion.

    Tracks the shot type, camera setup, scene context, and evidence linkage.
    Mirrors the Issue dataclass pattern from Phase 4 validation.
    """

    shot_id: str  # Unique identifier like "shot_000001"
    scene_id: str  # Scene this shot belongs to
    scene_number: int  # Scene sequence number
    shot_number: int  # Shot order within scene
    shot_type: ShotType
    angle: CameraAngle = CameraAngle.EYE_LEVEL
    movement: CameraMovement = CameraMovement.STATIC
    description: str = ""
    subject: Optional[str] = None  # Character or object in focus
    characters: List[str] = field(default_factory=list)
    location: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    suggested_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict with enum values as strings, sorted lists for determinism.
        """
        return {
            "shot_id": self.shot_id,
            "scene_id": self.scene_id,
            "scene_number": self.scene_number,
            "shot_number": self.shot_number,
            "shot_type": self.shot_type.value,
            "angle": self.angle.value,
            "movement": self.movement.value,
            "description": self.description,
            "subject": self.subject,
            "characters": sorted(self.characters) if self.characters else [],
            "location": self.location,
            "evidence_ids": sorted(self.evidence_ids) if self.evidence_ids else [],
            "notes": self.notes,
            "suggested_at": self.suggested_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shot":
        """Create from dictionary.

        Args:
            data: Dictionary with shot data

        Returns:
            Shot instance
        """
        return cls(
            shot_id=data["shot_id"],
            scene_id=data["scene_id"],
            scene_number=data["scene_number"],
            shot_number=data["shot_number"],
            shot_type=ShotType(data["shot_type"]),
            angle=CameraAngle(data.get("angle", "eye-level")),
            movement=CameraMovement(data.get("movement", "Static")),
            description=data.get("description", ""),
            subject=data.get("subject"),
            characters=data.get("characters", []),
            location=data.get("location", ""),
            evidence_ids=data.get("evidence_ids", []),
            notes=data.get("notes"),
            suggested_at=(
                datetime.fromisoformat(data["suggested_at"])
                if data.get("suggested_at")
                else datetime.now()
            ),
        )


@dataclass
class ShotList:
    """
    Represents a complete shot list for a project.

    Contains all shots organized by scene, with methods for
    serialization and filtering.
    """

    project_id: str
    shots: List[Shot] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Shots are sorted by scene_number, then shot_number for determinism.

        Returns:
            Dict with full shot list and metadata
        """
        # Sort shots by scene_number, then shot_number
        sorted_shots = sorted(
            self.shots,
            key=lambda s: (s.scene_number, s.shot_number),
        )

        return {
            "version": "1.0",
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "total_shots": len(sorted_shots),
            "shots": [shot.to_dict() for shot in sorted_shots],
        }

    def save(self, path: Path) -> None:
        """Write shot list to JSON file.

        Args:
            path: Output file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShotList":
        """Create from dictionary.

        Args:
            data: Dictionary with shot list data

        Returns:
            ShotList instance
        """
        shots = [Shot.from_dict(s) for s in data.get("shots", [])]
        return cls(
            project_id=data["project_id"],
            shots=shots,
            generated_at=(
                datetime.fromisoformat(data["generated_at"])
                if data.get("generated_at")
                else datetime.now()
            ),
        )

    @classmethod
    def load(cls, path: Path) -> "ShotList":
        """Load shot list from JSON file.

        Args:
            path: Path to shot list JSON

        Returns:
            ShotList instance
        """
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def get_shots_for_scene(self, scene_id: str) -> List[Shot]:
        """Get all shots for a specific scene.

        Args:
            scene_id: Scene identifier

        Returns:
            List of shots for the scene, sorted by shot_number
        """
        shots = [s for s in self.shots if s.scene_id == scene_id]
        return sorted(shots, key=lambda s: s.shot_number)

    def get_shots_for_scene_number(self, scene_number: int) -> List[Shot]:
        """Get all shots for a scene by number.

        Args:
            scene_number: Scene sequence number

        Returns:
            List of shots for the scene, sorted by shot_number
        """
        shots = [s for s in self.shots if s.scene_number == scene_number]
        return sorted(shots, key=lambda s: s.shot_number)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the shot list.

        Returns:
            Dict with counts by shot type and scene
        """
        type_counts: Dict[str, int] = {}
        scene_counts: Dict[int, int] = {}

        for shot in self.shots:
            type_key = shot.shot_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

            scene_counts[shot.scene_number] = scene_counts.get(shot.scene_number, 0) + 1

        return {
            "total_shots": len(self.shots),
            "by_shot_type": type_counts,
            "by_scene": scene_counts,
            "unique_scenes": len(scene_counts),
        }

    def add_shot(self, shot: Shot) -> None:
        """Add a shot to the list.

        Args:
            shot: Shot to add
        """
        self.shots.append(shot)
