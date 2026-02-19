"""Unit tests for vault note writer."""
import pytest
from pathlib import Path
from datetime import datetime

from core.vault import (
    VaultNoteWriter,
    render_character_template,
    render_location_template,
    render_scene_template,
)
from core.vault.templates import _slugify


@pytest.fixture
def sample_character():
    """Sample character entity for testing."""
    return {
        "id": "CHAR_001",
        "name": "John Smith",
        "type": "character",
        "aliases": ["Johnny", "Mr. Smith"],
        "evidence_ids": ["ev_001", "ev_002"],
    }


@pytest.fixture
def sample_location():
    """Sample location entity for testing."""
    return {
        "id": "LOC_001",
        "name": "Coffee Shop",
        "type": "location",
        "attributes": {
            "int_ext": "INT",
            "time_of_day": "MORNING",
        },
        "evidence_ids": ["ev_003"],
    }


@pytest.fixture
def sample_scene():
    """Sample scene entity for testing."""
    return {
        "id": "SCN_001",
        "name": "INT. COFFEE SHOP - MORNING",
        "type": "scene",
        "attributes": {
            "scene_number": "001",
            "location": "Coffee Shop",
            "int_ext": "INT",
            "time_of_day": "MORNING",
        },
        "evidence_ids": ["ev_004"],
    }


class TestSlugify:
    """Tests for slug generation."""

    def test_simple_name(self):
        """Test slugification of simple name."""
        assert _slugify("John Smith") == "john-smith"

    def test_uppercase_name(self):
        """Test slugification converts to lowercase."""
        assert _slugify("JOHN SMITH") == "john-smith"

    def test_special_characters(self):
        """Test slugification removes special characters."""
        assert _slugify("John @Smith!") == "john-smith"

    def test_multiple_spaces(self):
        """Test slugification converts multiple spaces."""
        # Note: Current implementation preserves multiple spaces as hyphens
        assert _slugify("John   Smith") == "john---smith"

    def test_leading_trailing_spaces(self):
        """Test slugification strips spaces."""
        assert _slugify("  John Smith  ") == "john-smith"


class TestCharacterTemplate:
    """Tests for character template rendering."""

    def test_character_template_rendering(self, sample_character):
        """Verify template produces valid markdown with frontmatter."""
        evidence_links = "- [[inbox/ev.md#^ev_001]]\n- [[inbox/ev.md#^ev_002]]"
        content = render_character_template(sample_character, evidence_links)

        # Check YAML frontmatter
        assert content.startswith("---")
        assert "id: CHAR_001" in content
        assert "name: John Smith" in content
        assert "type: character" in content
        assert "aliases:" in content

        # Check body content
        assert "# John Smith" in content
        assert "## Aliases" in content
        assert "- Johnny" in content
        assert "- Mr. Smith" in content

        # Check evidence links
        assert "## Evidence" in content
        assert "[[inbox/ev.md#^ev_001]]" in content

    def test_character_template_no_aliases(self):
        """Test character template with no aliases."""
        entity = {
            "id": "CHAR_002",
            "name": "Jane Doe",
            "type": "character",
            "aliases": [],
            "evidence_ids": [],
        }
        content = render_character_template(entity, "")

        assert "*None recorded*" in content

    def test_protected_block_markers_character(self, sample_character):
        """Verify protected block markers present in character template."""
        content = render_character_template(sample_character, "")

        assert "<!-- CONFUCIUS:BEGIN AUTO -->" in content
        assert "<!-- CONFUCIUS:END AUTO -->" in content


class TestLocationTemplate:
    """Tests for location template rendering."""

    def test_location_template_rendering(self, sample_location):
        """Verify location template with int_ext metadata."""
        evidence_links = "- [[inbox/ev.md#^ev_003]]"
        content = render_location_template(sample_location, evidence_links)

        # Check YAML frontmatter
        assert "id: LOC_001" in content
        assert "name: Coffee Shop" in content
        assert "type: location" in content
        assert "int_ext: INT" in content
        assert "time_of_day: MORNING" in content

        # Check body content
        assert "# Coffee Shop" in content
        assert "## Type" in content
        assert "**INT** - MORNING" in content

        # Check evidence links
        assert "## Evidence" in content

    def test_location_template_no_time(self):
        """Test location template without time of day."""
        entity = {
            "id": "LOC_002",
            "name": "Park",
            "type": "location",
            "attributes": {
                "int_ext": "EXT",
            },
            "evidence_ids": [],
        }
        content = render_location_template(entity, "")

        assert "**EXT**" in content
        assert "time_of_day: " in content  # Empty value in frontmatter

    def test_protected_block_markers_location(self, sample_location):
        """Verify protected block markers present in location template."""
        content = render_location_template(sample_location, "")

        assert "<!-- CONFUCIUS:BEGIN AUTO -->" in content
        assert "<!-- CONFUCIUS:END AUTO -->" in content


class TestSceneTemplate:
    """Tests for scene template rendering."""

    def test_scene_template_rendering(self, sample_scene):
        """Verify scene template with scene number."""
        evidence_links = "- [[inbox/ev.md#^ev_004]]"
        content = render_scene_template(sample_scene, evidence_links)

        # Check YAML frontmatter
        assert "id: SCN_001" in content
        assert "scene_number: 001" in content
        assert "location: Coffee Shop" in content
        assert "int_ext: INT" in content
        assert "time_of_day: MORNING" in content

        # Check body content
        assert "# INT. COFFEE SHOP - MORNING" in content
        assert "## Location" in content
        assert "[[Coffee Shop]]" in content
        assert "## Time" in content
        assert "**INT** - MORNING" in content

        # Check evidence links
        assert "## Evidence" in content

    def test_protected_block_markers_scene(self, sample_scene):
        """Verify protected block markers present in scene template."""
        content = render_scene_template(sample_scene, "")

        assert "<!-- CONFUCIUS:BEGIN AUTO -->" in content
        assert "<!-- CONFUCIUS:END AUTO -->" in content


class TestEvidenceLinkFormatting:
    """Tests for evidence link formatting."""

    def test_evidence_link_formatting(self, tmp_path):
        """Verify evidence IDs become Obsidian wikilinks."""
        writer = VaultNoteWriter(tmp_path)

        # Create minimal evidence index
        import json
        build_path = tmp_path.parent / "build"
        build_path.mkdir(exist_ok=True)
        evidence_index = {
            "evidence": {
                "ev_001": {"source_path": "inbox/script"},
                "ev_002": {"source_path": "inbox/script"},
            }
        }
        (build_path / "evidence_index.json").write_text(json.dumps(evidence_index))

        writer.build_path = build_path
        links = writer.format_evidence_links(["ev_001", "ev_002"])

        assert "[[inbox/script#^ev_001]]" in links
        assert "[[inbox/script#^ev_002]]" in links

    def test_evidence_link_empty_list(self, tmp_path):
        """Test formatting with empty evidence list."""
        writer = VaultNoteWriter(tmp_path)
        links = writer.format_evidence_links([])

        assert links == ""


class TestVaultNoteWriter:
    """Tests for VaultNoteWriter class."""

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates vault subdirectories."""
        writer = VaultNoteWriter(tmp_path)

        assert (tmp_path / "10_Characters").exists()
        assert (tmp_path / "20_Locations").exists()
        assert (tmp_path / "50_Scenes").exists()

    def test_write_character_creates_file(self, tmp_path, sample_character):
        """Integration test that file is created in correct dir."""
        writer = VaultNoteWriter(tmp_path)
        result = writer.write_character(sample_character)

        assert result.exists()
        assert result.parent.name == "10_Characters"
        assert result.name == "john-smith.md"

        # Verify content
        content = result.read_text()
        assert "# John Smith" in content
        assert "id: CHAR_001" in content

    def test_write_location_creates_file(self, tmp_path, sample_location):
        """Test that location file is created in correct dir."""
        writer = VaultNoteWriter(tmp_path)
        result = writer.write_location(sample_location)

        assert result.exists()
        assert result.parent.name == "20_Locations"
        assert result.name == "coffee-shop.md"

        # Verify content
        content = result.read_text()
        assert "# Coffee Shop" in content
        assert "id: LOC_001" in content

    def test_write_scene_creates_file(self, tmp_path, sample_scene):
        """Test that scene file is created in correct dir."""
        writer = VaultNoteWriter(tmp_path)
        result = writer.write_scene(sample_scene)

        assert result.exists()
        assert result.parent.name == "50_Scenes"
        assert result.name == "SCN_001.md"

        # Verify content
        content = result.read_text()
        assert "# INT. COFFEE SHOP - MORNING" in content
        assert "id: SCN_001" in content

    def test_deterministic_output(self, tmp_path, sample_character):
        """Same entity input produces identical file content."""
        writer = VaultNoteWriter(tmp_path)

        # Write twice with same entity
        path1 = writer.write_character(sample_character)
        content1 = path1.read_text()

        # Modify created_at to make it deterministic
        from unittest.mock import patch
        from datetime import datetime

        fixed_date = "2026-02-19"
        with patch('core.vault.templates.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = fixed_date
            path2 = writer.write_character(sample_character)
            content2 = path2.read_text()

        # Content should be identical
        assert content1 == content2

    def test_write_entity_convenience(self, tmp_path, sample_character, sample_location, sample_scene):
        """Test write_entity convenience method."""
        writer = VaultNoteWriter(tmp_path)

        # Test character
        char_path = writer.write_entity(sample_character)
        assert char_path.exists()
        assert "10_Characters" in str(char_path)

        # Test location
        loc_path = writer.write_entity(sample_location)
        assert loc_path.exists()
        assert "20_Locations" in str(loc_path)

        # Test scene
        scene_path = writer.write_entity(sample_scene)
        assert scene_path.exists()
        assert "50_Scenes" in str(scene_path)

        # Test unknown type
        unknown_entity = {"id": "TEST", "type": "unknown"}
        result = writer.write_entity(unknown_entity)
        assert result is None
