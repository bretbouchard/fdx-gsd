"""Character extraction (CAN-01).

Extracts character names from screenplay text using lightweight patterns.
Per ADR-0002: No ML library, interactive disambiguation.
"""
from typing import Any, Dict, List

from .base import BaseExtractor, ExtractionCandidate
from .patterns import (
    CHARACTER_PATTERNS,
    CHARACTER_EXCLUSIONS,
    is_valid_character_name,
    normalize_name,
)


class CharacterExtractor(BaseExtractor):
    """Extract character entities from text."""

    def __init__(self):
        super().__init__(CHARACTER_PATTERNS)
        self._known_aliases: Dict[str, str] = {}  # alias -> canonical_id

    @property
    def entity_type(self) -> str:
        return "character"

    def is_valid(self, text: str) -> bool:
        """Check if text is a valid character name."""
        return is_valid_character_name(text)

    def normalize(self, text: str) -> str:
        """Normalize character name to canonical form."""
        return normalize_name(text)

    def extract_metadata(self, match: Any, line: str, pattern: Any = None) -> Dict[str, Any]:
        """Extract character-specific metadata."""
        metadata = {}

        # Check if this is in dialogue context (ALL CAPS pattern)
        upper_line = line.upper()
        if match.group(0).isupper() and len(match.group(0)) > 1:
            metadata["in_dialogue"] = True

        # Check for role reference pattern (THE WAITER, A MAN)
        if pattern and "role_reference" in pattern.name:
            metadata["is_role"] = True

        # Check for character with extension (V.O., O.S., CONT'D)
        if pattern and "character_with_extension" in pattern.name:
            # Group 1 is the name, Group 2 is the extension
            if match.lastindex >= 2:
                extension = match.group(2).upper().replace('.', '')
                # Normalize extension
                if extension in ('VO', 'V O', 'VOICE OVER'):
                    metadata["extension"] = "V.O."
                elif extension in ('OS', 'O S', 'OFF SCREEN'):
                    metadata["extension"] = "O.S."
                elif extension in ('OC', 'O C'):
                    metadata["extension"] = "O.C."
                elif extension in ("CONT'D", 'CONTD'):
                    metadata["extension"] = "CONT'D"
                else:
                    metadata["extension"] = match.group(2)

                metadata["has_extension"] = True

        return metadata

    def set_known_aliases(self, aliases: Dict[str, str]):
        """
        Set known aliases from Confucius memory.

        Args:
            aliases: Dict mapping alias -> canonical_id
        """
        self._known_aliases = aliases

    def check_known_alias(self, name: str) -> str | None:
        """
        Check if name is a known alias.

        Args:
            name: Name to check

        Returns:
            Canonical ID if known, None otherwise
        """
        normalized = self.normalize(name)
        return self._known_aliases.get(normalized.lower())


def extract_characters(
    text: str,
    source_file: str = "",
    line_number: int = 0,
    block_ref: str = "",
    known_aliases: Dict[str, str] = None
) -> List[ExtractionCandidate]:
    """
    Convenience function to extract characters from text.

    Args:
        text: Text to extract from
        source_file: Source file path
        line_number: Line number
        block_ref: Evidence block reference
        known_aliases: Known alias mappings

    Returns:
        List of character candidates
    """
    extractor = CharacterExtractor()
    if known_aliases:
        extractor.set_known_aliases(known_aliases)

    return extractor.extract_from_line(
        line=text,
        source_file=source_file,
        line_number=line_number,
        block_ref=block_ref,
    )
