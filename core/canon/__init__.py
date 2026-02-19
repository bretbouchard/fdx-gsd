"""Canon builder - Orchestrates entity extraction and vault writing.

Wires together:
- Entity extractors (characters, locations, scenes)
- Alias resolution (fuzzy matching)
- Disambiguation queue
- Evidence linking
- Vault note generation
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..extraction import (
    CharacterExtractor,
    LocationExtractor,
    SceneExtractor,
    SceneBoundary,
    ExtractionCandidate,
)
from ..resolution import FuzzyMatcher, create_matcher
from ..vault import VaultNoteWriter

# Constants
FUZZY_QUEUE_THRESHOLD = 50  # Minimum score to consider fuzzy match for queueing
FUZZY_MERGE_THRESHOLD = 70  # Score at which we suggest merge vs link


@dataclass
class CanonBuildResult:
    """Result of a canon build operation."""
    success: bool
    characters_created: int = 0
    characters_linked: int = 0
    locations_created: int = 0
    locations_linked: int = 0
    scenes_created: int = 0
    queue_items: int = 0
    vault_notes_written: int = 0
    errors: List[str] = field(default_factory=list)


class CanonBuilder:
    """Builds canonical entities from inbox content."""

    def __init__(self, project_path: Path, config: Dict[str, Any] = None):
        """
        Initialize the canon builder.

        Args:
            project_path: Path to project root
            config: Project configuration from gsd.yaml
        """
        self.project_path = Path(project_path)
        self.config = config or {}

        # Paths
        self.inbox_path = self.project_path / "inbox"
        self.vault_path = self.project_path / "vault"
        self.build_path = self.project_path / "build"

        # Extractors
        self.char_extractor = CharacterExtractor()
        self.loc_extractor = LocationExtractor()
        self.scene_extractor = SceneExtractor()

        # Matcher
        disambig_config = self.config.get("disambiguation", {})
        self.matcher = create_matcher(
            threshold=disambig_config.get("fuzzy_threshold", 70)
        )

        # Config
        self.auto_accept_threshold = disambig_config.get("auto_accept", 0.95)
        self.always_ask_new = disambig_config.get("always_ask_new", True)

        # Vault writer
        self.vault_writer = VaultNoteWriter(self.vault_path, self.build_path)

        # State
        self._entities: Dict[str, Dict] = {}  # canonical_id -> entity data
        self._queue_items: List[Dict] = []

    def build(self) -> CanonBuildResult:
        """
        Execute the full canon build pipeline.

        Returns:
            CanonBuildResult with statistics
        """
        result = CanonBuildResult(success=True)

        # Load existing storygraph
        storygraph = self._load_storygraph()

        # Load existing entities into matcher
        self._load_existing_entities(storygraph)

        # Count existing scenes for accurate creation count
        existing_scene_count = len([e for e in storygraph.get("entities", []) if e.get("type") == "scene"])

        # Process each inbox file
        inbox_files = list(self.inbox_path.glob("*.md"))

        for inbox_file in inbox_files:
            try:
                file_result = self._process_inbox_file(inbox_file)
                result.characters_created += file_result.get("chars_created", 0)
                result.characters_linked += file_result.get("chars_linked", 0)
                result.locations_created += file_result.get("locs_created", 0)
                result.locations_linked += file_result.get("locs_linked", 0)
                result.scenes_created += file_result.get("scenes_created", 0)
            except Exception as e:
                result.errors.append(f"Error processing {inbox_file}: {str(e)}")

        # Generate scene IDs for boundaries
        self._process_scene_boundaries(inbox_files)

        # Count newly created scenes
        new_scene_count = len([e for e in self._entities.values() if e.get("type") == "scene"])
        result.scenes_created = new_scene_count - existing_scene_count

        # Update storygraph
        self._update_storygraph(storygraph)

        # Write vault notes
        result.vault_notes_written = self._write_vault_notes()

        # Update disambiguation queue
        result.queue_items = len(self._queue_items)
        self._update_disambiguation_queue()

        return result

    def _load_storygraph(self) -> Dict:
        """Load or create storygraph.json."""
        storygraph_path = self.build_path / "storygraph.json"

        if storygraph_path.exists():
            return json.loads(storygraph_path.read_text())

        project_id = self.project_path.name
        return {
            "version": "1.0",
            "project_id": project_id,
            "entities": [],
            "edges": [],
            "evidence_index": {}
        }

    def _load_existing_entities(self, storygraph: Dict):
        """Load existing entities into the matcher."""
        for entity in storygraph.get("entities", []):
            canonical_id = entity["id"]
            name = entity["name"]
            aliases = entity.get("aliases", [])

            self.matcher.add_entity(canonical_id, name, aliases)
            self._entities[canonical_id] = entity

    def _process_inbox_file(self, inbox_file: Path) -> Dict:
        """Process a single inbox file."""
        result = {
            "chars_created": 0,
            "chars_linked": 0,
            "locs_created": 0,
            "locs_linked": 0,
            "scenes_created": 0,
        }

        # Extract characters using instance extractor
        characters = self.char_extractor.extract_from_file(inbox_file)

        for candidate in characters:
            canonical_id = self._resolve_or_create_entity(
                candidate, "character"
            )
            if canonical_id:
                if canonical_id in self._entities:
                    result["chars_linked"] += 1
                else:
                    result["chars_created"] += 1

        # Extract locations using instance extractor
        locations = self.loc_extractor.extract_from_file(inbox_file)

        for candidate in locations:
            canonical_id = self._resolve_or_create_entity(
                candidate, "location"
            )
            if canonical_id:
                if canonical_id in self._entities:
                    result["locs_linked"] += 1
                else:
                    result["locs_created"] += 1

        return result

    def _process_scene_boundaries(self, inbox_files: List[Path]):
        """Process scene boundaries from all files."""
        for inbox_file in inbox_files:
            content = inbox_file.read_text(encoding="utf-8")
            boundaries = self.scene_extractor.detect_boundaries(content, str(inbox_file))

            for boundary in boundaries:
                if boundary.scene_type == "slugline":
                    self._create_scene_from_boundary(boundary, inbox_file)

    def _resolve_or_create_entity(
        self,
        candidate: ExtractionCandidate,
        entity_type: str
    ) -> Optional[str]:
        """
        Resolve an entity or create a new one.

        Returns:
            Canonical ID if resolved/created, None if queued
        """
        normalized = candidate.normalized

        # Try confident match first
        canonical_id = self.matcher.is_confident_match(
            normalized,
            self.auto_accept_threshold
        )

        if canonical_id:
            return canonical_id

        # Try fuzzy match
        match = self.matcher.match(normalized)

        if match and match.score >= 50:
            # Queue for disambiguation
            self._queue_items.append({
                "id": f"dq_{len(self._queue_items) + 1:04d}",
                "status": "open",
                "kind": "entity_merge" if match.score >= 70 else "reference_link",
                "entity_type": entity_type,
                "label": f"Is '{candidate.text}' the same as '{match.canonical_name}'?",
                "mention": candidate.text,
                "context_excerpt": candidate.context[:200],
                "candidates": [{
                    "entity_id": match.canonical_id,
                    "name": match.canonical_name,
                    "confidence": match.score / 100,
                    "evidence_ids": [candidate.block_ref]
                }],
                "recommended_action": "merge" if match.score >= 70 else "link",
                "recommended_target": match.canonical_id,
                "evidence_ids": [candidate.block_ref],
                "created_at": datetime.now().isoformat(),
                "source_file": candidate.source_file,
                "source_line": candidate.line_number,
            })
            return None

        # Create new entity
        if self.always_ask_new:
            # Queue for confirmation
            self._queue_items.append({
                "id": f"dq_{len(self._queue_items) + 1:04d}",
                "status": "open",
                "kind": "role_assignment",
                "entity_type": entity_type,
                "label": f"Create new {entity_type} '{candidate.text}'?",
                "mention": candidate.text,
                "context_excerpt": candidate.context[:200],
                "candidates": [],
                "recommended_action": "create",
                "evidence_ids": [candidate.block_ref],
                "created_at": datetime.now().isoformat(),
                "source_file": candidate.source_file,
                "source_line": candidate.line_number,
            })
            return None

        # Auto-create
        return self._create_entity(candidate, entity_type)

    def _create_entity(self, candidate: ExtractionCandidate, entity_type: str) -> str:
        """Create a new entity from a candidate."""
        prefix_map = {
            "character": "CHAR",
            "location": "LOC",
            "scene": "SCN"
        }
        prefix = prefix_map.get(entity_type, "ENT")

        # Generate ID
        import hashlib
        slug = candidate.normalized.replace(" ", "_")[:20]
        hash_part = hashlib.md5(candidate.text.encode()).hexdigest()[:8]
        canonical_id = f"{prefix}_{slug}_{hash_part}"

        # Create entity
        entity = {
            "id": canonical_id,
            "type": entity_type,
            "name": candidate.normalized,
            "aliases": [candidate.text],
            "attributes": candidate.metadata,
            "evidence_ids": [candidate.block_ref],
            "confidence": candidate.confidence
        }

        # Add to matcher
        self.matcher.add_entity(canonical_id, candidate.normalized, [candidate.text])

        # Store
        self._entities[canonical_id] = entity

        return canonical_id

    def _create_scene_from_boundary(self, boundary: SceneBoundary, source_file: Path):
        """Create a scene entity from a slugline boundary."""
        # Use a counter for scene numbering since SceneBoundary doesn't track it
        scene_num = len([e for e in self._entities.values() if e.get("type") == "scene"]) + 1
        canonical_id = f"SCN_{scene_num:03d}"

        if canonical_id in self._entities:
            return

        entity = {
            "id": canonical_id,
            "type": "scene",
            "name": boundary.slugline or f"Scene {scene_num}",
            "aliases": [],
            "attributes": {
                "int_ext": boundary.int_ext,
                "time_of_day": boundary.time_of_day,
                "location": boundary.location,
                "line_number": boundary.line_number,
                "source_file": str(source_file),
                "scene_type": boundary.scene_type,
            },
            "evidence_ids": [boundary.block_ref] if boundary.block_ref else [],
            "confidence": boundary.confidence
        }

        self._entities[canonical_id] = entity

    def _update_storygraph(self, storygraph: Dict):
        """Update storygraph with new entities."""
        # Merge entities
        existing_ids = {e["id"] for e in storygraph.get("entities", [])}

        for entity_id, entity in self._entities.items():
            if entity_id not in existing_ids:
                # Ensure evidence_ids are sorted for determinism
                if "evidence_ids" in entity:
                    entity["evidence_ids"] = sorted(set(entity.get("evidence_ids", [])))
                storygraph["entities"].append(entity)

        # Sort entities for deterministic output
        storygraph["entities"] = sorted(
            storygraph["entities"],
            key=lambda e: (e.get("type", ""), e.get("id", ""))
        )

        # Write back
        storygraph_path = self.build_path / "storygraph.json"
        storygraph_path.write_text(json.dumps(storygraph, indent=2))

    def _write_vault_notes(self) -> int:
        """
        Write vault notes for all entities.

        Returns:
            Number of notes written
        """
        notes_written = 0

        for entity_id, entity in self._entities.items():
            entity_type = entity.get("type", "")

            try:
                if entity_type == "character":
                    self.vault_writer.write_character(entity)
                    notes_written += 1
                elif entity_type == "location":
                    self.vault_writer.write_location(entity)
                    notes_written += 1
                elif entity_type == "scene":
                    self.vault_writer.write_scene(entity)
                    notes_written += 1
            except Exception:
                # Don't fail the build if vault writing fails
                pass

        return notes_written

    def _update_disambiguation_queue(self):
        """Update disambiguation queue file."""
        queue_path = self.build_path / "disambiguation_queue.json"

        existing = {"version": "1.0", "items": []}
        if queue_path.exists():
            existing = json.loads(queue_path.read_text())

        # Add new items
        existing["items"].extend(self._queue_items)
        existing["updated_at"] = datetime.now().isoformat()

        # Sort items for deterministic output
        existing["items"] = sorted(
            existing["items"],
            key=lambda i: i.get("id", "")
        )

        queue_path.write_text(json.dumps(existing, indent=2))


def build_canon(project_path: Path, config: Dict = None) -> CanonBuildResult:
    """
    Convenience function to build canon.

    Args:
        project_path: Path to project root
        config: Optional project configuration

    Returns:
        CanonBuildResult
    """
    builder = CanonBuilder(project_path, config)
    return builder.build()
