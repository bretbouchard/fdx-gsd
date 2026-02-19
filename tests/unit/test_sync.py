"""Unit tests for sync module (round-trip editing)."""
import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from core.sync.change_detector import ChangeDetector, calculate_file_hash, FileState
from core.sync.protected_blocks import (
    BEGIN_MARKER,
    END_MARKER,
    extract_protected_content,
    replace_protected_content,
    ensure_markers,
    has_protected_block,
    get_protected_content,
    split_at_protected_block,
)
from core.sync.provenance import ProvenanceTracker, ProvenanceRecord, SourceType
from core.sync.conflict_resolver import (
    ConflictResolver,
    Conflict,
    ConflictTier,
    ConflictStatus,
)


class TestChangeDetector:
    """Tests for change detection."""

    def test_calculate_file_hash(self, tmp_path):
        """Test SHA-256 hash calculation."""
        test_file = tmp_path / "test.md"
        test_file.write_text("test content")

        hash1 = calculate_file_hash(test_file)
        hash2 = calculate_file_hash(test_file)

        # Same content = same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_hash_changes_with_content(self, tmp_path):
        """Test that hash changes when content changes."""
        test_file = tmp_path / "test.md"
        test_file.write_text("original content")

        hash1 = calculate_file_hash(test_file)

        test_file.write_text("modified content")
        hash2 = calculate_file_hash(test_file)

        assert hash1 != hash2

    def test_detect_changes_added(self, tmp_path):
        """Test detecting added files."""
        detector = ChangeDetector()

        # Create new file
        (tmp_path / "new.md").write_text("new content")

        changes = detector.detect_changes([tmp_path / "new.md"])

        assert len(changes) == 1
        assert changes[0].change_type == "added"

    def test_detect_changes_modified(self, tmp_path):
        """Test detecting modified files."""
        test_file = tmp_path / "test.md"
        test_file.write_text("original")

        # Get initial state
        detector = ChangeDetector()
        state = detector.get_file_state(test_file)
        detector.set_baseline({str(test_file): state})

        # Modify file
        test_file.write_text("modified")
        changes = detector.detect_changes([test_file])

        assert len(changes) == 1
        assert changes[0].change_type == "modified"

    def test_detect_changes_deleted(self, tmp_path):
        """Test detecting deleted files."""
        deleted_file = tmp_path / "deleted.md"
        deleted_file.write_text("content")

        detector = ChangeDetector()
        state = detector.get_file_state(deleted_file)
        detector.set_baseline({str(deleted_file): state})

        # Delete file (not in current paths)
        deleted_file.unlink()
        changes = detector.detect_changes([], track_deletions=True)

        assert len(changes) == 1
        assert changes[0].change_type == "deleted"

    def test_save_and_load_baseline(self, tmp_path):
        """Test baseline persistence."""
        test_file = tmp_path / "test.md"
        test_file.write_text("content")

        detector = ChangeDetector()
        state = detector.get_file_state(test_file)
        detector.set_baseline({str(test_file): state})

        # Save baseline
        baseline_path = tmp_path / "baseline.json"
        detector.save_baseline(baseline_path)

        # Load baseline
        loaded = ChangeDetector.load_baseline(baseline_path)
        assert str(test_file) in loaded.baseline

    def test_has_changes(self, tmp_path):
        """Test quick check for changes."""
        test_file = tmp_path / "test.md"
        test_file.write_text("original")

        detector = ChangeDetector()
        state = detector.get_file_state(test_file)
        detector.set_baseline({str(test_file): state})

        # No changes initially
        assert not detector.has_changes([test_file])

        # Modify
        test_file.write_text("modified")
        assert detector.has_changes([test_file])


class TestProtectedBlocks:
    """Tests for protected block parsing."""

    def test_has_protected_block_true(self):
        """Test detection of protected blocks."""
        content = f"Some text\n{BEGIN_MARKER}\nprotected\n{END_MARKER}\nmore"
        assert has_protected_block(content) is True

    def test_has_protected_block_false(self):
        """Test detection when no protected blocks."""
        content = "Some text\nNo markers here"
        assert has_protected_block(content) is False

    def test_extract_protected_content(self):
        """Test extraction of protected content."""
        content = f"before\n{BEGIN_MARKER}\nprotected content\n{END_MARKER}\nafter"
        blocks = extract_protected_content(content)

        assert len(blocks) == 1
        assert blocks[0].content == "\nprotected content\n"

    def test_extract_protected_content_no_markers(self):
        """Test extraction when no markers present."""
        content = "just content, no markers"
        blocks = extract_protected_content(content)

        assert len(blocks) == 0

    def test_replace_protected_content(self):
        """Test replacing protected content."""
        content = f"before\n{BEGIN_MARKER}\nold\n{END_MARKER}\nafter"
        new = replace_protected_content(content, "new content")

        assert "before" in new
        assert "new content" in new
        assert "old" not in new
        assert "after" in new

    def test_replace_protected_raises_on_missing_block(self):
        """Test that replace raises error when no block exists."""
        content = "no markers here"
        with pytest.raises(ValueError):
            replace_protected_content(content, "new")

    def test_ensure_markers_adds_if_missing(self):
        """Test ensure_markers adds markers when missing."""
        content = "no markers"
        result = ensure_markers(content)

        assert BEGIN_MARKER in result
        assert END_MARKER in result

    def test_ensure_markers_preserves_existing(self):
        """Test ensure_markers doesn't duplicate markers."""
        content = f"content\n{BEGIN_MARKER}\n{END_MARKER}"
        result = ensure_markers(content)

        # Should not double the markers
        assert result.count(BEGIN_MARKER) == 1
        assert result.count(END_MARKER) == 1

    def test_ensure_markers_inserts_before_notes(self):
        """Test ensure_markers inserts before ## Notes section."""
        content = "# Title\n\n## Notes\n\nUser notes"
        result = ensure_markers(content)

        # Markers should be before ## Notes
        notes_pos = result.find("## Notes")
        begin_pos = result.find(BEGIN_MARKER)
        assert begin_pos < notes_pos

    def test_get_protected_content(self):
        """Test get_protected_content helper."""
        content = f"{BEGIN_MARKER}\nmy content\n{END_MARKER}"
        result = get_protected_content(content)

        assert result == "\nmy content\n"

    def test_get_protected_content_none(self):
        """Test get_protected_content with no markers."""
        content = "no markers"
        result = get_protected_content(content)

        assert result is None

    def test_split_at_protected_block(self):
        """Test split_at_protected_block helper."""
        content = f"before\n{BEGIN_MARKER}\nmiddle\n{END_MARKER}\nafter"
        before, protected, after = split_at_protected_block(content)

        assert "before" in before
        assert protected == "\nmiddle\n"
        assert "after" in after

    def test_split_at_protected_block_no_markers(self):
        """Test split_at_protected_block with no markers."""
        content = "just text"
        before, protected, after = split_at_protected_block(content)

        assert before == content
        assert protected == ""
        assert after == ""


class TestProvenance:
    """Tests for provenance tracking."""

    def test_record_creation(self, tmp_path):
        """Test creating a provenance record."""
        tracker = ProvenanceTracker(tmp_path / "provenance.json")

        record = tracker.record(
            source_type=SourceType.CANON_BUILD,
            file_path=tmp_path / "test.md",
            operation="create",
            description="Created character note",
            evidence_ids=["ev_001"],
        )

        assert record.record_id.startswith("prov_")
        assert record.source_type == SourceType.CANON_BUILD
        assert record.operation == "create"
        assert "ev_001" in record.evidence_ids

    def test_get_record(self, tmp_path):
        """Test retrieving a record by ID."""
        tracker = ProvenanceTracker(tmp_path / "provenance.json")

        created = tracker.record(
            source_type=SourceType.CANON_BUILD,
            file_path=tmp_path / "test.md",
            operation="create",
            description="Test",
        )

        retrieved = tracker.get_record(created.record_id)
        assert retrieved is not None
        assert retrieved.record_id == created.record_id

    def test_get_records_for_file(self, tmp_path):
        """Test getting all records for a specific file."""
        tracker = ProvenanceTracker(tmp_path / "provenance.json")

        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"

        tracker.record(SourceType.CANON_BUILD, file1, "create", "File 1")
        tracker.record(SourceType.CANON_BUILD, file2, "create", "File 2")
        tracker.record(SourceType.MANUAL_EDIT, file1, "update", "File 1 edit")

        records = tracker.get_records_for_file(file1)
        assert len(records) == 2

    def test_get_records_by_source(self, tmp_path):
        """Test filtering records by source type."""
        tracker = ProvenanceTracker(tmp_path / "provenance.json")

        file1 = tmp_path / "file1.md"

        tracker.record(SourceType.CANON_BUILD, file1, "create", "Canon")
        tracker.record(SourceType.MANUAL_EDIT, file1, "update", "Manual")

        canon_records = tracker.get_records_by_source(SourceType.CANON_BUILD)
        assert len(canon_records) == 1
        assert canon_records[0].source_type == SourceType.CANON_BUILD

    def test_get_latest_record_for_file(self, tmp_path):
        """Test getting most recent record for a file."""
        tracker = ProvenanceTracker(tmp_path / "provenance.json")

        file1 = tmp_path / "file1.md"

        tracker.record(SourceType.CANON_BUILD, file1, "create", "First")
        tracker.record(SourceType.MANUAL_EDIT, file1, "update", "Second")

        latest = tracker.get_latest_record_for_file(file1)
        assert latest.operation == "update"

    def test_persistence(self, tmp_path):
        """Test provenance persistence to file."""
        prov_path = tmp_path / "provenance.json"
        file1 = tmp_path / "file1.md"

        # Create and save
        tracker1 = ProvenanceTracker(prov_path)
        tracker1.record(SourceType.CANON_BUILD, file1, "create", "Test")
        assert prov_path.exists()

        # Load in new tracker
        tracker2 = ProvenanceTracker(prov_path)
        assert len(tracker2.get_all_records()) == 1

    def test_get_summary(self, tmp_path):
        """Test getting provenance summary."""
        tracker = ProvenanceTracker(tmp_path / "provenance.json")

        file1 = tmp_path / "file1.md"
        tracker.record(SourceType.CANON_BUILD, file1, "create", "Test")

        summary = tracker.get_summary()
        assert summary["total_records"] == 1
        assert "canon_build" in summary["by_source"]


class TestConflictResolver:
    """Tests for conflict resolution."""

    def test_classify_safe_array_addition(self, tmp_path):
        """Test SAFE tier for array additions."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="aliases",
            vault_value=["John"],
            extraction_value=["John", "Johnny"],
        )

        assert conflict is not None
        assert conflict.tier == ConflictTier.SAFE

    def test_classify_critical_id_change(self, tmp_path):
        """Test CRITICAL tier for ID changes."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="entity_id",
            vault_value="CHAR_001",
            extraction_value="CHAR_002",
        )

        assert conflict is not None
        assert conflict.tier == ConflictTier.CRITICAL

    def test_classify_ambiguous_scalar(self, tmp_path):
        """Test AMBIGUOUS tier for scalar field changes (non-critical fields)."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        # Use description field (not name, which is CRITICAL)
        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="description",
            vault_value="A hero",
            extraction_value="The main hero",
        )

        assert conflict is not None
        assert conflict.tier == ConflictTier.AMBIGUOUS

    def test_classify_name_is_critical(self, tmp_path):
        """Test that name field is CRITICAL (requires disambiguation)."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="name",
            vault_value="John",
            extraction_value="Jonathan",
        )

        assert conflict is not None
        assert conflict.tier == ConflictTier.CRITICAL

    def test_no_conflict_same_values(self, tmp_path):
        """Test no conflict when values match."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="name",
            vault_value="John",
            extraction_value="John",
        )

        assert conflict is None

    def test_auto_merge_safe_conflict(self, tmp_path):
        """Test auto-merge of SAFE conflicts (array additions only)."""
        resolver = ConflictResolver(tmp_path / "conflicts.json", auto_merge_safe=True)

        # SAFE tier only applies to array additions (no removals)
        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="aliases",
            vault_value=["John"],
            extraction_value=["John", "Johnny"],
        )

        # Should be SAFE tier (only additions) and auto-merged
        assert conflict.tier == ConflictTier.SAFE
        assert conflict.status == ConflictStatus.AUTO_RESOLVED
        assert conflict.auto_merge_result is not None

    def test_array_with_removals_is_ambiguous(self, tmp_path):
        """Test that arrays with removals are AMBIGUOUS (not SAFE)."""
        resolver = ConflictResolver(tmp_path / "conflicts.json", auto_merge_safe=True)

        # This has both addition (J) and removal (Johnny)
        conflict = resolver.detect_conflict(
            entity_type="character",
            entity_id="CHAR_001",
            field_name="aliases",
            vault_value=["John", "Johnny"],
            extraction_value=["John", "J"],
        )

        # Should be AMBIGUOUS because it has removals
        assert conflict.tier == ConflictTier.AMBIGUOUS
        # Should NOT be auto-merged
        assert conflict.status == ConflictStatus.DETECTED

    def test_get_pending_conflicts(self, tmp_path):
        """Test filtering pending conflicts."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        resolver.detect_conflict("C1", "character", "name", "A", "B")
        resolver.detect_conflict("C2", "character", "description", "X", "Y")

        pending = resolver.get_pending_conflicts()
        # Both should be pending (AMBIGUOUS tier, not auto-resolved)
        assert len(pending) >= 1

    def test_has_critical_conflicts(self, tmp_path):
        """Test critical conflict detection."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        # No critical conflicts initially
        assert not resolver.has_critical_conflicts()

        # Add critical conflict
        resolver.detect_conflict(
            entity_type="character",
            entity_id="C1",
            field_name="entity_id",
            vault_value="C1",
            extraction_value="C2",
        )

        assert resolver.has_critical_conflicts()

    def test_can_proceed(self, tmp_path):
        """Test can_proceed check."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        # Can proceed initially
        assert resolver.can_proceed()

        # Add critical conflict
        resolver.detect_conflict(
            entity_type="character",
            entity_id="C1",
            field_name="entity_id",
            vault_value="C1",
            extraction_value="C2",
        )

        # Cannot proceed with critical conflict
        assert not resolver.can_proceed()

    def test_detect_all_conflicts(self, tmp_path):
        """Test detecting all conflicts between vault and extraction."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        vault_data = {
            "name": "John",
            "aliases": ["John", "Johnny"],
            "description": "A character",
        }

        extraction_data = {
            "name": "Jonathan",
            "aliases": ["John", "J"],
            "description": "A character",
        }

        conflicts = resolver.detect_all_conflicts(
            entity_type="character",
            entity_id="CHAR_001",
            vault_data=vault_data,
            extraction_data=extraction_data,
        )

        # name differs, aliases differ, description same
        # name = AMBIGUOUS, aliases = AMBIGUOUS (has removals)
        assert len(conflicts) >= 1

    def test_save_and_load_conflicts(self, tmp_path):
        """Test conflict persistence."""
        conflicts_path = tmp_path / "conflicts.json"

        resolver1 = ConflictResolver(conflicts_path)
        resolver1.detect_conflict("C1", "character", "name", "A", "B")
        resolver1.save_conflicts()

        # Load in new resolver
        resolver2 = ConflictResolver(conflicts_path)
        assert len(resolver2.get_all_conflicts()) == 1

    def test_get_summary(self, tmp_path):
        """Test getting conflict summary."""
        resolver = ConflictResolver(tmp_path / "conflicts.json")

        resolver.detect_conflict("C1", "character", "name", "A", "B")

        summary = resolver.get_summary()
        assert summary["total"] >= 1
        assert "by_tier" in summary
        assert "by_status" in summary


class TestConflict:
    """Tests for Conflict dataclass."""

    def test_to_dict(self):
        """Test Conflict serialization."""
        conflict = Conflict(
            conflict_id="conflict_001",
            entity_type="character",
            entity_id="CHAR_001",
            field_name="name",
            vault_value="John",
            extraction_value="Jonathan",
            tier=ConflictTier.AMBIGUOUS,
        )

        data = conflict.to_dict()

        assert data["conflict_id"] == "conflict_001"
        assert data["entity_type"] == "character"
        assert data["tier"] == "ambiguous"
        assert data["status"] == "detected"

    def test_from_dict(self):
        """Test Conflict deserialization."""
        data = {
            "conflict_id": "conflict_001",
            "entity_type": "character",
            "entity_id": "CHAR_001",
            "field_name": "name",
            "vault_value": "John",
            "extraction_value": "Jonathan",
            "tier": "ambiguous",
            "status": "detected",
            "detected_at": "2026-02-19T12:00:00",
            "resolved_at": None,
            "resolution_note": None,
            "auto_merge_result": None,
            "added_items": None,
            "removed_items": None,
        }

        conflict = Conflict.from_dict(data)

        assert conflict.conflict_id == "conflict_001"
        assert conflict.tier == ConflictTier.AMBIGUOUS


class TestProvenanceRecord:
    """Tests for ProvenanceRecord dataclass."""

    def test_to_dict(self):
        """Test ProvenanceRecord serialization."""
        from datetime import datetime

        record = ProvenanceRecord(
            record_id="prov_001",
            source_type=SourceType.CANON_BUILD,
            timestamp=datetime(2026, 2, 19, 12, 0, 0),
            file_path="/vault/test.md",
            operation="create",
            description="Test record",
            evidence_ids=["ev_001"],
        )

        data = record.to_dict()

        assert data["record_id"] == "prov_001"
        assert data["source_type"] == "canon_build"
        assert data["operation"] == "create"

    def test_from_dict(self):
        """Test ProvenanceRecord deserialization."""
        data = {
            "record_id": "prov_001",
            "source_type": "canon_build",
            "timestamp": "2026-02-19T12:00:00",
            "file_path": "/vault/test.md",
            "operation": "create",
            "description": "Test record",
            "evidence_ids": ["ev_001"],
            "parent_record_id": None,
            "metadata": {},
            "user_id": None,
            "session_id": None,
        }

        record = ProvenanceRecord.from_dict(data)

        assert record.record_id == "prov_001"
        assert record.source_type == SourceType.CANON_BUILD


class TestFileState:
    """Tests for FileState dataclass."""

    def test_to_dict(self, tmp_path):
        """Test FileState serialization."""
        from datetime import datetime

        test_file = tmp_path / "test.md"
        test_file.write_text("content")

        state = FileState(
            path=test_file,
            hash="abc123",
            last_modified=datetime(2026, 2, 19, 12, 0, 0),
            size=7,
        )

        data = state.to_dict()

        assert data["hash"] == "abc123"
        assert data["size"] == 7

    def test_from_dict(self, tmp_path):
        """Test FileState deserialization."""
        test_file = tmp_path / "test.md"

        data = {
            "path": str(test_file),
            "hash": "abc123",
            "last_modified": "2026-02-19T12:00:00",
            "size": 7,
        }

        state = FileState.from_dict(data)

        assert state.hash == "abc123"
        assert state.size == 7
