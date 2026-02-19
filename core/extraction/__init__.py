"""Entity extraction module for FDX GSD.

This module provides lightweight entity extraction (no ML) per ADR-0002.

Extractors:
- CharacterExtractor: Extract character names from text
- LocationExtractor: Extract location names from text
- SceneExtractor: Detect scene boundaries

Usage:
    from core.extraction import CharacterExtractor, LocationExtractor, SceneExtractor

    char_extractor = CharacterExtractor()
    characters = char_extractor.extract_from_file(Path("inbox/notes.md"))

    scene_extractor = SceneExtractor()
    boundaries = scene_extractor.detect_boundaries(content)
"""
from .base import BaseExtractor, ExtractionCandidate
from .patterns import (
    ExtractionPattern,
    CHARACTER_PATTERNS,
    LOCATION_PATTERNS,
    SCENE_PATTERNS,
    is_valid_character_name,
    is_valid_location_name,
    normalize_name,
    get_time_of_day,
    get_int_ext,
)
from .characters import CharacterExtractor, extract_characters
from .locations import LocationExtractor, extract_locations
from .scenes import SceneExtractor, SceneBoundary, detect_scenes


__all__ = [
    # Base
    "BaseExtractor",
    "ExtractionCandidate",
    "ExtractionPattern",

    # Patterns
    "CHARACTER_PATTERNS",
    "LOCATION_PATTERNS",
    "SCENE_PATTERNS",
    "is_valid_character_name",
    "is_valid_location_name",
    "normalize_name",
    "get_time_of_day",
    "get_int_ext",

    # Extractors
    "CharacterExtractor",
    "LocationExtractor",
    "SceneExtractor",

    # Convenience functions
    "extract_characters",
    "extract_locations",
    "detect_scenes",

    # Scene types
    "SceneBoundary",
]
