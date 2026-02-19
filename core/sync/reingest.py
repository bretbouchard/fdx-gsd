"""Reingestion pipeline for vault-to-StoryGraph synchronization.

Provides the VaultReingester class for detecting modified vault files,
parsing their content, merging with existing StoryGraph entities,
flagging conflicts, and saving updated StoryGraph.

Pipeline stages:
    1. Detect modified vault files (ChangeDetector)
    2. Parse vault note content (frontmatter + body)
    3. Merge with existing StoryGraph entities
    4. Flag conflicts for review (ConflictResolver)
    5. Track provenance (ProvenanceTracker)
    6. Save updated StoryGraph
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .change_detector import ChangeDetector, ChangeRecord
from .conflict_resolver import Conflict, ConflictResolver, ConflictStatus, ConflictTier
from .provenance import ProvenanceRecord, ProvenanceTracker, SourceType


# Vault directory patterns by entity type
VAULT_DIRS = {
    "character": "10_Characters",
    "location": "20_Locations",
    "scene": "50_Scenes",
}

# Entity type prefixes for ID generation
ENTITY_PREFIXES = {
    "character": "CHAR",
    "location": "LOC",
    "scene": "SCN",
}


@dataclass
class ParsedNote:
    """Represents a parsed vault note."""

    file_path: Path
    entity_type: str
    frontmatter: Dict[str, Any]
    body: str
    protected_content: Optional[str] = None
    manual_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": str(self.file_path),
            "entity_type": self.entity_type,
            "frontmatter": self.frontmatter,
            "body": self.body,
            "protected_content": self.protected_content,
            "manual_notes": self.manual_notes,
        }


@dataclass
class EntityUpdate:
    """Represents an update to be applied to an entity."""

    entity_type: str
    entity_id: str
    field_name: str
    old_value: Any
    new_value: Any
    source: str  # "vault" or "extraction"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source": self.source,
        }


@dataclass
class ReingestResult:
    """Result of a reingestion operation."""

    success: bool
    files_processed: int
    entities_updated: int
    conflicts_detected: int
    conflicts_auto_resolved: int
    conflicts_pending: int
    conflicts_blocked: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    updated_entities: List[str] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    provenance_records: List[ProvenanceRecord] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "files_processed": self.files_processed,
            "entities_updated": self.entities_updated,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_auto_resolved": self.conflicts_auto_resolved,
            "conflicts_pending": self.conflicts_pending,
            "conflicts_blocked": self.conflicts_blocked,
            "errors": self.errors,
            "warnings": self.warnings,
            "updated_entities": self.updated_entities,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "provenance_records": [p.to_dict() for p in self.provenance_records],
            "duration_seconds": self.duration_seconds,
        }


def extract_frontmatter(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract YAML frontmatter from markdown text.

    Args:
        text: Full markdown content

    Returns:
        Dict of frontmatter values, or None if no frontmatter found
    """
    import yaml

    # Match frontmatter between --- delimiters
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, text, re.DOTALL)

    if not match:
        return None

    try:
        frontmatter_text = match.group(1)
        return yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None


def parse_frontmatter_yaml(text: str) -> Dict[str, Any]:
    """
    Parse YAML frontmatter into a dictionary.

    Args:
        text: Text starting with YAML frontmatter

    Returns:
        Dictionary of parsed values, empty dict if parsing fails
    """
    result = extract_frontmatter(text)
    return result if result else {}


def get_entity_type_from_path(file_path: Path) -> Optional[str]:
    """
    Determine entity type from vault file path.

    Args:
        file_path: Path to vault note

    Returns:
        Entity type string or None if not a managed directory
    """
    path_str = str(file_path)

    for entity_type, dir_name in VAULT_DIRS.items():
        if f"/{dir_name}/" in path_str or path_str.endswith(f"/{dir_name}"):
            return entity_type

    return None


def extract_manual_notes(text: str) -> Optional[str]:
    """
    Extract manual notes section from vault note.

    Notes section is expected after the protected block,
    typically marked with "## Notes" heading.

    Args:
        text: Full markdown content

    Returns:
        Manual notes content, or None if not found
    """
    # Look for ## Notes section
    pattern = r"^##\s+Notes\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)

    if match:
        return match.group(1).strip()

    return None


class VaultReingester:
    """
    Reingests vault changes back into StoryGraph.

    Coordinates the full pipeline:
    1. Detect modified vault files
    2. Parse note content (frontmatter + body)
    3. Merge with existing entities
    4. Flag conflicts
    5. Track provenance
    6. Save updated StoryGraph
    """

    def __init__(
        self,
        vault_path: Path,
        storygraph_path: Path,
        baseline_path: Optional[Path] = None,
        conflicts_path: Optional[Path] = None,
        provenance_path: Optional[Path] = None,
        auto_merge_safe: bool = True,
    ):
        """
        Initialize the vault reingester.

        Args:
            vault_path: Path to Obsidian vault root
            storygraph_path: Path to storygraph.json
            baseline_path: Path to baseline JSON for change detection
            conflicts_path: Path to persist conflicts
            provenance_path: Path to persist provenance records
            auto_merge_safe: Whether to auto-merge SAFE tier conflicts
        """
        self.vault_path = Path(vault_path)
        self.storygraph_path = Path(storygraph_path)

        # Initialize change detector
        baseline_file = baseline_path or (self.vault_path.parent / "build" / "sync_baseline.json")
        self.change_detector = ChangeDetector.load_baseline(baseline_file)

        # Initialize conflict resolver
        conflicts_file = conflicts_path or (self.vault_path.parent / "build" / "conflicts.json")
        self.conflict_resolver = ConflictResolver(
            conflicts_path=conflicts_file,
            auto_merge_safe=auto_merge_safe,
        )

        # Initialize provenance tracker
        provenance_file = provenance_path or (self.vault_path.parent / "build" / "provenance.json")
        self.provenance_tracker = ProvenanceTracker(
            storage_path=provenance_file,
        )

        # Load current StoryGraph
        self.storygraph = self._load_storygraph()

        # Build entity lookup index
        self._entity_index: Dict[str, Dict[str, Any]] = {}
        self._build_entity_index()

        # Track warnings during operations
        self.warnings: List[str] = []

    def _load_storygraph(self) -> Dict[str, Any]:
        """Load StoryGraph from JSON file."""
        if not self.storygraph_path.exists():
            return {
                "version": "1.0",
                "project_id": "unknown",
                "entities": [],
                "edges": [],
                "evidence_index": {},
            }

        return json.loads(self.storygraph_path.read_text())

    def _save_storygraph(self) -> None:
        """Save StoryGraph to JSON file."""
        self.storygraph_path.parent.mkdir(parents=True, exist_ok=True)

        # Update generated_at timestamp
        self.storygraph["generated_at"] = datetime.now().isoformat()

        # Sort entities for deterministic output
        self.storygraph["entities"] = sorted(
            self.storygraph["entities"],
            key=lambda e: (e.get("type", ""), e.get("id", ""))
        )

        self.storygraph_path.write_text(
            json.dumps(self.storygraph, indent=2, sort_keys=True)
        )

    def _build_entity_index(self) -> None:
        """Build lookup index by entity ID."""
        self._entity_index = {}

        for entity in self.storygraph.get("entities", []):
            entity_id = entity.get("id")
            if entity_id:
                self._entity_index[entity_id] = entity

    def _get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID from index."""
        return self._entity_index.get(entity_id)

    def _get_entity_by_name(
        self,
        name: str,
        entity_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get entity by name (and optionally type)."""
        for entity in self.storygraph.get("entities", []):
            if entity.get("name") == name:
                if entity_type is None or entity.get("type") == entity_type:
                    return entity
        return None

    def get_vault_files(self, entity_types: Optional[List[str]] = None) -> List[Path]:
        """
        Get all managed vault files.

        Args:
            entity_types: Optional filter by entity types

        Returns:
            List of vault file paths
        """
        files = []
        types_to_scan = entity_types or list(VAULT_DIRS.keys())

        for entity_type in types_to_scan:
            if entity_type not in VAULT_DIRS:
                continue

            dir_name = VAULT_DIRS[entity_type]
            dir_path = self.vault_path / dir_name

            if dir_path.exists():
                for md_file in dir_path.glob("*.md"):
                    files.append(md_file)

        return sorted(files)

    def detect_modified_files(
        self,
        entity_types: Optional[List[str]] = None,
    ) -> List[ChangeRecord]:
        """
        Detect vault files modified since baseline.

        Args:
            entity_types: Optional filter by entity types

        Returns:
            List of ChangeRecord for modified files
        """
        current_files = self.get_vault_files(entity_types)
        return self.change_detector.detect_changes(current_files)

    def parse_vault_note(self, file_path: Path) -> Optional[ParsedNote]:
        """
        Parse a vault note file.

        Args:
            file_path: Path to the note file

        Returns:
            ParsedNote object, or None if parsing fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Determine entity type from path
        entity_type = get_entity_type_from_path(file_path)
        if not entity_type:
            return None

        # Extract frontmatter
        frontmatter = parse_frontmatter_yaml(text)

        # Extract body (everything after frontmatter)
        body = text
        fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        if fm_match:
            body = text[fm_match.end():]

        # Extract protected content
        from .protected_blocks import extract_protected_content
        protected_blocks = extract_protected_content(body)
        protected_content = None
        if protected_blocks:
            protected_content = protected_blocks[0].content

        # Extract manual notes
        manual_notes = extract_manual_notes(text)

        return ParsedNote(
            file_path=file_path,
            entity_type=entity_type,
            frontmatter=frontmatter,
            body=body,
            protected_content=protected_content,
            manual_notes=manual_notes,
        )

    def extract_entity_data(self, note: ParsedNote) -> Dict[str, Any]:
        """
        Extract entity data from a parsed note.

        Combines frontmatter and structured body content.

        Args:
            note: Parsed vault note

        Returns:
            Dictionary of entity data
        """
        data = {}

        # Get frontmatter values
        fm = note.frontmatter

        # Common fields
        if "id" in fm:
            data["id"] = fm["id"]
        if "name" in fm:
            data["name"] = fm["name"]
        if "aliases" in fm:
            data["aliases"] = fm["aliases"] if isinstance(fm["aliases"], list) else []

        # Type-specific fields
        if note.entity_type == "character":
            # Characters have aliases list
            pass

        elif note.entity_type == "location":
            if "int_ext" in fm:
                data.setdefault("attributes", {})["int_ext"] = fm["int_ext"]
            if "time_of_day" in fm:
                data.setdefault("attributes", {})["time_of_day"] = fm["time_of_day"]

        elif note.entity_type == "scene":
            if "scene_number" in fm:
                data["scene_number"] = fm["scene_number"]
            if "location" in fm:
                data.setdefault("attributes", {})["location"] = fm["location"]
            if "int_ext" in fm:
                data.setdefault("attributes", {})["int_ext"] = fm["int_ext"]
            if "time_of_day" in fm:
                data.setdefault("attributes", {})["time_of_day"] = fm["time_of_day"]

        # Extract evidence IDs from wikilinks in body
        evidence_ids = self._extract_evidence_ids_from_body(note.body)
        if evidence_ids:
            data["evidence_ids"] = evidence_ids

        # Parse aliases from protected content
        if note.protected_content:
            aliases = self._extract_aliases_from_protected(note.protected_content)
            if aliases:
                # Merge with frontmatter aliases
                existing = set(data.get("aliases", []))
                data["aliases"] = sorted(existing | set(aliases))

        return data

    def _extract_evidence_ids_from_body(self, body: str) -> List[str]:
        """Extract evidence IDs from wikilinks in body."""
        # Pattern: [[path#^ev_xxx]]
        pattern = r"\[\[[^\]]*#\^(ev_[a-z0-9]+)\]\]"
        matches = re.findall(pattern, body)
        return sorted(set(matches))

    def _extract_aliases_from_protected(self, content: str) -> List[str]:
        """Extract aliases from protected block content."""
        aliases = []

        # Look for ## Aliases section
        pattern = r"##\s+Aliases\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            aliases_text = match.group(1)
            # Parse list items
            for line in aliases_text.strip().split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    alias = line[2:].strip()
                    if alias and alias != "*None recorded*":
                        aliases.append(alias)

        return aliases

    def merge_entity(
        self,
        entity_id: str,
        vault_data: Dict[str, Any],
    ) -> List[Conflict]:
        """
        Merge vault data with existing entity.

        Args:
            entity_id: Entity ID to merge
            vault_data: Data extracted from vault

        Returns:
            List of detected conflicts
        """
        existing = self._get_entity_by_id(entity_id)
        if not existing:
            self.warnings.append(f"Entity {entity_id} not found in StoryGraph")
            return []

        entity_type = existing.get("type", "unknown")
        conflicts = []

        # Check each field for conflicts
        for field_name, vault_value in vault_data.items():
            if field_name == "id":
                continue  # Skip ID field

            existing_value = existing.get(field_name)

            # Handle attributes nested object
            if field_name == "attributes":
                existing_attrs = existing_value or {}
                vault_attrs = vault_value or {}

                for attr_name, attr_value in vault_attrs.items():
                    existing_attr = existing_attrs.get(attr_name)

                    conflict = self.conflict_resolver.detect_conflict(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        field_name=attr_name,
                        vault_value=attr_value,
                        extraction_value=existing_attr,
                    )

                    if conflict:
                        conflicts.append(conflict)

                continue

            # Regular field comparison
            conflict = self.conflict_resolver.detect_conflict(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                vault_value=vault_value,
                extraction_value=existing_value,
            )

            if conflict:
                conflicts.append(conflict)

        return conflicts

    def apply_merge(
        self,
        entity_id: str,
        vault_data: Dict[str, Any],
    ) -> bool:
        """
        Apply merged data to entity.

        Only applies auto-merged SAFE conflicts and non-conflicting fields.

        Args:
            entity_id: Entity ID to update
            vault_data: Data extracted from vault

        Returns:
            True if any changes were applied
        """
        existing = self._get_entity_by_id(entity_id)
        if not existing:
            return False

        entity_type = existing.get("type", "unknown")
        changes_made = False

        for field_name, vault_value in vault_data.items():
            if field_name == "id":
                continue

            existing_value = existing.get(field_name)

            # Handle attributes
            if field_name == "attributes":
                existing_attrs = existing_value or {}
                vault_attrs = vault_value or {}

                for attr_name, attr_value in vault_attrs.items():
                    existing_attr = existing_attrs.get(attr_name)

                    # Check for auto-merge result
                    auto_result = self.conflict_resolver.get_auto_merge_result(
                        entity_type, entity_id, attr_name
                    )

                    if auto_result is not None:
                        existing_attrs[attr_name] = auto_result
                        changes_made = True
                    elif attr_value != existing_attr and existing_attr is None:
                        # No conflict, new field
                        existing_attrs[attr_name] = attr_value
                        changes_made = True

                if changes_made:
                    existing["attributes"] = existing_attrs

                continue

            # Check for auto-merge result
            auto_result = self.conflict_resolver.get_auto_merge_result(
                entity_type, entity_id, field_name
            )

            if auto_result is not None:
                existing[field_name] = auto_result
                changes_made = True
            elif vault_value != existing_value and existing_value is None:
                # No conflict, new field
                existing[field_name] = vault_value
                changes_made = True
            elif vault_value == existing_value:
                # Same value, no action needed
                pass

        return changes_made

    def reingest_file(self, file_path: Path) -> Tuple[List[Conflict], bool]:
        """
        Reingest a single vault file.

        Args:
            file_path: Path to vault note

        Returns:
            Tuple of (conflicts list, was_updated bool)
        """
        # Parse the note
        note = self.parse_vault_note(file_path)
        if not note:
            return [], False

        # Extract entity data
        vault_data = self.extract_entity_data(note)

        # Get entity ID from frontmatter or try to match by name
        entity_id = vault_data.get("id")
        if not entity_id:
            # Try to find by name
            entity = self._get_entity_by_name(
                vault_data.get("name"),
                note.entity_type
            )
            if entity:
                entity_id = entity.get("id")

        if not entity_id:
            return [], False

        # Detect conflicts
        conflicts = self.merge_entity(entity_id, vault_data)

        # Apply merges
        updated = self.apply_merge(entity_id, vault_data)

        # Record provenance if updated
        if updated:
            self.provenance_tracker.record(
                source_type=SourceType.SYNC,
                file_path=file_path,
                operation="update",
                description=f"Reingested vault changes for {entity_id}",
                metadata={"entity_id": entity_id, "conflicts": len(conflicts)},
            )

        return conflicts, updated

    def reingest_all(
        self,
        entity_types: Optional[List[str]] = None,
        include_unchanged: bool = False,
    ) -> ReingestResult:
        """
        Reingest all modified vault files.

        Args:
            entity_types: Optional filter by entity types
            include_unchanged: Also process unchanged files

        Returns:
            ReingestResult with statistics and details
        """
        start_time = datetime.now()
        result = ReingestResult(
            success=True,
            files_processed=0,
            entities_updated=0,
            conflicts_detected=0,
            conflicts_auto_resolved=0,
            conflicts_pending=0,
            conflicts_blocked=0,
        )

        # Get files to process
        if include_unchanged:
            files = self.get_vault_files(entity_types)
        else:
            changes = self.detect_modified_files(entity_types)
            files = [c.path for c in changes if c.change_type in ("added", "modified")]

        # Process each file
        for file_path in files:
            try:
                conflicts, updated = self.reingest_file(file_path)
                result.files_processed += 1

                if updated:
                    result.entities_updated += 1
                    result.updated_entities.append(str(file_path))

                result.conflicts_detected += len(conflicts)
                result.conflicts.extend(conflicts)

            except Exception as e:
                result.errors.append(f"Error processing {file_path}: {str(e)}")
                result.success = False

        # Count conflict states
        for conflict in result.conflicts:
            if conflict.status == ConflictStatus.AUTO_RESOLVED:
                result.conflicts_auto_resolved += 1
            elif conflict.status == ConflictStatus.BLOCKED:
                result.conflicts_blocked += 1
            elif conflict.status in (ConflictStatus.DETECTED, ConflictStatus.PENDING_REVIEW):
                result.conflicts_pending += 1

        # Check if we can proceed
        if not self.conflict_resolver.can_proceed():
            result.success = False
            result.warnings.append("Cannot save due to CRITICAL or BLOCKED conflicts")

        # Save if successful
        if result.success and result.entities_updated > 0:
            self._save_storygraph()
            self.conflict_resolver.save_conflicts()

        # Get provenance records
        result.provenance_records = self.provenance_tracker.get_all_records()

        # Calculate duration
        end_time = datetime.now()
        result.duration_seconds = (end_time - start_time).total_seconds()

        return result

    def update_baseline(self) -> None:
        """Update baseline to current file states."""
        files = self.get_vault_files()
        baseline = {}

        for file_path in files:
            state = self.change_detector.get_file_state(file_path)
            baseline[str(file_path)] = state

        self.change_detector.set_baseline(baseline)

        # Save baseline
        baseline_path = self.vault_path.parent / "build" / "sync_baseline.json"
        self.change_detector.save_baseline(baseline_path)

    def get_conflicts_summary(self) -> Dict[str, Any]:
        """Get summary of all conflicts."""
        return self.conflict_resolver.get_summary()

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        note: Optional[str] = None,
    ) -> Optional[Conflict]:
        """
        Manually resolve a conflict.

        Args:
            conflict_id: Conflict ID
            resolution: "vault", "extraction", or "custom"
            note: Optional resolution note

        Returns:
            Updated Conflict, or None if not found
        """
        return self.conflict_resolver.resolve_conflict(conflict_id, resolution, note)


# Convenience function
def reingest_vault(
    vault_path: Path,
    storygraph_path: Path,
    entity_types: Optional[List[str]] = None,
) -> ReingestResult:
    """
    Reingest vault changes into StoryGraph.

    Args:
        vault_path: Path to vault root
        storygraph_path: Path to storygraph.json
        entity_types: Optional filter by entity types

    Returns:
        ReingestResult with statistics
    """
    reingester = VaultReingester(vault_path, storygraph_path)
    return reingester.reingest_all(entity_types)
