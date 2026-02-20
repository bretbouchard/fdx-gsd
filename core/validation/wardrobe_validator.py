"""Wardrobe continuity validator.

Detects wardrobe inconsistencies across scenes:
- WARD-01: Unexplained wardrobe state changes
- WARD-02: Conflicting wardrobe in continuous timeline
- WARD-03: Missing signature items
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base import BaseValidator, Issue, IssueSeverity


class WardrobeValidator(BaseValidator):
    """
    Validator for wardrobe/costume continuity.

    Checks:
    - WARD-01: Wardrobe changes without cause beat (WARNING)
    - WARD-02: Conflicting wardrobe in continuous timeline (ERROR)
    - WARD-03: Missing signature items (INFO)
    """

    # Patterns to detect wardrobe mentions
    WARDROBE_PATTERNS = [
        r"wearing\s+(.+?)(?:\.|,|\n)",
        r"dressed\s+in\s+(.+?)(?:\.|,|\n)",
        r"in\s+(?:a|the)\s+(\w+\s+(?:coat|jacket|dress|suit|outfit|robe|uniform))",
        r"(\w+)\s+(?:cloak|robe|uniform|costume|gown)",
        r"(?:puts? on|donning)\s+(?:a|the|her|his)\s+(.+?)(?:\.|,|\n)",
        r"(?:removes?|takes off)\s+(?:her|his|the)\s+(.+?)(?:\.|,|\n)",
    ]

    # Time skip markers that explain wardrobe changes
    TIME_SKIP_MARKERS = [
        "LATER",
        "THE NEXT DAY",
        "THE FOLLOWING DAY",
        "THREE DAYS LATER",
        "HOURS LATER",
        "A WEEK LATER",
        "MONTHS LATER",
        "YEARS LATER",
        "THAT NIGHT",
        "THE NEXT MORNING",
    ]

    # Continuous time markers
    CONTINUOUS_MARKERS = [
        "CONTINUOUS",
        "MOMENTS LATER",
        "SAME TIME",
        "AT THE SAME TIME",
    ]

    def __init__(
        self,
        build_path: Path,
        signature_items: Optional[Dict[str, List[str]]] = None,
    ):
        """
        Initialize wardrobe validator.

        Args:
            build_path: Path to build directory
            signature_items: Dict mapping character_id -> list of signature items
        """
        super().__init__(build_path)
        self.signature_items = signature_items or {}

    def validate(self) -> List[Issue]:
        """
        Run wardrobe validation checks.

        Returns:
            List of wardrobe continuity issues
        """
        self._load_graphs()
        self.clear_issues()

        # Build wardrobe timeline
        timeline = self._build_wardrobe_timeline()

        # Run checks
        for character_id, appearances in timeline.items():
            if len(appearances) < 2:
                continue

            # Sort by scene number
            appearances.sort(key=lambda x: x.get("scene_number", 0))

            # Check for issues
            self._check_state_changes(character_id, appearances)
            self._check_timeline_conflicts(character_id, appearances)
            self._check_signature_items(character_id, appearances)

        # Sort issues by severity, then scene number
        return sorted(
            self._issues,
            key=lambda i: (
                0 if i.severity == IssueSeverity.ERROR
                else 1 if i.severity == IssueSeverity.WARNING
                else 2,
                i.scene_number or 9999,
            ),
        )

    def _build_wardrobe_timeline(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build wardrobe timeline for each character.

        Returns:
            Dict: character_id -> list of appearance dicts with wardrobe info
        """
        timeline: Dict[str, List[Dict[str, Any]]] = {}

        # Get all characters
        characters = self.get_characters()

        # Get all scenes sorted by scene number
        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_id = scene.get("id", "")
            scene_num = scene.get("attributes", {}).get("scene_number", 0)
            scene_content = self._get_scene_content(scene)

            # Get characters in this scene
            scene_characters = scene.get("characters", [])
            if not scene_characters:
                scene_characters = self._extract_characters_from_content(scene_content)

            # Extract wardrobe mentions for each character
            for char_id in scene_characters:
                wardrobe = self._extract_wardrobe_state(scene_content, char_id)
                if wardrobe:
                    if char_id not in timeline:
                        timeline[char_id] = []
                    timeline[char_id].append({
                        "scene_id": scene_id,
                        "scene_number": scene_num,
                        "wardrobe_state": wardrobe,
                        "evidence_ids": scene.get("evidence_ids", []),
                        "time_marker": self._extract_time_marker(scene_content),
                    })

        return timeline

    def _get_scene_content(self, scene: Dict) -> str:
        """Get scene content from scriptgraph or scene notes."""
        if self._scriptgraph:
            # Try to find matching scene in scriptgraph
            scene_id = scene.get("id", "")
            for para in self._scriptgraph.get("paragraphs", []):
                if para.get("scene_id") == scene_id:
                    return para.get("text", "")

        # Fallback to scene description/notes
        return scene.get("description", "") or scene.get("notes", "")

    def _extract_characters_from_content(self, content: str) -> List[str]:
        """Extract character IDs from scene content."""
        # Simple extraction - look for character names in dialogue headers
        # Pattern: JOHN\n(dialogue)
        pattern = r"^([A-Z][A-Z\s]+)\n\("
        matches = re.findall(pattern, content, re.MULTILINE)

        # Map to character entities
        char_ids = []
        characters = self.get_characters()
        for match in matches:
            name = match.strip()
            for char in characters:
                if char.get("name", "").upper() == name:
                    char_ids.append(char.get("id", ""))
                    break
                # Check aliases
                aliases = char.get("aliases", [])
                if any(a.upper() == name for a in aliases):
                    char_ids.append(char.get("id", ""))
                    break

        return list(set(char_ids))

    def _extract_wardrobe_state(
        self, content: str, character_id: str
    ) -> Optional[str]:
        """
        Extract wardrobe state for a character from scene content.

        Returns:
            Wardrobe description or None
        """
        # Get character name for context
        character = self.get_entity_by_id(character_id)
        if not character:
            return None

        char_name = character.get("name", "")
        aliases = character.get("aliases", [])
        all_names = [char_name] + aliases

        # Search for wardrobe mentions near character name
        for pattern in self.WARDROBE_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                wardrobe_desc = match.group(1).strip()

                # Check if this wardrobe mention is for our character
                # Look for character name in surrounding context
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 50)
                context = content[start:end]

                for name in all_names:
                    if name.lower() in context.lower():
                        return wardrobe_desc.lower()

        return None

    def _extract_time_marker(self, content: str) -> Optional[str]:
        """Extract time marker from scene content."""
        content_upper = content.upper()

        for marker in self.TIME_SKIP_MARKERS + self.CONTINUOUS_MARKERS:
            if marker in content_upper:
                return marker

        return None

    def _check_state_changes(
        self, character_id: str, appearances: List[Dict]
    ) -> None:
        """WARD-01: Check for unexplained wardrobe changes."""
        for i in range(1, len(appearances)):
            prev = appearances[i - 1]
            curr = appearances[i]

            prev_wardrobe = prev.get("wardrobe_state", "")
            curr_wardrobe = curr.get("wardrobe_state", "")

            # Skip if wardrobe unchanged
            if prev_wardrobe == curr_wardrobe:
                continue

            # Check for cause beat
            if self._has_costume_change_cause(prev, curr):
                continue

            # Create issue - wardrobe changed without explanation
            character = self.get_entity_by_id(character_id)
            char_name = character.get("name", character_id) if character else character_id

            self._add_issue(
                rule_code="WARD-01",
                title="Unexplained wardrobe change",
                description=(
                    f"Character {char_name}'s wardrobe changes from "
                    f"'{prev_wardrobe}' to '{curr_wardrobe}' between scenes "
                    f"{prev.get('scene_number')} and {curr.get('scene_number')} "
                    f"without a clear cause beat (time skip, costume change scene, etc.)"
                ),
                severity=IssueSeverity.WARNING,
                scene_id=curr.get("scene_id"),
                scene_number=curr.get("scene_number"),
                entity_ids=[character_id],
                evidence_ids=curr.get("evidence_ids", []),
                suggested_fix=(
                    f"Add a time skip marker (LATER, THE NEXT DAY) between scenes, "
                    f"or show {char_name} changing clothes"
                ),
            )

    def _check_timeline_conflicts(
        self, character_id: str, appearances: List[Dict]
    ) -> None:
        """WARD-02: Check for conflicting wardrobe in continuous timeline."""
        for i in range(1, len(appearances)):
            prev = appearances[i - 1]
            curr = appearances[i]

            # Check if scenes are continuous
            if not self._are_adjacent_timeline(prev, curr):
                continue

            prev_wardrobe = prev.get("wardrobe_state", "")
            curr_wardrobe = curr.get("wardrobe_state", "")

            # Skip if wardrobe matches or either is None
            if not prev_wardrobe or not curr_wardrobe:
                continue
            if prev_wardrobe == curr_wardrobe:
                continue

            # ERROR: Wardrobe differs in continuous time
            character = self.get_entity_by_id(character_id)
            char_name = character.get("name", character_id) if character else character_id

            self._add_issue(
                rule_code="WARD-02",
                title="Wardrobe conflict in continuous timeline",
                description=(
                    f"Character {char_name} has conflicting wardrobe in continuous time: "
                    f"'{prev_wardrobe}' in scene {prev.get('scene_number')} vs "
                    f"'{curr_wardrobe}' in scene {curr.get('scene_number')} (CONTINUOUS)"
                ),
                severity=IssueSeverity.ERROR,
                scene_id=curr.get("scene_id"),
                scene_number=curr.get("scene_number"),
                entity_ids=[character_id],
                evidence_ids=curr.get("evidence_ids", []),
                suggested_fix=(
                    f"Either change the time marker between scenes, or ensure "
                    f"{char_name}'s wardrobe is consistent in continuous time"
                ),
            )

    def _check_signature_items(
        self, character_id: str, appearances: List[Dict]
    ) -> None:
        """WARD-03: Check for missing signature items."""
        if character_id not in self.signature_items:
            return

        signature = self.signature_items[character_id]
        if not signature:
            return

        character = self.get_entity_by_id(character_id)
        char_name = character.get("name", character_id) if character else character_id

        for appearance in appearances:
            wardrobe = appearance.get("wardrobe_state", "")
            if not wardrobe:
                continue

            # Check for signature items
            for item in signature:
                if item.lower() not in wardrobe.lower():
                    self._add_issue(
                        rule_code="WARD-03",
                        title="Missing signature item",
                        description=(
                            f"Character {char_name}'s signature item '{item}' "
                            f"is not mentioned in scene {appearance.get('scene_number')}"
                        ),
                        severity=IssueSeverity.INFO,
                        scene_id=appearance.get("scene_id"),
                        scene_number=appearance.get("scene_number"),
                        entity_ids=[character_id],
                        evidence_ids=appearance.get("evidence_ids", []),
                        suggested_fix=(
                            f"Consider mentioning {char_name}'s {item} in this scene "
                            f"for continuity"
                        ),
                    )

    def _has_costume_change_cause(
        self, prev_appearance: Dict, curr_appearance: Dict
    ) -> bool:
        """Check if there's a valid cause for costume change."""
        curr_marker = curr_appearance.get("time_marker")

        # Time skip markers explain costume changes
        if curr_marker in self.TIME_SKIP_MARKERS:
            return True

        return False

    def _are_adjacent_timeline(
        self, prev_appearance: Dict, curr_appearance: Dict
    ) -> bool:
        """Check if two appearances are in continuous time."""
        curr_marker = curr_appearance.get("time_marker")

        if curr_marker in self.CONTINUOUS_MARKERS:
            return True

        # Check if scenes are adjacent numbers
        prev_num = prev_appearance.get("scene_number", 0)
        curr_num = curr_appearance.get("scene_number", 0)
        if curr_num - prev_num == 1 and curr_marker is None:
            # Adjacent scenes without time marker might be continuous
            return True

        return False
