"""Location extraction (CAN-02).

Extracts location names from screenplay text using lightweight patterns.
Per ADR-0002: No ML library, interactive disambiguation.
"""
from typing import Any, Dict, List, Optional

from .base import BaseExtractor, ExtractionCandidate
from .patterns import (
    LOCATION_PATTERNS,
    is_valid_location_name,
    normalize_name,
    get_time_of_day,
    get_int_ext,
)


class LocationExtractor(BaseExtractor):
    """Extract location entities from text."""

    def __init__(self):
        super().__init__(LOCATION_PATTERNS)
        self._known_aliases: Dict[str, str] = {}

    @property
    def entity_type(self) -> str:
        return "location"

    def is_valid(self, text: str) -> bool:
        """Check if text is a valid location name."""
        return is_valid_location_name(text)

    def normalize(self, text: str) -> str:
        """Normalize location name to canonical form."""
        return normalize_name(text)

    def extract_metadata(self, match: Any, line: str, pattern: Any = None) -> Dict[str, Any]:
        """Extract location-specific metadata."""
        metadata = {}

        # Extract time of day from slugline
        time = get_time_of_day(line)
        if time:
            metadata["time_of_day"] = time

        # Extract INT/EXT
        int_ext = get_int_ext(line)
        if int_ext:
            metadata["int_ext"] = int_ext

        # Check if this came from a slugline pattern
        if pattern and "slugline" in pattern.name:
            metadata["from_slugline"] = True
            # Extract location name from slugline (group 2 in pattern)
            if match.lastindex and match.lastindex >= 2:
                metadata["location_name"] = match.group(2).strip()

        return metadata

    def set_known_aliases(self, aliases: Dict[str, str]):
        """Set known aliases from Confucius memory."""
        self._known_aliases = aliases

    def check_known_alias(self, name: str) -> Optional[str]:
        """Check if name is a known alias."""
        normalized = self.normalize(name)
        return self._known_aliases.get(normalized.lower())


def extract_locations(
    text: str,
    source_file: str = "",
    line_number: int = 0,
    block_ref: str = "",
    known_aliases: Dict[str, str] = None
) -> List[ExtractionCandidate]:
    """
    Convenience function to extract locations from text.

    Args:
        text: Text to extract from
        source_file: Source file path
        line_number: Line number
        block_ref: Evidence block reference
        known_aliases: Known alias mappings

    Returns:
        List of location candidates
    """
    extractor = LocationExtractor()
    if known_aliases:
        extractor.set_known_aliases(known_aliases)

    return extractor.extract_from_line(
        line=text,
        source_file=source_file,
        line_number=line_number,
        block_ref=block_ref,
    )
