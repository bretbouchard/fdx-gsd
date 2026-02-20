"""Props continuity validator.

Detects prop continuity issues:
- PROP-01: Props appearing without introduction
- PROP-02: Ownership transfers not shown on screen
- PROP-03: Prop damage that doesn't persist
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base import BaseValidator, Issue, IssueSeverity


class PropsValidator(BaseValidator):
    """
    Validator for prop continuity.

    Checks:
    - PROP-01: Props appearing without introduction (WARNING)
    - PROP-02: Ownership transfers not shown (ERROR)
    - PROP-03: Damage not persisting (WARNING)
    """

    # Patterns to detect prop mentions and actions
    PROP_PATTERNS = {
        "holding": [
            r"(?:holds?|holding|carries?|carrying)\s+(?:a|the|her|his)\s+(.+?)(?:\.|,|\n)",
            r"(?:has|with)\s+(?:a|the)\s+(.+?)\s+in\s+(?:hand|possession)",
        ],
        "taking": [
            r"(?:takes?|grabbed?|picks? up|retrieves?)\s+(?:a|the|her|his)\s+(.+?)(?:\.|,|\n)",
            r"(?:snatches?|steals?|swipes?)\s+(?:the|a)\s+(.+?)(?:\.|,|\n)",
        ],
        "giving": [
            r"(?:gives?|hands?|passes?|offers?)\s+(.+?)\s+to\s+",
            r"(?:returns?|delivers?)\s+(?:the|a)\s+(.+?)\s+to\s+",
        ],
        "damaging": [
            r"(?:dropped?|broke?|shattered?|smashed?|destroyed?)\s+(?:the|a)\s+(.+?)(?:\.|,|\n)",
            r"(?:rips?|tears?|burns?)\s+(?:through|up|the)\s+(.+?)(?:\.|,|\n)",
        ],
        "repairing": [
            r"(?:fixes?|repairs?|mends?|restores?)\s+(?:the|a)\s+(.+?)(?:\.|,|\n)",
            r"(?:glues?|tapes?|sews?)\s+(?:up|together|the)\s+(.+?)(?:\.|,|\n)",
        ],
    }

    # Introduction action types
    INTRODUCTION_ACTIONS = {"holding", "taking", "giving"}

    # Transfer action types
    TRANSFER_ACTIONS = {"giving", "taking"}

    def __init__(self, build_path: Path):
        """Initialize props validator."""
        super().__init__(build_path)
        self._prop_normalizations: Dict[str, str] = {}

    def validate(self) -> List[Issue]:
        """
        Run props validation checks.

        Returns:
            List of prop continuity issues
        """
        self._load_graphs()
        self.clear_issues()

        # Build prop timeline
        timeline = self._build_prop_timeline()

        # Run checks
        self._check_prop_introductions(timeline)
        self._check_ownership_transfers(timeline)
        self._check_damage_persistence(timeline)

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

    def _build_prop_timeline(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build timeline of prop appearances.

        Returns:
            Dict: normalized_prop_name -> list of appearance dicts
        """
        timeline: Dict[str, List[Dict[str, Any]]] = {}

        # Get all scenes sorted by scene number
        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_id = scene.get("id", "")
            scene_num = scene.get("attributes", {}).get("scene_number", 0)
            scene_content = self._get_scene_content(scene)

            # Extract prop mentions from scene
            prop_mentions = self._extract_prop_mentions(scene_content)

            for mention in prop_mentions:
                prop_name = self._normalize_prop_name(mention["prop"])
                action = mention["action"]
                holder = mention.get("holder")

                if prop_name not in timeline:
                    timeline[prop_name] = []

                timeline[prop_name].append({
                    "scene_id": scene_id,
                    "scene_number": scene_num,
                    "action": action,
                    "holder": holder,
                    "raw_prop": mention["prop"],
                    "evidence_ids": scene.get("evidence_ids", []),
                })

        return timeline

    def _get_scene_content(self, scene: Dict) -> str:
        """Get scene content from scriptgraph or scene notes."""
        if self._scriptgraph:
            scene_id = scene.get("id", "")
            for para in self._scriptgraph.get("paragraphs", []):
                if para.get("scene_id") == scene_id:
                    return para.get("text", "")

        return scene.get("description", "") or scene.get("notes", "")

    def _extract_prop_mentions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract prop mentions from scene content.

        Returns:
            List of dicts with prop, action, and optional holder
        """
        mentions = []

        for action_type, patterns in self.PROP_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    prop_text = match.group(1).strip()

                    # Try to extract holder from context
                    holder = self._extract_holder(content, match)

                    mentions.append({
                        "prop": prop_text,
                        "action": action_type,
                        "holder": holder,
                    })

        return mentions

    def _extract_holder(self, content: str, match: re.Match) -> Optional[str]:
        """Try to extract who is holding/using the prop."""
        # Look for character name before the match
        start = max(0, match.start() - 50)
        context = content[start : match.start()]

        # Pattern: "JOHN holds the gun"
        name_match = re.search(r"([A-Z][a-z]+)\s+(?:holds?|has|takes?|gives?)\s*$", context)
        if name_match:
            name = name_match.group(1)
            # Try to match to a character entity
            characters = self.get_characters()
            for char in characters:
                if char.get("name", "").lower() == name.lower():
                    return char.get("id", "")
                if any(a.lower() == name.lower() for a in char.get("aliases", [])):
                    return char.get("id", "")

        return None

    def _normalize_prop_name(self, name: str) -> str:
        """
        Normalize prop name for comparison.

        Returns:
            Normalized lowercase name without articles
        """
        # Lowercase
        normalized = name.lower()

        # Remove articles
        for article in ["a ", "an ", "the ", "her ", "his ", "my ", "their "]:
            if normalized.startswith(article):
                normalized = normalized[len(article) :]
                break

        # Strip trailing punctuation
        normalized = normalized.rstrip(".,!?;:")

        # Apply any configured normalizations
        if normalized in self._prop_normalizations:
            return self._prop_normalizations[normalized]

        return normalized

    def _check_prop_introductions(self, timeline: Dict[str, List[Dict]]) -> None:
        """PROP-01: Check for props appearing without introduction."""
        for prop_name, appearances in timeline.items():
            if not appearances:
                continue

            # Sort by scene number
            appearances.sort(key=lambda x: x.get("scene_number", 0))

            # Get first appearance
            first = appearances[0]
            first_action = first.get("action", "")

            # Check if first action is an introduction
            if first_action not in self.INTRODUCTION_ACTIONS:
                # Check if prop appears earlier with introduction action
                introduced = False
                for ap in appearances:
                    if ap.get("action") in self.INTRODUCTION_ACTIONS:
                        if ap.get("scene_number", 999) < first.get("scene_number", 0):
                            introduced = True
                            break

                if not introduced:
                    self._add_issue(
                        rule_code="PROP-01",
                        title="Prop appears without introduction",
                        description=(
                            f"Prop '{first.get('raw_prop', prop_name)}' appears in "
                            f"scene {first.get('scene_number')} without a clear introduction "
                            f"(holding, receiving, picking up, etc.)"
                        ),
                        severity=IssueSeverity.WARNING,
                        scene_id=first.get("scene_id"),
                        scene_number=first.get("scene_number"),
                        suggested_fix=(
                            f"Add an introduction beat for '{first.get('raw_prop', prop_name)}' "
                            f"before or in scene {first.get('scene_number')}"
                        ),
                    )

    def _check_ownership_transfers(self, timeline: Dict[str, List[Dict]]) -> None:
        """PROP-02: Check for ownership transfers not shown."""
        for prop_name, appearances in timeline.items():
            if len(appearances) < 2:
                continue

            # Sort by scene number
            appearances.sort(key=lambda x: x.get("scene_number", 0))

            # Track holder changes
            for i in range(1, len(appearances)):
                prev = appearances[i - 1]
                curr = appearances[i]

                prev_holder = prev.get("holder")
                curr_holder = curr.get("holder")

                # Skip if no holder info or same holder
                if not prev_holder or not curr_holder:
                    continue
                if prev_holder == curr_holder:
                    continue

                # Check if there's a transfer action between them
                if self._has_transfer_action(appearances, prev, curr):
                    continue

                # Find character names
                prev_char = self.get_entity_by_id(prev_holder)
                curr_char = self.get_entity_by_id(curr_holder)
                prev_name = prev_char.get("name", prev_holder) if prev_char else prev_holder
                curr_name = curr_char.get("name", curr_holder) if curr_char else curr_holder

                self._add_issue(
                    rule_code="PROP-02",
                    title="Ownership transfer not shown",
                    description=(
                        f"Prop '{curr.get('raw_prop', prop_name)}' changes holder from "
                        f"{prev_name} to {curr_name} between scenes {prev.get('scene_number')} "
                        f"and {curr.get('scene_number')} without showing the transfer"
                    ),
                    severity=IssueSeverity.ERROR,
                    scene_id=curr.get("scene_id"),
                    scene_number=curr.get("scene_number"),
                    entity_ids=[prev_holder, curr_holder],
                    evidence_ids=curr.get("evidence_ids", []),
                    suggested_fix=(
                        f"Show {prev_name} giving '{curr.get('raw_prop', prop_name)}' to "
                        f"{curr_name}, or explain the transfer"
                    ),
                )

    def _check_damage_persistence(self, timeline: Dict[str, List[Dict]]) -> None:
        """PROP-03: Check for damage not persisting."""
        for prop_name, appearances in timeline.items():
            if len(appearances) < 2:
                continue

            # Sort by scene number
            appearances.sort(key=lambda x: x.get("scene_number", 0))

            # Track damage state
            damaged_scene = None
            repaired = False

            for ap in appearances:
                action = ap.get("action", "")

                # Track damage
                if action == "damaging":
                    damaged_scene = ap
                    repaired = False
                    continue

                # Track repair
                if action == "repairing":
                    repaired = True
                    continue

                # If damaged and appears intact later without repair
                if damaged_scene and not repaired:
                    if ap.get("scene_number", 0) > damaged_scene.get("scene_number", 0):
                        # Check if holding action suggests intact prop
                        if action in ["holding", "taking"]:
                            self._add_issue(
                                rule_code="PROP-03",
                                title="Damaged prop appears intact",
                                description=(
                                    f"Prop '{ap.get('raw_prop', prop_name)}' was damaged in "
                                    f"scene {damaged_scene.get('scene_number')} but appears "
                                    f"intact in scene {ap.get('scene_number')} without repair"
                                ),
                                severity=IssueSeverity.WARNING,
                                scene_id=ap.get("scene_id"),
                                scene_number=ap.get("scene_number"),
                                suggested_fix=(
                                    f"Either show '{ap.get('raw_prop', prop_name)}' being "
                                    f"repaired, or maintain damage state throughout"
                                ),
                            )
                            # Only report once per damage
                            break

    def _has_transfer_action(
        self, appearances: List[Dict], prev: Dict, curr: Dict
    ) -> bool:
        """Check if there's a transfer action between two appearances."""
        prev_scene = prev.get("scene_number", 0)
        curr_scene = curr.get("scene_number", 0)

        for ap in appearances:
            ap_scene = ap.get("scene_number", 0)
            if prev_scene <= ap_scene <= curr_scene:
                if ap.get("action") in self.TRANSFER_ACTIONS:
                    return True

        return False
