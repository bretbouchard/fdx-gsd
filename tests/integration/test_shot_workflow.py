"""End-to-end integration tests for shot suggestion workflow.

Tests the complete workflow:
1. Create test project with scriptgraph.json
2. Run ShotSuggester.suggest()
3. Verify ShotSuggestionResult is successful
4. Get ShotList and verify shots exist
5. Export to CSV
6. Verify CSV file exists and has correct content
7. Export to JSON (shotgraph.json)
8. Verify JSON file exists and is valid
"""
import csv
import json
import tempfile
from pathlib import Path

import pytest

from core.shots import ShotSuggester, ShotListExporter, ShotType


class TestFullShotWorkflow:
    """End-to-end shot workflow tests."""

    @pytest.fixture
    def test_project(self):
        """Create a test project with scriptgraph.json."""
        scriptgraph = {
            "version": "1.0",
            "project_id": "test-movie",
            "scenes": [
                {
                    "id": "scene_001",
                    "order": 1,
                    "slugline": "INT. OFFICE - DAY",
                    "paragraphs": [
                        {"type": "action", "text": "John walks into the office and approaches the desk.", "evidence_ids": ["ev_001"]},
                        {"type": "character", "text": "JOHN", "evidence_ids": ["ev_002"], "meta": {"character": "JOHN"}},
                        {"type": "dialogue", "text": "I love this place! It makes me want to cry with joy.", "evidence_ids": ["ev_003"], "meta": {"character": "JOHN"}},
                        {"type": "action", "text": "He picks up a letter from the desk.", "evidence_ids": ["ev_004"]},
                        {"type": "character", "text": "MARY", "evidence_ids": ["ev_005"], "meta": {"character": "MARY"}},
                        {"type": "dialogue", "text": "That letter is for me.", "evidence_ids": ["ev_006"], "meta": {"character": "MARY"}},
                    ],
                    "links": {"characters": ["JOHN", "MARY"], "locations": ["OFFICE"]},
                },
                {
                    "id": "scene_002",
                    "order": 2,
                    "slugline": "EXT. STREET - NIGHT",
                    "paragraphs": [
                        {"type": "action", "text": "Mary runs down the street, fleeing from something.", "evidence_ids": ["ev_007"]},
                        {"type": "action", "text": "She sees a phone booth ahead.", "evidence_ids": ["ev_008"]},
                    ],
                    "links": {"characters": ["MARY"], "locations": ["STREET"]},
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create build directory with scriptgraph
            build_path = project_path / "build"
            build_path.mkdir()
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            # Create exports directory
            exports_path = project_path / "exports"
            exports_path.mkdir()

            yield {
                "project_path": project_path,
                "build_path": build_path,
                "exports_path": exports_path,
                "scriptgraph": scriptgraph,
            }

    def test_full_shot_workflow(self, test_project):
        """Complete shot suggestion workflow."""
        build_path = test_project["build_path"]
        exports_path = test_project["exports_path"]

        # 1. Run ShotSuggester.suggest()
        suggester = ShotSuggester(build_path)
        result = suggester.suggest()

        # 2. Verify ShotSuggestionResult is successful
        assert result.success is True
        assert result.scenes_processed == 2
        assert result.shots_suggested > 0

        # 3. Get ShotList and verify shots exist
        shot_list = suggester.get_shot_list()
        assert shot_list.project_id == "test-movie"
        assert len(shot_list.shots) >= 4  # At least 2 establishing + some detected shots

        # 4. Export to CSV
        exporter = ShotListExporter()
        csv_path = exports_path / "shotlist.csv"
        exporter.export_csv(shot_list, csv_path)

        # 5. Verify CSV file exists and has correct content
        assert csv_path.exists()
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) >= 4
        # Check headers are correct
        assert "scene_number" in rows[0]
        assert "shot_size" in rows[0]
        assert "description" in rows[0]

        # 6. Export to JSON (shotgraph.json)
        json_path = build_path / "shotgraph.json"
        shot_list.save(json_path)

        # 7. Verify JSON file exists and is valid
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["project_id"] == "test-movie"
        assert data["total_shots"] >= 4
        assert len(data["shots"]) >= 4

    def test_shot_workflow_with_emotional_scene(self, test_project):
        """Scriptgraph with emotional dialogue scene generates CU shots."""
        build_path = test_project["build_path"]

        suggester = ShotSuggester(build_path)
        suggester.suggest()
        shots = suggester.get_shots()

        # Scene 1 has emotional dialogue ("I love this place!", "cry with joy")
        # Should generate at least one CU shot
        cu_shots = [s for s in shots if s.shot_type == ShotType.CU]
        assert len(cu_shots) >= 1

        # Verify the CU shot has correct scene
        cu_shot = cu_shots[0]
        assert cu_shot.scene_number == 1

    def test_shot_workflow_with_action_scene(self, test_project):
        """Scriptgraph with action scene generates MS shots."""
        build_path = test_project["build_path"]

        suggester = ShotSuggester(build_path)
        suggester.suggest()
        shots = suggester.get_shots()

        # Scene 1 has "walks", Scene 2 has "runs", "fleeing"
        # Should generate MS shots for movement
        ms_shots = [s for s in shots if s.shot_type == ShotType.MS]
        assert len(ms_shots) >= 2  # At least one per scene

    def test_shot_workflow_with_detail_insert(self, test_project):
        """Scriptgraph with detail mentions generates INSERT shots."""
        build_path = test_project["build_path"]

        suggester = ShotSuggester(build_path)
        suggester.suggest()
        shots = suggester.get_shots()

        # Scene 1 has "letter", Scene 2 has "phone"
        # Should generate INSERT shots
        insert_shots = [s for s in shots if s.shot_type == ShotType.INSERT]
        assert len(insert_shots) >= 1

    def test_deterministic_rebuild(self, test_project):
        """Running suggester twice on same scriptgraph produces identical results."""
        build_path = test_project["build_path"]

        # First run
        suggester1 = ShotSuggester(build_path)
        suggester1.suggest()
        shots1 = suggester1.get_shots()
        ids1 = [s.shot_id for s in shots1]

        # Second run
        suggester2 = ShotSuggester(build_path)
        suggester2.suggest()
        shots2 = suggester2.get_shots()
        ids2 = [s.shot_id for s in shots2]

        # IDs should be different because counter is reset
        # But shot types and descriptions should match
        assert len(shots1) == len(shots2)

        for s1, s2 in zip(shots1, shots2):
            assert s1.shot_type == s2.shot_type
            assert s1.scene_number == s2.scene_number
            assert s1.shot_number == s2.shot_number
            assert s1.description == s2.description

    def test_export_to_csv_and_json_produce_consistent_data(self, test_project):
        """CSV and JSON exports contain the same shots."""
        build_path = test_project["build_path"]
        exports_path = test_project["exports_path"]

        suggester = ShotSuggester(build_path)
        suggester.suggest()
        shot_list = suggester.get_shot_list()

        # Export both formats
        exporter = ShotListExporter()
        csv_path = exports_path / "shotlist.csv"
        json_path = build_path / "shotgraph.json"

        exporter.export_csv(shot_list, csv_path)
        shot_list.save(json_path)

        # Read CSV
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)

        # Read JSON
        json_data = json.loads(json_path.read_text())
        json_shots = json_data["shots"]

        # Same count
        assert len(csv_rows) == len(json_shots)

        # Same shot types in order
        for csv_row, json_shot in zip(csv_rows, json_shots):
            assert csv_row["shot_size"] == json_shot["shot_type"]
            assert int(csv_row["scene_number"]) == json_shot["scene_number"]
            assert int(csv_row["shot_number"]) == json_shot["shot_number"]

    def test_shot_list_summary_accurate(self, test_project):
        """Shot list summary reflects actual shot counts."""
        build_path = test_project["build_path"]

        suggester = ShotSuggester(build_path)
        suggester.suggest()
        shot_list = suggester.get_shot_list()
        summary = shot_list.get_summary()

        # Count manually
        total = len(shot_list.shots)
        by_type = {}
        by_scene = {}

        for shot in shot_list.shots:
            type_key = shot.shot_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            by_scene[shot.scene_number] = by_scene.get(shot.scene_number, 0) + 1

        assert summary["total_shots"] == total
        assert summary["by_shot_type"] == by_type
        assert summary["by_scene"] == by_scene
        assert summary["unique_scenes"] == len(by_scene)


class TestEdgeCases:
    """Edge case tests for shot workflow."""

    def test_empty_paragraphs(self):
        """Scene with no paragraphs still gets establishing shot."""
        scriptgraph = {
            "version": "1.0",
            "project_id": "test",
            "scenes": [
                {
                    "id": "scene_001",
                    "order": 1,
                    "slugline": "INT. EMPTY ROOM - DAY",
                    "paragraphs": [],
                    "links": {"characters": []},
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir) / "build"
            build_path.mkdir()
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            suggester = ShotSuggester(build_path)
            result = suggester.suggest()

            assert result.success is True
            shots = suggester.get_shots()

            # Should have at least the establishing shot
            assert len(shots) == 1
            assert shots[0].shot_type == ShotType.WS

    def test_many_scenes(self):
        """Handles many scenes efficiently."""
        scenes = []
        for i in range(1, 51):  # 50 scenes
            scenes.append({
                "id": f"scene_{i:03d}",
                "order": i,
                "slugline": f"INT. LOCATION {i} - DAY",
                "paragraphs": [
                    {"type": "action", "text": f"Character walks in scene {i}.", "evidence_ids": [f"ev_{i}"]},
                ],
                "links": {"characters": ["CHARACTER"]},
            })

        scriptgraph = {
            "version": "1.0",
            "project_id": "test",
            "scenes": scenes,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir) / "build"
            build_path.mkdir()
            (build_path / "scriptgraph.json").write_text(json.dumps(scriptgraph))

            suggester = ShotSuggester(build_path)
            result = suggester.suggest()

            assert result.success is True
            assert result.scenes_processed == 50

            # Each scene should have at least establishing shot + movement shot
            shots = suggester.get_shots()
            assert len(shots) >= 100  # 50 scenes * 2 shots minimum
