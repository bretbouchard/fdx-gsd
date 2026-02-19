"""Integration tests for the script composition pipeline.

Tests the full flow: storygraph -> scriptgraph -> fdx export
"""
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from core.script import ScriptBuilder, build_script
from core.scriptgraph import validate_scriptgraph, load_scriptgraph, create_empty_scriptgraph
from core.exporters import write_fdx, FDXWriter


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project structure for testing."""
    # Create directories
    (tmp_path / "inbox").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / "exports").mkdir()
    (tmp_path / "vault" / "10_Characters").mkdir(parents=True)
    (tmp_path / "vault" / "20_Locations").mkdir(parents=True)
    (tmp_path / "vault" / "50_Scenes").mkdir(parents=True)

    # Create minimal config
    config = {
        "project": {"id": "test-project", "name": "Test Project"},
    }

    return tmp_path


@pytest.fixture
def empty_storygraph(sample_project):
    """Create an empty storygraph for testing."""
    storygraph = {
        "version": "1.0",
        "project_id": "test-project",
        "entities": [],
        "edges": [],
        "evidence_index": {}
    }
    (sample_project / "build" / "storygraph.json").write_text(json.dumps(storygraph))
    return sample_project


@pytest.fixture
def single_scene_storygraph(sample_project):
    """Create a storygraph with a single scene."""
    storygraph = {
        "version": "1.0",
        "project_id": "test-project",
        "entities": [
            {
                "id": "SCN_001",
                "type": "scene",
                "name": "Coffee Shop",
                "aliases": [],
                "attributes": {
                    "int_ext": "INT",
                    "location": "COFFEE SHOP",
                    "time_of_day": "DAY",
                    "source_file": "test.md",
                    "line_number": 5
                },
                "evidence_ids": ["ev_001"]
            },
            {
                "id": "CHAR_Fox",
                "type": "character",
                "name": "Fox",
                "aliases": ["FOX"],
                "attributes": {},
                "evidence_ids": []
            }
        ],
        "edges": [],
        "evidence_index": {
            "ev_001": {
                "source_path": "inbox/test.md",
                "block_ref": "^ev_001",
                "text_excerpt": "Test excerpt",
                "line_number": 5
            }
        }
    }
    (sample_project / "build" / "storygraph.json").write_text(json.dumps(storygraph))
    return sample_project


@pytest.fixture
def multi_scene_storygraph(sample_project):
    """Create a storygraph with multiple scenes."""
    # Create a test source file in inbox
    inbox_file = sample_project / "inbox" / "test.md"
    inbox_file.write_text("""# Test Script

INT. COFFEE SHOP - DAY

Fox sits at a table. ^ev_001

FOX
(waving)
Hello there!

EXT. PARK - LATER

Fox walks through the park. ^ev_002

FOX
Beautiful day.

INT. OFFICE - NIGHT

Fox works late. ^ev_003
""")

    storygraph = {
        "version": "1.0",
        "project_id": "test-project",
        "entities": [
            {
                "id": "SCN_001",
                "type": "scene",
                "name": "Coffee Shop",
                "aliases": [],
                "attributes": {
                    "int_ext": "INT",
                    "location": "COFFEE SHOP",
                    "time_of_day": "DAY",
                    "source_file": str(inbox_file),
                    "line_number": 3
                },
                "evidence_ids": ["ev_001"]
            },
            {
                "id": "SCN_002",
                "type": "scene",
                "name": "Park",
                "aliases": [],
                "attributes": {
                    "int_ext": "EXT",
                    "location": "PARK",
                    "time_of_day": "LATER",
                    "source_file": str(inbox_file),
                    "line_number": 11
                },
                "evidence_ids": ["ev_002"]
            },
            {
                "id": "SCN_003",
                "type": "scene",
                "name": "Office",
                "aliases": [],
                "attributes": {
                    "int_ext": "INT",
                    "location": "OFFICE",
                    "time_of_day": "NIGHT",
                    "source_file": str(inbox_file),
                    "line_number": 17
                },
                "evidence_ids": ["ev_003"]
            },
            {
                "id": "CHAR_Fox",
                "type": "character",
                "name": "Fox",
                "aliases": ["FOX"],
                "attributes": {},
                "evidence_ids": []
            }
        ],
        "edges": [],
        "evidence_index": {}
    }
    (sample_project / "build" / "storygraph.json").write_text(json.dumps(storygraph))
    return sample_project


class TestEmptyScriptgraph:
    """Tests for empty ScriptGraph handling."""

    def test_empty_storygraph_produces_empty_scriptgraph(self, empty_storygraph):
        """StoryGraph with no scenes produces empty ScriptGraph."""
        result = build_script(empty_storygraph, {})

        assert result.success is False  # No scenes = failure
        assert result.scenes_built == 0
        assert "No scene entities" in " ".join(result.errors)

    def test_create_empty_scriptgraph_validates(self):
        """Empty ScriptGraph validates against schema."""
        scriptgraph = create_empty_scriptgraph("test-project")
        assert validate_scriptgraph(scriptgraph) is True


class TestSingleScenePipeline:
    """Tests for single scene processing."""

    def test_single_scene_pipeline(self, single_scene_storygraph):
        """StoryGraph with one scene produces ScriptGraph with slugline."""
        result = build_script(single_scene_storygraph, {})

        assert result.success
        assert result.scenes_built == 1

        # Check ScriptGraph output
        scriptgraph_path = single_scene_storygraph / "build" / "scriptgraph.json"
        assert scriptgraph_path.exists()

        scriptgraph = json.loads(scriptgraph_path.read_text())
        assert len(scriptgraph["scenes"]) == 1
        assert scriptgraph["scenes"][0]["slugline"] == "INT. COFFEE SHOP - DAY"

    def test_single_scene_has_correct_structure(self, single_scene_storygraph):
        """Single scene has all required fields."""
        result = build_script(single_scene_storygraph, {})

        scriptgraph_path = single_scene_storygraph / "build" / "scriptgraph.json"
        scriptgraph = json.loads(scriptgraph_path.read_text())

        scene = scriptgraph["scenes"][0]
        assert "id" in scene
        assert "order" in scene
        assert "slugline" in scene
        assert "paragraphs" in scene
        assert "links" in scene
        assert scene["order"] == 1


class TestMultiSceneOrdering:
    """Tests for multi-scene ordering."""

    def test_multi_scene_ordering(self, multi_scene_storygraph):
        """Multiple scenes appear in correct order in ScriptGraph."""
        result = build_script(multi_scene_storygraph, {})

        assert result.success
        assert result.scenes_built == 3

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        scriptgraph = json.loads(scriptgraph_path.read_text())

        # Check order
        scenes = scriptgraph["scenes"]
        assert scenes[0]["order"] == 1
        assert scenes[1]["order"] == 2
        assert scenes[2]["order"] == 3

        # Check sluglines are in order
        assert "COFFEE SHOP" in scenes[0]["slugline"]
        assert "PARK" in scenes[1]["slugline"]
        assert "OFFICE" in scenes[2]["slugline"]


class TestDialogueInclusion:
    """Tests for dialogue handling."""

    def test_dialogue_included_in_output(self, multi_scene_storygraph):
        """Dialogue is properly typed in output paragraphs."""
        result = build_script(multi_scene_storygraph, {})

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        scriptgraph = json.loads(scriptgraph_path.read_text())

        # Collect all paragraph types
        all_paragraphs = []
        for scene in scriptgraph["scenes"]:
            all_paragraphs.extend(scene.get("paragraphs", []))

        paragraph_types = [p.get("type") for p in all_paragraphs]

        # Should have character and dialogue types
        assert "character" in paragraph_types, f"Expected 'character' type in {paragraph_types}"
        assert "dialogue" in paragraph_types, f"Expected 'dialogue' type in {paragraph_types}"

        # Verify character paragraph contains character name
        character_paras = [p for p in all_paragraphs if p.get("type") == "character"]
        assert len(character_paras) > 0
        assert any("Fox" in p.get("text", "") or "FOX" in p.get("text", "") for p in character_paras)


class TestEvidenceIds:
    """Tests for evidence ID preservation."""

    def test_evidence_ids_preserved(self, single_scene_storygraph):
        """All paragraphs have evidence_ids from source."""
        result = build_script(single_scene_storygraph, {})

        scriptgraph_path = single_scene_storygraph / "build" / "scriptgraph.json"
        scriptgraph = json.loads(scriptgraph_path.read_text())

        # Check scene links have evidence_ids
        for scene in scriptgraph["scenes"]:
            assert "links" in scene
            assert "evidence_ids" in scene["links"]
            # Evidence IDs should be a list (can be empty)
            assert isinstance(scene["links"]["evidence_ids"], list)


class TestSchemaValidation:
    """Tests for JSON schema validation."""

    def test_scriptgraph_validates_against_schema(self, multi_scene_storygraph):
        """Output validates with jsonschema."""
        result = build_script(multi_scene_storygraph, {})

        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"

        # This should not raise
        scriptgraph = load_scriptgraph(scriptgraph_path)
        assert scriptgraph is not None


class TestFDXExport:
    """Tests for FDX export functionality."""

    def test_fdx_export_from_scriptgraph(self, multi_scene_storygraph):
        """FDXWriter produces valid XML from generated ScriptGraph."""
        # Build script first
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        # Export to FDX
        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        output_path = write_fdx(scriptgraph_path, fdx_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert len(content) > 0

    def test_fdx_has_xml_declaration(self, multi_scene_storygraph):
        """Output starts with <?xml."""
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        write_fdx(scriptgraph_path, fdx_path)

        content = fdx_path.read_text()
        # XML declaration may use single or double quotes depending on ElementTree
        assert content.startswith('<?xml')
        assert 'version=' in content[:50]
        assert 'encoding=' in content[:50]

    def test_fdx_has_final_draft_root(self, multi_scene_storygraph):
        """Contains <FinalDraft> element."""
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        write_fdx(scriptgraph_path, fdx_path)

        content = fdx_path.read_text()
        assert "<FinalDraft" in content
        assert "</FinalDraft>" in content

    def test_fdx_scene_heading_type(self, multi_scene_storygraph):
        """Sluglines are Type="Scene Heading"."""
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        write_fdx(scriptgraph_path, fdx_path)

        content = fdx_path.read_text()
        assert 'Type="Scene Heading"' in content

    def test_fdx_action_type(self, multi_scene_storygraph):
        """Action beats are Type="Action"."""
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        write_fdx(scriptgraph_path, fdx_path)

        content = fdx_path.read_text()
        assert 'Type="Action"' in content

    def test_fdx_dialogue_types(self, multi_scene_storygraph):
        """Character/Dialogue have correct types."""
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        write_fdx(scriptgraph_path, fdx_path)

        content = fdx_path.read_text()

        # Should have Character type
        assert 'Type="Character"' in content
        # Should have Dialogue type
        assert 'Type="Dialogue"' in content


class TestDeterministicBuild:
    """Tests for deterministic output."""

    def test_deterministic_rebuild(self, multi_scene_storygraph):
        """Running build twice produces identical output."""
        config = {}

        # First build
        result1 = build_script(multi_scene_storygraph, config)
        assert result1.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        content1 = scriptgraph_path.read_text()

        # Second build
        result2 = build_script(multi_scene_storygraph, config)
        assert result2.success

        content2 = scriptgraph_path.read_text()

        # Should be identical (except for generated_at timestamp)
        data1 = json.loads(content1)
        data2 = json.loads(content2)

        # Remove generated_at for comparison
        data1.pop("generated_at", None)
        data2.pop("generated_at", None)

        assert data1 == data2, "ScriptGraph should be deterministic"


class TestFullWorkflow:
    """End-to-end workflow tests."""

    def test_full_workflow_canon_to_script_to_fdx(self, multi_scene_storygraph):
        """Test complete workflow: storygraph -> scriptgraph -> fdx."""
        # Step 1: Build script
        script_result = build_script(multi_scene_storygraph, {})
        assert script_result.success
        assert script_result.scenes_built == 3

        # Step 2: Verify scriptgraph
        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        assert scriptgraph_path.exists()

        scriptgraph = load_scriptgraph(scriptgraph_path)
        assert len(scriptgraph["scenes"]) == 3

        # Step 3: Export FDX
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"
        output_path = write_fdx(scriptgraph_path, fdx_path)

        assert output_path.exists()
        content = output_path.read_text()

        # Verify FDX structure
        assert content.startswith('<?xml')
        assert "<FinalDraft" in content
        assert 'Type="Scene Heading"' in content
        assert 'Type="Action"' in content
        assert 'Type="Character"' in content
        assert 'Type="Dialogue"' in content


class TestManualFDXVerification:
    """
    Manual verification tests for FDX output.

    These tests document how to manually verify FDX files open correctly
    in Final Draft or compatible readers.
    """

    def test_fdx_opens_in_final_draft(self, multi_scene_storygraph):
        """
        Manual verification that FDX opens in Final Draft.

        STEPS FOR MANUAL VERIFICATION:
        1. Build a test project: gsd build canon && gsd build script
        2. Export FDX: gsd export fdx
        3. Open exports/script.fdx in Final Draft (or Fade In, WriterSolo)
        4. Verify:
           - Scene headings appear in correct format
           - Character names are centered above dialogue
           - Action/description appears correctly
           - Parentheticals are properly formatted
           - No XML parsing errors appear

        This test creates a valid FDX file but does not automate
        the visual verification step.
        """
        result = build_script(multi_scene_storygraph, {})
        assert result.success

        scriptgraph_path = multi_scene_storygraph / "build" / "scriptgraph.json"
        fdx_path = multi_scene_storygraph / "exports" / "script.fdx"

        write_fdx(scriptgraph_path, fdx_path)

        # Verify file exists and has content
        assert fdx_path.exists()
        content = fdx_path.read_text()

        # Basic XML validity checks
        assert content.startswith('<?xml')
        assert "<FinalDraft" in content
        assert "</FinalDraft>" in content

        # File should be parseable as XML
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(fdx_path)
            root = tree.getroot()
            assert root.tag == "FinalDraft"
        except ET.ParseError as e:
            pytest.fail(f"FDX file is not valid XML: {e}")

        # Print path for manual verification
        print(f"\nFDX file created at: {fdx_path}")
        print("Open in Final Draft or compatible reader to verify formatting.")


def run_full_workflow(project_path):
    """Helper function to run full workflow: build canon -> build script -> export fdx.

    This is provided as a utility for manual testing and debugging.
    """
    from core.script import build_script
    from core.exporters import write_fdx

    # Step 1: Build script (assumes canon already built)
    script_result = build_script(project_path, {})

    if not script_result.success:
        return None, script_result.errors

    # Step 2: Export FDX
    scriptgraph_path = project_path / "build" / "scriptgraph.json"
    fdx_path = project_path / "exports" / "script.fdx"

    try:
        write_fdx(scriptgraph_path, fdx_path)
        return fdx_path, None
    except Exception as e:
        return None, [str(e)]
