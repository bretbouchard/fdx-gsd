"""Regex patterns for entity extraction.

Per ADR-0002: Lightweight extraction without ML.
These patterns are intentionally simple and conservative.
"""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExtractionPattern:
    """A pattern for extracting entities from text."""
    name: str
    pattern: re.Pattern
    entity_type: str
    confidence_base: float
    description: str


# Character extraction patterns
CHARACTER_PATTERNS = [
    # ALL CAPS names in dialogue (e.g., FOX, SARAH)
    ExtractionPattern(
        name="dialogue_caps",
        pattern=re.compile(r'\b([A-Z]{2,}(?:\s+[A-Z]{2,})*)\b'),
        entity_type="character",
        confidence_base=0.9,
        description="Character names in ALL CAPS (dialogue style)"
    ),

    # Proper nouns in action lines (e.g., Fox enters, Sarah says)
    ExtractionPattern(
        name="action_proper_noun",
        pattern=re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'),
        entity_type="character",
        confidence_base=0.7,
        description="Proper noun capitalized names in action"
    ),

    # Role references (e.g., THE WAITER, A MAN, OLD WOMAN)
    ExtractionPattern(
        name="role_reference",
        pattern=re.compile(r'\b(THE|A|AN)\s+([A-Z][A-Z\s]+?)\b'),
        entity_type="character",
        confidence_base=0.6,
        description="Role-based character references"
    ),

    # Possessive references (e.g., Sarah's apartment, his jacket)
    ExtractionPattern(
        name="possessive_name",
        pattern=re.compile(r"\b([A-Z][a-z]+)'s\b"),
        entity_type="character",
        confidence_base=0.75,
        description="Names in possessive form"
    ),
]


# Location extraction patterns
LOCATION_PATTERNS = [
    # Standard slugline (INT./EXT. LOCATION - TIME)
    ExtractionPattern(
        name="slugline",
        pattern=re.compile(
            r'(INT\.?|EXT\.?|INT\./EXT\.?|I/E)\s*\.?\s*([A-Z][A-Za-z\s\-\']+?)\s*-\s*(DAY|NIGHT|DAWN|DUSK|MORNING|AFTERNOON|EVENING|CONTINUOUS|LATER)',
            re.IGNORECASE
        ),
        entity_type="location",
        confidence_base=0.95,
        description="Standard screenplay slugline"
    ),

    # "the [place]" references
    ExtractionPattern(
        name="the_place",
        pattern=re.compile(r'\bthe\s+([a-z]+(?:\s+[a-z]+)?)\b', re.IGNORECASE),
        entity_type="location",
        confidence_base=0.5,
        description="Lowercase location references with 'the'"
    ),

    # Named locations (e.g., Joe's Diner, The Rusty Anchor)
    ExtractionPattern(
        name="named_location",
        pattern=re.compile(r"\b([A-Z][a-z]+(?:'s)?\s+[A-Z][a-z]+)\b"),
        entity_type="location",
        confidence_base=0.7,
        description="Multi-word named locations"
    ),

    # Location with descriptor (e.g., back booth, front door)
    ExtractionPattern(
        name="location_descriptor",
        pattern=re.compile(r'\b(back|front|side|main|north|south|east|west)\s+(booth|door|room|entrance|exit|counter|table)\b', re.IGNORECASE),
        entity_type="location",
        confidence_base=0.6,
        description="Descriptive location references"
    ),
]


# Scene detection patterns
SCENE_PATTERNS = [
    # Standard slugline (also triggers scene boundary)
    ExtractionPattern(
        name="scene_slugline",
        pattern=re.compile(
            r'(INT\.?|EXT\.?|INT\./EXT\.?|I/E)\s*\.?\s*[A-Z][A-Za-z\s\-\']+?\s*-\s*(DAY|NIGHT|DAWN|DUSK|MORNING|AFTERNOON|EVENING|CONTINUOUS|LATER)',
            re.IGNORECASE
        ),
        entity_type="scene",
        confidence_base=0.95,
        description="Scene slugline"
    ),

    # Scene transitions
    ExtractionPattern(
        name="scene_transition",
        pattern=re.compile(
            r'\b(CUT TO:|FADE TO:|FADE OUT|DISSOLVE TO:|SMASH CUT:|TIME CUT:|MATCH CUT:)\b',
            re.IGNORECASE
        ),
        entity_type="scene",
        confidence_base=0.9,
        description="Scene transition markers"
    ),

    # Scene transitions (without trailing colon in word boundary)
    ExtractionPattern(
        name="scene_transition_alt",
        pattern=re.compile(
            r'^(CUT TO:|FADE TO:|FADE OUT\.|DISSOLVE TO:|SMASH CUT:|TIME CUT:|MATCH CUT:)$',
            re.IGNORECASE
        ),
        entity_type="scene",
        confidence_base=0.95,
        description="Scene transition markers (standalone)"
    ),

    # Time jumps
    ExtractionPattern(
        name="time_jump",
        pattern=re.compile(
            r'\b(LATER|MEANWHILE|BACK TO|THE NEXT DAY|THE NEXT MORNING|THE NEXT NIGHT|MOMENTS LATER|A FEW MINUTES LATER|HOURS LATER)\b',
            re.IGNORECASE
        ),
        entity_type="scene",
        confidence_base=0.7,
        description="Time-based scene transitions"
    ),
]


# Common words to exclude from character extraction
CHARACTER_EXCLUSIONS = {
    # Common words that might match patterns
    'THE', 'A', 'AN', 'AND', 'OR', 'BUT', 'IF', 'THEN', 'ELSE',
    'INT', 'EXT', 'DAY', 'NIGHT', 'DAWN', 'DUSK', 'MORNING', 'AFTERNOON', 'EVENING',
    'CONTINUOUS', 'LATER', 'CUT', 'FADE', 'DISSOLVE', 'SMASH', 'TIME', 'MATCH',
    'I', 'ME', 'MY', 'YOU', 'YOUR', 'HE', 'HIM', 'HIS', 'SHE', 'HER', 'IT', 'ITS',
    'WE', 'US', 'OUR', 'THEY', 'THEM', 'THEIR',
    # Common adjectives that might look like names
    'GOOD', 'BAD', 'OLD', 'NEW', 'BIG', 'SMALL', 'LONG', 'SHORT',
    # Screenplay terms
    'V.O', 'O.S', 'O.C', 'CONT\'D', 'MORE',
}

# Location exclusions
LOCATION_EXCLUSIONS = {
    'THE', 'A', 'AN', 'AND', 'OR', 'BUT',
    'INT', 'EXT', 'DAY', 'NIGHT',
}


def is_valid_character_name(name: str) -> bool:
    """Check if a name is a valid character candidate."""
    upper = name.upper().strip()

    # Check exclusions
    if upper in CHARACTER_EXCLUSIONS:
        return False

    # Must have at least one letter
    if not any(c.isalpha() for c in name):
        return False

    # Not just single character (unless it's an initial like "J.")
    if len(name) == 1 and name.isalpha():
        return False

    return True


def is_valid_location_name(name: str) -> bool:
    """Check if a name is a valid location candidate."""
    upper = name.upper().strip()

    # Check exclusions
    if upper in LOCATION_EXCLUSIONS:
        return False

    # Must have at least one letter
    if not any(c.isalpha() for c in name):
        return False

    return True


def normalize_name(name: str) -> str:
    """Normalize an entity name for comparison."""
    return name.strip().title()


def get_time_of_day(text: str) -> Optional[str]:
    """Extract time of day from slugline text."""
    times = ['DAY', 'NIGHT', 'DAWN', 'DUSK', 'MORNING', 'AFTERNOON', 'EVENING', 'CONTINUOUS', 'LATER']
    upper = text.upper()
    for time in times:
        if time in upper:
            return time
    return None


def get_int_ext(text: str) -> Optional[str]:
    """Extract INT/EXT from slugline text."""
    upper = text.upper()
    if 'INT./EXT' in upper or 'I/E' in upper:
        return 'INT./EXT'
    elif 'INT' in upper:
        return 'INT'
    elif 'EXT' in upper:
        return 'EXT'
    return None
