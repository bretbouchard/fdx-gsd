"""Shot detection heuristics for screenplay analysis.

Detects shot opportunities from paragraph content using rule-based
heuristics. Follows the BeatExtractor pattern from core/script/beats.py.
"""
import re
from typing import Any, Dict, List, Optional, Set

from .models import Shot
from .types import CameraAngle, CameraMovement, ShotType


class ShotDetector:
    """Detects shot opportunities from screenplay paragraphs.

    Uses rule-based heuristics to suggest appropriate camera shots
    based on dialogue emotion, action movement, and detail indicators.

    Detection Rules:
        - Emotional dialogue keywords -> Close-Up (CU)
        - Movement/action verbs -> Medium Shot (MS)
        - Detail/object indicators -> Insert (INSERT)
        - POV phrases -> Point of View (POV)
    """

    # Keywords indicating emotional dialogue (Close-Up opportunity)
    EMOTIONAL_KEYWORDS: Set[str] = {
        "cry", "tears", "sob", "scream", "whisper", "gasp",
        "shock", "horror", "love", "hate", "fear", "anger",
        "smile", "laugh", "grin", "frown", "tremble", "shake",
        "pale", "flush", "blush", "sobbing", "weeping",
        "terrified", "horrified", "ecstatic", "devastated",
        "angrily", "sadly", "happily", "softly", "quietly",
    }

    # Verbs indicating movement (Medium Shot opportunity)
    MOVEMENT_VERBS: Set[str] = {
        "walks", "runs", "enters", "exits", "moves", "crosses",
        "approaches", "retreats", "chases", "flees", "rushes",
        "sprints", "strolls", "wanders", "storms", "strides",
        "pacing", "darting", "charging", "lunging", "stumbling",
        "crawling", "climbing", "jumping", "leaping", "diving",
    }

    # Objects indicating detail insert shot
    DETAIL_INDICATORS: Set[str] = {
        "ring", "letter", "phone", "gun", "knife", "key",
        "photograph", "watch", "blood", "tear", "locket",
        "coin", "map", "book", "note", "card", "flower",
        "medal", "tattoo", "necklace", "bracelet", "diary",
        "newspaper", "ticket", "receipt", "signature",
    }

    # Phrases indicating POV shot
    POV_INDICATORS: Set[str] = {
        "sees", "watches", "looks at", "notices", "spots",
        "glimpses", "stares", "gazes", "observes", "peers",
        "glances", "eyes", "witnesses", "beholds",
    }

    def __init__(self) -> None:
        """Initialize the shot detector with keyword sets."""
        pass  # Keywords are class-level constants

    def detect_from_paragraph(
        self,
        paragraph: Dict[str, Any],
        scene: Dict[str, Any],
        shot_order: int = 1
    ) -> Optional[Shot]:
        """Analyze a paragraph and return a Shot if opportunity detected.

        Detection priority:
        1. Emotional dialogue -> CU (highest priority for dialogue)
        2. Movement action -> MS (highest priority for action)
        3. Detail insert -> INSERT (medium priority)
        4. POV opportunity -> POV (lower priority)

        Args:
            paragraph: Paragraph dict with 'type', 'text', 'evidence_ids'
            scene: Scene dict with 'id', 'order', 'slugline'
            shot_order: Order number for this shot within the scene

        Returns:
            Shot if opportunity detected, None otherwise
        """
        para_type = paragraph.get("type", "")
        text = paragraph.get("text", "").lower()
        evidence_ids = paragraph.get("evidence_ids", [])

        # Try detection in priority order
        if para_type == "dialogue":
            shot = self._detect_emotional_dialogue(paragraph, scene, shot_order)
            if shot:
                return shot
        elif para_type == "action":
            # Try movement first, then detail
            shot = self._detect_movement_action(paragraph, scene, shot_order)
            if shot:
                return shot
            shot = self._detect_detail_insert(paragraph, scene, shot_order)
            if shot:
                return shot

        # POV can apply to any paragraph type
        shot = self._detect_pov_opportunity(paragraph, scene, shot_order)
        if shot:
            return shot

        return None

    def _detect_emotional_dialogue(
        self,
        paragraph: Dict[str, Any],
        scene: Dict[str, Any],
        shot_order: int
    ) -> Optional[Shot]:
        """Check for emotional keywords in dialogue -> CU.

        Args:
            paragraph: Dialogue paragraph dict
            scene: Scene dict
            shot_order: Shot order number

        Returns:
            Shot with CU type if emotional content found
        """
        text = paragraph.get("text", "").lower()

        # Check for emotional keywords
        for keyword in self.EMOTIONAL_KEYWORDS:
            if keyword in text:
                # Extract character from previous character paragraph
                character = self._extract_character(paragraph)

                return Shot(
                    shot_id="",  # Will be set by suggester
                    scene_id=scene.get("id", ""),
                    scene_number=scene.get("order", 0),
                    shot_number=shot_order,
                    shot_type=ShotType.CU,
                    description=f"Close-up - Emotional moment ({keyword})",
                    subject=character,
                    characters=[character] if character else [],
                    evidence_ids=paragraph.get("evidence_ids", []),
                )

        return None

    def _detect_movement_action(
        self,
        paragraph: Dict[str, Any],
        scene: Dict[str, Any],
        shot_order: int
    ) -> Optional[Shot]:
        """Check for movement verbs in action -> MS.

        Args:
            paragraph: Action paragraph dict
            scene: Scene dict
            shot_order: Shot order number

        Returns:
            Shot with MS type if movement detected
        """
        text = paragraph.get("text", "").lower()

        # Check for movement verbs
        for verb in self.MOVEMENT_VERBS:
            if verb in text:
                return Shot(
                    shot_id="",  # Will be set by suggester
                    scene_id=scene.get("id", ""),
                    scene_number=scene.get("order", 0),
                    shot_number=shot_order,
                    shot_type=ShotType.MS,
                    description=f"Medium shot - Movement ({verb})",
                    evidence_ids=paragraph.get("evidence_ids", []),
                )

        return None

    def _detect_detail_insert(
        self,
        paragraph: Dict[str, Any],
        scene: Dict[str, Any],
        shot_order: int
    ) -> Optional[Shot]:
        """Check for detail indicators -> INSERT.

        Args:
            paragraph: Action paragraph dict
            scene: Scene dict
            shot_order: Shot order number

        Returns:
            Shot with INSERT type if detail object detected
        """
        text = paragraph.get("text", "").lower()

        # Check for detail indicators
        for indicator in self.DETAIL_INDICATORS:
            if indicator in text:
                detail = self._extract_detail(text, indicator)
                return Shot(
                    shot_id="",  # Will be set by suggester
                    scene_id=scene.get("id", ""),
                    scene_number=scene.get("order", 0),
                    shot_number=shot_order,
                    shot_type=ShotType.INSERT,
                    description=f"Insert - {detail}",
                    subject=detail,
                    evidence_ids=paragraph.get("evidence_ids", []),
                )

        return None

    def _detect_pov_opportunity(
        self,
        paragraph: Dict[str, Any],
        scene: Dict[str, Any],
        shot_order: int
    ) -> Optional[Shot]:
        """Check for POV phrases -> POV (lower priority).

        Args:
            paragraph: Paragraph dict
            scene: Scene dict
            shot_order: Shot order number

        Returns:
            Shot with POV type if POV indicator detected
        """
        text = paragraph.get("text", "").lower()

        # Check for POV indicators
        for indicator in self.POV_INDICATORS:
            if indicator in text:
                character = self._extract_character(paragraph)
                return Shot(
                    shot_id="",  # Will be set by suggester
                    scene_id=scene.get("id", ""),
                    scene_number=scene.get("order", 0),
                    shot_number=shot_order,
                    shot_type=ShotType.POV,
                    description=f"POV - Character perspective",
                    subject=character,
                    characters=[character] if character else [],
                    evidence_ids=paragraph.get("evidence_ids", []),
                )

        return None

    def _extract_character(self, paragraph: Dict[str, Any]) -> str:
        """Extract character name from paragraph metadata.

        Looks for character info in meta.character_id or meta.speaker.

        Args:
            paragraph: Paragraph dict with potential meta info

        Returns:
            Character name or empty string
        """
        meta = paragraph.get("meta", {})
        # Try various character fields
        if "character_id" in meta:
            return meta["character_id"]
        if "speaker" in meta:
            return meta["speaker"]
        if "character" in meta:
            return meta["character"]
        return ""

    def _extract_detail(self, text: str, indicator: str) -> str:
        """Extract the detail object from text.

        Returns the indicator capitalized as the detail name.

        Args:
            text: Full text
            indicator: The matched indicator

        Returns:
            Capitalized detail name
        """
        return indicator.capitalize()

    def should_add_two_shot(self, scene_characters: List[str]) -> bool:
        """Determine if a two-shot or OTS should be suggested.

        A two-shot is appropriate when exactly 2 characters are
        present in a scene with dialogue.

        Args:
            scene_characters: List of character IDs in scene

        Returns:
            True if two-shot recommended
        """
        return len(set(scene_characters)) == 2


def detect_shot(
    paragraph: Dict[str, Any],
    scene: Dict[str, Any],
    shot_order: int = 1
) -> Optional[Shot]:
    """Convenience function to detect a shot from a paragraph.

    Args:
        paragraph: Paragraph dict
        scene: Scene dict
        shot_order: Shot order number

    Returns:
        Shot if detected, None otherwise
    """
    detector = ShotDetector()
    return detector.detect_from_paragraph(paragraph, scene, shot_order)
