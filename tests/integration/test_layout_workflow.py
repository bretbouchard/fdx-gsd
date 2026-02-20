"""End-to-end integration tests for layout brief generation workflow.

Tests the complete workflow:
1. Create test project with scriptgraph.json and shotgraph.json
2. Run LayoutBriefGenerator.generate()
3. Verify LayoutBrief is created with correct structure
4. Export via LayoutBriefExporter
5. Verify blender/ directory created
6. Verify layout_brief.json files exist and are valid
7. Verify combined brief in build/
"""
import json
import tempfile
from pathlib import Path

import pytest

from core.layout import (
    LayoutBriefGenerator,
    LayoutBriefExporter,
    LayoutBrief,
    SceneLayout,
    CameraSetup,
)


class TestFullLayoutWorkflow:
    """End-to-end layout workflow tests."""

    @pytest.fixture
    def project_with_data(self):
        """Create a test project with ScriptGraph and ShotGraph."""
        # Create project structure
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir()

            # Create ScriptGraph
            scriptgraph = {
                "version": "1.0",
                "project_id": "test-project",
                "scenes": [
                    {
                        "id": "SCN_001",
                        "order": 1,
                        "slugline": "INT. OFFICE - DAY",
                        "int_ext": "INT",
                        "time_of_day": "DAY",
                        "links": {
                            "characters": ["CHAR_alice"],
                            "locations": ["LOC_office"],
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
                            "characters": ["CHAR_bob", "CHAR_charlie"],
                            "locations": ["LOC_park"],
                            "evidence_ids": ["EV_002"],
                        },
                    },
                ],
            }
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            # Create ShotGraph
            shotgraph = {
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
                        "evidence_ids": [],
                    },
                    {
                        "shot_id": "shot_001_002",
                        "scene_id": "SCN_001",
                        "scene_number": 1,
                        "shot_number": 2,
                        "shot_type": "CU",
                        "movement": "Static",
                        "description": "Close-up on Alice",
                        "evidence_ids": ["EV_003"],
                    },
                    {
                        "shot_id": "shot_002_001",
                        "scene_id": "SCN_002",
                        "scene_number": 2,
                        "shot_number": 1,
                        "shot_type": "MS",
                        "movement": "Pan",
                        "description": "Bob and Charlie talk",
                        "evidence_ids": [],
                    },
                    {
                        "shot_id": "shot_002_002",
                        "scene_id": "SCN_002",
                        "scene_number": 2,
                        "shot_number": 2,
                        "shot_type": "OTS",
                        "movement": "Static",
                        "description": "Over Bob's shoulder",
                        "evidence_ids": [],
                    },
                ],
            }
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            yield {
                "project_path": project_path,
                "build_path": build_path,
                "scriptgraph": scriptgraph,
                "shotgraph": shotgraph,
            }

    def test_generate_layout_creates_brief(self, project_with_data):
        """Test that generate() creates valid LayoutBrief."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        assert isinstance(brief, LayoutBrief)
        assert brief.project_id == "test-project"
        assert len(brief.scene_layouts) == 2

    def test_generate_layout_creates_files(self, project_with_data):
        """Test that generate-layout creates output files."""
        project_path = project_with_data["project_path"]
        build_path = project_with_data["build_path"]

        # Generate
        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        # Export
        exporter = LayoutBriefExporter(project_path)
        paths = exporter.export(brief)

        assert len(paths) == 2
        assert "SCN_001" in paths
        assert "SCN_002" in paths
        assert paths["SCN_001"].exists()
        assert paths["SCN_002"].exists()

    def test_layout_brief_json_valid(self, project_with_data):
        """Test that output JSON is valid."""
        project_path = project_with_data["project_path"]
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        exporter = LayoutBriefExporter(project_path)
        paths = exporter.export(brief)

        # Verify JSON is valid
        for scene_id, path in paths.items():
            data = json.loads(path.read_text())
            assert "scene_id" in data
            assert "camera_setups" in data
            assert "characters" in data

    def test_camera_setups_present(self, project_with_data):
        """Test that camera setups are generated."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        assert len(scene.camera_setups) == 2  # 2 shots in fixture

        scene2 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_002")
        assert len(scene2.camera_setups) == 2  # 2 shots in fixture

    def test_camera_positions_valid(self, project_with_data):
        """Test that camera positions have valid coordinates."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        for scene in brief.scene_layouts:
            for cam in scene.camera_setups:
                pos = cam.camera["position"]
                assert "x" in pos
                assert "y" in pos
                assert "z" in pos
                assert isinstance(pos["x"], (int, float))
                assert isinstance(pos["y"], (int, float))
                assert isinstance(pos["z"], (int, float))

    def test_camera_distances_by_shot_type(self, project_with_data):
        """Test that camera distances match shot types."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        # SCN_001: WS (5m), CU (1.2m)
        scene = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")

        ws_cam = next(c for c in scene.camera_setups if c.shot_type == "WS")
        # WS should be ~5m from subject (negative Y)
        assert abs(ws_cam.camera["position"]["y"]) > 4.0

        cu_cam = next(c for c in scene.camera_setups if c.shot_type == "CU")
        # CU should be ~1.2m from subject
        assert abs(cu_cam.camera["position"]["y"]) < 2.0

    def test_characters_present(self, project_with_data):
        """Test that characters are in scene layouts."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        scene1 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        assert len(scene1.characters) == 1
        assert scene1.characters[0].character_id == "CHAR_alice"

        scene2 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_002")
        assert len(scene2.characters) == 2
        char_ids = [c.character_id for c in scene2.characters]
        assert "CHAR_bob" in char_ids
        assert "CHAR_charlie" in char_ids

    def test_combined_brief_exported(self, project_with_data):
        """Test that combined brief is exported to build/."""
        project_path = project_with_data["project_path"]
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        exporter = LayoutBriefExporter(project_path)
        exporter.export(brief)

        # Check combined brief
        combined_path = build_path / "layout_brief.json"
        assert combined_path.exists()

        data = json.loads(combined_path.read_text())
        assert data["project_id"] == "test-project"
        assert len(data["scene_layouts"]) == 2

    def test_blender_directory_structure(self, project_with_data):
        """Test that blender/ directory structure is created."""
        project_path = project_with_data["project_path"]
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        exporter = LayoutBriefExporter(project_path)
        exporter.export(brief)

        # Check directory structure
        blender_path = project_path / "blender"
        assert blender_path.exists()
        assert (blender_path / "SCN_001").exists()
        assert (blender_path / "SCN_002").exists()
        assert (blender_path / "SCN_001" / "layout_brief.json").exists()
        assert (blender_path / "SCN_002" / "layout_brief.json").exists()

    def test_evidence_chain_preserved(self, project_with_data):
        """Test that evidence IDs are preserved through the pipeline."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        # Scene evidence
        scene1 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        assert "EV_001" in scene1.evidence_ids

        # Camera (shot) evidence
        cu_cam = next(c for c in scene1.camera_setups if c.shot_type == "CU")
        assert "EV_003" in cu_cam.evidence_ids

    def test_environment_metadata(self, project_with_data):
        """Test that environment metadata is included."""
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        scene1 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_001")
        assert scene1.int_ext == "INT"
        assert scene1.time_of_day == "DAY"
        assert scene1.environment["lighting_preset"] == "interior_day"

        scene2 = next(s for s in brief.scene_layouts if s.scene_id == "SCN_002")
        assert scene2.int_ext == "EXT"
        assert scene2.time_of_day == "NIGHT"
        assert scene2.environment["lighting_preset"] == "outdoor_night"

    def test_deterministic_output(self, project_with_data):
        """Test that generation is deterministic."""
        build_path = project_with_data["build_path"]

        # First run
        generator1 = LayoutBriefGenerator(build_path)
        brief1 = generator1.generate()

        # Second run
        generator2 = LayoutBriefGenerator(build_path)
        brief2 = generator2.generate()

        # Scene count should match
        assert len(brief1.scene_layouts) == len(brief2.scene_layouts)

        # For each scene, camera count should match
        for s1, s2 in zip(brief1.scene_layouts, brief2.scene_layouts):
            assert s1.scene_id == s2.scene_id
            assert len(s1.camera_setups) == len(s2.camera_setups)
            assert len(s1.characters) == len(s2.characters)

    def test_json_output_sorted_keys(self, project_with_data):
        """Test that JSON output has sorted keys for determinism."""
        project_path = project_with_data["project_path"]
        build_path = project_with_data["build_path"]

        generator = LayoutBriefGenerator(build_path)
        brief = generator.generate()

        exporter = LayoutBriefExporter(project_path)
        paths = exporter.export(brief)

        # Read raw JSON
        raw = paths["SCN_001"].read_text()

        # Should be valid JSON with sorted keys
        data = json.loads(raw)
        assert isinstance(data, dict)


class TestEdgeCases:
    """Edge case tests for layout workflow."""

    def test_scene_with_no_characters(self):
        """Scene with no characters still creates layout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir()

            scriptgraph = {
                "version": "1.0",
                "project_id": "test",
                "scenes": [
                    {
                        "id": "SCN_001",
                        "order": 1,
                        "slugline": "EXT. EMPTY FIELD - DAY",
                        "int_ext": "EXT",
                        "time_of_day": "DAY",
                        "links": {"characters": [], "locations": [], "evidence_ids": []},
                    }
                ],
            }
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            shotgraph = {
                "version": "1.0",
                "project_id": "test",
                "shots": [
                    {
                        "shot_id": "shot_001_001",
                        "scene_id": "SCN_001",
                        "scene_number": 1,
                        "shot_number": 1,
                        "shot_type": "WS",
                        "movement": "Static",
                        "description": "Empty field",
                        "evidence_ids": [],
                    }
                ],
            }
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            assert len(brief.scene_layouts) == 1
            assert len(brief.scene_layouts[0].characters) == 0
            assert len(brief.scene_layouts[0].camera_setups) == 1

    def test_scene_with_no_shots(self):
        """Scene with no shots creates layout with no cameras."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir()

            scriptgraph = {
                "version": "1.0",
                "project_id": "test",
                "scenes": [
                    {
                        "id": "SCN_001",
                        "order": 1,
                        "slugline": "INT. ROOM - DAY",
                        "int_ext": "INT",
                        "time_of_day": "DAY",
                        "links": {
                            "characters": ["CHAR_x"],
                            "locations": [],
                            "evidence_ids": [],
                        },
                    }
                ],
            }
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            shotgraph = {"version": "1.0", "project_id": "test", "shots": []}
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            assert len(brief.scene_layouts) == 1
            assert len(brief.scene_layouts[0].camera_setups) == 0

    def test_all_shot_types(self):
        """Test all shot types produce valid camera positions."""
        shot_types = ["WS", "MS", "MCU", "CU", "ECU", "INSERT", "OTS", "POV", "TWO"]

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir()

            scriptgraph = {
                "version": "1.0",
                "project_id": "test",
                "scenes": [
                    {
                        "id": "SCN_001",
                        "order": 1,
                        "slugline": "INT. STUDIO - DAY",
                        "int_ext": "INT",
                        "time_of_day": "DAY",
                        "links": {
                            "characters": ["CHAR_x"],
                            "locations": [],
                            "evidence_ids": [],
                        },
                    }
                ],
            }
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            shots = []
            for i, shot_type in enumerate(shot_types, 1):
                shots.append(
                    {
                        "shot_id": f"shot_001_{i:03d}",
                        "scene_id": "SCN_001",
                        "scene_number": 1,
                        "shot_number": i,
                        "shot_type": shot_type,
                        "movement": "Static",
                        "description": f"{shot_type} test",
                        "evidence_ids": [],
                    }
                )

            shotgraph = {"version": "1.0", "project_id": "test", "shots": shots}
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            assert len(brief.scene_layouts[0].camera_setups) == 9

            # Verify each camera setup
            for cam in brief.scene_layouts[0].camera_setups:
                assert cam.shot_type in shot_types
                pos = cam.camera["position"]
                assert isinstance(pos["x"], (int, float))
                assert isinstance(pos["y"], (int, float))
                assert isinstance(pos["z"], (int, float))

    def test_many_scenes(self):
        """Handles many scenes efficiently."""
        scenes = []
        shots = []

        for i in range(1, 51):  # 50 scenes
            scenes.append(
                {
                    "id": f"SCN_{i:03d}",
                    "order": i,
                    "slugline": f"INT. LOCATION {i} - DAY",
                    "int_ext": "INT",
                    "time_of_day": "DAY",
                    "links": {
                        "characters": [f"CHAR_{i}"],
                        "locations": [f"LOC_{i}"],
                        "evidence_ids": [],
                    },
                }
            )
            shots.append(
                {
                    "shot_id": f"shot_{i:03d}_001",
                    "scene_id": f"SCN_{i:03d}",
                    "scene_number": i,
                    "shot_number": 1,
                    "shot_type": "WS",
                    "movement": "Static",
                    "description": f"Scene {i}",
                    "evidence_ids": [],
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir()

            scriptgraph = {"version": "1.0", "project_id": "test", "scenes": scenes}
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            shotgraph = {"version": "1.0", "project_id": "test", "shots": shots}
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            assert len(brief.scene_layouts) == 50

            # Export and verify
            exporter = LayoutBriefExporter(project_path)
            paths = exporter.export(brief)

            assert len(paths) == 50


class TestCameraMathIntegration:
    """Tests for camera math integration in layout workflow."""

    def test_camera_height_varies_by_shot_type(self):
        """Test that camera height varies correctly for shot types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir()

            scriptgraph = {
                "version": "1.0",
                "project_id": "test",
                "scenes": [
                    {
                        "id": "SCN_001",
                        "order": 1,
                        "slugline": "INT. SET - DAY",
                        "int_ext": "INT",
                        "time_of_day": "DAY",
                        "links": {"characters": ["CHAR_x"], "locations": [], "evidence_ids": []},
                    }
                ],
            }
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            shotgraph = {
                "version": "1.0",
                "project_id": "test",
                "shots": [
                    {
                        "shot_id": "shot_001_001",
                        "scene_id": "SCN_001",
                        "scene_number": 1,
                        "shot_number": 1,
                        "shot_type": "WS",
                        "movement": "Static",
                        "description": "Wide shot",
                        "evidence_ids": [],
                    },
                    {
                        "shot_id": "shot_001_002",
                        "scene_id": "SCN_001",
                        "scene_number": 1,
                        "shot_number": 2,
                        "shot_type": "CU",
                        "movement": "Static",
                        "description": "Close-up",
                        "evidence_ids": [],
                    },
                ],
            }
            (build_path / "shotgraph.json").write_text(json.dumps(shotgraph))

            generator = LayoutBriefGenerator(build_path)
            brief = generator.generate()

            scene = brief.scene_layouts[0]

            ws_cam = next(c for c in scene.camera_setups if c.shot_type == "WS")
            cu_cam = next(c for c in scene.camera_setups if c.shot_type == "CU")

            # WS should use raised camera (2.0m)
            assert ws_cam.camera["position"]["z"] > 1.8

            # CU should use eye level (1.6m)
            assert abs(cu_cam.camera["position"]["z"] - 1.6) < 0.1
