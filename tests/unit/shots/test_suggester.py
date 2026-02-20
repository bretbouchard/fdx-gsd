"""Unit tests for ShotSuggester orchestrator."""
import json
import tempfile
from pathlib import Path

import pytest

from core.shots.types import ShotType
from core.shots.suggester import ShotSuggester, ShotSuggestionResult, suggest_shots


class TestShotSuggester:
    """Tests for ShotSuggester class."""

    @pytest.fixture
    def sample_scriptgraph(self):
        """Create a sample scriptgraph for testing."""
        return {
            "version": "1.0",
            "project_id": "test-movie",
            "scenes": [
                {
                    "id": "scene_001",
                    "order": 1,
                    "slugline": "INT. OFFICE - DAY",
                    "paragraphs": [
                        {"type": "action", "text": "John walks into the office.", "evidence_ids": ["ev_001"]},
                        {"type": "character", "text": "JOHN", "evidence_ids": ["ev_002"], "meta": {"character": "JOHN"}},
                        {"type": "dialogue", "text": "I love this place!", "evidence_ids": ["ev_003"], "meta": {"character": "JOHN"}},
                    ],
                    "links": {"characters": ["JOHN"]},
                },
                {
                    "id": "scene_002",
                    "order": 2,
                    "slugline": "EXT. STREET - NIGHT",
                    "paragraphs": [
                        {"type": "action", "text": "Mary runs down the street.", "evidence_ids": ["ev_004"]},
                    ],
                    "links": {"characters": ["MARY"]},
                },
            ],
        }

    @pytest.fixture
    def build_path_with_scriptgraph(self, sample_scriptgraph):
        """Create a temp build directory with scriptgraph.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir) / "build"
            build_path.mkdir()
            (build_path / "scriptgraph.json").write_text(json.dumps(sample_scriptgraph))
            yield build_path

    def test_suggester_initialization(self, build_path_with_scriptgraph):
        """ShotSuggester creates with build_path."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        assert suggester is not None
        assert suggester.build_path == build_path_with_scriptgraph

    def test_suggester_loads_scriptgraph(self, build_path_with_scriptgraph):
        """_load_scriptgraph loads valid JSON."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester._load_scriptgraph()

        assert suggester._scriptgraph is not None
        assert suggester._project_id == "test-movie"

    def test_suggester_no_scriptgraph(self):
        """Returns error when no scriptgraph.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir) / "build"
            build_path.mkdir()

            suggester = ShotSuggester(build_path)
            result = suggester.suggest()

            assert result.success is False
            assert "No scriptgraph.json found" in result.errors

    def test_suggester_empty_scenes(self):
        """Handles empty scenes list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir) / "build"
            build_path.mkdir()
            (build_path / "scriptgraph.json").write_text(json.dumps({
                "version": "1.0",
                "project_id": "test",
                "scenes": [],
            }))

            suggester = ShotSuggester(build_path)
            result = suggester.suggest()

            assert result.success is False
            assert "No scenes found in scriptgraph" in result.errors

    def test_create_shot_id(self, build_path_with_scriptgraph):
        """Shot IDs follow correct format (shot_XXX_YYY)."""
        suggester = ShotSuggester(build_path_with_scriptgraph)

        id1 = suggester._create_shot_id(1)
        id2 = suggester._create_shot_id(1)
        id3 = suggester._create_shot_id(2)

        assert id1 == "shot_001_001"
        assert id2 == "shot_001_002"
        assert id3 == "shot_002_003"

    def test_suggest_processes_all_scenes(self, build_path_with_scriptgraph):
        """suggest() processes all scenes in scriptgraph."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        result = suggester.suggest()

        assert result.success is True
        assert result.scenes_processed == 2

    def test_suggest_returns_result(self, build_path_with_scriptgraph):
        """suggest() returns ShotSuggestionResult."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        result = suggester.suggest()

        assert isinstance(result, ShotSuggestionResult)
        assert result.success is True

    def test_get_shots_sorted(self, build_path_with_scriptgraph):
        """get_shots returns shots sorted by scene/shot number."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester.suggest()
        shots = suggester.get_shots()

        # Should be sorted by scene_number, then shot_number
        for i in range(len(shots) - 1):
            curr = shots[i]
            next_shot = shots[i + 1]
            assert (curr.scene_number, curr.shot_number) <= (next_shot.scene_number, next_shot.shot_number)

    def test_get_shot_list(self, build_path_with_scriptgraph):
        """get_shot_list returns valid ShotList."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester.suggest()
        shot_list = suggester.get_shot_list()

        assert shot_list.project_id == "test-movie"
        assert len(shot_list.shots) > 0

    def test_get_summary(self, build_path_with_scriptgraph):
        """get_summary returns correct statistics."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester.suggest()
        summary = suggester.get_summary()

        assert "total_shots" in summary
        assert "by_shot_type" in summary
        assert "by_scene" in summary
        assert summary["total_shots"] > 0

    def test_establishing_shot_always_first(self, build_path_with_scriptgraph):
        """Every scene starts with WS."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester.suggest()
        shots = suggester.get_shots()

        # Group by scene
        scenes = {}
        for shot in shots:
            if shot.scene_number not in scenes:
                scenes[shot.scene_number] = []
            scenes[shot.scene_number].append(shot)

        # Each scene's first shot should be WS
        for scene_num, scene_shots in scenes.items():
            first_shot = min(scene_shots, key=lambda s: s.shot_number)
            assert first_shot.shot_type == ShotType.WS, f"Scene {scene_num} doesn't start with WS"

    def test_scene_with_movement_generates_shots(self, build_path_with_scriptgraph):
        """Action scene generates MS shots for movement."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester.suggest()
        shots = suggester.get_shots()

        # Should have at least one MS for "walks" or "runs"
        ms_shots = [s for s in shots if s.shot_type == ShotType.MS]
        assert len(ms_shots) >= 1

    def test_scene_with_emotional_dialogue_generates_shots(self, build_path_with_scriptgraph):
        """Dialogue scene generates CU shots for emotional content."""
        suggester = ShotSuggester(build_path_with_scriptgraph)
        suggester.suggest()
        shots = suggester.get_shots()

        # "I love this place!" should trigger a CU
        cu_shots = [s for s in shots if s.shot_type == ShotType.CU]
        assert len(cu_shots) >= 1

    def test_suggest_shots_convenience_function(self, build_path_with_scriptgraph):
        """Convenience function works correctly."""
        result = suggest_shots(build_path_with_scriptgraph)

        assert isinstance(result, ShotSuggestionResult)
        assert result.success is True


class TestTwoCharacterScene:
    """Tests for two-character dialogue shot suggestions."""

    @pytest.fixture
    def two_char_scriptgraph(self):
        """Create scriptgraph with two-character scene."""
        return {
            "version": "1.0",
            "project_id": "test-movie",
            "scenes": [
                {
                    "id": "scene_001",
                    "order": 1,
                    "slugline": "INT. OFFICE - DAY",
                    "paragraphs": [
                        {"type": "character", "text": "JOHN", "meta": {"character": "JOHN"}},
                        {"type": "dialogue", "text": "Hello Mary.", "meta": {"character": "JOHN"}},
                        {"type": "character", "text": "MARY", "meta": {"character": "MARY"}},
                        {"type": "dialogue", "text": "Hello John.", "meta": {"character": "MARY"}},
                    ],
                    "links": {"characters": ["JOHN", "MARY"]},
                },
            ],
        }

    def test_two_character_scene_generates_ots(self, two_char_scriptgraph):
        """Scene with 2 characters gets OTS suggestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_path = Path(tmpdir) / "build"
            build_path.mkdir()
            (build_path / "scriptgraph.json").write_text(json.dumps(two_char_scriptgraph))

            suggester = ShotSuggester(build_path)
            suggester.suggest()
            shots = suggester.get_shots()

            # Should have OTS for two-character dialogue
            ots_shots = [s for s in shots if s.shot_type == ShotType.OTS]
            assert len(ots_shots) >= 1
