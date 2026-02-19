"""Beat extraction from narrative text.

Extracts action beats and dialogue from screenplay text between
scene boundaries. Each extracted beat becomes a paragraph with
proper evidence linking.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class Paragraph:
    """Represents a screenplay paragraph."""
    type: str  # action, character, dialogue, parenthetical
    text: str
    evidence_ids: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "type": self.type,
            "text": self.text,
        }
        if self.evidence_ids:
            result["evidence_ids"] = sorted(set(self.evidence_ids))
        if self.meta:
            result["meta"] = self.meta
        return result


class BeatExtractor:
    """Extracts action beats and dialogue from screenplay text."""

    # Pattern for character names (ALL CAPS at start of line)
    CHARACTER_PATTERN = re.compile(r'^([A-Z][A-Z\s\-\'\.]+)(\s*\([^)]*\))?$')

    # Pattern for parentheticals
    PARENTHETICAL_PATTERN = re.compile(r'^\s*\(([^)]+)\)\s*$')

    # Patterns to skip (not action or dialogue)
    SKIP_PATTERNS = [
        re.compile(r'^(INT\.?|EXT\.?|INT\./EXT\.?|EXT\./INT\.?)\s+', re.IGNORECASE),  # Sluglines
        re.compile(r'^(FADE|CUT|DISSOLVE|SMASH|MATCH)\s+(IN|TO|OUT|CUT)', re.IGNORECASE),  # Transitions
        re.compile(r'^\[.*\]$', re.IGNORECASE),  # Production notes
        re.compile(r'^\^([a-z0-9_]+)$'),  # Block refs
    ]

    def __init__(self, known_characters: Optional[List[str]] = None):
        """
        Initialize the beat extractor.

        Args:
            known_characters: List of known character names for dialogue detection
        """
        self.known_characters = set(c.upper() for c in (known_characters or []))

    def extract_beats(
        self,
        content: str,
        scene_start_line: int,
        scene_end_line: int,
        block_refs: Dict[int, str]
    ) -> List[Dict[str, Any]]:
        """
        Extract action paragraphs between scene boundaries.

        Args:
            content: Full text content
            scene_start_line: Line number where scene starts (1-indexed)
            scene_end_line: Line number where scene ends (1-indexed, exclusive)
            block_refs: Dict mapping line numbers to block reference IDs

        Returns:
            List of paragraph dicts with type="action"
        """
        paragraphs = []
        lines = content.split("\n")

        # Get lines within scene boundaries
        start_idx = max(0, scene_start_line - 1)  # Convert to 0-indexed
        end_idx = min(len(lines), scene_end_line) if scene_end_line > 0 else len(lines)

        current_beat_lines: List[str] = []
        current_evidence_ids: Set[str] = set()

        for i in range(start_idx, end_idx):
            line = lines[i]
            line_num = i + 1  # 1-indexed for block refs

            # Skip empty lines - flush current beat
            if not line.strip():
                if current_beat_lines:
                    paragraphs.append(self._create_action_paragraph(
                        current_beat_lines,
                        current_evidence_ids
                    ))
                    current_beat_lines = []
                    current_evidence_ids = set()
                continue

            # Skip sluglines and transitions
            if self._should_skip(line):
                if current_beat_lines:
                    paragraphs.append(self._create_action_paragraph(
                        current_beat_lines,
                        current_evidence_ids
                    ))
                    current_beat_lines = []
                    current_evidence_ids = set()
                continue

            # Skip character names and dialogue (handled separately)
            if self._is_character_name(line):
                if current_beat_lines:
                    paragraphs.append(self._create_action_paragraph(
                        current_beat_lines,
                        current_evidence_ids
                    ))
                    current_beat_lines = []
                    current_evidence_ids = set()
                continue

            # This is action text - accumulate
            current_beat_lines.append(line.strip())
            if line_num in block_refs:
                current_evidence_ids.add(block_refs[line_num])

        # Flush any remaining beat
        if current_beat_lines:
            paragraphs.append(self._create_action_paragraph(
                current_beat_lines,
                current_evidence_ids
            ))

        return paragraphs

    def extract_dialogue(
        self,
        content: str,
        character_names: List[str],
        block_refs: Dict[int, str],
        scene_start_line: int = 0,
        scene_end_line: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Extract dialogue blocks from text.

        Args:
            content: Full text content
            character_names: Known character names
            block_refs: Dict mapping line numbers to block reference IDs
            scene_start_line: Optional scene boundary (1-indexed)
            scene_end_line: Optional scene boundary (-1 for end of file)

        Returns:
            List of paragraph dicts with type="character" and "dialogue"
        """
        paragraphs = []
        lines = content.split("\n")

        # Normalize character names for matching
        known_chars = set(c.upper().strip() for c in character_names)
        self.known_characters.update(known_chars)

        # Get lines within scene boundaries
        start_idx = max(0, scene_start_line - 1) if scene_start_line > 0 else 0
        end_idx = min(len(lines), scene_end_line) if scene_end_line > 0 else len(lines)

        i = start_idx
        while i < end_idx:
            line = lines[i]
            line_stripped = line.strip()

            # Check for character name
            char_match = self._is_character_name(line_stripped)
            if char_match:
                char_name = char_match.group(1).strip()
                extension = char_match.group(2) if char_match.lastindex and char_match.lastindex >= 2 else ""

                # Get evidence ID for character line
                char_evidence = block_refs.get(i + 1, "")

                # Add character paragraph
                char_paragraph = {
                    "type": "character",
                    "text": char_name + (extension if extension else ""),
                    "evidence_ids": [char_evidence] if char_evidence else []
                }
                if extension:
                    char_paragraph["meta"] = {"extension": extension.strip()}
                paragraphs.append(char_paragraph)

                # Collect dialogue lines
                dialogue_lines: List[str] = []
                dialogue_evidence: Set[str] = set()
                i += 1

                while i < end_idx:
                    next_line = lines[i].strip()

                    # Empty line - might be more dialogue, continue
                    if not next_line:
                        # Check if next non-empty is new character
                        j = i + 1
                        while j < end_idx and not lines[j].strip():
                            j += 1
                        if j < end_idx and self._is_character_name(lines[j].strip()):
                            break
                        i += 1
                        continue

                    # Parenthetical
                    paren_match = self.PARENTHETICAL_PATTERN.match(next_line)
                    if paren_match:
                        # Add parenthetical as separate paragraph
                        paren_evidence = block_refs.get(i + 1, "")
                        paragraphs.append({
                            "type": "parenthetical",
                            "text": paren_match.group(1),
                            "evidence_ids": [paren_evidence] if paren_evidence else []
                        })
                        i += 1
                        continue

                    # New character name - stop dialogue
                    if self._is_character_name(next_line):
                        break

                    # Check for slugline/transition - stop dialogue
                    if self._should_skip(next_line):
                        break

                    # This is dialogue text
                    dialogue_lines.append(next_line)
                    if i + 1 in block_refs:
                        dialogue_evidence.add(block_refs[i + 1])
                    i += 1

                # Add dialogue paragraph
                if dialogue_lines:
                    paragraphs.append({
                        "type": "dialogue",
                        "text": " ".join(dialogue_lines),
                        "evidence_ids": sorted(dialogue_evidence) if dialogue_evidence else []
                    })

                continue

            i += 1

        return paragraphs

    def extract_all(
        self,
        content: str,
        scene_start_line: int,
        scene_end_line: int,
        block_refs: Dict[int, str],
        character_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract both action beats and dialogue from scene content.

        This is the main entry point for extracting all paragraphs
        from a scene in proper screenplay order.

        Args:
            content: Full text content
            scene_start_line: Line number where scene starts (1-indexed)
            scene_end_line: Line number where scene ends (1-indexed, exclusive)
            block_refs: Dict mapping line numbers to block reference IDs
            character_names: Optional list of known character names

        Returns:
            List of paragraph dicts in screenplay order
        """
        paragraphs = []
        lines = content.split("\n")

        # Normalize character names
        known_chars = set(c.upper().strip() for c in (character_names or []))
        self.known_characters.update(known_chars)

        # Get lines within scene boundaries
        start_idx = max(0, scene_start_line - 1)
        end_idx = min(len(lines), scene_end_line) if scene_end_line > 0 else len(lines)

        current_action_lines: List[str] = []
        current_action_evidence: Set[str] = set()

        i = start_idx
        while i < end_idx:
            line = lines[i]
            line_stripped = line.strip()
            line_num = i + 1

            # Empty line - flush action
            if not line_stripped:
                if current_action_lines:
                    paragraphs.append(self._create_action_paragraph(
                        current_action_lines,
                        current_action_evidence
                    ))
                    current_action_lines = []
                    current_action_evidence = set()
                i += 1
                continue

            # Skip sluglines and transitions
            if self._should_skip(line_stripped):
                if current_action_lines:
                    paragraphs.append(self._create_action_paragraph(
                        current_action_lines,
                        current_action_evidence
                    ))
                    current_action_lines = []
                    current_action_evidence = set()
                i += 1
                continue

            # Check for character name (start of dialogue block)
            char_match = self._is_character_name(line_stripped)
            if char_match:
                # Flush current action
                if current_action_lines:
                    paragraphs.append(self._create_action_paragraph(
                        current_action_lines,
                        current_action_evidence
                    ))
                    current_action_lines = []
                    current_action_evidence = set()

                # Extract character + dialogue block
                char_name = char_match.group(1).strip()
                extension = char_match.group(2) if char_match.lastindex and char_match.lastindex >= 2 else ""

                char_evidence = block_refs.get(line_num, "")
                char_paragraph = {
                    "type": "character",
                    "text": char_name + (extension if extension else ""),
                    "evidence_ids": [char_evidence] if char_evidence else []
                }
                if extension:
                    char_paragraph["meta"] = {"extension": extension.strip()}
                paragraphs.append(char_paragraph)

                # Collect dialogue and parentheticals
                dialogue_lines: List[str] = []
                dialogue_evidence: Set[str] = set()
                i += 1

                while i < end_idx:
                    next_line = lines[i].strip()
                    next_line_num = i + 1

                    # Empty line - check for continuation
                    if not next_line:
                        j = i + 1
                        while j < end_idx and not lines[j].strip():
                            j += 1
                        if j < end_idx and self._is_character_name(lines[j].strip()):
                            break
                        i += 1
                        continue

                    # Parenthetical
                    paren_match = self.PARENTHETICAL_PATTERN.match(next_line)
                    if paren_match:
                        # Save current dialogue if any
                        if dialogue_lines:
                            paragraphs.append({
                                "type": "dialogue",
                                "text": " ".join(dialogue_lines),
                                "evidence_ids": sorted(dialogue_evidence)
                            })
                            dialogue_lines = []
                            dialogue_evidence = set()

                        # Add parenthetical
                        paren_evidence = block_refs.get(next_line_num, "")
                        paragraphs.append({
                            "type": "parenthetical",
                            "text": paren_match.group(1),
                            "evidence_ids": [paren_evidence] if paren_evidence else []
                        })
                        i += 1
                        continue

                    # New character - stop
                    if self._is_character_name(next_line):
                        break

                    # Slugline/transition - stop
                    if self._should_skip(next_line):
                        break

                    # Dialogue text
                    dialogue_lines.append(next_line)
                    if next_line_num in block_refs:
                        dialogue_evidence.add(block_refs[next_line_num])
                    i += 1

                # Add final dialogue
                if dialogue_lines:
                    paragraphs.append({
                        "type": "dialogue",
                        "text": " ".join(dialogue_lines),
                        "evidence_ids": sorted(dialogue_evidence)
                    })

                continue

            # This is action text
            current_action_lines.append(line_stripped)
            if line_num in block_refs:
                current_action_evidence.add(block_refs[line_num])
            i += 1

        # Flush remaining action
        if current_action_lines:
            paragraphs.append(self._create_action_paragraph(
                current_action_lines,
                current_action_evidence
            ))

        return paragraphs

    def _create_action_paragraph(
        self,
        lines: List[str],
        evidence_ids: Set[str]
    ) -> Dict[str, Any]:
        """Create an action paragraph from lines."""
        return {
            "type": "action",
            "text": " ".join(lines),
            "evidence_ids": sorted(evidence_ids) if evidence_ids else []
        }

    def _should_skip(self, line: str) -> bool:
        """Check if line should be skipped (not content)."""
        for pattern in self.SKIP_PATTERNS:
            if pattern.match(line):
                return True
        return False

    def _is_character_name(self, line: str) -> Optional[re.Match]:
        """
        Check if line is a character name.

        Returns match object if it is, None otherwise.
        """
        # Must be uppercase with possible extension
        match = self.CHARACTER_PATTERN.match(line)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            if name in ("INT", "EXT", "THE", "A", "AN"):
                return None
            # Check against known characters if available
            if self.known_characters and name.upper() not in self.known_characters:
                # Still return match but with lower confidence
                pass
            return match
        return None


def extract_beats(
    content: str,
    scene_start_line: int,
    scene_end_line: int,
    block_refs: Dict[int, str]
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract action beats.

    Args:
        content: Full text content
        scene_start_line: Line number where scene starts (1-indexed)
        scene_end_line: Line number where scene ends (1-indexed, exclusive)
        block_refs: Dict mapping line numbers to block reference IDs

    Returns:
        List of paragraph dicts with type="action"
    """
    extractor = BeatExtractor()
    return extractor.extract_beats(content, scene_start_line, scene_end_line, block_refs)
