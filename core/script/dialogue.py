"""Dialogue formatting and character resolution.

Detects dialogue in narrative text, formats it according to screenplay
standards (character names centered, dialogue indented), and links
speakers to canonical character entities from StoryGraph.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CharacterMatch:
    """Result of speaker detection."""
    entity: Dict[str, Any]
    confidence: float
    match_type: str  # exact, case_insensitive, alias


class DialogueFormatter:
    """Formats dialogue with character resolution."""

    # Pattern for parentheticals at start of dialogue
    PARENTHETICAL_START_PATTERN = re.compile(r'^\s*\(([^)]+)\)\s*(.*)$')

    # Minimum confidence threshold for auto-matching
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, character_entities: Optional[List[Dict]] = None):
        """
        Initialize the dialogue formatter.

        Args:
            character_entities: List of known character entities from StoryGraph
                               Each entity should have: id, name, aliases
        """
        self.character_entities = character_entities or []
        self._build_lookup_index()

    def _build_lookup_index(self) -> None:
        """Build fast lookup index for character matching."""
        # Index: normalized_name -> (entity, match_type, confidence)
        self._lookup: Dict[str, Tuple[Dict, str, float]] = {}

        for entity in self.character_entities:
            entity_id = entity.get("id", "")
            name = entity.get("name", "")

            if not name:
                continue

            # Exact match (highest confidence)
            self._lookup[name.upper()] = (entity, "exact", 1.0)

            # Case-insensitive match
            self._lookup[name.lower()] = (entity, "case_insensitive", 0.95)

            # Alias matches
            for alias in entity.get("aliases", []):
                if alias:
                    self._lookup[alias.upper()] = (entity, "alias", 0.9)
                    self._lookup[alias.lower()] = (entity, "alias", 0.85)

    def detect_speaker(
        self,
        line: str,
        context: Optional[List[str]] = None
    ) -> Optional[CharacterMatch]:
        """
        Detect if a line is a character name and match to known entity.

        Args:
            line: The line to check (potential character name)
            context: Surrounding lines for context (unused but for future enhancement)

        Returns:
            CharacterMatch if matched, None otherwise
        """
        line_stripped = line.strip()

        # Check if line looks like a character cue
        # Character names are typically ALL CAPS, possibly with extension
        if not self._is_character_cue(line_stripped):
            return None

        # Extract name without extension (V.O., O.S., CONT'D, etc.)
        name = self._extract_name(line_stripped)

        # Try lookup
        if name.upper() in self._lookup:
            entity, match_type, confidence = self._lookup[name.upper()]
            return CharacterMatch(
                entity=entity,
                confidence=confidence,
                match_type=match_type
            )

        if name.lower() in self._lookup:
            entity, match_type, confidence = self._lookup[name.lower()]
            return CharacterMatch(
                entity=entity,
                confidence=confidence,
                match_type=match_type
            )

        # No match found
        # Below threshold - could queue for disambiguation in future
        return None

    def _is_character_cue(self, line: str) -> bool:
        """Check if line looks like a character cue."""
        if not line:
            return False

        # Must have at least 2 characters
        if len(line) < 2:
            return False

        # Check it's mostly uppercase (allowing for extensions)
        # Character cues are typically: NAME or NAME (V.O.) or NAME (O.S.)
        upper_ratio = sum(1 for c in line if c.isupper()) / max(len(line), 1)

        # At least 50% uppercase (allows for extensions like "(V.O.)")
        if upper_ratio < 0.5:
            return False

        # Exclude common false positives
        false_positives = {"INT", "EXT", "THE", "A", "AN", "IN", "ON", "AT"}
        first_word = line.split()[0] if line.split() else ""
        if first_word.upper() in false_positives:
            return False

        return True

    def _extract_name(self, line: str) -> str:
        """Extract character name without extension."""
        # Remove extension like (V.O.), (O.S.), (CONT'D)
        match = re.match(r'^([A-Z][A-Z\s\-\'\.]+?)(?:\s*\([^)]*\))?$', line)
        if match:
            return match.group(1).strip()
        return line.strip()

    def extract_parenthetical(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Detect and extract parenthetical at start of dialogue.

        Args:
            text: Dialogue text that may start with parenthetical

        Returns:
            Tuple of (remaining_text, parenthetical or None)
        """
        match = self.PARENTHETICAL_START_PATTERN.match(text)
        if match:
            parenthetical = match.group(1)
            remaining = match.group(2).strip()
            return (remaining, parenthetical)
        return (text, None)

    def format_dialogue_block(
        self,
        speaker: CharacterMatch,
        lines: List[str],
        evidence_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Format a complete dialogue block.

        Args:
            speaker: Matched character
            lines: Dialogue lines (may include parentheticals)
            evidence_ids: Evidence IDs for this block

        Returns:
            List of paragraph dicts: character, optional parenthetical, dialogue
        """
        paragraphs = []
        entity = speaker.entity

        # Character cue paragraph
        char_paragraph = {
            "type": "character",
            "text": entity.get("name", "UNKNOWN"),
            "evidence_ids": evidence_ids[:1] if evidence_ids else [],
            "meta": {
                "character_id": entity.get("id", ""),
                "match_confidence": speaker.confidence,
                "match_type": speaker.match_type
            }
        }
        paragraphs.append(char_paragraph)

        # Process dialogue lines
        dialogue_text = " ".join(lines)

        # Check for parenthetical at start
        remaining, parenthetical = self.extract_parenthetical(dialogue_text)

        if parenthetical:
            # Add parenthetical paragraph
            paragraphs.append({
                "type": "parenthetical",
                "text": parenthetical,
                "evidence_ids": evidence_ids[1:2] if len(evidence_ids) > 1 else []
            })

        # Add dialogue paragraph
        if remaining.strip():
            paragraphs.append({
                "type": "dialogue",
                "text": remaining.strip(),
                "evidence_ids": evidence_ids
            })

        return paragraphs

    def add_character_entity(self, entity: Dict[str, Any]) -> None:
        """
        Add a character entity to the lookup index.

        Args:
            entity: Character entity with id, name, aliases
        """
        self.character_entities.append(entity)

        name = entity.get("name", "")
        if not name:
            return

        # Add to lookup
        self._lookup[name.upper()] = (entity, "exact", 1.0)
        self._lookup[name.lower()] = (entity, "case_insensitive", 0.95)

        for alias in entity.get("aliases", []):
            if alias:
                self._lookup[alias.upper()] = (entity, "alias", 0.9)
                self._lookup[alias.lower()] = (entity, "alias", 0.85)


def format_dialogue(
    speaker_match: CharacterMatch,
    lines: List[str],
    evidence_ids: List[str]
) -> List[Dict[str, Any]]:
    """
    Convenience function to format dialogue.

    Args:
        speaker_match: Matched character
        lines: Dialogue lines
        evidence_ids: Evidence IDs

    Returns:
        List of paragraph dicts
    """
    formatter = DialogueFormatter()
    return formatter.format_dialogue_block(speaker_match, lines, evidence_ids)


def detect_speaker(
    line: str,
    character_entities: List[Dict],
    context: Optional[List[str]] = None
) -> Optional[CharacterMatch]:
    """
    Convenience function to detect speaker.

    Args:
        line: Line to check
        character_entities: Known character entities
        context: Surrounding context

    Returns:
        CharacterMatch if found, None otherwise
    """
    formatter = DialogueFormatter(character_entities)
    return formatter.detect_speaker(line, context)
