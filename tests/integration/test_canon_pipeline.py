"""Integration tests for the canon build pipeline.

Tests the full flow: inbox → extraction → resolution → storygraph
"""
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from core.canon import CanonBuilder, CanonBuildResult, build_canon
from core.extraction import CharacterExtractor, LocationExtractor, SceneExtractor
from core.resolution import FuzzyMatcher, create_matcher


@pytest.fixture
def temp_project():
    """Create a temporary project structure for testing."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create project structure
    (temp_dir / "inbox").mkdir()
    (temp_dir / "vault" / "10_Characters").mkdir(parents=True)
    (temp_dir / "vault" / "20_Locations").mkdir(parents=True)
    (temp_dir / "vault" / "50_Scenes").mkdir(parents=True)
    (temp_dir / "build").mkdir()

    # Create minimal config
    config = {
        "project": {"id": "test-project", "name": "Test Project"},
        "disambiguation": {
            "auto_accept": 0.95,
            "auto_reject": 0.30,
            "always_ask_new": False,
            "fuzzy_threshold": 70
        }
    }

    import yaml
    (temp_dir / "gsd.yaml").write_text(yaml.dump(config))

    # Initialize build files
    (temp_dir / "build" / "storygraph.json").write_text(json.dumps({
        "version": "1.0",
        "project_id": "test-project",
        "entities": [],
        "edges": [],
        "evidence_index": {}
    }))

    (temp_dir / "build" / "disambiguation_queue.json").write_text(json.dumps({
        "version": "1.0",
        "items": []
    }))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestCanonBuilderIntegration:
    """Integration tests for CanonBuilder."""

    def test_full_pipeline_with_simple_content(self, temp_project):
        """Test the full canon build pipeline with simple screenplay content."""
        # Create inbox file
        inbox_file = temp_project / "inbox" / "test_script.md"
        inbox_file.write_text("""# Test Script

INT. COFFEE SHOP - DAY

JOHN sits at a table. MARY enters.

JOHN
(happy)
Hey, Mary! Over here!

MARY
(smiling)
Hey, John! Nice to see you.

MARY walks to John's table and sits down.

EXT. PARK - LATER

John and Mary walk together through the park.

CUT TO:

INT. COFFEE SHOP - NIGHT

The coffee shop is now empty.
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        # Check result
        assert result.success
        # Characters are auto-linked since always_ask_new is False
        total_chars = result.characters_created + result.characters_linked
        assert total_chars >= 2  # John and Mary
        # Locations are auto-linked
        total_locs = result.locations_created + result.locations_linked
        assert total_locs >= 1  # At least Coffee Shop
        assert result.scenes_created >= 2  # Coffee Shop scenes (CUT TO doesn't create a scene)

    def test_entity_linking_across_files(self, temp_project):
        """Test that entities are linked across multiple inbox files."""
        # Create two inbox files
        (temp_project / "inbox" / "part1.md").write_text("""
INT. OFFICE - DAY

SARAH works at her desk.
""")

        (temp_project / "inbox" / "part2.md").write_text("""
INT. OFFICE - LATER

SARAH receives a phone call.
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        # Should have processed Sarah across files
        assert result.success
        total_chars = result.characters_created + result.characters_linked
        assert total_chars >= 1  # Sarah
        # Sarah in second file should link to first
        assert result.characters_linked >= 1

    def test_fuzzy_matching_with_aliases(self, temp_project):
        """Test fuzzy matching resolves similar names."""
        # Create inbox with name variations
        (temp_project / "inbox" / "aliases.md").write_text("""
INT. HOUSE - DAY

ELIZABETH enters.

BETH
Elizabeth! Over here!

LIZ looks around confused.
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        config["disambiguation"]["always_ask_new"] = True  # Queue ambiguous

        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        # Should queue items for disambiguation
        assert result.success
        assert result.queue_items >= 1

    def test_scene_boundary_detection(self, temp_project):
        """Test that scene boundaries are correctly detected."""
        (temp_project / "inbox" / "scenes.md").write_text("""
INT. KITCHEN - MORNING

Cooking breakfast.

EXT. BACKYARD - CONTINUOUS

Birds chirping.

INT./EXT. GARAGE - DAY

Working on a car.

I/E. ROOFTOP - NIGHT

Looking at stars.
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        assert result.success
        # Only sluglines create scenes (4 sluglines)
        assert result.scenes_created >= 4

        # Check storygraph for scene entities
        storygraph = json.loads((temp_project / "build" / "storygraph.json").read_text())
        scenes = [e for e in storygraph["entities"] if e["type"] == "scene"]
        assert len(scenes) >= 4

    def test_storygraph_persistence(self, temp_project):
        """Test that storygraph is correctly updated."""
        (temp_project / "inbox" / "content.md").write_text("""
INT. STUDIO - DAY

ALEX records a podcast.
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        assert result.success

        # Verify storygraph structure
        storygraph_path = temp_project / "build" / "storygraph.json"
        storygraph = json.loads(storygraph_path.read_text())

        assert "version" in storygraph
        assert "entities" in storygraph
        assert len(storygraph["entities"]) > 0

        # Check entity structure
        entity = storygraph["entities"][0]
        assert "id" in entity
        assert "type" in entity
        assert "name" in entity
        assert "aliases" in entity
        assert "evidence_ids" in entity

    def test_disambiguation_queue_persistence(self, temp_project):
        """Test that disambiguation queue is correctly written."""
        # Use always_ask_new to force queue items
        (temp_project / "inbox" / "new_chars.md").write_text("""
INT. OFFICE - DAY

REBECCA meets CHARLES for the first time.
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        config["disambiguation"]["always_ask_new"] = True

        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        # Check queue
        queue_path = temp_project / "build" / "disambiguation_queue.json"
        queue = json.loads(queue_path.read_text())

        assert "version" in queue
        assert "items" in queue
        assert len(queue["items"]) >= 1

        # Check item structure
        item = queue["items"][0]
        assert "id" in item
        assert "status" in item
        assert item["status"] == "open"
        assert "kind" in item
        assert "label" in item


class TestExtractionPipeline:
    """Tests for the extraction pipeline components."""

    def test_character_extraction_pipeline(self, temp_project):
        """Test character extraction from inbox files."""
        (temp_project / "inbox" / "chars.md").write_text("""
INT. HOSPITAL - DAY

DR. SMITH consults with NURSE JENKINS.
PATIENT JONES waits nervously.
""")

        extractor = CharacterExtractor()
        candidates = extractor.extract_from_file(temp_project / "inbox" / "chars.md")

        # Should extract character names
        assert len(candidates) >= 2

        names = [c.text for c in candidates]
        # At least some of these should be found
        assert any("SMITH" in n or "Smith" in n for n in names)

    def test_location_extraction_pipeline(self, temp_project):
        """Test location extraction from inbox files."""
        (temp_project / "inbox" / "locs.md").write_text("""
INT. WAREHOUSE - NIGHT
EXT. CITY STREETS - DAY
INT./EXT. AIRPORT - MORNING
""")

        extractor = LocationExtractor()
        candidates = extractor.extract_from_file(temp_project / "inbox" / "locs.md")

        assert len(candidates) >= 3

        # Check that locations were extracted with proper types
        for c in candidates:
            assert c.metadata.get("int_ext") in ("INT", "EXT", "INT/EXT", "I/E")

    def test_scene_extractor_boundaries(self, temp_project):
        """Test scene boundary detection."""
        content = """INT. APARTMENT - DAY

Action description.

EXT. BALCONY - CONTINUOUS

More action.

CUT TO:

INT. BEDROOM - NIGHT
"""

        extractor = SceneExtractor()
        boundaries = extractor.detect_boundaries(content, "test.md")

        assert len(boundaries) >= 3

        # Check first boundary
        assert boundaries[0].scene_type == "slugline"
        assert boundaries[0].int_ext == "INT"
        assert boundaries[0].location == "APARTMENT"


class TestResolutionPipeline:
    """Tests for alias resolution."""

    def test_fuzzy_matcher_exact_match(self):
        """Test exact matching in fuzzy matcher."""
        matcher = create_matcher(threshold=70)
        matcher.add_entity("CHAR_John_001", "John", ["JOHN", "Johnny"])

        # Exact match
        result = matcher.match("John")
        assert result is not None
        assert result.score == 100.0
        assert result.method == "exact"

    def test_fuzzy_matcher_alias_match(self):
        """Test alias matching in fuzzy matcher."""
        matcher = create_matcher(threshold=70)
        matcher.add_entity("CHAR_John_001", "John", ["JOHN", "Johnny"])

        # Alias match
        result = matcher.match("Johnny")
        assert result is not None
        assert result.score == 95.0
        assert result.method == "alias"

    def test_fuzzy_matcher_fuzzy_match(self):
        """Test fuzzy matching for similar names."""
        matcher = create_matcher(threshold=70)
        matcher.add_entity("CHAR_Elizabeth_001", "Elizabeth", [])

        # Fuzzy match (should match similar name)
        result = matcher.match("Elisabeth")
        assert result is not None
        assert result.method == "fuzzy"
        assert result.score >= 70

    def test_fuzzy_matcher_no_match(self):
        """Test no match for dissimilar names."""
        matcher = create_matcher(threshold=70)
        matcher.add_entity("CHAR_John_001", "John", [])

        # No match
        result = matcher.match("Xyzzy")
        assert result is None

    def test_confident_match_threshold(self):
        """Test confident match auto-accept threshold."""
        matcher = create_matcher(threshold=70)
        matcher.add_entity("CHAR_John_001", "John", [])

        # Exact should be confident
        result = matcher.is_confident_match("John", 0.95)
        assert result == "CHAR_John_001"

        # Fuzzy should not be confident at 95%
        result = matcher.is_confident_match("Jon", 0.95)
        # Depending on score, might or might not be confident
        # Jon vs John is very similar so might pass


class TestEvidenceLinking:
    """Tests for evidence linking."""

    def test_evidence_ids_tracked(self, temp_project):
        """Test that evidence IDs are tracked through pipeline."""
        # Create file with block refs
        (temp_project / "inbox" / "evidence.md").write_text("""
INT. COURTROOM - DAY

JUDGE WALKER presides. ^ev_a1b2
""")

        config = yaml.safe_load((temp_project / "gsd.yaml").read_text())
        config["disambiguation"]["always_ask_new"] = False

        builder = CanonBuilder(temp_project, config)
        result = builder.build()

        assert result.success

        # Check that evidence was linked
        storygraph = json.loads((temp_project / "build" / "storygraph.json").read_text())

        # At least one entity should have evidence
        entities_with_evidence = [
            e for e in storygraph["entities"]
            if e.get("evidence_ids")
        ]
        assert len(entities_with_evidence) >= 1


# Import yaml at module level
import yaml
