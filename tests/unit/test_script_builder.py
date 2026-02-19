"""Unit tests for ScriptBuilder and related modules.

Tests cover:
- SluglineGenerator: slugline generation from scene metadata
- BeatExtractor: action beat and dialogue extraction
- ScriptBuilder: full StoryGraph to ScriptGraph transformation
"""
import json
import tempfile
from pathlib import Path

import pytest

from core.script import (
    ScriptBuilder,
    ScriptBuildResult,
    build_script,
    SluglineGenerator,
    generate_slugline,
    BeatExtractor,
    extract_beats,
)
from core.script.dialogue import (
    DialogueFormatter,
    CharacterMatch,
    detect_speaker,
    format_dialogue,
)


# ============================================================================
# SluglineGenerator Tests
# ============================================================================

class TestSluglineGenerator:
    """Tests for SluglineGenerator class."""

    def test_slugline_generation_basic(self):
        """Test basic INT. DINER - NIGHT format."""
        generator = SluglineGenerator()

        scene_entity = {
            "attributes": {
                "int_ext": "INT",
                "location": "Diner",
                "time_of_day": "NIGHT"
            }
        }

        slugline = generator.generate_slugline(scene_entity)
        assert slugline == "INT. DINER - NIGHT"

    def test_slugline_generation_ext(self):
        """Test EXT format."""
        generator = SluglineGenerator()

        scene_entity = {
            "attributes": {
                "int_ext": "EXT",
                "location": "City Street",
                "time_of_day": "DAY"
            }
        }

        slugline = generator.generate_slugline(scene_entity)
        assert slugline == "EXT. CITY STREET - DAY"

    def test_slugline_int_ext_variant(self):
        """Test INT./EXT variant."""
        generator = SluglineGenerator()

        scene_entity = {
            "attributes": {
                "int_ext": "INT./EXT",
                "location": "Car",
                "time_of_day": "CONTINUOUS"
            }
        }

        slugline = generator.generate_slugline(scene_entity)
        assert slugline == "INT./EXT. CAR - CONTINUOUS"

    def test_slugline_location_resolution(self):
        """Test location lookup from storygraph entities."""
        generator = SluglineGenerator()

        scene_entity = {
            "attributes": {
                "int_ext": "INT",
                "location": "The Diner",  # Alias
                "time_of_day": "MORNING"
            }
        }

        storygraph = {
            "entities": [
                {
                    "type": "location",
                    "name": "MAIN STREET DINER",
                    "aliases": ["The Diner", "Diner"]
                }
            ]
        }

        slugline = generator.generate_slugline(scene_entity, storygraph)
        assert slugline == "INT. MAIN STREET DINER - MORNING"

    def test_slugline_missing_location(self):
        """Test fallback to raw location string when not found."""
        generator = SluglineGenerator()

        scene_entity = {
            "attributes": {
                "int_ext": "INT",
                "location": "Some Random Place",
                "time_of_day": "EVENING"
            }
        }

        storygraph = {"entities": []}

        slugline = generator.generate_slugline(scene_entity, storygraph)
        assert slugline == "INT. SOME RANDOM PLACE - EVENING"

    def test_slugline_missing_attributes(self):
        """Test default values for missing attributes."""
        generator = SluglineGenerator()

        scene_entity = {"attributes": {}}

        slugline = generator.generate_slugline(scene_entity)
        # Default INT and DAY
        assert "INT." in slugline
        assert "UNKNOWN LOCATION" in slugline
        assert "DAY" in slugline

    def test_slugline_normalizes_values(self):
        """Test that values are normalized to uppercase."""
        generator = SluglineGenerator()

        scene_entity = {
            "attributes": {
                "int_ext": "int",  # lowercase
                "location": "beach house",  # lowercase
                "time_of_day": "night"  # lowercase
            }
        }

        slugline = generator.generate_slugline(scene_entity)
        assert slugline == "INT. BEACH HOUSE - NIGHT"

    def test_convenience_generate_slugline(self):
        """Test convenience function."""
        scene_entity = {
            "attributes": {
                "int_ext": "EXT",
                "location": "Beach",
                "time_of_day": "DUSK"
            }
        }

        slugline = generate_slugline(scene_entity)
        assert slugline == "EXT. BEACH - DUSK"


# ============================================================================
# BeatExtractor Tests
# ============================================================================

class TestBeatExtractor:
    """Tests for BeatExtractor class."""

    def test_beat_extraction_simple(self):
        """Test single action beat extracted."""
        extractor = BeatExtractor()

        content = "FOX enters. He looks around."
        beats = extractor.extract_beats(content, 1, 2, {1: "ev_test"})

        assert len(beats) == 1
        assert beats[0]["type"] == "action"
        assert "FOX enters" in beats[0]["text"]

    def test_beat_extraction_multiple(self):
        """Test multiple beats in sequence."""
        extractor = BeatExtractor()

        content = """Line 1.

Line 2.

Line 3."""
        beats = extractor.extract_beats(content, 1, 7, {1: "ev_1", 3: "ev_2", 5: "ev_3"})

        assert len(beats) == 3

    def test_beat_extraction_with_evidence(self):
        """Test evidence linking."""
        extractor = BeatExtractor()

        content = "Some action text."
        beats = extractor.extract_beats(content, 1, 2, {1: "ev_abc123"})

        assert len(beats) == 1
        assert "ev_abc123" in beats[0]["evidence_ids"]

    def test_dialogue_detection(self):
        """Test character name followed by speech detected."""
        extractor = BeatExtractor(known_characters=["FOX"])

        content = """FOX
I'm looking for something.

MULDER
What kind of something?"""

        paragraphs = extractor.extract_dialogue(
            content,
            ["FOX", "MULDER"],
            {1: "ev_1", 2: "ev_2", 4: "ev_3", 5: "ev_4"}
        )

        # Should find FOX character + dialogue
        char_para = next((p for p in paragraphs if p["type"] == "character"), None)
        assert char_para is not None
        assert "FOX" in char_para["text"]

        dial_para = next((p for p in paragraphs if p["type"] == "dialogue"), None)
        assert dial_para is not None
        assert "looking for something" in dial_para["text"]

    def test_dialogue_with_parenthetical(self):
        """Test dialogue with parenthetical."""
        extractor = BeatExtractor(known_characters=["FOX"])

        content = """FOX
(whispering)
This is a secret."""

        paragraphs = extractor.extract_all(
            content, 1, 4, {1: "ev_1", 2: "ev_2", 3: "ev_3"}, ["FOX"]
        )

        # Should have character, parenthetical, dialogue
        types = [p["type"] for p in paragraphs]
        assert "character" in types
        assert "parenthetical" in types
        assert "dialogue" in types

    def test_evidence_linking(self):
        """Test each paragraph has evidence_ids."""
        extractor = BeatExtractor()

        content = "First action.\n\nSecond action."
        block_refs = {1: "ev_first", 3: "ev_second"}

        paragraphs = extractor.extract_beats(content, 1, 4, block_refs)

        for para in paragraphs:
            assert "evidence_ids" in para

    def test_extract_all_order(self):
        """Test extract_all returns paragraphs in correct order."""
        extractor = BeatExtractor(known_characters=["ALICE", "BOB"])

        content = """Alice enters the room.

ALICE
Hello everyone.

She waves.

BOB
Hi Alice!"""

        paragraphs = extractor.extract_all(
            content, 1, 10, {}, ["ALICE", "BOB"]
        )

        # Order should be: action, character, dialogue, action, character, dialogue
        types = [p["type"] for p in paragraphs]

        # First should be action (Alice enters)
        assert types[0] == "action"

        # Find ALICE character
        alice_idx = next(i for i, p in enumerate(paragraphs) if p["type"] == "character" and "ALICE" in p["text"])
        # Dialogue should follow
        assert paragraphs[alice_idx + 1]["type"] == "dialogue"

    def test_beat_extraction_skips_sluglines(self):
        """Test that sluglines are not extracted as beats."""
        extractor = BeatExtractor()

        content = """INT. OFFICE - DAY

Some action here.

EXT. STREET - NIGHT"""

        paragraphs = extractor.extract_beats(content, 1, 6, {1: "ev_1", 3: "ev_2", 5: "ev_3"})

        # Only action should be extracted
        for para in paragraphs:
            assert para["type"] == "action"
            assert "INT." not in para["text"]
            assert "EXT." not in para["text"]

    def test_convenience_extract_beats(self):
        """Test convenience function."""
        content = "Action text here."
        beats = extract_beats(content, 1, 2, {1: "ev_test"})

        assert len(beats) == 1
        assert beats[0]["type"] == "action"


# ============================================================================
# ScriptBuilder Tests
# ============================================================================

class TestScriptBuilder:
    """Tests for ScriptBuilder class."""

    def test_scriptbuilder_init(self):
        """Test ScriptBuilder initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            builder = ScriptBuilder(project_path)

            assert builder.project_path == project_path
            assert builder.slugline_generator is not None
            assert builder.beat_extractor is not None

    def test_scriptbuilder_no_storygraph(self):
        """Test builder handles missing storygraph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            builder = ScriptBuilder(project_path)

            result = builder.build()

            assert result.success is False
            assert any("storygraph" in e.lower() for e in result.errors)

    def test_scriptbuilder_empty_storygraph(self):
        """Test builder handles empty storygraph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            build_path = project_path / "build"
            build_path.mkdir(parents=True)

            # Create empty storygraph
            storygraph = {
                "version": "1.0",
                "project_id": "test_project",
                "entities": [],
                "edges": [],
                "evidence_index": {}
            }
            (build_path / "storygraph.json").write_text(json.dumps(storygraph))

            builder = ScriptBuilder(project_path)
            result = builder.build()

            assert result.success is False
            assert any("scene" in e.lower() for e in result.errors)

    def test_scriptbuilder_produces_valid_scriptgraph(self, tmp_path):
        """Test output validates against schema requirements."""
        # Create project structure
        project_path = tmp_path
        build_path = project_path / "build"
        inbox_path = project_path / "inbox"
        build_path.mkdir(parents=True)
        inbox_path.mkdir(parents=True)

        # Create source file
        source_file = inbox_path / "scene1.md"
        source_file.write_text("""^block_001
INT. DINER - NIGHT

FOX enters. He looks around.

FOX
I need coffee.
""")

        # Create storygraph with scene and character
        storygraph = {
            "version": "1.0",
            "project_id": "test_project",
            "entities": [
                {
                    "id": "CHAR_FOX_abc123",
                    "type": "character",
                    "name": "FOX",
                    "aliases": ["Fox"],
                    "attributes": {},
                    "evidence_ids": ["ev_char_1"]
                },
                {
                    "id": "SCN_001",
                    "type": "scene",
                    "name": "Scene 1",
                    "aliases": [],
                    "attributes": {
                        "int_ext": "INT",
                        "location": "Diner",
                        "time_of_day": "NIGHT",
                        "line_number": 2,
                        "source_file": str(source_file),
                        "scene_type": "slugline"
                    },
                    "evidence_ids": ["block_001"]
                }
            ],
            "edges": [],
            "evidence_index": {
                "block_001": {"line_number": 1, "file": str(source_file)}
            }
        }
        (build_path / "storygraph.json").write_text(json.dumps(storygraph))

        # Build script
        builder = ScriptBuilder(project_path)
        result = builder.build()

        assert result.success is True
        assert result.scenes_built >= 1

        # Check output file exists
        scriptgraph_path = build_path / "scriptgraph.json"
        assert scriptgraph_path.exists()

        # Load and validate
        scriptgraph = json.loads(scriptgraph_path.read_text())

        # Check required fields
        assert scriptgraph["version"] == "1.0"
        assert "scenes" in scriptgraph
        assert len(scriptgraph["scenes"]) >= 1

        # Check scene structure
        scene = scriptgraph["scenes"][0]
        assert "id" in scene
        assert "order" in scene
        assert "slugline" in scene
        assert "paragraphs" in scene
        assert "links" in scene

        # Check links structure
        links = scene["links"]
        assert "characters" in links
        assert "locations" in links
        assert "evidence_ids" in links

    def test_scriptbuilder_produces_deterministic_output(self, tmp_path):
        """Test same input produces identical JSON output (except timestamp)."""
        # Create project structure
        project_path = tmp_path
        build_path = project_path / "build"
        inbox_path = project_path / "inbox"
        build_path.mkdir(parents=True)
        inbox_path.mkdir(parents=True)

        # Create source file
        source_file = inbox_path / "scene1.md"
        source_file.write_text("""^block_001
INT. OFFICE - DAY

ALICE types on her keyboard.
""")

        # Create storygraph
        storygraph = {
            "version": "1.0",
            "project_id": "test_project",
            "entities": [
                {
                    "id": "SCN_001",
                    "type": "scene",
                    "name": "Scene 1",
                    "aliases": [],
                    "attributes": {
                        "int_ext": "INT",
                        "location": "Office",
                        "time_of_day": "DAY",
                        "line_number": 2,
                        "source_file": str(source_file),
                        "scene_type": "slugline"
                    },
                    "evidence_ids": ["block_001"]
                }
            ],
            "edges": [],
            "evidence_index": {}
        }
        (build_path / "storygraph.json").write_text(json.dumps(storygraph))

        # Build twice
        builder1 = ScriptBuilder(project_path)
        result1 = builder1.build()

        sg1 = json.loads((build_path / "scriptgraph.json").read_text())

        builder2 = ScriptBuilder(project_path)
        result2 = builder2.build()

        sg2 = json.loads((build_path / "scriptgraph.json").read_text())

        # Remove timestamps for comparison
        sg1.pop("generated_at", None)
        sg2.pop("generated_at", None)

        # All other content should be identical
        assert sg1 == sg2

        # Verify scenes are sorted by order
        assert sg1["scenes"] == sorted(sg1["scenes"], key=lambda s: s["order"])

        # Verify evidence_ids are sorted
        for scene in sg1["scenes"]:
            assert scene["links"]["evidence_ids"] == sorted(scene["links"]["evidence_ids"])

    def test_scriptbuilder_all_paragraphs_have_evidence(self, tmp_path):
        """Test all paragraphs have evidence_ids field."""
        project_path = tmp_path
        build_path = project_path / "build"
        inbox_path = project_path / "inbox"
        build_path.mkdir(parents=True)
        inbox_path.mkdir(parents=True)

        # Create source file
        source_file = inbox_path / "scene1.md"
        source_file.write_text("""^block_001
INT. WAREHOUSE - NIGHT

The place is empty.

JACK
(looking around)
Nothing here.
""")

        storygraph = {
            "version": "1.0",
            "project_id": "test_project",
            "entities": [
                {
                    "id": "CHAR_JACK_xyz",
                    "type": "character",
                    "name": "JACK",
                    "aliases": [],
                    "attributes": {},
                    "evidence_ids": []
                },
                {
                    "id": "SCN_001",
                    "type": "scene",
                    "name": "Scene 1",
                    "aliases": [],
                    "attributes": {
                        "int_ext": "INT",
                        "location": "Warehouse",
                        "time_of_day": "NIGHT",
                        "line_number": 2,
                        "source_file": str(source_file),
                        "scene_type": "slugline"
                    },
                    "evidence_ids": ["block_001"]
                }
            ],
            "edges": [],
            "evidence_index": {}
        }
        (build_path / "storygraph.json").write_text(json.dumps(storygraph))

        builder = ScriptBuilder(project_path)
        result = builder.build()

        scriptgraph = json.loads((build_path / "scriptgraph.json").read_text())

        for scene in scriptgraph.get("scenes", []):
            for para in scene.get("paragraphs", []):
                assert "evidence_ids" in para
                assert isinstance(para["evidence_ids"], list)

    def test_convenience_build_script(self, tmp_path):
        """Test convenience build_script function."""
        project_path = tmp_path
        build_path = project_path / "build"
        build_path.mkdir(parents=True)

        # Create minimal storygraph
        storygraph = {
            "version": "1.0",
            "project_id": "test",
            "entities": [],
            "edges": []
        }
        (build_path / "storygraph.json").write_text(json.dumps(storygraph))

        result = build_script(project_path)

        assert isinstance(result, ScriptBuildResult)


# ============================================================================
# Integration Tests
# ============================================================================

class TestScriptBuilderIntegration:
    """Integration tests for full script building workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow from StoryGraph to ScriptGraph."""
        project_path = tmp_path
        build_path = project_path / "build"
        inbox_path = project_path / "inbox"
        build_path.mkdir(parents=True)
        inbox_path.mkdir(parents=True)

        # Create source file with full scene
        source_file = inbox_path / "pilot.md"
        source_file.write_text("""^pilot_block_1
INT. FBI OFFICE - DAY

MULDER sits at his desk, surrounded by files.

MULDER
Scully, you have to see this.

SCULLY enters, looking skeptical.

SCULLY
What is it this time, Mulder?

MULDER
(grinning)
The truth.

^pilot_block_2
EXT. PARKING LOT - NIGHT

A dark car waits. The engine idles.
""")

        # Create complete storygraph
        storygraph = {
            "version": "1.0",
            "project_id": "xfiles_pilot",
            "entities": [
                {
                    "id": "CHAR_MULDER_a1b2",
                    "type": "character",
                    "name": "MULDER",
                    "aliases": ["Mulder", "Fox Mulder"],
                    "attributes": {},
                    "evidence_ids": ["pilot_block_1"]
                },
                {
                    "id": "CHAR_SCULLY_c3d4",
                    "type": "character",
                    "name": "SCULLY",
                    "aliases": ["Scully", "Dana Scully"],
                    "attributes": {},
                    "evidence_ids": ["pilot_block_1"]
                },
                {
                    "id": "LOC_FBI_OFFICE",
                    "type": "location",
                    "name": "FBI OFFICE",
                    "aliases": ["FBI Office", "the office"],
                    "attributes": {},
                    "evidence_ids": ["pilot_block_1"]
                },
                {
                    "id": "SCN_001",
                    "type": "scene",
                    "name": "Scene 1",
                    "aliases": [],
                    "attributes": {
                        "int_ext": "INT",
                        "location": "FBI Office",
                        "time_of_day": "DAY",
                        "line_number": 2,
                        "source_file": str(source_file),
                        "scene_type": "slugline"
                    },
                    "evidence_ids": ["pilot_block_1"]
                },
                {
                    "id": "SCN_002",
                    "type": "scene",
                    "name": "Scene 2",
                    "aliases": [],
                    "attributes": {
                        "int_ext": "EXT",
                        "location": "Parking Lot",
                        "time_of_day": "NIGHT",
                        "line_number": 16,
                        "source_file": str(source_file),
                        "scene_type": "slugline"
                    },
                    "evidence_ids": ["pilot_block_2"]
                }
            ],
            "edges": [
                {"from": "SCN_001", "to": "CHAR_MULDER_a1b2", "type": "contains"},
                {"from": "SCN_001", "to": "CHAR_SCULLY_c3d4", "type": "contains"},
                {"from": "SCN_001", "to": "LOC_FBI_OFFICE", "type": "set_in"}
            ],
            "evidence_index": {
                "pilot_block_1": {"line_number": 1, "file": str(source_file)},
                "pilot_block_2": {"line_number": 15, "file": str(source_file)}
            }
        }
        (build_path / "storygraph.json").write_text(json.dumps(storygraph))

        # Build script
        builder = ScriptBuilder(project_path)
        result = builder.build()

        # Verify success
        assert result.success is True
        assert result.scenes_built == 2

        # Load output
        scriptgraph = json.loads((build_path / "scriptgraph.json").read_text())

        # Verify structure
        assert len(scriptgraph["scenes"]) == 2

        # Check first scene
        scene1 = scriptgraph["scenes"][0]
        assert scene1["order"] == 1
        assert "INT. FBI OFFICE - DAY" == scene1["slugline"]
        assert len(scene1["paragraphs"]) > 0

        # Check character links
        assert "MULDER" in scene1["links"]["characters"]
        assert "SCULLY" in scene1["links"]["characters"]

        # Check second scene
        scene2 = scriptgraph["scenes"][1]
        assert scene2["order"] == 2
        assert "EXT. PARKING LOT - NIGHT" == scene2["slugline"]

    def test_scriptbuilder_with_config(self, tmp_path):
        """Test ScriptBuilder with custom config."""
        project_path = tmp_path
        build_path = project_path / "build"
        build_path.mkdir(parents=True)

        config = {"some": "config"}

        builder = ScriptBuilder(project_path, config)

        assert builder.config == config


# ============================================================================
# DialogueFormatter Tests
# ============================================================================

class TestDialogueFormatter:
    """Tests for DialogueFormatter and speaker detection."""

    def test_speaker_detection_exact_match(self):
        """Test FOX matches Fox entity exactly."""
        formatter = DialogueFormatter([
            {"id": "CHAR_Fox_1234", "name": "Fox", "aliases": []}
        ])

        match = formatter.detect_speaker("FOX", [])

        assert match is not None
        assert match.entity.get("id") == "CHAR_Fox_1234"
        assert match.confidence == 1.0
        assert match.match_type == "exact"

    def test_speaker_detection_case_insensitive(self):
        """Test Fox matches Fox entity (case-insensitive via lookup)."""
        formatter = DialogueFormatter([
            {"id": "CHAR_Fox_1234", "name": "Fox", "aliases": []}
        ])

        # Character cues are typically uppercase, but we test lookup flexibility
        # FOX (exact match) -> FOX -> Fox entity
        match = formatter.detect_speaker("FOX", [])

        assert match is not None
        assert match.entity.get("id") == "CHAR_Fox_1234"
        # FOX uppercase matches the uppercase name stored in lookup
        assert match.confidence == 1.0
        assert match.match_type == "exact"

    def test_speaker_detection_alias(self):
        """Test Johnny matches entity with that alias."""
        formatter = DialogueFormatter([
            {"id": "CHAR_John_5678", "name": "John Smith", "aliases": ["Johnny", "Johnny Boy"]}
        ])

        match = formatter.detect_speaker("JOHNNY", [])

        assert match is not None
        assert match.entity.get("id") == "CHAR_John_5678"
        assert match.confidence == 0.9
        assert match.match_type == "alias"

    def test_speaker_no_match(self):
        """Test unknown name returns None."""
        formatter = DialogueFormatter([
            {"id": "CHAR_Fox_1234", "name": "Fox", "aliases": []}
        ])

        match = formatter.detect_speaker("UNKNOWN CHARACTER", [])

        assert match is None

    def test_parenthetical_extraction(self):
        """Test (pauses) Hello splits correctly."""
        formatter = DialogueFormatter()

        remaining, parenthetical = formatter.extract_parenthetical("(pauses) Hello there.")

        assert parenthetical == "pauses"
        assert remaining == "Hello there."

    def test_dialogue_block_formatting(self):
        """Test produces character + dialogue paragraphs."""
        formatter = DialogueFormatter([
            {"id": "CHAR_Fox_1234", "name": "Fox", "aliases": []}
        ])

        speaker_match = formatter.detect_speaker("FOX", [])
        paragraphs = formatter.format_dialogue_block(
            speaker_match,
            ["I knew this booth was bad luck."],
            ["ev_test_1"]
        )

        # Should have character and dialogue
        assert len(paragraphs) == 2
        assert paragraphs[0]["type"] == "character"
        assert paragraphs[0]["text"] == "Fox"
        assert paragraphs[1]["type"] == "dialogue"
        assert "bad luck" in paragraphs[1]["text"]

    def test_dialogue_character_id_in_meta(self):
        """Test paragraph meta contains character_id."""
        formatter = DialogueFormatter([
            {"id": "CHAR_Fox_1234", "name": "Fox", "aliases": []}
        ])

        speaker_match = formatter.detect_speaker("FOX", [])
        paragraphs = formatter.format_dialogue_block(
            speaker_match,
            ["Some dialogue."],
            ["ev_test"]
        )

        char_para = paragraphs[0]
        assert "meta" in char_para
        assert char_para["meta"]["character_id"] == "CHAR_Fox_1234"
        assert "match_confidence" in char_para["meta"]

    def test_full_scene_with_dialogue(self):
        """Test end-to-end: scene has both action and dialogue with character_id."""
        # Set up BeatExtractor with character entities
        extractor = BeatExtractor(
            character_entities=[
                {"id": "CHAR_Fox_1234", "type": "character", "name": "FOX", "aliases": []}
            ]
        )

        content = """FOX enters and sits down.

FOX
(pauses)
I knew this booth was bad luck."""

        paragraphs = extractor.extract_all(
            content, 1, 6, {1: "ev_1", 3: "ev_2", 4: "ev_3", 5: "ev_4"}, ["FOX"]
        )

        # Should have action, character, parenthetical, dialogue
        types = [p["type"] for p in paragraphs]
        assert "action" in types
        assert "character" in types
        assert "parenthetical" in types
        assert "dialogue" in types

        # Check character paragraph has character_id
        char_para = next((p for p in paragraphs if p["type"] == "character"), None)
        assert char_para is not None
        assert "FOX" in char_para["text"]
        assert char_para.get("meta", {}).get("character_id") == "CHAR_Fox_1234"
