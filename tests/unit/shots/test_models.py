"""Unit tests for Shot and ShotList dataclasses."""
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from core.shots.types import ShotType, CameraAngle, CameraMovement
from core.shots.models import Shot, ShotList


class TestShot:
    """Tests for Shot dataclass."""

    def test_shot_creation(self):
        """Create Shot with required fields, verify attributes."""
        shot = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        )

        assert shot.shot_id == "shot_001_001"
        assert shot.scene_id == "scene_001"
        assert shot.scene_number == 1
        assert shot.shot_number == 1
        assert shot.shot_type == ShotType.WS
        assert shot.angle == CameraAngle.EYE_LEVEL  # default
        assert shot.movement == CameraMovement.STATIC  # default

    def test_shot_with_all_fields(self):
        """Create Shot with all fields populated."""
        shot = Shot(
            shot_id="shot_001_002",
            scene_id="scene_001",
            scene_number=1,
            shot_number=2,
            shot_type=ShotType.CU,
            angle=CameraAngle.HIGH,
            movement=CameraMovement.PAN,
            description="Close-up of John's face",
            subject="JOHN",
            characters=["JOHN", "MARY"],
            location="OFFICE",
            evidence_ids=["ev_001", "ev_002"],
            notes="Emotional moment",
        )

        assert shot.description == "Close-up of John's face"
        assert shot.subject == "JOHN"
        assert shot.characters == ["JOHN", "MARY"]
        assert shot.location == "OFFICE"
        assert shot.evidence_ids == ["ev_001", "ev_002"]
        assert shot.notes == "Emotional moment"

    def test_shot_to_dict(self):
        """Verify serialization produces correct dict with sorted lists."""
        shot = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.CU,
            characters=["MARY", "JOHN"],  # unsorted
            evidence_ids=["ev_002", "ev_001"],  # unsorted
        )

        result = shot.to_dict()

        assert result["shot_id"] == "shot_001_001"
        assert result["shot_type"] == "CU"
        assert result["characters"] == ["JOHN", "MARY"]  # sorted
        assert result["evidence_ids"] == ["ev_001", "ev_002"]  # sorted
        assert "suggested_at" in result

    def test_shot_from_dict(self):
        """Verify deserialization reconstructs Shot correctly."""
        data = {
            "shot_id": "shot_001_001",
            "scene_id": "scene_001",
            "scene_number": 1,
            "shot_number": 1,
            "shot_type": "CU",
            "angle": "high",
            "movement": "Pan",
            "description": "Close-up",
            "subject": "JOHN",
            "characters": ["JOHN"],
            "location": "OFFICE",
            "evidence_ids": ["ev_001"],
            "notes": None,
            "suggested_at": "2026-02-19T12:00:00",
        }

        shot = Shot.from_dict(data)

        assert shot.shot_id == "shot_001_001"
        assert shot.shot_type == ShotType.CU
        assert shot.angle == CameraAngle.HIGH
        assert shot.movement == CameraMovement.PAN
        assert shot.description == "Close-up"

    def test_shot_from_dict_defaults(self):
        """Verify deserialization with missing optional fields uses defaults."""
        data = {
            "shot_id": "shot_001_001",
            "scene_id": "scene_001",
            "scene_number": 1,
            "shot_number": 1,
            "shot_type": "WS",
        }

        shot = Shot.from_dict(data)

        assert shot.angle == CameraAngle.EYE_LEVEL
        assert shot.movement == CameraMovement.STATIC
        assert shot.characters == []
        assert shot.evidence_ids == []

    def test_shot_deterministic_output(self):
        """Same Shot should produce same to_dict() output."""
        shot1 = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
            characters=["BOB", "ALICE"],
        )

        shot2 = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
            characters=["ALICE", "BOB"],  # different order
        )

        # Characters should be sorted, so output is the same
        dict1 = shot1.to_dict()
        dict2 = shot2.to_dict()

        assert dict1["characters"] == dict2["characters"]


class TestShotList:
    """Tests for ShotList dataclass."""

    def test_shot_list_creation(self):
        """Create ShotList with multiple shots."""
        shot1 = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        )
        shot2 = Shot(
            shot_id="shot_002_001",
            scene_id="scene_002",
            scene_number=2,
            shot_number=1,
            shot_type=ShotType.WS,
        )

        shot_list = ShotList(
            project_id="test-project",
            shots=[shot1, shot2],
        )

        assert shot_list.project_id == "test-project"
        assert len(shot_list.shots) == 2

    def test_shot_list_to_dict(self):
        """Verify ShotList serialization with sorted shots."""
        shot1 = Shot(
            shot_id="shot_001_002",
            scene_id="scene_001",
            scene_number=1,
            shot_number=2,
            shot_type=ShotType.CU,
        )
        shot2 = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        )

        shot_list = ShotList(project_id="test", shots=[shot1, shot2])
        result = shot_list.to_dict()

        # Shots should be sorted by scene_number, then shot_number
        assert result["shots"][0]["shot_number"] == 1
        assert result["shots"][1]["shot_number"] == 2
        assert result["total_shots"] == 2

    def test_shot_list_get_shots_for_scene(self):
        """Filter shots by scene_id."""
        shot1 = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        )
        shot2 = Shot(
            shot_id="shot_002_001",
            scene_id="scene_002",
            scene_number=2,
            shot_number=1,
            shot_type=ShotType.WS,
        )

        shot_list = ShotList(project_id="test", shots=[shot1, shot2])
        result = shot_list.get_shots_for_scene("scene_001")

        assert len(result) == 1
        assert result[0].scene_id == "scene_001"

    def test_shot_list_get_shots_for_scene_number(self):
        """Filter shots by scene number."""
        shot_list = ShotList(project_id="test")
        shot_list.add_shot(Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        ))
        shot_list.add_shot(Shot(
            shot_id="shot_002_001",
            scene_id="scene_002",
            scene_number=2,
            shot_number=1,
            shot_type=ShotType.WS,
        ))

        result = shot_list.get_shots_for_scene_number(2)
        assert len(result) == 1
        assert result[0].scene_number == 2

    def test_shot_list_save(self):
        """Save to JSON file and verify contents."""
        shot = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        )
        shot_list = ShotList(project_id="test", shots=[shot])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "shotgraph.json"
            shot_list.save(path)

            assert path.exists()
            data = json.loads(path.read_text())
            assert data["project_id"] == "test"
            assert len(data["shots"]) == 1

    def test_shot_list_load(self):
        """Load shot list from JSON file."""
        json_content = """{
            "version": "1.0",
            "project_id": "test-project",
            "generated_at": "2026-02-19T12:00:00",
            "total_shots": 1,
            "shots": [{
                "shot_id": "shot_001_001",
                "scene_id": "scene_001",
                "scene_number": 1,
                "shot_number": 1,
                "shot_type": "WS",
                "angle": "eye-level",
                "movement": "Static",
                "description": "",
                "subject": null,
                "characters": [],
                "location": "",
                "evidence_ids": [],
                "notes": null,
                "suggested_at": "2026-02-19T12:00:00"
            }]
        }"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "shotgraph.json"
            path.write_text(json_content)

            shot_list = ShotList.load(path)

            assert shot_list.project_id == "test-project"
            assert len(shot_list.shots) == 1
            assert shot_list.shots[0].shot_type == ShotType.WS

    def test_shot_list_get_summary(self):
        """Get summary of shot list."""
        shot_list = ShotList(project_id="test")
        shot_list.add_shot(Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        ))
        shot_list.add_shot(Shot(
            shot_id="shot_001_002",
            scene_id="scene_001",
            scene_number=1,
            shot_number=2,
            shot_type=ShotType.CU,
        ))
        shot_list.add_shot(Shot(
            shot_id="shot_002_001",
            scene_id="scene_002",
            scene_number=2,
            shot_number=1,
            shot_type=ShotType.WS,
        ))

        summary = shot_list.get_summary()

        assert summary["total_shots"] == 3
        assert summary["by_shot_type"]["WS"] == 2
        assert summary["by_shot_type"]["CU"] == 1
        assert summary["by_scene"][1] == 2
        assert summary["by_scene"][2] == 1
        assert summary["unique_scenes"] == 2

    def test_shot_list_add_shot(self):
        """Add shot to list."""
        shot_list = ShotList(project_id="test")
        shot = Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
        )

        shot_list.add_shot(shot)

        assert len(shot_list.shots) == 1
        assert shot_list.shots[0].shot_id == "shot_001_001"
