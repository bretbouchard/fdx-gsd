"""Three-tier conflict resolution for vault synchronization.

Provides conflict detection, classification, and resolution for handling
discrepancies between vault content and extraction data.

Conflict Tiers:
    - SAFE: Auto-merge (array additions like aliases, evidence_ids)
    - AMBIGUOUS: Flag for review (scalar field changes)
    - CRITICAL: Block operation (entity ID/type changes)
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ConflictTier(Enum):
    """Severity tier for conflict classification."""

    SAFE = "safe"  # Auto-merge allowed (array additions)
    AMBIGUOUS = "ambiguous"  # Flag for review (scalar changes)
    CRITICAL = "critical"  # Block operation (identity changes)


class ConflictStatus(Enum):
    """Status of a conflict."""

    DETECTED = "detected"  # Newly detected, not yet resolved
    AUTO_RESOLVED = "auto_resolved"  # Automatically merged (SAFE tier)
    PENDING_REVIEW = "pending_review"  # Awaiting user decision (AMBIGUOUS)
    BLOCKED = "blocked"  # Cannot proceed without resolution (CRITICAL)
    RESOLVED = "resolved"  # User has resolved the conflict
    DISMISSED = "dismissed"  # User chose to keep existing value


@dataclass
class Conflict:
    """
    Represents a detected conflict between vault and extraction data.

    Tracks the field, values, tier classification, and resolution status.
    """

    conflict_id: str
    entity_type: str  # "character", "location", "scene"
    entity_id: str
    field_name: str
    vault_value: Any
    extraction_value: Any
    tier: ConflictTier
    status: ConflictStatus = ConflictStatus.DETECTED
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    auto_merge_result: Optional[Any] = None

    # For array fields, track what was added/removed
    added_items: Optional[List[Any]] = None
    removed_items: Optional[List[Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "conflict_id": self.conflict_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "vault_value": self.vault_value,
            "extraction_value": self.extraction_value,
            "tier": self.tier.value,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "auto_merge_result": self.auto_merge_result,
            "added_items": sorted(self.added_items) if self.added_items else None,
            "removed_items": sorted(self.removed_items) if self.removed_items else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conflict":
        """Create from dictionary."""
        return cls(
            conflict_id=data["conflict_id"],
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            field_name=data["field_name"],
            vault_value=data["vault_value"],
            extraction_value=data["extraction_value"],
            tier=ConflictTier(data["tier"]),
            status=ConflictStatus(data["status"]),
            detected_at=datetime.fromisoformat(data["detected_at"]),
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"])
                if data.get("resolved_at")
                else None
            ),
            resolution_note=data.get("resolution_note"),
            auto_merge_result=data.get("auto_merge_result"),
            added_items=data.get("added_items"),
            removed_items=data.get("removed_items"),
        )


class ConflictResolver:
    """
    Detects and resolves conflicts between vault and extraction data.

    Implements three-tier conflict classification:
    - SAFE: Array field additions can be auto-merged
    - AMBIGUOUS: Scalar field changes need review
    - CRITICAL: Identity field changes block operations
    """

    # Fields that can be safely auto-merged (arrays only)
    SAFE_ARRAY_FIELDS: Set[str] = {
        "aliases",
        "evidence_ids",
        "tags",
        "scenes",
        "characters",
        "locations",
        "beats",
    }

    # Fields that are CRITICAL - changing them breaks identity
    CRITICAL_FIELDS: Set[str] = {
        "entity_id",
        "canonical_id",
        "entity_type",
        "name",  # Name changes require disambiguation
    }

    # Fields that are AMBIGUOUS - scalar values needing review
    AMBIGUOUS_FIELDS: Set[str] = {
        "description",
        "notes",
        "summary",
        "time_of_day",
        "int_ext",
        "location_type",
    }

    # Conflict persistence path
    DEFAULT_CONFLICTS_PATH = Path("build/conflicts.json")

    def __init__(
        self,
        conflicts_path: Optional[Path] = None,
        auto_merge_safe: bool = True,
    ):
        """
        Initialize the conflict resolver.

        Args:
            conflicts_path: Path to persist conflicts JSON (default: build/conflicts.json)
            auto_merge_safe: Whether to auto-merge SAFE tier conflicts
        """
        self.conflicts_path = conflicts_path or self.DEFAULT_CONFLICTS_PATH
        self.auto_merge_safe = auto_merge_safe
        self._conflicts: Dict[str, Conflict] = {}
        self._conflict_counter = 0

        # Load existing conflicts if available
        if self.conflicts_path.exists():
            self._load_conflicts()

    def detect_conflict(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        vault_value: Any,
        extraction_value: Any,
    ) -> Optional[Conflict]:
        """
        Detect and classify a potential conflict.

        Args:
            entity_type: Type of entity ("character", "location", "scene")
            entity_id: Unique identifier for the entity
            field_name: Name of the field being compared
            vault_value: Current value in the vault
            extraction_value: Value from extraction

        Returns:
            Conflict object if a conflict exists, None if values match
        """
        # Normalize values for comparison
        vault_normalized = self._normalize_value(vault_value)
        extraction_normalized = self._normalize_value(extraction_value)

        # No conflict if values match
        if vault_normalized == extraction_normalized:
            return None

        # Classify the conflict tier
        tier = self._classify_conflict(field_name, vault_value, extraction_value)

        # Create conflict record
        self._conflict_counter += 1
        conflict = Conflict(
            conflict_id=f"conflict_{self._conflict_counter:06d}",
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            vault_value=vault_value,
            extraction_value=extraction_value,
            tier=tier,
        )

        # For array fields, calculate additions/removals
        if self._is_array_field(field_name):
            vault_set = set(vault_value) if vault_value else set()
            extraction_set = set(extraction_value) if extraction_value else set()
            conflict.added_items = list(extraction_set - vault_set) or None
            conflict.removed_items = list(vault_set - extraction_set) or None

        # Store and possibly auto-resolve
        self._conflicts[conflict.conflict_id] = conflict

        if tier == ConflictTier.SAFE and self.auto_merge_safe:
            self._auto_merge(conflict)

        return conflict

    def detect_all_conflicts(
        self,
        entity_type: str,
        entity_id: str,
        vault_data: Dict[str, Any],
        extraction_data: Dict[str, Any],
        fields_to_check: Optional[List[str]] = None,
    ) -> List[Conflict]:
        """
        Detect all conflicts between vault and extraction data for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Unique identifier
            vault_data: Dictionary of vault values
            extraction_data: Dictionary of extraction values
            fields_to_check: Optional list of fields to check (default: all common fields)

        Returns:
            List of detected Conflict objects
        """
        conflicts = []

        # Determine fields to check
        if fields_to_check:
            all_fields = set(fields_to_check)
        else:
            vault_fields = set(vault_data.keys())
            extraction_fields = set(extraction_data.keys())
            all_fields = vault_fields | extraction_fields

        for field_name in sorted(all_fields):  # Sorted for deterministic order
            vault_value = vault_data.get(field_name)
            extraction_value = extraction_data.get(field_name)

            conflict = self.detect_conflict(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                vault_value=vault_value,
                extraction_value=extraction_value,
            )

            if conflict:
                conflicts.append(conflict)

        return conflicts

    def _classify_conflict(
        self,
        field_name: str,
        vault_value: Any,
        extraction_value: Any,
    ) -> ConflictTier:
        """
        Classify the severity tier of a conflict.

        Args:
            field_name: Name of the conflicting field
            vault_value: Current vault value
            extraction_value: Extraction value

        Returns:
            ConflictTier classification
        """
        # CRITICAL: Identity fields
        if field_name in self.CRITICAL_FIELDS:
            return ConflictTier.CRITICAL

        # Check if this is an array field with only additions
        if self._is_array_field(field_name):
            vault_set = set(vault_value) if vault_value else set()
            extraction_set = set(extraction_value) if extraction_value else set()

            # SAFE: Only additions (no removals)
            if extraction_set >= vault_set:  # extraction is superset of vault
                return ConflictTier.SAFE

            # Has removals - needs review
            return ConflictTier.AMBIGUOUS

        # Explicit ambiguous fields
        if field_name in self.AMBIGUOUS_FIELDS:
            return ConflictTier.AMBIGUOUS

        # Default: any other scalar field is ambiguous
        return ConflictTier.AMBIGUOUS

    def _is_array_field(self, field_name: str) -> bool:
        """Check if a field is an array type."""
        return field_name in self.SAFE_ARRAY_FIELDS

    def _normalize_value(self, value: Any) -> Any:
        """Normalize a value for comparison."""
        if value is None:
            return None
        if isinstance(value, list):
            return sorted(value) if all(isinstance(x, (str, int, float)) for x in value) else value
        if isinstance(value, str):
            return value.strip()
        return value

    def _auto_merge(self, conflict: Conflict) -> None:
        """
        Auto-merge a SAFE tier conflict.

        For array fields, merges additions into vault value.
        """
        if conflict.tier != ConflictTier.SAFE:
            return

        if self._is_array_field(conflict.field_name):
            vault_list = list(conflict.vault_value) if conflict.vault_value else []
            extraction_list = list(conflict.extraction_value) if conflict.extraction_value else []

            # Merge: union of both lists
            merged = list(set(vault_list) | set(extraction_list))
            merged.sort()  # Deterministic output

            conflict.auto_merge_result = merged
            conflict.status = ConflictStatus.AUTO_RESOLVED
            conflict.resolved_at = datetime.now()
            conflict.resolution_note = "Auto-merged array additions"

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        note: Optional[str] = None,
    ) -> Optional[Conflict]:
        """
        Manually resolve a conflict.

        Args:
            conflict_id: ID of the conflict to resolve
            resolution: Resolution choice ("vault", "extraction", "custom")
            note: Optional resolution note

        Returns:
            Updated Conflict object, or None if not found
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        conflict.resolved_at = datetime.now()
        conflict.resolution_note = note

        if resolution == "vault":
            conflict.status = ConflictStatus.DISMISSED
        elif resolution == "extraction":
            conflict.status = ConflictStatus.RESOLVED
            conflict.auto_merge_result = conflict.extraction_value
        elif resolution == "custom":
            conflict.status = ConflictStatus.RESOLVED

        return conflict

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Get a specific conflict by ID."""
        return self._conflicts.get(conflict_id)

    def get_all_conflicts(self) -> List[Conflict]:
        """Get all conflicts, sorted by detection time."""
        return sorted(self._conflicts.values(), key=lambda c: c.detected_at)

    def get_conflicts_by_tier(self, tier: ConflictTier) -> List[Conflict]:
        """Get all conflicts of a specific tier."""
        return [c for c in self.get_all_conflicts() if c.tier == tier]

    def get_conflicts_by_status(self, status: ConflictStatus) -> List[Conflict]:
        """Get all conflicts with a specific status."""
        return [c for c in self.get_all_conflicts() if c.status == status]

    def get_conflicts_for_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> List[Conflict]:
        """Get all conflicts for a specific entity."""
        return [
            c
            for c in self.get_all_conflicts()
            if c.entity_type == entity_type and c.entity_id == entity_id
        ]

    def get_pending_conflicts(self) -> List[Conflict]:
        """Get all conflicts requiring attention (not resolved)."""
        pending_statuses = {
            ConflictStatus.DETECTED,
            ConflictStatus.PENDING_REVIEW,
            ConflictStatus.BLOCKED,
        }
        return [c for c in self.get_all_conflicts() if c.status in pending_statuses]

    def has_critical_conflicts(self) -> bool:
        """Check if any CRITICAL tier conflicts exist."""
        return any(c.tier == ConflictTier.CRITICAL for c in self._conflicts.values())

    def has_blocked_conflicts(self) -> bool:
        """Check if any BLOCKED status conflicts exist."""
        return any(c.status == ConflictStatus.BLOCKED for c in self._conflicts.values())

    def can_proceed(self) -> bool:
        """
        Check if sync operation can proceed.

        Returns:
            True if no CRITICAL conflicts and no BLOCKED status conflicts
        """
        return not self.has_critical_conflicts() and not self.has_blocked_conflicts()

    def block_conflict(self, conflict_id: str, reason: str) -> Optional[Conflict]:
        """
        Mark a conflict as blocking.

        Args:
            conflict_id: ID of the conflict
            reason: Reason for blocking

        Returns:
            Updated Conflict, or None if not found
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        conflict.status = ConflictStatus.BLOCKED
        conflict.resolution_note = reason
        return conflict

    def clear_conflicts(self) -> None:
        """Clear all conflicts from memory."""
        self._conflicts = {}
        self._conflict_counter = 0

    def save_conflicts(self) -> None:
        """Persist conflicts to JSON file."""
        self.conflicts_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "total_conflicts": len(self._conflicts),
            "summary": self.get_summary(),
            "conflicts": [c.to_dict() for c in self.get_all_conflicts()],
        }

        self.conflicts_path.write_text(
            json.dumps(data, indent=2, sort_keys=True)
        )

    def _load_conflicts(self) -> None:
        """Load conflicts from JSON file."""
        if not self.conflicts_path.exists():
            return

        data = json.loads(self.conflicts_path.read_text())

        for conflict_data in data.get("conflicts", []):
            conflict = Conflict.from_dict(conflict_data)
            self._conflicts[conflict.conflict_id] = conflict

            # Update counter to avoid ID collisions
            if conflict.conflict_id.startswith("conflict_"):
                try:
                    num = int(conflict.conflict_id.split("_")[1])
                    self._conflict_counter = max(self._conflict_counter, num)
                except (IndexError, ValueError):
                    pass

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all conflicts.

        Returns:
            Dict with counts by tier, status, and entity type
        """
        tier_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        entity_counts: Dict[str, int] = {}

        for conflict in self._conflicts.values():
            tier_key = conflict.tier.value
            tier_counts[tier_key] = tier_counts.get(tier_key, 0) + 1

            status_key = conflict.status.value
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

            entity_key = conflict.entity_type
            entity_counts[entity_key] = entity_counts.get(entity_key, 0) + 1

        return {
            "total": len(self._conflicts),
            "by_tier": tier_counts,
            "by_status": status_counts,
            "by_entity_type": entity_counts,
            "can_proceed": self.can_proceed(),
            "pending_count": len(self.get_pending_conflicts()),
        }

    def merge_safe_conflicts(self) -> List[Conflict]:
        """
        Auto-merge all SAFE tier conflicts.

        Returns:
            List of conflicts that were auto-merged
        """
        merged = []
        for conflict in self.get_conflicts_by_tier(ConflictTier.SAFE):
            if conflict.status == ConflictStatus.DETECTED:
                self._auto_merge(conflict)
                if conflict.status == ConflictStatus.AUTO_RESOLVED:
                    merged.append(conflict)

        return merged

    def get_auto_merge_result(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
    ) -> Optional[Any]:
        """
        Get the auto-merge result for a specific field.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            field_name: Field name

        Returns:
            Auto-merged value if available, None otherwise
        """
        for conflict in self.get_conflicts_for_entity(entity_type, entity_id):
            if conflict.field_name == field_name and conflict.auto_merge_result is not None:
                return conflict.auto_merge_result
        return None
