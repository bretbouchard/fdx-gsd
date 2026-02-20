"""Unit tests for layout data models.

Tests all dataclasses in core/layout/models.py:
- CharacterPosition
- PropPosition
- CameraSetup
- SceneLayout
- LayoutBrief
"""
import json
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from core.layout.models import (
    CharacterPosition,
    PropPosition,
    CameraSetup,
    SceneLayout,
    LayoutBrief,
)


class TestCharacterPosition:
    """Tests for CharacterPosition dataclass."""

    def test_to_dict(self):
        """Test to_dict() produces correct dict with sorted lists."""
        char = CharacterPosition(
            character_id="CHAR_john",
            name="John",
            position={"x": 1.0, "y": 0.0, "z": 0.0},
            facing={"x": 0, "y": 1, "z": 0},
            posture="standing",
            blocking_notes="enters from left",
            evidence_ids=["EV_002", "EV_001"],
        )
        result = char.to_dict()

        assert result["character_id"] == "CHAR_john"
        assert result["name"] == "John"
        assert result["position"] == {"x": 1.0, "y": 0.0, "z": 0.0}
        assert result["facing"] == {"x": 0, "y": 1, "z": 0}
        assert result["posture"] == "standing"
        assert result["blocking_notes"] == "enters from left"
        # Evidence IDs should be sorted
        assert result["evidence_ids"] == ["EV_001", "EV_002"]

    def test_from_dict(self):
        """Test from_dict() recreates object correctly."""
        data = {
            "character_id": "CHAR_jane",
            "name": "Jane",
            "position": {"x": -1.5, "y": 0.0, "z": 0.0},
            "facing": {"x": 0, "y": 1, "z": 0},
            "posture": "sitting",
            "blocking_notes": "",
            "evidence_ids": ["EV_003"],
        }
        char = CharacterPosition.from_dict(data)

        assert char.character_id == "CHAR_jane"
        assert char.name == "Jane"
        assert char.position == {"x": -1.5, "y": 0.0, "z": 0.0}
        assert char.posture == "sitting"
        assert char.evidence_ids == ["EV_003"]

    def test_roundtrip(self):
        """Test to_dict() -> from_dict() roundtrip."""
        original = CharacterPosition(
            character_id="CHAR_test",
            name="Test",
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            facing={"x": 0, "y": 1, "z": 0},
            evidence_ids=["EV_001", "EV_002"],
        )
        data = original.to_dict()
        restored = CharacterPosition.from_dict(data)

        assert restored.character_id == original.character_id
        assert restored.name == original.name
        assert restored.position == original.position
        assert restored.evidence_ids == original.evidence_ids

    def test_default_values(self):
        """Test default values are set correctly."""
        char = CharacterPosition(
            character_id="CHAR_x",
            name="X",
            position={"x": 0, "y": 0, "z": 0},
            facing={"x": 0, "y": 1, "z": 0},
        )
        assert char.posture == "standing"
        assert char.blocking_notes == ""
        assert char.evidence_ids == []


class TestPropPosition:
    """Tests for PropPosition dataclass."""

    def test_to_dict(self):
        """Test to_dict() produces correct dict."""
        prop = PropPosition(
            prop_id="PROP_gun",
            name="Gun",
            position={"x": 0.5, "y": 0.0, "z": 1.0},
            evidence_ids=["EV_004"],
        )
        result = prop.to_dict()

        assert result["prop_id"] == "PROP_gun"
        assert result["name"] == "Gun"
        assert result["position"] == {"x": 0.5, "y": 0.0, "z": 1.0}
        assert result["evidence_ids"] == ["EV_004"]

    def test_from_dict(self):
        """Test from_dict() recreates object."""
        data = {
            "prop_id": "PROP_phone",
            "name": "Phone",
            "position": {"x": 0, "y": 0, "z": 0},
            "evidence_ids": [],
        }
        prop = PropPosition.from_dict(data)

        assert prop.prop_id == "PROP_phone"
        assert prop.name == "Phone"


class TestCameraSetup:
    """Tests for CameraSetup dataclass."""

    def test_to_dict_includes_nested_dicts(self):
        """Test to_dict() includes camera and target dicts."""
        setup = CameraSetup(
            setup_id="CAM_shot_001_001",
            shot_id="shot_001_001",
            shot_type="WS",
            camera={
                "position": {"x": 0, "y": -5, "z": 2},
                "rotation": {"pitch": -10, "yaw": 0, "roll": 0},
                "lens_mm": 35,
                "sensor_width": 36,
            },
            target={"x": 0, "y": 0, "z": 1.6},
            movement="Static",
            description="Establishing shot",
            evidence_ids=["EV_001"],
        )
        result = setup.to_dict()

        assert result["setup_id"] == "CAM_shot_001_001"
        assert result["shot_id"] == "shot_001_001"
        assert result["shot_type"] == "WS"
        assert "position" in result["camera"]
        assert result["target"] == {"x": 0, "y": 0, "z": 1.6}
        assert result["movement"] == "Static"

    def test_from_dict_handles_nested_dicts(self):
        """Test from_dict() handles nested camera dict."""
        data = {
            "setup_id": "CAM_test",
            "shot_id": "shot_test",
            "shot_type": "CU",
            "camera": {
                "position": {"x": 0, "y": -1.2, "z": 1.6},
                "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                "lens_mm": 50,
                "sensor_width": 36,
            },
            "target": {"x": 0, "y": 0, "z": 1.6},
            "movement": "Pan",
            "description": "",
            "evidence_ids": [],
        }
        setup = CameraSetup.from_dict(data)

        assert setup.setup_id == "CAM_test"
        assert setup.shot_type == "CU"
        assert setup.camera["lens_mm"] == 50


class TestSceneLayout:
    """Tests for SceneLayout dataclass."""

    def test_to_dict_includes_nested_lists(self):
        """Test to_dict() includes characters, props, cameras."""
        scene = SceneLayout(
            scene_id="SCN_001",
            slugline="INT. OFFICE - DAY",
            location_id="LOC_office",
            int_ext="INT",
            time_of_day="DAY",
            environment={"description": "Office", "lighting_preset": "interior_day"},
            characters=[
                CharacterPosition(
                    character_id="CHAR_alice",
                    name="Alice",
                    position={"x": 0, "y": 0, "z": 0},
                    facing={"x": 0, "y": 1, "z": 0},
                )
            ],
            props=[],
            camera_setups=[
                CameraSetup(
                    setup_id="CAM_shot_001_001",
                    shot_id="shot_001_001",
                    shot_type="WS",
                    camera={},
                    target={"x": 0, "y": 0, "z": 1.6},
                )
            ],
            evidence_ids=["EV_001"],
        )
        result = scene.to_dict()

        assert result["scene_id"] == "SCN_001"
        assert result["slugline"] == "INT. OFFICE - DAY"
        assert len(result["characters"]) == 1
        assert len(result["camera_setups"]) == 1
        assert result["evidence_ids"] == ["EV_001"]

    def test_from_dict_recreates_nested_objects(self):
        """Test from_dict() recreates nested CharacterPosition and CameraSetup."""
        data = {
            "scene_id": "SCN_002",
            "slugline": "EXT. PARK - NIGHT",
            "location_id": "LOC_park",
            "int_ext": "EXT",
            "time_of_day": "NIGHT",
            "environment": {},
            "characters": [
                {
                    "character_id": "CHAR_bob",
                    "name": "Bob",
                    "position": {"x": 0, "y": 0, "z": 0},
                    "facing": {"x": 0, "y": 1, "z": 0},
                }
            ],
            "props": [],
            "camera_setups": [],
            "evidence_ids": [],
        }
        scene = SceneLayout.from_dict(data)

        assert scene.scene_id == "SCN_002"
        assert len(scene.characters) == 1
        assert isinstance(scene.characters[0], CharacterPosition)
        assert scene.characters[0].name == "Bob"

    def test_empty_lists_handled(self):
        """Test empty lists are handled correctly."""
        scene = SceneLayout(
            scene_id="SCN_003",
            slugline="INT. EMPTY ROOM - DAY",
            location_id="",
            int_ext="INT",
            time_of_day="DAY",
            environment={},
        )
        result = scene.to_dict()

        assert result["characters"] == []
        assert result["props"] == []
        assert result["camera_setups"] == []


class TestLayoutBrief:
    """Tests for LayoutBrief dataclass."""

    def test_to_dict_includes_version_and_metadata(self):
        """Test to_dict() includes version, project_id, generated_at."""
        brief = LayoutBrief(
            version="1.0",
            project_id="test-project",
            scene_layouts=[],
            generated_at=datetime(2026, 2, 19, 12, 0, 0),
        )
        result = brief.to_dict()

        assert result["version"] == "1.0"
        assert result["project_id"] == "test-project"
        assert "generated_at" in result
        assert result["total_scenes"] == 0

    def test_save_writes_valid_json(self):
        """Test save() writes valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            brief = LayoutBrief(
                version="1.0",
                project_id="test-project",
                scene_layouts=[],
            )
            path = Path(tmpdir) / "layout_brief.json"
            brief.save(path)

            assert path.exists()
            data = json.loads(path.read_text())
            assert data["version"] == "1.0"
            assert data["project_id"] == "test-project"

    def test_load_works_correctly(self):
        """Test load() creates LayoutBrief from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "layout_brief.json"
            data = {
                "version": "1.0",
                "project_id": "load-test",
                "generated_at": "2026-02-19T12:00:00",
                "total_scenes": 0,
                "scene_layouts": [],
            }
            path.write_text(json.dumps(data))

            brief = LayoutBrief.load(path)

            assert brief.version == "1.0"
            assert brief.project_id == "load-test"
            assert len(brief.scene_layouts) == 0


class TestDeterminism:
    """Tests for deterministic output."""

    def test_sorted_lists(self):
        """Test lists are sorted for determinism."""
        char = CharacterPosition(
            character_id="CHAR_test",
            name="Test",
            position={"x": 0, "y": 0, "z": 0},
            facing={"x": 0, "y": 1, "z": 0},
            evidence_ids=["EV_003", "EV_001", "EV_002"],
        )
        result = char.to_dict()

        # Should be sorted
        assert result["evidence_ids"] == ["EV_001", "EV_002", "EV_003"]

    def test_reproducible_output(self):
        """Test multiple to_dict() calls produce identical output."""
        scene = SceneLayout(
            scene_id="SCN_test",
            slugline="Test",
            location_id="",
            int_ext="INT",
            time_of_day="DAY",
            environment={},
            characters=[
                CharacterPosition(
                    character_id="CHAR_b",
                    name="B",
                    position={"x": 0, "y": 0, "z": 0},
                    facing={"x": 0, "y": 1, "z": 0},
                ),
                CharacterPosition(
                    character_id="CHAR_a",
                    name="A",
                    position={"x": 1, "y": 0, "z": 0},
                    facing={"x": 0, "y": 1, "z": 0},
                ),
            ],
        )

        # Multiple calls should produce identical JSON
        json1 = json.dumps(scene.to_dict(), sort_keys=True)
        json2 = json.dumps(scene.to_dict(), sort_keys=True)

        assert json1 == json2
