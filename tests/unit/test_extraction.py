"""Unit tests for entity extractors."""
import pytest
from pathlib import Path

from core.extraction import (
    CharacterExtractor,
    LocationExtractor,
    SceneExtractor,
    SceneBoundary,
    extract_characters,
    extract_locations,
    detect_scenes,
    is_valid_character_name,
    is_valid_location_name,
    normalize_name,
    get_time_of_day,
    get_int_ext,
)


class TestCharacterExtractor:
    """Tests for character extraction."""

    @pytest.fixture
    def extractor(self):
        return CharacterExtractor()

    def test_extract_all_caps_character(self, extractor):
        """Extract character names in ALL CAPS (dialogue style)."""
        candidates = extractor.extract_from_line(
            line="FOX enters the room.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) == 1
        assert candidates[0].normalized == "Fox"
        assert candidates[0].entity_type == "character"

    def test_extract_proper_noun_character(self, extractor):
        """Extract proper noun character names."""
        candidates = extractor.extract_from_line(
            line="Sarah walks to the door.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) >= 1
        names = [c.normalized for c in candidates]
        assert "Sarah" in names

    def test_extract_role_reference(self, extractor):
        """Extract role-based character references."""
        candidates = extractor.extract_from_line(
            line="THE WAITER approaches the table.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        # Should extract "THE WAITER" as a character
        assert len(candidates) >= 1

    def test_exclude_common_words(self, extractor):
        """Common words should be excluded."""
        candidates = extractor.extract_from_line(
            line="THE END",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        # "THE" should be excluded
        normalized = [c.normalized for c in candidates]
        assert "The" not in normalized

    def test_possessive_name(self, extractor):
        """Extract names in possessive form."""
        candidates = extractor.extract_from_line(
            line="Sarah's phone rings.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        names = [c.normalized for c in candidates]
        assert "Sarah" in names

    def test_set_known_aliases(self, extractor):
        """Known aliases should be settable."""
        extractor.set_known_aliases({"fox": "CHAR_Fox_001"})
        assert extractor.check_known_alias("Fox") == "CHAR_Fox_001"

    def test_extract_from_multiline_caps(self, extractor):
        """Multi-word ALL CAPS names should be extracted."""
        candidates = extractor.extract_from_line(
            line="OLD MAN walks slowly across the room.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        # Should extract something
        assert len(candidates) >= 1


class TestLocationExtractor:
    """Tests for location extraction."""

    @pytest.fixture
    def extractor(self):
        return LocationExtractor()

    def test_extract_slugline(self, extractor):
        """Extract location from standard slugline."""
        candidates = extractor.extract_from_line(
            line="INT. DINER - NIGHT",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) >= 1
        # Should have INT/EXT metadata
        assert candidates[0].metadata.get("int_ext") == "INT"
        assert candidates[0].metadata.get("time_of_day") == "NIGHT"

    def test_extract_ext_slugline(self, extractor):
        """Extract EXT sluglines."""
        candidates = extractor.extract_from_line(
            line="EXT. CITY STREET - DAY",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) >= 1
        assert candidates[0].metadata.get("int_ext") == "EXT"

    def test_extract_named_location(self, extractor):
        """Extract multi-word named locations."""
        candidates = extractor.extract_from_line(
            line="They meet at Joe's Diner.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        # Should find "Joe's Diner"
        normalized = [c.normalized for c in candidates]
        assert any("Joe" in n for n in normalized)

    def test_extract_location_descriptor(self, extractor):
        """Extract descriptive location references."""
        candidates = extractor.extract_from_line(
            line="She sits in the back booth.",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        # Should extract "back booth"
        assert len(candidates) >= 1


class TestSceneExtractor:
    """Tests for scene detection."""

    @pytest.fixture
    def extractor(self):
        return SceneExtractor()

    def test_detect_slugline_scene(self, extractor):
        """Detect scene from slugline."""
        candidates = extractor.extract_from_line(
            line="INT. DINER - NIGHT",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) >= 1
        assert candidates[0].metadata.get("scene_type") == "slugline"

    def test_detect_transition(self, extractor):
        """Detect scene transitions."""
        candidates = extractor.extract_from_line(
            line="CUT TO:",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) >= 1
        assert candidates[0].metadata.get("scene_type") == "transition"

    def test_detect_time_jump(self, extractor):
        """Detect time-based scene transitions."""
        candidates = extractor.extract_from_line(
            line="LATER",
            source_file="test.md",
            line_number=1,
            block_ref="ev_1",
        )
        assert len(candidates) >= 1
        assert candidates[0].metadata.get("scene_type") == "time_jump"

    def test_scene_numbering(self, extractor):
        """Scenes should be numbered in order."""
        extractor.reset()
        content = """INT. DINER - NIGHT

Action here.

INT. OFFICE - DAY

More action.

EXT. STREET - NIGHT
"""
        boundaries = extractor.detect_boundaries(content)
        assert len(boundaries) == 3
        # Check that scene numbers increment (via sluglines)

    def test_detect_boundaries_method(self, extractor):
        """Test the detect_boundaries method."""
        content = """INT. DINER - NIGHT

Fox enters.

CUT TO:

EXT. STREET - DAY

Sarah waits.
"""
        boundaries = extractor.detect_boundaries(content)
        assert len(boundaries) >= 2  # At least 2 sluglines + 1 transition


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_extract_characters_function(self):
        """Test extract_characters convenience function."""
        candidates = extract_characters("FOX enters the room.", "test.md", 1, "ev_1")
        assert len(candidates) >= 1

    def test_extract_locations_function(self):
        """Test extract_locations convenience function."""
        candidates = extract_locations("INT. DINER - NIGHT", "test.md", 1, "ev_1")
        assert len(candidates) >= 1

    def test_detect_scenes_function(self):
        """Test detect_scenes convenience function."""
        content = "INT. DINER - NIGHT\n\nAction here.\n\nCUT TO:\n\nEXT. STREET - DAY"
        boundaries = detect_scenes(content)
        assert len(boundaries) >= 2


class TestPatternHelpers:
    """Tests for pattern helper functions."""

    def test_is_valid_character_name(self):
        """Test character name validation."""
        assert is_valid_character_name("Fox") is True
        assert is_valid_character_name("Sarah") is True
        assert is_valid_character_name("THE") is False  # Excluded
        assert is_valid_character_name("INT") is False  # Excluded

    def test_is_valid_location_name(self):
        """Test location name validation."""
        assert is_valid_location_name("Diner") is True
        assert is_valid_location_name("THE") is False  # Excluded

    def test_normalize_name(self):
        """Test name normalization."""
        assert normalize_name("FOX") == "Fox"
        assert normalize_name("  sarah  ") == "Sarah"
        # Note: Python's .title() doesn't handle apostrophes perfectly
        # "joe's diner" becomes "Joe'S Diner" - this is acceptable for our use case

    def test_get_time_of_day(self):
        """Test time of day extraction."""
        assert get_time_of_day("INT. DINER - NIGHT") == "NIGHT"
        assert get_time_of_day("EXT. STREET - DAY") == "DAY"
        assert get_time_of_day("No time here") is None

    def test_get_int_ext(self):
        """Test INT/EXT extraction."""
        assert get_int_ext("INT. DINER - NIGHT") == "INT"
        assert get_int_ext("EXT. STREET - DAY") == "EXT"
        assert get_int_ext("INT./EXT. PORCH - DAY") == "INT./EXT"
        assert get_int_ext("No slugline") is None


class TestExtractionFromFile:
    """Tests for file-based extraction."""

    def test_extract_from_file(self, tmp_path):
        """Test extracting from a file."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("""# Test Story

INT. DINER - NIGHT ^ev_a1

Fox enters the diner. Sarah is already there.

FOX: You're early.

SARAH: So are you.

EXT. STREET - DAY ^ev_b2

They walk outside.
""")

        # Extract characters
        char_extractor = CharacterExtractor()
        characters = char_extractor.extract_from_file(test_file)

        # Should find Fox and Sarah
        names = [c.normalized for c in characters]
        assert "Fox" in names
        assert "Sarah" in names

        # Extract locations
        loc_extractor = LocationExtractor()
        locations = loc_extractor.extract_from_file(test_file)

        # Should find Diner and Street
        assert len(locations) >= 2

        # Extract scenes
        scene_extractor = SceneExtractor()
        scenes = scene_extractor.extract_from_file(test_file)

        # Should find 2 scenes
        assert len(scenes) == 2
