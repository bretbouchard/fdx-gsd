"""Slugline generation from scene metadata.

Generates screenplay sluglines in canonical format:
{INT_EXT}. {LOCATION} - {TIME}

Examples:
- INT. DINER - NIGHT
- EXT. CITY STREET - DAY
- INT./EXT. CAR - CONTINUOUS
"""
from typing import Any, Dict, List, Optional


# Valid time_of_day values per schema
VALID_TIMES = frozenset([
    "DAY", "NIGHT", "DAWN", "DUSK",
    "MORNING", "AFTERNOON", "EVENING",
    "CONTINUOUS", "LATER"
])

# Valid INT/EXT values per schema
VALID_INT_EXT = frozenset([
    "INT", "EXT", "INT./EXT", "EXT./INT"
])

# Default values
DEFAULT_TIME = "DAY"
DEFAULT_INT_EXT = "INT"


class SluglineGenerator:
    """Generates screenplay sluglines from scene entity metadata."""

    def __init__(self):
        """Initialize the slugline generator."""
        pass

    def generate_slugline(
        self,
        scene_entity: Dict[str, Any],
        storygraph: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a slugline from a scene entity.

        Args:
            scene_entity: Scene entity dict with attributes:
                - int_ext: INT, EXT, INT./EXT, or EXT./INT
                - location: Location name (raw string or reference)
                - time_of_day: DAY, NIGHT, etc.
            storygraph: Optional StoryGraph for location lookup

        Returns:
            Canonical slugline string: "{INT_EXT}. {LOCATION} - {TIME}"
        """
        attributes = scene_entity.get("attributes", {})

        # Get INT/EXT with validation
        int_ext = self._normalize_int_ext(attributes.get("int_ext"))

        # Get location with resolution
        raw_location = attributes.get("location", "")
        location = self._resolve_location(raw_location, storygraph)

        # Get time of day with validation
        time_of_day = self._normalize_time(attributes.get("time_of_day"))

        # Format: INT. LOCATION - TIME
        return f"{int_ext}. {location} - {time_of_day}"

    def _normalize_int_ext(self, value: Optional[str]) -> str:
        """Normalize INT/EXT value to canonical form."""
        if not value:
            return DEFAULT_INT_EXT

        # Uppercase and strip
        normalized = value.upper().strip()

        # Handle variants
        if normalized in ("INT.", "INT", "INTERIOR", "I"):
            return "INT"
        elif normalized in ("EXT.", "EXT", "EXTERIOR", "E"):
            return "EXT"
        elif normalized in ("INT./EXT.", "INT/EXT", "I/E", "INT/EXT."):
            return "INT./EXT"
        elif normalized in ("EXT./INT.", "EXT/INT", "E/I", "EXT/INT."):
            return "EXT./INT"

        # Return as-is if valid, else default
        return normalized if normalized in VALID_INT_EXT else DEFAULT_INT_EXT

    def _normalize_time(self, value: Optional[str]) -> str:
        """Normalize time_of_day value to canonical form."""
        if not value:
            return DEFAULT_TIME

        # Uppercase and strip
        normalized = value.upper().strip()

        # Handle common variants
        time_mappings = {
            "DAYTIME": "DAY",
            "NIGHTTIME": "NIGHT",
            "MORN": "MORNING",
            "AFT": "AFTERNOON",
            "EVE": "EVENING",
            "DUSK/DAWN": "DUSK",
            "DAWN/DUSK": "DAWN",
            "CONT": "CONTINUOUS",
            "CONT'D": "CONTINUOUS",
            "LATER THAT DAY": "LATER",
            "LATER THAT NIGHT": "LATER",
        }

        if normalized in time_mappings:
            return time_mappings[normalized]

        # Return as-is if valid, else default
        return normalized if normalized in VALID_TIMES else DEFAULT_TIME

    def _resolve_location(
        self,
        raw_location: str,
        storygraph: Optional[Dict[str, Any]]
    ) -> str:
        """
        Resolve location name from storygraph entities.

        Args:
            raw_location: Raw location string from scene
            storygraph: StoryGraph dict with entities

        Returns:
            Canonical location name (uppercase for determinism)
        """
        if not raw_location:
            return "UNKNOWN LOCATION"

        # If no storygraph, return raw location
        if not storygraph:
            return raw_location.upper()

        # Look for matching location entity
        entities = storygraph.get("entities", [])
        for entity in entities:
            if entity.get("type") != "location":
                continue

            # Check name match
            if entity.get("name", "").upper() == raw_location.upper():
                return entity.get("name", raw_location).upper()

            # Check aliases
            aliases = entity.get("aliases", [])
            for alias in aliases:
                if alias.upper() == raw_location.upper():
                    return entity.get("name", raw_location).upper()

        # No match found, return raw location
        return raw_location.upper()

    def generate_slugline_from_boundary(
        self,
        int_ext: Optional[str],
        location: Optional[str],
        time_of_day: Optional[str],
        storygraph: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate slugline from individual components.

        Convenience method for when you have components rather than
        a full scene entity dict.

        Args:
            int_ext: INT/EXT indicator
            location: Location name
            time_of_day: Time of day
            storygraph: Optional StoryGraph for location lookup

        Returns:
            Canonical slugline string
        """
        scene_entity = {
            "attributes": {
                "int_ext": int_ext or DEFAULT_INT_EXT,
                "location": location or "",
                "time_of_day": time_of_day or DEFAULT_TIME
            }
        }
        return self.generate_slugline(scene_entity, storygraph)


def generate_slugline(
    scene_entity: Dict[str, Any],
    storygraph: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to generate a slugline.

    Args:
        scene_entity: Scene entity dict
        storygraph: Optional StoryGraph for location lookup

    Returns:
        Canonical slugline string
    """
    generator = SluglineGenerator()
    return generator.generate_slugline(scene_entity, storygraph)
