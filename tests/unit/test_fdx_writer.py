"""Unit tests for FDX writer."""
import json
import pytest
from pathlib import Path

from core.exporters.fdx_writer import FDXWriter, write_fdx


@pytest.fixture
def minimal_scriptgraph():
    """Minimal valid ScriptGraph for testing."""
    return {
        "version": "1.0",
        "project_id": "test_project",
        "scenes": [
            {
                "id": "SCN_001",
                "order": 1,
                "slugline": "INT. DINER - NIGHT",
                "paragraphs": [
                    {"type": "action", "text": "FOX enters the diner."},
                    {"type": "character", "text": "FOX"},
                    {"type": "dialogue", "text": "I knew this booth was bad luck."},
                ],
                "links": {
                    "characters": ["CHAR_Fox"],
                    "locations": ["LOC_Diner"],
                    "props": [],
                    "wardrobe": [],
                    "evidence_ids": ["ev_test"]
                }
            }
        ]
    }


@pytest.fixture
def multi_scene_scriptgraph():
    """Multi-scene ScriptGraph for testing."""
    return {
        "version": "1.0",
        "project_id": "test_project",
        "scenes": [
            {
                "id": "SCN_001",
                "order": 1,
                "slugline": "INT. DINER - NIGHT",
                "paragraphs": [
                    {"type": "action", "text": "Scene one action."},
                ],
                "links": {
                    "characters": [],
                    "locations": ["LOC_Diner"],
                    "props": [],
                    "wardrobe": [],
                    "evidence_ids": []
                }
            },
            {
                "id": "SCN_002",
                "order": 2,
                "slugline": "EXT. STREET - NIGHT",
                "paragraphs": [
                    {"type": "action", "text": "Scene two action."},
                ],
                "links": {
                    "characters": [],
                    "locations": ["LOC_Street"],
                    "props": [],
                    "wardrobe": [],
                    "evidence_ids": []
                }
            }
        ]
    }


class TestFDXWriter:
    """Tests for FDXWriter class."""

    def test_init(self, minimal_scriptgraph):
        """Test FDXWriter initialization."""
        writer = FDXWriter(minimal_scriptgraph)
        assert writer.scriptgraph == minimal_scriptgraph
        assert writer.project_id == "test_project"

    def test_from_file(self, tmp_path, minimal_scriptgraph):
        """Test loading from file."""
        json_path = tmp_path / "scriptgraph.json"
        json_path.write_text(json.dumps(minimal_scriptgraph))

        writer = FDXWriter.from_file(json_path)
        assert writer.project_id == "test_project"

    def test_write_produces_file(self, tmp_path, minimal_scriptgraph):
        """Test that write produces a file."""
        writer = FDXWriter(minimal_scriptgraph)
        out_path = tmp_path / "test.fdx"

        result = writer.write(out_path)

        assert result == out_path
        assert out_path.exists()

    def test_write_has_xml_declaration(self, tmp_path, minimal_scriptgraph):
        """Test that output has XML declaration."""
        writer = FDXWriter(minimal_scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        # Python's xml.etree uses single quotes, which is valid XML
        assert '<?xml' in content
        assert 'version=' in content
        assert 'encoding=' in content

    def test_write_has_final_draft_root(self, tmp_path, minimal_scriptgraph):
        """Test that output has FinalDraft root element."""
        writer = FDXWriter(minimal_scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        assert '<FinalDraft' in content
        assert 'DocumentType="Script"' in content

    def test_scene_heading_present(self, tmp_path, minimal_scriptgraph):
        """Test that scene heading is included."""
        writer = FDXWriter(minimal_scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        assert 'INT. DINER - NIGHT' in content
        assert 'Type="Scene Heading"' in content

    def test_action_present(self, tmp_path, minimal_scriptgraph):
        """Test that action paragraphs are included."""
        writer = FDXWriter(minimal_scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        assert 'FOX enters the diner' in content
        assert 'Type="Action"' in content

    def test_dialogue_present(self, tmp_path, minimal_scriptgraph):
        """Test that dialogue is included with correct types."""
        writer = FDXWriter(minimal_scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        assert 'FOX' in content
        assert 'I knew this booth was bad luck' in content
        assert 'Type="Character"' in content
        assert 'Type="Dialogue"' in content

    def test_scene_order_preserved(self, tmp_path, multi_scene_scriptgraph):
        """Test that scenes are ordered correctly."""
        writer = FDXWriter(multi_scene_scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        diner_pos = content.find('INT. DINER')
        street_pos = content.find('EXT. STREET')
        assert diner_pos < street_pos

    def test_to_string(self, minimal_scriptgraph):
        """Test string output."""
        writer = FDXWriter(minimal_scriptgraph)
        result = writer.to_string()

        assert '<?xml' in result
        assert '<FinalDraft' in result


class TestWriteFDXFunction:
    """Tests for write_fdx convenience function."""

    def test_write_fdx(self, tmp_path, minimal_scriptgraph):
        """Test the convenience function."""
        json_path = tmp_path / "scriptgraph.json"
        json_path.write_text(json.dumps(minimal_scriptgraph))

        out_path = tmp_path / "output.fdx"
        result = write_fdx(json_path, out_path)

        assert result == out_path
        assert out_path.exists()


class TestParagraphTypeMapping:
    """Tests for paragraph type mapping."""

    def test_all_types_mapped(self, tmp_path):
        """Test that all paragraph types produce valid FDX."""
        scriptgraph = {
            "version": "1.0",
            "project_id": "test",
            "scenes": [{
                "id": "SCN_001",
                "order": 1,
                "slugline": "INT. TEST - DAY",
                "paragraphs": [
                    {"type": "action", "text": "Action"},
                    {"type": "character", "text": "BOB"},
                    {"type": "dialogue", "text": "Hello"},
                    {"type": "parenthetical", "text": "(pauses)"},
                    {"type": "transition", "text": "CUT TO:"},
                    {"type": "shot", "text": "CLOSE ON"},
                ],
                "links": {
                    "characters": [],
                    "locations": [],
                    "props": [],
                    "wardrobe": [],
                    "evidence_ids": []
                }
            }]
        }

        writer = FDXWriter(scriptgraph)
        out_path = tmp_path / "test.fdx"
        writer.write(out_path)

        content = out_path.read_text()
        assert 'Type="Action"' in content
        assert 'Type="Character"' in content
        assert 'Type="Dialogue"' in content
        assert 'Type="Parenthetical"' in content
        assert 'Type="Transition"' in content
        assert 'Type="Shot"' in content
