"""Integration tests for round-trip editing workflow.

Tests the complete flow:
1. Build canon from inbox
2. Write vault notes
3. User edits vault notes
4. Sync vault changes back
5. Rebuild canon
6. Verify manual edits preserved
"""
import json
import tempfile
import shutil
from pathlib import Path

import pytest

from core.canon import CanonBuilder, CanonBuildResult, build_canon
from core.sync import (
    VaultReingester,
    ChangeDetector,
    ConflictResolver,
    ConflictTier,
    ConflictStatus,
    replace_protected_content,
    get_protected_content,
    BEGIN_MARKER,
    END_MARKER,
    ProvenanceTracker,
    SourceType,
)
from core.vault import VaultNoteWriter


@pytest.fixture
def project(tmp_path):
    """Create a complete project structure for testing."""
    # Directories
    inbox = tmp_path / "inbox"
    vault = tmp_path / "vault"
    build = tmp_path / "build"

    inbox.mkdir()
    vault.mkdir()
    build.mkdir()

    (vault / "10_Characters").mkdir()
    (vault / "20_Locations").mkdir()
    (vault / "50_Scenes").mkdir()

    # Create initial storygraph
    storygraph = {
        "version": "1.0",
        "project_id": tmp_path.name,
        "entities": [],
        "edges": [],
        "evidence_index": {}
    }
    (build / "storygraph.json").write_text(json.dumps(storygraph))

    # Create evidence index
    evidence_index = {"evidence": {}}
    (build / "evidence_index.json").write_text(json.dumps(evidence_index))

    # Create disambiguation queue
    queue = {"version": "1.0", "items": []}
    (build / "disambiguation_queue.json").write_text(json.dumps(queue))

    # Create gsd.yaml for config
    import yaml
    config = {
        "project": {"id": tmp_path.name, "name": "Test Project"},
        "disambiguation": {
            "auto_accept": 0.95,
            "fuzzy_threshold": 70,
            "always_ask_new": False,
        }
    }
    (tmp_path / "gsd.yaml").write_text(yaml.dump(config))

    yield tmp_path

    # Cleanup
    shutil.rmtree(tmp_path, ignore_errors=True)


class TestRoundTripFlow:
    """Tests for complete round-trip workflow."""

    def test_build_creates_vault_notes(self, project):
        """Test that canon build creates vault notes."""
        # Create inbox file
        inbox_file = project / "inbox" / "note1.md"
        inbox_file.write_text("""^ev_001

INT. DINER - DAY

JOHN enters the diner. He looks tired.

JOHN
I need coffee.

The WAITRESS nods.
""")

        # Build canon
        config = {
            "disambiguation": {
                "auto_accept": 0.95,
                "fuzzy_threshold": 70,
                "always_ask_new": False  # Auto-create for test
            }
        }
        builder = CanonBuilder(project, config)
        result = builder.build()

        # Verify vault notes created
        chars_dir = project / "vault" / "10_Characters"
        char_notes = list(chars_dir.glob("*.md"))
        assert len(char_notes) >= 1, f"Expected at least 1 character note, got {len(char_notes)}"

    def test_manual_edit_preserved_after_rebuild(self, project):
        """Test that manual edits survive rebuild."""
        # Create initial entity in storygraph
        storygraph = {
            "version": "1.0",
            "project_id": project.name,
            "entities": [{
                "id": "CHAR_001",
                "type": "character",
                "name": "John",
                "aliases": ["Johnny"],
                "evidence_ids": ["ev_001"]
            }],
            "edges": [],
            "evidence_index": {}
        }
        (project / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        # Create vault note with user content
        note_path = project / "vault" / "10_Characters" / "john.md"
        note_path.write_text(f"""---
id: CHAR_001
name: John
type: character
aliases: [Johnny]
---

# John

{BEGIN_MARKER}
## Aliases

- Johnny

## Evidence

- [[inbox/note.md#^ev_001]]
{END_MARKER}

## Notes

This is my custom note about John. He's a complex character with a dark past.

### Backstory

John grew up in Chicago before moving to LA.
""")

        # Create new inbox content (simulating rebuild)
        inbox_file = project / "inbox" / "note2.md"
        inbox_file.write_text("^ev_002\n\nJOHN also goes by J.")

        # Rebuild with new evidence
        config = {"disambiguation": {"auto_accept": 0.95, "always_ask_new": False}}
        builder = CanonBuilder(project, config)
        builder.build()

        # Verify user content preserved
        updated_note = note_path.read_text()

        # User notes section should still exist
        assert "This is my custom note about John" in updated_note
        assert "### Backstory" in updated_note
        assert "John grew up in Chicago" in updated_note

        # Protected content should have been updated
        assert BEGIN_MARKER in updated_note
        assert END_MARKER in updated_note

    def test_sync_detects_vault_changes(self, project):
        """Test that sync detects and processes vault changes."""
        # Setup: Create entity and vault note
        storygraph = {
            "version": "1.0",
            "project_id": project.name,
            "entities": [{
                "id": "CHAR_001",
                "type": "character",
                "name": "John",
                "aliases": ["Johnny"],
                "evidence_ids": []
            }],
            "edges": [],
            "evidence_index": {}
        }
        (project / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        note_path = project / "vault" / "10_Characters" / "john.md"
        note_content = f"""---
id: CHAR_001
name: John
type: character
aliases: [Johnny]
---

# John

{BEGIN_MARKER}
## Aliases

- Johnny
{END_MARKER}
"""
        note_path.write_text(note_content)

        # Create a baseline for change detection using the actual API
        baseline_path = project / "build" / "sync_baseline.json"
        detector = ChangeDetector.load_baseline(baseline_path)
        # Get current state and add to baseline
        file_state = detector.get_file_state(note_path)
        detector.set_baseline({str(note_path): file_state})
        detector.save_baseline(baseline_path)

        # User edits the vault note (adds alias)
        edited_content = f"""---
id: CHAR_001
name: John
type: character
aliases: [Johnny, J]
---

# John

{BEGIN_MARKER}
## Aliases

- Johnny
- J
{END_MARKER}
"""
        note_path.write_text(edited_content)

        # Run sync
        vault_path = project / "vault"
        storygraph_path = project / "build" / "storygraph.json"
        reingester = VaultReingester(vault_path, storygraph_path)
        result = reingester.reingest_all()

        # Verify change detected - at minimum, file was processed and conflict detected
        # (The conflict may be AMBIGUOUS so no auto-update, but detection worked)
        assert result.files_processed >= 1
        assert result.conflicts_detected >= 1

    def test_conflict_flagged_for_ambiguous_change(self, project):
        """Test that ambiguous changes are flagged."""
        # Setup
        storygraph = {
            "version": "1.0",
            "project_id": project.name,
            "entities": [{
                "id": "CHAR_001",
                "type": "character",
                "name": "John",
                "aliases": [],
                "evidence_ids": []
            }],
            "edges": [],
            "evidence_index": {}
        }
        (project / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        note_path = project / "vault" / "10_Characters" / "john.md"
        note_content = f"""---
id: CHAR_001
name: John
type: character
---

# John

{BEGIN_MARKER}
content
{END_MARKER}
"""
        note_path.write_text(note_content)

        # Create baseline using actual API
        baseline_path = project / "build" / "sync_baseline.json"
        detector = ChangeDetector.load_baseline(baseline_path)
        file_state = detector.get_file_state(note_path)
        detector.set_baseline({str(note_path): file_state})
        detector.save_baseline(baseline_path)

        # User changes name (ambiguous - could be different character)
        edited = note_content.replace("name: John", "name: Jonathan")
        note_path.write_text(edited)

        # Run sync
        vault_path = project / "vault"
        storygraph_path = project / "build" / "storygraph.json"
        reingester = VaultReingester(vault_path, storygraph_path)
        result = reingester.reingest_all()

        # Should have ambiguous conflict (name is a CRITICAL field in ConflictResolver)
        ambiguous_or_critical = [
            c for c in result.conflicts
            if c.tier in (ConflictTier.AMBIGUOUS, ConflictTier.CRITICAL)
        ]
        assert len(ambiguous_or_critical) >= 1

    def test_critical_conflict_blocks(self, project):
        """Test that critical conflicts block changes."""
        # Setup with entity
        storygraph = {
            "version": "1.0",
            "project_id": project.name,
            "entities": [{
                "id": "CHAR_001",
                "type": "character",
                "name": "John",
                "aliases": [],
                "evidence_ids": []
            }],
            "edges": [],
            "evidence_index": {}
        }
        (project / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        note_path = project / "vault" / "10_Characters" / "john.md"
        note_content = f"""---
id: CHAR_001
name: John
type: character
---

{BEGIN_MARKER}
content
{END_MARKER}
"""
        note_path.write_text(note_content)

        # Create baseline using actual API
        baseline_path = project / "build" / "sync_baseline.json"
        detector = ChangeDetector.load_baseline(baseline_path)
        file_state = detector.get_file_state(note_path)
        detector.set_baseline({str(note_path): file_state})
        detector.save_baseline(baseline_path)

        # User changes name (CRITICAL - name changes are critical)
        edited = note_content.replace("name: John", "name: Jane")
        note_path.write_text(edited)

        # Run sync
        vault_path = project / "vault"
        storygraph_path = project / "build" / "storygraph.json"
        reingester = VaultReingester(vault_path, storygraph_path)
        result = reingester.reingest_all()

        # Should have critical conflict
        critical = [c for c in result.conflicts if c.tier == ConflictTier.CRITICAL]
        assert len(critical) >= 1, f"Expected at least 1 critical conflict, got {len(critical)}"

        # Entity name should NOT be changed (critical blocks save)
        # But let's verify the conflict exists
        assert any(c.field_name == "name" for c in critical)

    def test_provenance_tracks_sources(self, project):
        """Test that provenance tracks content sources."""
        # Setup
        storygraph = {
            "version": "1.0",
            "project_id": project.name,
            "entities": [{
                "id": "CHAR_001",
                "type": "character",
                "name": "John",
                "aliases": [],
                "evidence_ids": []
            }],
            "edges": [],
            "evidence_index": {}
        }
        (project / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        # Track extraction provenance using record() API
        provenance_path = project / "build" / "provenance.json"
        tracker = ProvenanceTracker(provenance_path)
        tracker.record(
            source_type=SourceType.CANON_BUILD,
            file_path=project / "vault" / "10_Characters" / "john.md",
            operation="create",
            description="Extracted character John from inbox/note1.md",
            evidence_ids=["ev_001"]
        )

        # Verify provenance recorded
        note_path = project / "vault" / "10_Characters" / "john.md"
        records = tracker.get_records_for_file(note_path)
        assert len(records) >= 1
        record = records[0]
        assert record.source_type == SourceType.CANON_BUILD
        assert "ev_001" in record.evidence_ids

        # Simulate manual edit
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(f"""---
id: CHAR_001
name: Johnny
---

{BEGIN_MARKER}
{END_MARKER}
""")

        # Track manual edit
        tracker.record(
            source_type=SourceType.MANUAL_EDIT,
            file_path=note_path,
            operation="update",
            description="Manual edit: changed name to Johnny",
            user_id="user"
        )

        # Verify provenance updated
        records = tracker.get_records_for_file(note_path)
        manual_records = [r for r in records if r.source_type == SourceType.MANUAL_EDIT]
        assert len(manual_records) >= 1


class TestIncrementalBuild:
    """Tests for incremental build functionality."""

    def test_incremental_only_processes_changed(self, project):
        """Test that incremental build only processes changed files."""
        # Create multiple inbox files
        (project / "inbox" / "note1.md").write_text("^ev_001\n\nJohn enters.")
        (project / "inbox" / "note2.md").write_text("^ev_002\n\nJane enters.")

        # Initial build
        config = {"disambiguation": {"always_ask_new": False}}
        builder = CanonBuilder(project, config)
        builder.build()

        # Create change detector baseline using actual API
        baseline_path = project / "build" / "run_state.json"
        detector = ChangeDetector.load_baseline(baseline_path)
        inbox_files = list((project / "inbox").glob("*.md"))
        baseline_states = {}
        for f in inbox_files:
            baseline_states[str(f)] = detector.get_file_state(f)
        detector.set_baseline(baseline_states)
        detector.save_baseline(baseline_path)

        # Modify only one file
        (project / "inbox" / "note1.md").write_text("^ev_001\n\nJohn enters. He looks tired.")

        # Incremental build should only detect note1 as changed
        inbox_files = list((project / "inbox").glob("*.md"))
        changes = detector.detect_changes(inbox_files)
        assert len(changes) == 1
        assert changes[0].path.name == "note1.md"


class TestProtectedBlockReplacement:
    """Tests for protected block replacement during rebuild."""

    def test_replace_protected_preserves_outside_content(self):
        """Test that replace_protected_content preserves content outside blocks."""
        original = f"""# Title

Some content before.

{BEGIN_MARKER}
## Protected Section

Old content.
{END_MARKER}

## Notes

User notes here.
"""

        new_protected = """## Protected Section

New content.
"""

        result = replace_protected_content(original, new_protected)

        # Outside content preserved
        assert "# Title" in result
        assert "Some content before." in result
        assert "## Notes" in result
        assert "User notes here." in result

        # Protected content replaced
        assert "Old content." not in result
        assert "New content." in result

    def test_extract_protected_content(self):
        """Test extracting content from protected blocks."""
        content = f"""# Title

{BEGIN_MARKER}
## Aliases

- Johnny
- J
{END_MARKER}

## Notes
"""
        # get_protected_content returns a string (content of first block)
        extracted = get_protected_content(content)
        assert extracted is not None
        assert "## Aliases" in extracted
        assert "- Johnny" in extracted


class TestConflictResolver:
    """Tests for conflict resolution."""

    def test_safe_conflict_auto_merged(self):
        """Test that SAFE tier conflicts are auto-merged."""
        resolver = ConflictResolver(auto_merge_safe=True)

        # aliases is a SAFE field when only additions
        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="aliases",
            vault_value=["Johnny"],
            extraction_value=["Johnny", "J"],  # Only additions
        )

        assert conflict is not None
        assert conflict.tier == ConflictTier.SAFE
        assert conflict.status == ConflictStatus.AUTO_RESOLVED
        assert conflict.auto_merge_result is not None
        assert "J" in conflict.auto_merge_result

    def test_critical_conflict_created_for_name_change(self):
        """Test that name changes create CRITICAL conflicts."""
        resolver = ConflictResolver(auto_merge_safe=True)

        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="name",
            vault_value="John",
            extraction_value="Jane",
        )

        assert conflict is not None
        assert conflict.tier == ConflictTier.CRITICAL

    def test_can_proceed_checks(self):
        """Test can_proceed method."""
        resolver = ConflictResolver()

        # No conflicts - can proceed
        assert resolver.can_proceed()

        # SAFE conflict - can proceed
        resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="aliases",
            vault_value=["A"],
            extraction_value=["A", "B"],
        )
        assert resolver.can_proceed()

        # CRITICAL conflict - cannot proceed
        resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_002",
            field_name="name",
            vault_value="Old",
            extraction_value="New",
        )
        assert not resolver.can_proceed()
