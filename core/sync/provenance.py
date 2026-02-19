"""Provenance tracking for vault synchronization.

Tracks the source and history of changes to vault content,
enabling audit trails and change attribution.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4


class SourceType(Enum):
    """Type of source that produced a change."""

    CANON_BUILD = "canon_build"
    SCRIPT_BUILD = "script_build"
    MANUAL_EDIT = "manual_edit"
    DISAMBIGUATION = "disambiguation"
    IMPORT = "import"
    SYNC = "sync"
    SYSTEM = "system"


@dataclass
class ProvenanceRecord:
    """
    Records the provenance of a content change.

    Tracks where a change came from, when it was made,
    and what evidence supports it.
    """

    record_id: str
    source_type: SourceType
    timestamp: datetime
    file_path: str
    operation: str  # "create", "update", "delete"
    description: str
    evidence_ids: List[str] = field(default_factory=list)
    parent_record_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None  # For manual edits
    session_id: Optional[str] = None  # Build session identifier

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "record_id": self.record_id,
            "source_type": self.source_type.value,
            "timestamp": self.timestamp.isoformat(),
            "file_path": self.file_path,
            "operation": self.operation,
            "description": self.description,
            "evidence_ids": sorted(self.evidence_ids),  # Deterministic output
            "parent_record_id": self.parent_record_id,
            "metadata": self.metadata,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceRecord":
        """Create from dictionary."""
        return cls(
            record_id=data["record_id"],
            source_type=SourceType(data["source_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            file_path=data["file_path"],
            operation=data["operation"],
            description=data["description"],
            evidence_ids=data.get("evidence_ids", []),
            parent_record_id=data.get("parent_record_id"),
            metadata=data.get("metadata", {}),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
        )


class ProvenanceTracker:
    """
    Tracks provenance records for vault changes.

    Maintains an append-only log of all changes with full
    attribution and evidence linking.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize the provenance tracker.

        Args:
            storage_path: Optional path to persist provenance log
            session_id: Optional session identifier for grouping records
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.session_id = session_id or str(uuid4())[:8]
        self._records: List[ProvenanceRecord] = []
        self._record_index: Dict[str, ProvenanceRecord] = {}

        # Load existing records if storage exists
        if self.storage_path and self.storage_path.exists():
            self._load_from_storage()

    def record(
        self,
        source_type: SourceType,
        file_path: Path,
        operation: str,
        description: str,
        evidence_ids: Optional[List[str]] = None,
        parent_record_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> ProvenanceRecord:
        """
        Record a provenance event.

        Args:
            source_type: Type of source producing the change
            file_path: Path to affected file
            operation: Operation type (create, update, delete)
            description: Human-readable description
            evidence_ids: Optional list of evidence IDs
            parent_record_id: Optional parent record for chaining
            metadata: Optional additional metadata
            user_id: Optional user ID for manual edits

        Returns:
            Created ProvenanceRecord
        """
        record = ProvenanceRecord(
            record_id=f"prov_{uuid4().hex[:12]}",
            source_type=source_type,
            timestamp=datetime.now(),
            file_path=str(file_path),
            operation=operation,
            description=description,
            evidence_ids=evidence_ids or [],
            parent_record_id=parent_record_id,
            metadata=metadata or {},
            user_id=user_id,
            session_id=self.session_id,
        )

        self._records.append(record)
        self._record_index[record.record_id] = record

        # Auto-persist if storage path is set
        if self.storage_path:
            self._save_to_storage()

        return record

    def get_record(self, record_id: str) -> Optional[ProvenanceRecord]:
        """
        Get a specific record by ID.

        Args:
            record_id: The record identifier

        Returns:
            ProvenanceRecord if found, None otherwise
        """
        return self._record_index.get(record_id)

    def get_records_for_file(self, file_path: Path) -> List[ProvenanceRecord]:
        """
        Get all records for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of ProvenanceRecords for the file, sorted by timestamp
        """
        path_str = str(file_path)
        records = [
            r for r in self._records if r.file_path == path_str
        ]
        return sorted(records, key=lambda r: r.timestamp)

    def get_records_by_source(
        self,
        source_type: SourceType,
    ) -> List[ProvenanceRecord]:
        """
        Get all records from a specific source type.

        Args:
            source_type: The source type to filter by

        Returns:
            List of ProvenanceRecords from that source
        """
        return [
            r for r in self._records if r.source_type == source_type
        ]

    def get_records_by_session(self, session_id: str) -> List[ProvenanceRecord]:
        """
        Get all records from a specific session.

        Args:
            session_id: The session identifier

        Returns:
            List of ProvenanceRecords from that session
        """
        return [
            r for r in self._records if r.session_id == session_id
        ]

    def get_latest_record_for_file(
        self,
        file_path: Path,
    ) -> Optional[ProvenanceRecord]:
        """
        Get the most recent record for a file.

        Args:
            file_path: Path to the file

        Returns:
            Most recent ProvenanceRecord, or None if no records exist
        """
        records = self.get_records_for_file(file_path)
        return records[-1] if records else None

    def get_lineage(self, record_id: str) -> List[ProvenanceRecord]:
        """
        Get the full lineage (chain of parent records) for a record.

        Args:
            record_id: The record identifier

        Returns:
            List of records from oldest to newest
        """
        lineage = []
        current = self.get_record(record_id)

        while current:
            lineage.append(current)
            if current.parent_record_id:
                current = self.get_record(current.parent_record_id)
            else:
                break

        return list(reversed(lineage))

    def get_all_records(self) -> List[ProvenanceRecord]:
        """
        Get all records, sorted by timestamp.

        Returns:
            List of all ProvenanceRecords
        """
        return sorted(self._records, key=lambda r: r.timestamp)

    def get_records_by_operation(self, operation: str) -> List[ProvenanceRecord]:
        """
        Get all records for a specific operation type.

        Args:
            operation: Operation type (create, update, delete)

        Returns:
            List of matching ProvenanceRecords
        """
        return [
            r for r in self._records if r.operation == operation
        ]

    def get_records_with_evidence(self, evidence_id: str) -> List[ProvenanceRecord]:
        """
        Get all records that reference a specific evidence ID.

        Args:
            evidence_id: The evidence identifier

        Returns:
            List of ProvenanceRecords referencing the evidence
        """
        return [
            r for r in self._records if evidence_id in r.evidence_ids
        ]

    def clear_records(self) -> None:
        """Clear all records from memory (does not delete storage)."""
        self._records = []
        self._record_index = {}

    def _load_from_storage(self) -> None:
        """Load records from storage file."""
        if not self.storage_path or not self.storage_path.exists():
            return

        data = json.loads(self.storage_path.read_text())

        for record_data in data.get("records", []):
            record = ProvenanceRecord.from_dict(record_data)
            self._records.append(record)
            self._record_index[record.record_id] = record

    def _save_to_storage(self) -> None:
        """Save records to storage file."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "session_id": self.session_id,
            "records": [r.to_dict() for r in self.get_all_records()],
        }

        self.storage_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def export_to_json(self, output_path: Path) -> None:
        """
        Export all records to a JSON file.

        Args:
            output_path: Path to write the export
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "total_records": len(self._records),
            "records": [r.to_dict() for r in self.get_all_records()],
        }

        output_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of tracked provenance.

        Returns:
            Dict with counts by source type, operation, etc.
        """
        source_counts: Dict[str, int] = {}
        operation_counts: Dict[str, int] = {}

        for record in self._records:
            source_key = record.source_type.value
            source_counts[source_key] = source_counts.get(source_key, 0) + 1

            operation_counts[record.operation] = (
                operation_counts.get(record.operation, 0) + 1
            )

        return {
            "total_records": len(self._records),
            "session_id": self.session_id,
            "by_source": source_counts,
            "by_operation": operation_counts,
            "unique_files": len(set(r.file_path for r in self._records)),
        }
