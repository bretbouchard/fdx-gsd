"""Unit tests for LayoutBriefGenerator.

Tests all functions in core/layout/generator.py:
- LayoutBriefGenerator class
- LayoutGenerationResult dataclass
- generate_layout_brief convenience function
"""
import json
import pytest
from pathlib import Path
import tempfile

from core.layout.generator import (
    LayoutBriefGenerator,
    LayoutGenerationResult,
    generate_layout_brief,
)
from core.layout.models import LayoutBrief, SceneLayout, CameraSetup, CharacterPosition


@pytest.fixture
def sample_scriptgraph():
    """Create sample ScriptGraph for testing."""
    return {
        "version": "1.0",
        "project_id": "test-project",
        "scenes": [
            {
                "id": "SCN_001",
                "order": 1,
                "slugline": "INT. COFFEE SHOP - DAY",
                "int_ext": "INT",
                "time_of_day": "DAY",
                "links": {
                    "characters": ["CHAR_john", "CHAR_jane"],
                    "locations": ["LOC_coffee_shop"],
                    "evidence_ids": ["EV_001"],
                },
            },
            {
                "id": "SCN_002",
                "order": 2,
                "slugline": "EXT. PARK - NIGHT",
                "int_ext": "EXT",
                "time_of_day": "NIGHT",
                "links": {
                    "characters": ["CHAR_mike"],
                    "locations": ["LOC_park"],
                    "evidence_ids": ["EV_002"],
                },
            },
        ],
    }


@pytest.fixture
def sample_shotgraph():
    """Create sample ShotGraph for testing."""
    return {
        "version": "1.0",
        "project_id": "test-project",
        "shots": [
            {
                "shot_id": "shot_001_001",
                "scene_id": "SCN_001",
                "scene_number": 1,
                "shot_number": 1,
                "shot_type": "WS",
                "movement": "Static",
                "description": "Establishing shot",
                "evidence_ids": ["EV_003"],
            },
            {
                "shot_id": "shot_001_002",
                "scene_id": "SCN_001",
                "scene_number": 1,
                "shot_number": 2,
                "shot_type": "CU",
                "movement": "Push In",
                "description": "Close-up on John",
                "evidence_ids": [],
            },
            {
                "shot_id": "shot_002_001",
                "scene_id": "SCN_002",
                "scene_number": 2,
                "shot_number": 1,
                "shot_type": "MS",
                "movement": "Static",
                "description": "Mike in park",
                "evidence_ids": ["EV_004"],
            },
        ],
    }


@pytest.fixture
def build_path_with_data(sample_scriptgraph, sample_shotgraph):
    """Create temporary build directory with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        build_path = Path(tmpdir)
        (build_path / "scriptgraph.json").write_text(json.dumps(sample_scriptgraph))
        (build_path / "shotgraph.json").write_text(json.dumps(sample_shotgraph))
        yield build_path


class TestLayoutGenerationResult:
    """Tests for LayoutGenerationResult dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = LayoutGenerationResult(success=True)

        assert result.success is True
        assert result.scenes_processed == 0
        assert result.layouts_generated == 0
        assert result.errors == []

    def test_with_values(self):
        """Test result with custom values."""
        result = LayoutGenerationResult(
            success=True,
            scenes_processed=5,
            layouts_generated=5,
            errors=[],
        )

        assert result.success is True
        assert result.scenes_processed == 5
        assert result.layouts_generated == 5

    def test_with_errors(self):
        """Test result with errors."""
        result = LayoutGenerationResult(
            success=False,
            scenes_processed=0,
            layouts_generated=0,
            errors=["No scriptgraph.json found"],
        )

        assert result.success is False
        assert len(result.errors) == 1


class TestLayoutBriefGenerator:
    """Tests for LayoutBriefGenerator class."""

    def test_init_with_path(self, build_path_with_data):
        """Test generator initialization with build path."""
        generator = LayoutBriefGenerator(build_path_with_data)

        assert generator.build_path == build_path_with_data
        assert generator._scriptgraph is None
        assert generator._shotgraph is None

    def test_generate_creates_layout_brief(self, build_path_with_data):
        """Test generate() returns valid LayoutBrief."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        assert isinstance(brief, LayoutBrief)
        assert brief.project_id == "test-project"
        assert len(brief.scene_layouts) == 2

    def test_generate_creates_scene_layouts(self, build_path_with_data):
        """Test generate creates SceneLayout for each scene."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene_ids = [s.scene_id for s in brief.scene_layouts]

        assert "SCN_001" in scene_ids
        assert "SCN_002" in scene_ids

    def test_scene_layout_includes_characters(self, build_path_with_data):
        """Test SceneLayout includes characters."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        # Find SCN_001
        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        assert len(scene.characters) == 2
        char_ids = [c.character_id for c in scene.characters]
        assert "CHAR_jane" in char_ids  # Sorted
        assert "CHAR_john" in char_ids

    def test_scene_layout_includes_cameras(self, build_path_with_data):
        """Test SceneLayout includes camera setups."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        # Find SCN_001 (has 2 shots)
        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        assert len(scene.camera_setups) == 2

    def test_camera_setup_links_to_shot(self, build_path_with_data):
        """Test CameraSetup links to shot_id."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        shot_ids = [c.shot_id for c in scene.camera_setups]

        assert "shot_001_001" in shot_ids
        assert "shot_001_002" in shot_ids

    def test_camera_setup_has_shot_type(self, build_path_with_data):
        """Test CameraSetup has correct shot_type."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        # Find WS shot
        ws_cam = next(c for c in scene.camera_setups if c.shot_id == "shot_001_001")
        assert ws_cam.shot_type == "WS"

        # Find CU shot
        cu_cam = next(c for c in scene.camera_setups if c.shot_id == "shot_001_002")
        assert cu_cam.shot_type == "CU"

    def test_evidence_ids_propagated_to_scene(self, build_path_with_data):
        """Test scene evidence_ids are in SceneLayout."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        assert "EV_001" in scene.evidence_ids

    def test_evidence_ids_propagated_to_camera(self, build_path_with_data):
        """Test shot evidence_ids are in CameraSetup."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        ws_cam = next(c for c in scene.camera_setups if c.shot_id == "shot_001_001")

        assert "EV_003" in ws_cam.evidence_ids

    def test_character_position_calculated(self, build_path_with_data):
        """Test characters have calculated positions."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        for char in scene.characters:
            assert "x" in char.position
            assert "y" in char.position
            assert "z" in char.position

    def test_camera_position_calculated(self, build_path_with_data):
        """Test cameras have calculated positions."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        for cam in scene.camera_setups:
            assert "position" in cam.camera
            pos = cam.camera["position"]
            assert "x" in pos
            assert "y" in pos
            assert "z" in pos

    def test_environment_built_from_scene(self, build_path_with_data):
        """Test environment dict built from scene metadata."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        assert scene.environment["lighting_preset"] == "interior_day"

        scene2 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_002")

        assert scene2.environment["lighting_preset"] == "outdoor_night"

    def test_location_id_extracted(self, build_path_with_data):
        """Test location_id extracted from scene links."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        assert scene.location_id == "LOC_coffee_shop"

    def test_empty_shots_produces_empty_cameras(self, sample_scriptgraph):
        """Test scene with no shots produces empty camera_setups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir)
            (build_path / "scriptgraph.json").write_text(json.dumps(sample_scriptgraph))
            # Create shotgraph with no shots for SCN_001
            shotgraph = {"version": "1.0", "project_id": "test-project", "shots": []}
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            # Should still create scene layouts
            assert len(brief.scene_layouts) == 2

            # But with no camera setups
            for scene in brief.scene_layouts:
                assert len(scene.camera_setups) == 0

    def test_missing_shotgraph_raises_error(self, sample_scriptgraph):
        """Test missing shotgraph.json still works (shots are optional)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir)
            (build_path / "scriptgraph.json").write_text(json.dumps(sample_scriptgraph))
            # No shotgraph.json

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            # Should still create scene layouts
            assert len(brief.scene_layouts) == 2

    def test_missing_scriptgraph_raises_error(self):
        """Test missing scriptgraph.json raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir)
            # No scriptgraph.json

            generator = LayoutBriefGenerator(build_path)

            with pytest.raises(ValueError, match="No scriptgraph.json found"):
                generator.generate()

    def test_empty_scriptgraph_raises_error(self):
        """Test scriptgraph with no scenes raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir)
            scriptgraph = {"version": "1.0", "project_id": "test", "scenes": []}
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            generator = LayoutBriefGenerator(build_path)

            with pytest.raises(ValueError, match="No scenes found"):
                generator.generate()

    def test_get_summary(self, build_path_with_data):
        """Test get_summary returns correct statistics."""
        generator = LayoutBriefGenerator(build_path_with_data)
        generator.generate()

        summary = generator.get_summary()

        assert summary["total_scenes"] == 2
        assert summary["total_characters"] == 3  # 2 in scene 1, 1 in scene 2
        assert summary["total_cameras"] == 3  # 2 in scene 1, 1 in scene 2

    def test_get_summary_before_generate(self):
        """Test get_summary before generate returns zeros."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LayoutBriefGenerator(Path(tmpdir))

            summary = generator.get_summary()

            assert summary["total_scenes"] == 0
            assert summary["total_characters"] == 0

    def test_get_layout_brief_after_generate(self, build_path_with_data):
        """Test get_layout_brief returns brief after generate."""
        generator = LayoutBriefGenerator(build_path_with_data)
        generator.generate()

        brief = generator.get_layout_brief()

        assert isinstance(brief, LayoutBrief)
        assert len(brief.scene_layouts) == 2

    def test_get_layout_brief_before_generate_raises(self):
        """Test get_layout_brief before generate raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LayoutBriefGenerator(Path(tmpdir))

            with pytest.raises(ValueError, match="Call generate\\(\\) first"):
                generator.get_layout_brief()

    def test_character_names_formatted(self, build_path_with_data):
        """Test character names formatted from IDs."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        names = [c.name for c in scene.characters]

        assert "John" in names
        assert "Jane" in names

    def test_camera_target_set(self, build_path_with_data):
        """Test camera target is set."""
        generator = LayoutBriefGenerator(build_path_with_data)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        for cam in scene.camera_setups:
            assert "x" in cam.target
            assert "y" in cam.target
            assert "z" in cam.target


class TestGenerateLayoutBriefFunction:
    """Tests for generate_layout_brief convenience function."""

    def test_success(self, build_path_with_data):
        """Test successful generation."""
        result = generate_layout_brief(build_path_with_data)

        assert result.success is True
        assert result.scenes_processed == 2
        assert result.layouts_generated == 2
        assert result.errors == []

    def test_failure_missing_scriptgraph(self):
        """Test failure with missing scriptgraph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_layout_brief(Path(tmpdir))

            assert result.success is False
            assert len(result.errors) == 1
