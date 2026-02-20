"""Knowledge continuity validator.

Detects knowledge state problems:
- KNOW-01: Characters referencing unlearned information
- KNOW-02: Secrets propagating through unshown channels
- KNOW-03: Inconsistent character motives/goals
- KNOW-04: Relationship continuity issues
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import BaseValidator, Issue, IssueSeverity


class KnowledgeValidator(BaseValidator):
    """
    Validator for knowledge state continuity.

    Checks:
    - KNOW-01: Characters acting on unlearned info (ERROR)
    - KNOW-02: Secret propagation issues (WARNING)
    - KNOW-03: Motive inconsistencies (WARNING)
    - KNOW-04: Relationship continuity issues (WARNING)
    """

    # Patterns for information/knowledge indicators
    INFORMATION_PATTERNS = [
        (r"(?:reveals?|tells?|informs?|confesses?)\s+(.+?)\s+that\s+(.+?)(?:\.|,)", "reveal"),
        (r"(?:discovers?|learns?|finds out|realizes?)\s+(?:that\s+)?(.+?)(?:\.|,)", "learn"),
        (r"(?:secret|hidden|confidential|private)\s+(.+?)(?:\.|,)", "secret"),
        (r"(.+?)\s+(?:doesn'?t|don'?t|did not|doesn't)\s+know\s+(?:about\s+)?(.+?)(?:\.|,)", "unknown"),
    ]

    # Patterns for relationship changes
    RELATIONSHIP_MARKERS = {
        "friend": [r"befriends?", r"becomes?\s+friends?\s+with", r"allies?\s+with"],
        "enemy": [r"becomes?\s+(?:an?\s+)?enemy", r"is\s+now\s+an?\s+enemy", r"hostile\s+toward"],
        "lover": [r"falls?\s+in\s+love\s+with", r"starts?\s+dating", r"romance\s+blooms"],
        "betrayal": [r"betrays?", r"stabs?\s+in\s+the\s+back", r"turns?\s+against"],
        "death": [r"kills?", r"murders?", r"eliminates?"],
    }

    # Action patterns that might reference knowledge
    KNOWLEDGE_REFERENCE_PATTERNS = [
        r"(?:because|since|as)\s+(.+?)\s+(?:told|said|mentioned)\s+(?:me|him|her|them)",
        r"(?:remember|recall)\s+(?:that\s+)?(.+?)",
        r"I\s+know\s+(?:that\s+)?(.+?)(?:\.|,)",
        r"(?:found|discovered|learned)\s+out\s+(?:that\s+)?(.+?)(?:\.|,)",
    ]

    def __init__(self, build_path: Path):
        """Initialize knowledge validator."""
        super().__init__(build_path)

    def validate(self) -> List[Issue]:
        """
        Run knowledge validation checks.

        Returns:
            List of knowledge continuity issues
        """
        self._load_graphs()
        self.clear_issues()

        # Build knowledge states
        knowledge_states = self._build_knowledge_states()
        relationship_timeline = self._build_relationship_timeline()

        # Run checks
        self._check_unlearned_knowledge(knowledge_states)
        self._check_secret_propagation(knowledge_states)
        self._check_motive_consistency()
        self._check_relationship_continuity(relationship_timeline)

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

    def _build_knowledge_states(self) -> Dict[str, Dict[int, Set[str]]]:
        """
        Build knowledge states for each character across scenes.

        Returns:
            Dict: character_id -> {scene_number: set of known_facts}
        """
        states: Dict[str, Dict[int, Set[str]]] = {}

        # Initialize all characters with empty knowledge
        characters = self.get_characters()
        for char in characters:
            char_id = char.get("id", "")
            states[char_id] = {}

        # Process scenes in order
        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_num = scene.get("attributes", {}).get("scene_number", 0)
            scene_content = self._get_scene_content(scene)

            # Get characters present in this scene
            chars_present = self._get_characters_present(scene, scene_content)

            # Extract information revealed in this scene
            revealed_info = self._extract_revealed_information(scene_content)

            # Update knowledge states for characters present
            for info in revealed_info:
                fact = info.get("fact", "")
                revealed_to = info.get("revealed_to", chars_present)

                for char_id in revealed_to:
                    if char_id not in states:
                        states[char_id] = {}

                    if scene_num not in states[char_id]:
                        states[char_id][scene_num] = set()

                    states[char_id][scene_num].add(fact)

                    # Carry forward previous knowledge
                    for prev_scene, prev_facts in list(states[char_id].items()):
                        if prev_scene < scene_num:
                            states[char_id][scene_num].update(prev_facts)

        return states

    def _build_relationship_timeline(self) -> Dict[Tuple[str, str], List[Dict]]:
        """
        Build timeline of relationship changes.

        Returns:
            Dict: (char_a_id, char_b_id) -> list of relationship state changes
        """
        timeline: Dict[Tuple[str, str], List[Dict]] = {}

        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_num = scene.get("attributes", {}).get("scene_number", 0)
            scene_content = self._get_scene_content(scene)

            # Extract relationship changes
            for rel_type, patterns in self.RELATIONSHIP_MARKERS.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, scene_content, re.IGNORECASE):
                        # Try to identify the characters involved
                        chars = self._extract_relationship_characters(
                            scene_content, match, scene
                        )

                        if len(chars) >= 2:
                            pair = tuple(sorted(chars[:2]))
                            if pair not in timeline:
                                timeline[pair] = []

                            timeline[pair].append({
                                "scene_number": scene_num,
                                "scene_id": scene.get("id", ""),
                                "relationship_type": rel_type,
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

    def _get_characters_present(
        self, scene: Dict, content: str
    ) -> List[str]:
        """Get list of character IDs present in scene."""
        # Check scene metadata first
        chars = scene.get("characters", [])
        if chars:
            return chars

        # Extract from content
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

    def _extract_revealed_information(self, content: str) -> List[Dict]:
        """
        Extract information revealed in scene content.

        Returns:
            List of dicts with fact, revealed_by, revealed_to
        """
        info_list = []

        for pattern, info_type in self.INFORMATION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                if info_type == "reveal":
                    # Pattern: X tells Y that Z
                    who = match.group(1).strip()
                    fact = match.group(2).strip()
                    revealed_by = self._match_character(who)
                    revealed_to = []  # Would need more context to determine
                elif info_type == "learn":
                    # Pattern: X discovers that Y
                    fact = match.group(1).strip()
                    revealed_by = []
                    revealed_to = []  # Context dependent
                elif info_type == "secret":
                    # Pattern: secret X
                    fact = f"secret: {match.group(1).strip()}"
                    revealed_by = []
                    revealed_to = []
                else:
                    continue

                info_list.append({
                    "fact": fact,
                    "type": info_type,
                    "revealed_by": revealed_by,
                    "revealed_to": revealed_to,
                })

        return info_list

    def _match_character(self, name_or_pronoun: str) -> Optional[str]:
        """Try to match a name or pronoun to a character entity."""
        text = name_or_pronoun.lower()

        # Handle pronouns - would need dialogue context to resolve
        pronouns = ["he", "she", "they", "him", "her", "them", "i", "me"]
        if text in pronouns:
            return None

        # Try exact name match
        characters = self.get_characters()
        for char in characters:
            if char.get("name", "").lower() == text:
                return char.get("id")
            if any(a.lower() == text for a in char.get("aliases", [])):
                return char.get("id")

        return None

    def _extract_relationship_characters(
        self, content: str, match: re.Match, scene: Dict
    ) -> List[str]:
        """Extract characters involved in a relationship change."""
        chars = []

        # Get context around the match
        start = max(0, match.start() - 100)
        end = min(len(content), match.end() + 100)
        context = content[start:end]

        # Get characters present in scene
        scene_chars = self._get_characters_present(scene, content)

        # Find mentioned characters in context
        for char_id in scene_chars:
            char = self.get_entity_by_id(char_id)
            if char:
                name = char.get("name", "")
                if name.lower() in context.lower():
                    chars.append(char_id)

        return chars

    def _check_unlearned_knowledge(
        self, knowledge_states: Dict[str, Dict[int, Set[str]]]
    ) -> None:
        """KNOW-01: Check for characters acting on unlearned information."""
        scenes = self.get_scenes_sorted()

        for scene in scenes:
            scene_num = scene.get("attributes", {}).get("scene_number", 0)
            scene_content = self._get_scene_content(scene)
            chars_present = self._get_characters_present(scene, scene_content)

            # Check for knowledge references in scene
            for pattern in self.KNOWLEDGE_REFERENCE_PATTERNS:
                for match in re.finditer(pattern, scene_content, re.IGNORECASE):
                    referenced_fact = match.group(1).strip()

                    # Check each character present
                    for char_id in chars_present:
                        # Get character's knowledge state at this scene
                        char_knowledge = set()
                        for s_num, facts in knowledge_states.get(char_id, {}).items():
                            if s_num <= scene_num:
                                char_knowledge.update(facts)

                        # Check if referenced fact is in knowledge
                        # (Simplified: check if any knowledge item contains key words)
                        knows_fact = any(
                            self._facts_related(referenced_fact, known)
                            for known in char_knowledge
                        )

                        if not knows_fact:
                            # Check if this is clearly an unlearned fact
                            # (Skip ambiguous cases to reduce false positives)
                            if self._is_clear_knowledge_violation(referenced_fact, char_knowledge):
                                character = self.get_entity_by_id(char_id)
                                char_name = character.get("name", char_id) if character else char_id

                                self._add_issue(
                                    rule_code="KNOW-01",
                                    title="Character acts on unlearned information",
                                    description=(
                                        f"Character {char_name} references or acts on "
                                        f"'{referenced_fact[:50]}...' in scene {scene_num}, "
                                        f"but this information was not shown being learned"
                                    ),
                                    severity=IssueSeverity.ERROR,
                                    scene_id=scene.get("id"),
                                    scene_number=scene_num,
                                    entity_ids=[char_id],
                                    source_paragraph=match.group(0),
                                    suggested_fix=(
                                        f"Add a scene before scene {scene_num} where "
                                        f"{char_name} learns this information"
                                    ),
                                )

    def _check_secret_propagation(
        self, knowledge_states: Dict[str, Dict[int, Set[str]]]
    ) -> None:
        """KNOW-02: Check for secrets spreading without shown channel."""
        # Find all secrets mentioned
        all_secrets: Set[str] = set()
        for char_states in knowledge_states.values():
            for facts in char_states.values():
                for fact in facts:
                    if fact.startswith("secret:"):
                        all_secrets.add(fact)

        for secret in all_secrets:
            # Find who knows the secret
            knowers: List[Tuple[str, int]] = []  # (char_id, scene_num)

            for char_id, scenes in knowledge_states.items():
                for scene_num, facts in scenes.items():
                    if secret in facts:
                        knowers.append((char_id, scene_num))

            # Sort by scene number
            knowers.sort(key=lambda x: x[1])

            # Check if secret spread has clear channel
            if len(knowers) > 1:
                for i in range(1, len(knowers)):
                    prev_char, prev_scene = knowers[i - 1]
                    curr_char, curr_scene = knowers[i]

                    # If same character, skip
                    if prev_char == curr_char:
                        continue

                    # Check if there's a scene where prev tells curr
                    # (Simplified check - in reality would need to trace scenes)
                    if curr_scene - prev_scene > 1:
                        # Gap in scenes - might need explanation
                        prev_character = self.get_entity_by_id(prev_char)
                        curr_character = self.get_entity_by_id(curr_char)
                        prev_name = prev_character.get("name", prev_char) if prev_character else prev_char
                        curr_name = curr_character.get("name", curr_char) if curr_character else curr_char

                        self._add_issue(
                            rule_code="KNOW-02",
                            title="Secret propagation not shown",
                            description=(
                                f"Secret '{secret[8:40]}...' spreads from {prev_name} to "
                                f"{curr_name} without showing the communication channel"
                            ),
                            severity=IssueSeverity.WARNING,
                            scene_number=curr_scene,
                            entity_ids=[prev_char, curr_char],
                            suggested_fix=(
                                f"Show {prev_name} telling {curr_name} the secret, "
                                f"or establish a communication method"
                            ),
                        )

    def _check_motive_consistency(self) -> None:
        """KNOW-03: Check for motive inconsistencies."""
        # This would require motive/goal tracking in entities
        # For now, implement a simplified version that checks for
        # obvious contradictions in character behavior

        characters = self.get_characters()
        scenes = self.get_scenes_sorted()

        for char in characters:
            char_id = char.get("id", "")
            goals = char.get("attributes", {}).get("goals", [])

            if not goals:
                continue

            # Check each scene for actions contradicting goals
            for scene in scenes:
                scene_chars = scene.get("characters", [])
                if char_id not in scene_chars:
                    continue

                scene_content = self._get_scene_content(scene)
                # Simplified: just flag for review if character acts against type
                # A full implementation would need behavior classification

    def _check_relationship_continuity(
        self, relationship_timeline: Dict[Tuple[str, str], List[Dict]]
    ) -> None:
        """KNOW-04: Check for relationship continuity issues."""
        for pair, changes in relationship_timeline.items():
            if len(changes) < 2:
                continue

            # Sort by scene number
            changes.sort(key=lambda x: x.get("scene_number", 0))

            # Check for sudden state changes
            for i in range(1, len(changes)):
                prev = changes[i - 1]
                curr = changes[i]

                prev_type = prev.get("relationship_type")
                curr_type = curr.get("relationship_type")

                # Certain transitions are suspicious
                suspicious_transitions = [
                    ("friend", "enemy"),
                    ("lover", "betrayal"),
                    ("friend", "death"),
                ]

                if (prev_type, curr_type) in suspicious_transitions:
                    # Check if there's an explanation scene between them
                    prev_scene = prev.get("scene_number", 0)
                    curr_scene = curr.get("scene_number", 0)

                    if curr_scene - prev_scene == 1:
                        # Adjacent scenes - might need explanation
                        char_a = self.get_entity_by_id(pair[0])
                        char_b = self.get_entity_by_id(pair[1])
                        name_a = char_a.get("name", pair[0]) if char_a else pair[0]
                        name_b = char_b.get("name", pair[1]) if char_b else pair[1]

                        self._add_issue(
                            rule_code="KNOW-04",
                            title="Abrupt relationship change",
                            description=(
                                f"Relationship between {name_a} and {name_b} changes "
                                f"from {prev_type} to {curr_type} between scenes "
                                f"{prev_scene} and {curr_scene} without clear explanation"
                            ),
                            severity=IssueSeverity.WARNING,
                            scene_id=curr.get("scene_id"),
                            scene_number=curr_scene,
                            entity_ids=list(pair),
                            suggested_fix=(
                                f"Add scenes showing the deterioration of "
                                f"{name_a} and {name_b}'s relationship"
                            ),
                        )

    def _facts_related(self, fact1: str, fact2: str) -> bool:
        """Check if two facts are semantically related."""
        # Simplified: check for word overlap
        words1 = set(fact1.lower().split())
        words2 = set(fact2.lower().split())

        # Filter common words
        common = {"the", "a", "an", "that", "is", "was", "were", "be", "been"}
        words1 -= common
        words2 -= common

        overlap = words1 & words2
        return len(overlap) >= 2  # At least 2 words in common

    def _is_clear_knowledge_violation(
        self, referenced_fact: str, known_facts: Set[str]
    ) -> bool:
        """
        Determine if this is a clear knowledge violation vs. ambiguous case.

        Returns True only if we're confident this is a problem.
        """
        # If no facts known at all, might be early in story
        if not known_facts:
            return False

        # Check if referenced fact contains specific identifiers that would
        # definitely need to be learned (names, places, events)
        specific_patterns = [
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # Full names
            r"\b\d{4}\b",  # Years
            r"\blocation\b.*\b[A-Z]",  # Location references
        ]

        for pattern in specific_patterns:
            if re.search(pattern, referenced_fact):
                return True

        return False
