"""Timeline continuity validator.

Detects timeline inconsistencies:
- TIME-01: Impossible travel between locations
- TIME-02: Unresolved relative time phrases
- TIME-04: Characters in two places at once
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import BaseValidator, Issue, IssueSeverity


class TimelineValidator(BaseValidator):
    """
    Validator for timeline continuity.

    Checks:
    - TIME-01: Impossible travel (ERROR)
    - TIME-02: Unresolved time phrases (WARNING)
    - TIME-04: Character location conflicts (ERROR)
    """

    # Time skip markers
    TIME_SKIP_MARKERS = [
        "LATER",
        "THE NEXT DAY",
        "THREE DAYS LATER",
        "HOURS LATER",
        "A WEEK LATER",
        "MONTHS LATER",
        "THAT NIGHT",
        "THE NEXT MORNING",
        "THE FOLLOWING DAY",
    ]

    # Continuous time markers
    CONTINUOUS_MARKERS = [
        "CONTINUOUS",
        "MOMENTS LATER",
        "SAME TIME",
        "AT THE SAME TIME",
        "MEANWHILE",
    ]

    # Relative time phrases that need resolution
    RELATIVE_TIME_PHRASES = [
        r"later\s+that\s+(day|night|morning|evening|afternoon)",
        r"earlier\s+that\s+(day|night|morning|evening|afternoon)",
        r"the\s+following\s+(day|morning|night)",
        r"the\s+previous\s+(day|morning|night)",
        r"(?:a\s+few|several)\s+(?:hours?|minutes?|days?)\s+(?:later|earlier)",
        r"not\s+long\s+(?:after|before)",
        r"shortly\s+(?:after|before)",
    ]

    # Default travel time estimates (in minutes) - can be overridden
    DEFAULT_TRAVEL_TIMES: Dict[Tuple[str, str], int] = {}

    def __init__(
        self,
        build_path: Path,
        location_distances: Optional[Dict[Tuple[str, str], int]] = None,
    ):
        """
        Initialize timeline validator.

        Args:
            build_path: Path to build directory
            location_distances: Dict of (loc_a, loc_b) -> travel_time_minutes
        """
        super().__init__(build_path)
        self.location_distances = location_distances or self.DEFAULT_TRAVEL_TIMES

    def validate(self) -> List[Issue]:
        """
        Run timeline validation checks.

        Returns:
            List of timeline continuity issues
        """
        self._load_graphs()
        self.clear_issues()

        # Build timelines
        scene_timeline = self._build_scene_timeline()
        char_timeline = self._build_character_timeline()

        # Run checks
        self._check_impossible_travel(char_timeline, scene_timeline)
        self._check_unresolved_time_phrases(scene_timeline)
        self._check_character_location_conflicts(char_timeline, scene_timeline)

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

    def _build_scene_timeline(self) -> List[Dict[str, Any]]:
        """
        Build ordered scene timeline.

        Returns:
            List of scene dicts sorted by scene_number
        """
        timeline = []
        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_id = scene.get("id", "")
            attrs = scene.get("attributes", {})
            scene_content = self._get_scene_content(scene)

            # Extract metadata
            scene_entry = {
                "scene_id": scene_id,
                "scene_number": attrs.get("scene_number", 0),
                "location": attrs.get("location", ""),
                "location_id": self._find_location_id(attrs.get("location", "")),
                "time_of_day": attrs.get("time_of_day", ""),
                "int_ext": attrs.get("int_ext", ""),
                "time_marker": self._extract_time_marker(scene_content),
                "evidence_ids": scene.get("evidence_ids", []),
                "content": scene_content,
            }

            timeline.append(scene_entry)

        return timeline

    def _build_character_timeline(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build timeline of character appearances.

        Returns:
            Dict: character_id -> list of appearance dicts
        """
        timeline: Dict[str, List[Dict[str, Any]]] = {}

        # Get all characters
        characters = self.get_characters()

        # Get all scenes
        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_id = scene.get("id", "")
            attrs = scene.get("attributes", {})
            scene_num = attrs.get("scene_number", 0)
            location = attrs.get("location", "")
            scene_content = self._get_scene_content(scene)

            # Get characters in scene
            scene_chars = scene.get("characters", [])
            if not scene_chars:
                scene_chars = self._extract_characters_from_content(scene_content)

            for char_id in scene_chars:
                if char_id not in timeline:
                    timeline[char_id] = []

                timeline[char_id].append({
                    "scene_id": scene_id,
                    "scene_number": scene_num,
                    "location": location,
                    "location_id": self._find_location_id(location),
                    "time_marker": self._extract_time_marker(scene_content),
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

    def _find_location_id(self, location_name: str) -> Optional[str]:
        """Find location entity ID by name."""
        if not location_name:
            return None

        locations = self.get_locations()
        for loc in locations:
            if loc.get("name", "").lower() == location_name.lower():
                return loc.get("id")
            if any(a.lower() == location_name.lower() for a in loc.get("aliases", [])):
                return loc.get("id")

        return None

    def _extract_characters_from_content(self, content: str) -> List[str]:
        """Extract character IDs from scene content."""
        pattern = r"^([A-Z][A-Z\s]+)\n\("
        matches = re.findall(pattern, content, re.MULTILINE)

        char_ids = []
        characters = self.get_characters()

        for match in matches:
            name = match.strip()
            for char in characters:
                if char.get("name", "").upper() == name:
                    char_ids.append(char.get("id", ""))
                    break
                if any(a.upper() == name for a in char.get("aliases", [])):
                    char_ids.append(char.get("id", ""))
                    break

        return list(set(char_ids))

    def _extract_time_marker(self, content: str) -> Optional[str]:
        """Extract time marker from scene content."""
        content_upper = content.upper()

        for marker in self.TIME_SKIP_MARKERS + self.CONTINUOUS_MARKERS:
            if marker in content_upper:
                return marker

        return None

    def _check_impossible_travel(
        self,
        char_timeline: Dict[str, List[Dict]],
        scene_timeline: List[Dict],
    ) -> None:
        """TIME-01: Check for impossible travel between locations."""
        for char_id, appearances in char_timeline.items():
            if len(appearances) < 2:
                continue

            # Sort by scene number
            appearances.sort(key=lambda x: x.get("scene_number", 0))

            for i in range(1, len(appearances)):
                prev = appearances[i - 1]
                curr = appearances[i]

                prev_loc = prev.get("location")
                curr_loc = curr.get("location")

                # Skip if same location or missing location
                if not prev_loc or not curr_loc or prev_loc == curr_loc:
                    continue

                # Check for time skip that explains travel
                curr_marker = curr.get("time_marker")
                if curr_marker in self.TIME_SKIP_MARKERS:
                    continue

                # Check travel time
                travel_time = self._get_travel_time(prev_loc, curr_loc)

                # If we have distance data and travel seems impossible
                if travel_time is not None and travel_time > 30:
                    # No time marker and locations are far apart
                    character = self.get_entity_by_id(char_id)
                    char_name = character.get("name", char_id) if character else char_id

                    self._add_issue(
                        rule_code="TIME-01",
                        title="Impossible travel between locations",
                        description=(
                            f"Character {char_name} appears at '{prev_loc}' in scene "
                            f"{prev.get('scene_number')} and at '{curr_loc}' in scene "
                            f"{curr.get('scene_number')} without sufficient travel time "
                            f"(~{travel_time} minutes needed)"
                        ),
                        severity=IssueSeverity.ERROR,
                        scene_id=curr.get("scene_id"),
                        scene_number=curr.get("scene_number"),
                        entity_ids=[char_id],
                        evidence_ids=curr.get("evidence_ids", []),
                        suggested_fix=(
                            f"Add a time skip marker between scenes, or show travel "
                            f"between {prev_loc} and {curr_loc}"
                        ),
                    )

    def _check_unresolved_time_phrases(self, scene_timeline: List[Dict]) -> None:
        """TIME-02: Check for unresolved relative time phrases."""
        for scene in scene_timeline:
            content = scene.get("content", "")

            for pattern in self.RELATIVE_TIME_PHRASES:
                matches = re.finditer(pattern, content, re.IGNORECASE)

                for match in matches:
                    phrase = match.group(0)

                    # Check if there's a clear time anchor
                    # For simplicity, flag if the phrase exists without explicit time
                    # A more sophisticated check would trace back to find the anchor
                    context_start = max(0, match.start() - 200)
                    context = content[context_start : match.start()]

                    # Check for time anchors in context
                    has_anchor = any(
                        marker.lower() in context.lower()
                        for marker in self.TIME_SKIP_MARKERS[:4]  # Basic anchors
                    )

                    if not has_anchor:
                        self._add_issue(
                            rule_code="TIME-02",
                            title="Unresolved relative time phrase",
                            description=(
                                f"Relative time phrase '{phrase}' in scene "
                                f"{scene.get('scene_number')} lacks a clear time anchor"
                            ),
                            severity=IssueSeverity.WARNING,
                            scene_id=scene.get("scene_id"),
                            scene_number=scene.get("scene_number"),
                            source_paragraph=phrase,
                            suggested_fix=(
                                f"Clarify '{phrase}' by adding an explicit time reference "
                                f"(e.g., 'Three hours after the meeting...')"
                            ),
                        )

    def _check_character_location_conflicts(
        self,
        char_timeline: Dict[str, List[Dict]],
        scene_timeline: List[Dict],
    ) -> None:
        """TIME-04: Check for characters in two places at once."""
        # Find simultaneous scenes (CONTINUOUS or SAME_TIME)
        simultaneous_groups = self._find_simultaneous_scenes(scene_timeline)

        for group in simultaneous_groups:
            if len(group) < 2:
                continue

            # Check if any character appears in multiple scenes in this group
            scene_locations = {s.get("scene_id"): s.get("location") for s in group}

            for char_id, appearances in char_timeline.items():
                char_scenes_in_group = [
                    ap
                    for ap in appearances
                    if ap.get("scene_id") in scene_locations
                ]

                if len(char_scenes_in_group) < 2:
                    continue

                # Character appears in multiple simultaneous scenes
                locations = set(ap.get("location") for ap in char_scenes_in_group)

                if len(locations) > 1:
                    # Different locations!
                    character = self.get_entity_by_id(char_id)
                    char_name = character.get("name", char_id) if character else char_id

                    loc_list = list(locations)
                    first_ap = char_scenes_in_group[0]
                    second_ap = char_scenes_in_group[1]

                    self._add_issue(
                        rule_code="TIME-04",
                        title="Character in two places at once",
                        description=(
                            f"Character {char_name} appears in multiple simultaneous "
                            f"scenes at different locations: '{loc_list[0]}' (scene "
                            f"{first_ap.get('scene_number')}) and '{loc_list[1]}' (scene "
                            f"{second_ap.get('scene_number')})"
                        ),
                        severity=IssueSeverity.ERROR,
                        scene_id=second_ap.get("scene_id"),
                        scene_number=second_ap.get("scene_number"),
                        entity_ids=[char_id],
                        evidence_ids=second_ap.get("evidence_ids", []),
                        suggested_fix=(
                            f"Either {char_name} cannot be in both locations, or these "
                            f"scenes are not simultaneous - clarify timing"
                        ),
                    )

    def _get_travel_time(self, location_a: str, location_b: str) -> Optional[int]:
        """
        Get travel time between two locations.

        Returns:
            Travel time in minutes, or None if unknown
        """
        # Normalize location names for lookup
        loc_a = location_a.lower().strip()
        loc_b = location_b.lower().strip()

        # Check direct lookup
        key = (loc_a, loc_b)
        if key in self.location_distances:
            return self.location_distances[key]

        # Check reverse
        key_rev = (loc_b, loc_a)
        if key_rev in self.location_distances:
            return self.location_distances[key_rev]

        # Estimate based on heuristics
        # Same building = 1-5 minutes
        # Different building, same city = 15-30 minutes
        # Different cities = hours

        if not loc_a or not loc_b:
            return None

        # Simple heuristic: if names share significant words, assume close
        words_a = set(loc_a.split())
        words_b = set(loc_b.split())
        overlap = words_a & words_b

        if overlap and len(overlap) >= 1:
            # Some overlap - same general area
            return 10

        # Unknown - return None (don't flag)
        return None

    def _find_simultaneous_scenes(
        self, scene_timeline: List[Dict]
    ) -> List[List[Dict]]:
        """
        Find groups of scenes that occur at the same time.

        Returns:
            List of scene groups that are simultaneous
        """
        groups: List[List[Dict]] = []
        current_group: List[Dict] = []

        for scene in scene_timeline:
            marker = scene.get("time_marker")

            if marker in self.CONTINUOUS_MARKERS:
                # This scene is simultaneous with previous
                if current_group:
                    current_group.append(scene)
                else:
                    # Start new group with previous scene if available
                    pass
            else:
                # Save previous group
                if len(current_group) > 1:
                    groups.append(current_group)
                # Start new group
                current_group = [scene]

        # Don't forget last group
        if len(current_group) > 1:
            groups.append(current_group)

        return groups

    def _scenes_are_simultaneous(
        self, scene_a: Dict, scene_b: Dict
    ) -> bool:
        """Check if two scenes occur at the same story time."""
        marker_a = scene_a.get("time_marker")
        marker_b = scene_b.get("time_marker")

        # If one has CONTINUOUS/SAME_TIME marker, they're simultaneous
        if marker_a in self.CONTINUOUS_MARKERS or marker_b in self.CONTINUOUS_MARKERS:
            return True

        return False
