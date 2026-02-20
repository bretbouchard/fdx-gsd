"""Unit tests for ShotDetector heuristics."""
import pytest

from core.shots.detector import ShotDetector
from core.shots.types import ShotType


class TestShotDetector:
    """Tests for ShotDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a ShotDetector instance."""
        return ShotDetector()

    @pytest.fixture
    def sample_scene(self):
        """Create a sample scene dict."""
        return {
            "id": "scene_001",
            "order": 1,
            "slugline": "INT. OFFICE - DAY",
        }

    def test_detector_initialization(self, detector):
        """ShotDetector creates with keyword sets."""
        assert detector is not None
        assert len(detector.EMOTIONAL_KEYWORDS) > 0
        assert len(detector.MOVEMENT_VERBS) > 0
        assert len(detector.DETAIL_INDICATORS) > 0
        assert len(detector.POV_INDICATORS) > 0

    def test_detect_emotional_dialogue_cry(self, detector, sample_scene):
        """Dialogue with 'cry' returns CU shot."""
        paragraph = {
            "type": "dialogue",
            "text": "I can't stop crying about this!",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.CU
        assert "cry" in shot.description.lower()

    def test_detect_emotional_dialogue_whisper(self, detector, sample_scene):
        """Dialogue with 'whisper' returns CU shot."""
        paragraph = {
            "type": "dialogue",
            "text": "She whispered the secret.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.CU

    def test_detect_emotional_dialogue_smile(self, detector, sample_scene):
        """Dialogue with 'smile' returns CU shot."""
        paragraph = {
            "type": "dialogue",
            "text": "She smiled at the memory.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.CU

    def test_detect_movement_walks(self, detector, sample_scene):
        """Action with 'walks' returns MS shot."""
        paragraph = {
            "type": "action",
            "text": "John walks across the room.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.MS
        assert "walks" in shot.description.lower()

    def test_detect_movement_enters(self, detector, sample_scene):
        """Action with 'enters' returns MS shot."""
        paragraph = {
            "type": "action",
            "text": "She enters the room.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.MS

    def test_detect_movement_runs(self, detector, sample_scene):
        """Action with 'runs' returns MS shot."""
        paragraph = {
            "type": "action",
            "text": "He runs toward the exit.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.MS

    def test_detect_detail_insert_ring(self, detector, sample_scene):
        """Action with 'ring' returns INSERT shot."""
        paragraph = {
            "type": "action",
            "text": "She looks at the ring on her finger.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.INSERT
        assert "Ring" in shot.description

    def test_detect_detail_insert_letter(self, detector, sample_scene):
        """Action with 'letter' returns INSERT shot."""
        paragraph = {
            "type": "action",
            "text": "He picks up the letter from the desk.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.shot_type == ShotType.INSERT

    def test_detect_pov_sees(self, detector, sample_scene):
        """Text with 'sees' returns POV shot."""
        paragraph = {
            "type": "action",
            "text": "She sees the car approaching.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        # POV has lower priority, might not trigger if nothing else matches
        # but should work with POV-specific text
        assert shot is not None
        assert shot.shot_type == ShotType.POV

    def test_detect_no_match(self, detector, sample_scene):
        """Regular text returns None."""
        paragraph = {
            "type": "action",
            "text": "The room is quiet.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        # No keywords match, should return None
        assert shot is None

    def test_evidence_propagation(self, detector, sample_scene):
        """Detected shot includes evidence_ids from paragraph."""
        paragraph = {
            "type": "dialogue",
            "text": "I love you!",
            "evidence_ids": ["ev_001", "ev_002", "ev_003"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.evidence_ids == ["ev_001", "ev_002", "ev_003"]

    def test_character_extraction(self, detector, sample_scene):
        """Dialogue paragraph extracts character name."""
        paragraph = {
            "type": "dialogue",
            "text": "I love you!",
            "evidence_ids": ["ev_001"],
            "meta": {"character": "MARY"},
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        assert shot is not None
        assert shot.subject == "MARY"

    def test_should_add_two_shot_two_characters(self, detector):
        """Two-character scene should add two-shot."""
        result = detector.should_add_two_shot(["JOHN", "MARY"])
        assert result is True

    def test_should_add_two_shot_one_character(self, detector):
        """Single character scene should not add two-shot."""
        result = detector.should_add_two_shot(["JOHN"])
        assert result is False

    def test_should_add_two_shot_three_characters(self, detector):
        """Three character scene should not add two-shot."""
        result = detector.should_add_two_shot(["JOHN", "MARY", "BOB"])
        assert result is False

    def test_detect_movement_priority_over_detail(self, detector, sample_scene):
        """Movement should be detected before detail."""
        paragraph = {
            "type": "action",
            "text": "He walks to the desk and picks up the letter.",
            "evidence_ids": ["ev_001"],
        }

        shot = detector.detect_from_paragraph(paragraph, sample_scene, shot_order=1)

        # Movement has higher priority than detail
        assert shot is not None
        assert shot.shot_type == ShotType.MS
