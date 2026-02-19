# Phase 3: Round-Trip Editing - Research

**Researched:** 2026-02-19
**Domain:** Two-way sync, protected blocks, incremental processing
**Confidence:** HIGH (verified with official docs and established patterns)

## Summary

This phase implements round-trip editing between Confucius-generated content and user edits in Obsidian. The core challenge is maintaining bidirectional sync while preserving manual annotations and tracking provenance.

**Key insight:** The project already has the foundational pieces in place:
- Protected block markers (`<!-- CONFUCIUS:BEGIN AUTO -->` / `<!-- CONFUCIUS:END AUTO -->`)
- VaultNoteWriter for generating notes
- Evidence linking system with block refs

This phase extends these foundations with change detection, re-ingestion, and conflict flagging.

**Primary recommendation:** Use SHA-256 file hashing for change detection, preserve the existing protected block pattern, and implement a three-tier conflict resolution strategy (auto-merge safe changes, flag ambiguous, prompt critical).

---

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib` | stdlib | SHA-256 file hashing | Built-in, no dependencies, cryptographic quality |
| `pathlib` | stdlib | File path operations | Modern Python file handling |
| `json` | stdlib | State persistence | Already used for storygraph, queue |
| `re` | stdlib | Protected block parsing | Regex extraction of markers |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `filelock` | 3.16+ | Concurrent file access | If multiple processes access vault |
| `watchdog` | 6.0+ | File system monitoring | Optional: for real-time vault watching |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SHA-256 | xxHash | xxHash is faster (2-3x) but less secure; SHA-256 is stdlib and sufficient for change detection |
| Manual parsing | python-frontmatter | python-frontmatter adds dependency for YAML parsing; existing code already handles YAML |
| Full re-ingestion | AST-based merge | AST approach preserves more formatting but significantly more complex |

**No new dependencies required** for core functionality. Optional `watchdog` for real-time sync.

---

## Architecture Patterns

### Recommended Project Structure

```
core/
├── sync/                       # NEW: Round-trip sync module
│   ├── __init__.py
│   ├── change_detector.py      # Hash-based file change detection
│   ├── protected_blocks.py     # Parse/extract/replace protected regions
│   ├── reingest.py             # Vault -> StoryGraph re-ingestion
│   ├── conflict_resolver.py    # Three-tier conflict handling
│   └── provenance.py           # Track content sources
├── vault/
│   ├── note_writer.py          # EXISTS: Extend with update logic
│   └── templates.py            # EXISTS: Already has markers
└── canon/
    └── __init__.py             # EXISTS: CanonBuilder

build/
├── run_state.json              # NEW: File hashes, last sync timestamp
├── conflicts.json              # NEW: Flagged conflicts for review
└── provenance.json             # NEW: Content source tracking
```

### Pattern 1: Protected Block Enforcement

**What:** Confucius ONLY writes content between `<!-- CONFUCIUS:BEGIN AUTO -->` and `<!-- CONFUCIUS:END AUTO -->` markers. User content outside markers is never touched.

**When to use:** All vault note writes, including initial creation and updates.

**Example:**

```python
# Source: Project patterns from core/vault/templates.py
import re
from typing import Optional, Tuple

BEGIN_MARKER = "<!-- CONFUCIUS:BEGIN AUTO -->"
END_MARKER = "<!-- CONFUCIUS:END AUTO -->"

def extract_protected_content(content: str) -> Tuple[str, str, str]:
    """
    Extract content into (before, protected, after) sections.

    Returns:
        Tuple of (pre-marker content, protected block, post-marker content)
    """
    pattern = re.escape(BEGIN_MARKER) + r"(.*?)" + re.escape(END_MARKER)
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        # No markers found - entire file is user content
        return (content, "", "")

    start = match.start()
    end = match.end()

    before = content[:start]
    protected = match.group(1)
    after = content[end:]

    return (before, protected, after)


def replace_protected_content(content: str, new_content: str) -> str:
    """
    Replace only the protected block, preserving everything else.

    Args:
        content: Original file content
        new_content: New content for protected region

    Returns:
        Updated file content with protected block replaced
    """
    before, _, after = extract_protected_content(content)

    if not before and not after:
        # No markers - append at end
        return content + f"\n\n{BEGIN_MARKER}\n{new_content}\n{END_MARKER}\n"

    return f"{before}{BEGIN_MARKER}\n{new_content}\n{END_MARKER}{after}"
```

### Pattern 2: Change Detection with SHA-256

**What:** Track file hashes to detect changes without comparing full content.

**When to use:** Before any re-ingestion or sync operation.

**Example:**

```python
# Source: Best practices from 2025 research (hashlib stdlib)
import hashlib
from pathlib import Path
from typing import Dict
import json

def calculate_file_hash(filepath: Path, chunk_size: int = 8192) -> str:
    """
    Calculate SHA-256 hash of file using chunked reading.

    Uses chunked reading to prevent MemoryError on large files.
    """
    hash_obj = hashlib.sha256()

    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


class ChangeDetector:
    """Track file changes via hash comparison."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._state: Dict[str, dict] = {}
        self._load_state()

    def _load_state(self):
        """Load existing state from run_state.json."""
        if self.state_path.exists():
            self._state = json.loads(self.state_path.read_text())
        else:
            self._state = {"files": {}, "last_sync": None}

    def _save_state(self):
        """Persist state to disk."""
        self.state_path.write_text(json.dumps(self._state, indent=2))

    def has_changed(self, filepath: Path) -> bool:
        """Check if file has changed since last sync."""
        current_hash = calculate_file_hash(filepath)
        stored_hash = self._state["files"].get(str(filepath), {}).get("hash")
        return current_hash != stored_hash

    def get_changed_files(self, directory: Path, pattern: str = "*.md") -> list[Path]:
        """Get all changed files in directory."""
        changed = []
        for filepath in directory.rglob(pattern):
            if self.has_changed(filepath):
                changed.append(filepath)
        return changed

    def mark_synced(self, filepath: Path):
        """Mark file as synced with current hash."""
        from datetime import datetime

        self._state["files"][str(filepath)] = {
            "hash": calculate_file_hash(filepath),
            "mtime": filepath.stat().st_mtime,
            "synced_at": datetime.now().isoformat()
        }
        self._save_state()
```

### Pattern 3: Three-Tier Conflict Resolution

**What:** Categorize conflicts by severity and handle appropriately.

| Tier | Type | Strategy | Example |
|------|------|----------|---------|
| 1 | Safe | Auto-merge | New alias added to character |
| 2 | Ambiguous | Flag for review | Same field changed in both vault and extraction |
| 3 | Critical | Block + prompt | Entity ID collision, deleted entity referenced |

**Example:**

```python
# Source: Two-way sync conflict resolution patterns (2025)
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any

class ConflictTier(Enum):
    SAFE = "safe"           # Auto-merge
    AMBIGUOUS = "ambiguous" # Flag for review
    CRITICAL = "critical"   # Block operation


@dataclass
class Conflict:
    """Represents a detected conflict."""
    tier: ConflictTier
    entity_id: str
    field: str
    vault_value: Any
    extracted_value: Any
    source: str  # Which vault file
    evidence_ids: List[str]
    resolution: Optional[str] = None  # Set after resolution

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "entity_id": self.entity_id,
            "field": self.field,
            "vault_value": self.vault_value,
            "extracted_value": self.extracted_value,
            "source": self.source,
            "evidence_ids": self.evidence_ids,
            "resolution": self.resolution
        }


class ConflictResolver:
    """Handle conflicts during re-ingestion."""

    def __init__(self, conflicts_path: Path):
        self.conflicts_path = conflicts_path
        self.conflicts: List[Conflict] = []

    def detect_conflict(
        self,
        entity_id: str,
        field: str,
        vault_value: Any,
        extracted_value: Any,
        source: str,
        evidence_ids: List[str]
    ) -> Optional[Conflict]:
        """Detect if there's a conflict between vault and extraction."""

        # No conflict if values match
        if vault_value == extracted_value:
            return None

        # Determine tier based on field type
        tier = self._classify_conflict(field, vault_value, extracted_value)

        conflict = Conflict(
            tier=tier,
            entity_id=entity_id,
            field=field,
            vault_value=vault_value,
            extracted_value=extracted_value,
            source=source,
            evidence_ids=evidence_ids
        )

        self.conflicts.append(conflict)
        self._save_conflicts()

        return conflict

    def _classify_conflict(
        self,
        field: str,
        vault_value: Any,
        extracted_value: Any
    ) -> ConflictTier:
        """Classify conflict severity."""

        # SAFE: Additive changes to arrays
        if isinstance(vault_value, list) and isinstance(extracted_value, list):
            if set(extracted_value) - set(vault_value):  # Only additions
                return ConflictTier.SAFE

        # CRITICAL: Entity ID or type changes
        if field in ("id", "type"):
            return ConflictTier.CRITICAL

        # AMBIGUOUS: Everything else
        return ConflictTier.AMBIGUOUS

    def _save_conflicts(self):
        """Persist conflicts to conflicts.json."""
        data = {
            "version": "1.0",
            "conflicts": [c.to_dict() for c in self.conflicts if c.tier != ConflictTier.SAFE]
        }
        self.conflicts_path.write_text(json.dumps(data, indent=2))
```

### Pattern 4: Provenance Tracking

**What:** Every piece of content knows its source (extraction vs manual edit).

**When to use:** All content in StoryGraph and vault notes.

**Example:**

```python
# Source: Project pattern "Evidence traceability mandatory"
from dataclasses import dataclass
from typing import Literal
from datetime import datetime

@dataclass
class ProvenanceRecord:
    """Track where content came from."""
    content_hash: str
    source_type: Literal["extraction", "manual_edit", "merge"]
    source_file: Optional[str]  # For extraction: inbox file
    vault_file: Optional[str]   # For manual_edit: vault file
    timestamp: str
    evidence_ids: List[str]

    def to_dict(self) -> dict:
        return {
            "content_hash": self.content_hash,
            "source_type": self.source_type,
            "source_file": self.source_file,
            "vault_file": self.vault_file,
            "timestamp": self.timestamp,
            "evidence_ids": self.evidence_ids
        }


class ProvenanceTracker:
    """Track content provenance across round-trips."""

    def __init__(self, provenance_path: Path):
        self.provenance_path = provenance_path
        self.records: Dict[str, ProvenanceRecord] = {}
        self._load()

    def track_extraction(
        self,
        content: str,
        entity_id: str,
        field: str,
        source_file: str,
        evidence_ids: List[str]
    ):
        """Track content from extraction."""
        key = f"{entity_id}:{field}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        self.records[key] = ProvenanceRecord(
            content_hash=content_hash,
            source_type="extraction",
            source_file=source_file,
            vault_file=None,
            timestamp=datetime.now().isoformat(),
            evidence_ids=evidence_ids
        )
        self._save()

    def track_manual_edit(
        self,
        content: str,
        entity_id: str,
        field: str,
        vault_file: str
    ):
        """Track content from manual vault edit."""
        key = f"{entity_id}:{field}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        self.records[key] = ProvenanceRecord(
            content_hash=content_hash,
            source_type="manual_edit",
            source_file=None,
            vault_file=vault_file,
            timestamp=datetime.now().isoformat(),
            evidence_ids=[]  # Manual edits have no evidence
        )
        self._save()

    def get_source(self, entity_id: str, field: str) -> Optional[ProvenanceRecord]:
        """Get provenance for specific content."""
        return self.records.get(f"{entity_id}:{field}")
```

### Anti-Patterns to Avoid

- **Overwriting entire files:** Destroys user annotations; always use protected block replacement
- **Assuming hash-based detection is enough:** Always check mtime first for quick rejection
- **Auto-merging ambiguous conflicts:** Silent data loss; always flag for review
- **Ignoring YAML frontmatter changes:** User may have edited metadata; detect and flag

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File hashing | Custom checksum | `hashlib.sha256()` | Stdlib, battle-tested, no dependencies |
| YAML parsing | Regex extraction | Project's existing frontmatter handling | Already works, consistent |
| Protected block parsing | String manipulation | `re.DOTALL` pattern matching | Handles edge cases, multiline |
| Conflict persistence | Custom format | JSON with versioning | Consistent with project patterns |

**Key insight:** The project already has solid foundations. This phase is about extending, not rebuilding.

---

## Common Pitfalls

### Pitfall 1: Marker Drift

**What goes wrong:** Protected block markers get corrupted or lost during edits.

**Why it happens:** User accidentally deletes marker, or regex fails on edge cases.

**How to avoid:**
1. Always validate markers exist before writing
2. If markers missing, append at end (never prepend)
3. Include marker validation in test suite

**Warning signs:**
- File hash changed but no protected block found
- Content appears outside expected sections

**Recovery:**
```python
def ensure_markers(content: str) -> str:
    """Ensure file has protected block markers."""
    if BEGIN_MARKER not in content:
        # Append markers at end
        return f"{content.rstrip()}\n\n{BEGIN_MARKER}\n{END_MARKER}\n"
    return content
```

### Pitfall 2: Hash Collision False Positives

**What goes wrong:** Different content produces same hash (theoretically).

**Why it happens:** Using weak hash (MD5) or truncated hashes.

**How to avoid:**
1. Use full SHA-256 (64 hex chars), never truncate
2. Combine hash with mtime for extra safety
3. On hash match but mtime change, do content diff

**Warning signs:**
- File marked unchanged but content different
- Sync misses obvious edits

### Pitfall 3: Orphaned Evidence Links

**What goes wrong:** Re-ingestion loses evidence links from original extraction.

**Why it happens:** Merging without tracking evidence_ids properly.

**How to avoid:**
1. Always preserve existing evidence_ids array
2. Merge new evidence_ids, never replace
3. Track provenance for audit trail

**Warning signs:**
- Evidence links disappear after rebuild
- Clicking evidence shows 404

### Pitfall 4: YAML Frontmatter Corruption

**What goes wrong:** Protected block replacement corrupts YAML frontmatter.

**Why it happens:** YAML is at start of file, markers come after.

**How to avoid:**
1. Never modify content before `---` delimiter ends frontmatter
2. Protected block replacement only affects body
3. Detect and flag frontmatter changes separately

---

## Code Examples

### Full Round-Trip Update Flow

```python
# Source: Integration of project patterns + research findings
from pathlib import Path
from typing import Dict, Any, List
import json

class RoundTripSync:
    """Orchestrate round-trip editing between vault and StoryGraph."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.vault_path = project_path / "vault"
        self.build_path = project_path / "build"

        # Components
        self.change_detector = ChangeDetector(self.build_path / "run_state.json")
        self.conflict_resolver = ConflictResolver(self.build_path / "conflicts.json")
        self.provenance = ProvenanceTracker(self.build_path / "provenance.json")

    def detect_vault_changes(self) -> List[Path]:
        """Find all vault files modified since last sync."""
        changed = []
        for subdir in ["10_Characters", "20_Locations", "50_Scenes"]:
            vault_dir = self.vault_path / subdir
            if vault_dir.exists():
                changed.extend(self.change_detector.get_changed_files(vault_dir))
        return changed

    def reingest_vault_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Re-ingest a single vault file.

        Returns extracted entity data.
        """
        content = filepath.read_text()

        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Parse frontmatter (simple key-value extraction)
                frontmatter = {}
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip()

                # Get protected block content
                _, protected, _ = extract_protected_content(parts[2])

                return {
                    "frontmatter": frontmatter,
                    "protected_content": protected,
                    "file": str(filepath)
                }

        return {}

    def sync_to_storygraph(self, entity_data: Dict, storygraph: Dict) -> bool:
        """
        Sync re-ingested entity to StoryGraph.

        Returns True if successful, False if conflicts.
        """
        entity_id = entity_data.get("frontmatter", {}).get("id")
        if not entity_id:
            return False

        # Find existing entity
        existing = next(
            (e for e in storygraph.get("entities", []) if e.get("id") == entity_id),
            None
        )

        if not existing:
            return False  # Entity doesn't exist in graph

        # Check for conflicts on each field
        has_critical_conflict = False
        for field, new_value in entity_data.get("frontmatter", {}).items():
            old_value = existing.get(field)

            conflict = self.conflict_resolver.detect_conflict(
                entity_id=entity_id,
                field=field,
                vault_value=new_value,
                extracted_value=old_value,
                source=entity_data.get("file", ""),
                evidence_ids=existing.get("evidence_ids", [])
            )

            if conflict and conflict.tier == ConflictTier.CRITICAL:
                has_critical_conflict = True
            elif conflict and conflict.tier == ConflictTier.SAFE:
                # Auto-merge: merge arrays
                if isinstance(old_value, list) and isinstance(new_value, list):
                    merged = list(set(old_value) | set(new_value))
                    existing[field] = sorted(merged)

        return not has_critical_conflict

    def run(self) -> Dict[str, Any]:
        """
        Execute full round-trip sync.

        Returns summary of changes and conflicts.
        """
        result = {
            "files_checked": 0,
            "files_changed": 0,
            "entities_updated": 0,
            "conflicts_safe": 0,
            "conflicts_ambiguous": 0,
            "conflicts_critical": 0
        }

        # Load current StoryGraph
        storygraph_path = self.build_path / "storygraph.json"
        storygraph = json.loads(storygraph_path.read_text())

        # Detect changes
        changed_files = self.detect_vault_changes()
        result["files_changed"] = len(changed_files)

        # Process each changed file
        for filepath in changed_files:
            entity_data = self.reingest_vault_file(filepath)

            if entity_data:
                success = self.sync_to_storygraph(entity_data, storygraph)
                if success:
                    result["entities_updated"] += 1
                    self.change_detector.mark_synced(filepath)

        # Save updated StoryGraph
        storygraph_path.write_text(json.dumps(storygraph, indent=2))

        # Count conflicts
        for conflict in self.conflict_resolver.conflicts:
            if conflict.tier == ConflictTier.SAFE:
                result["conflicts_safe"] += 1
            elif conflict.tier == ConflictTier.AMBIGUOUS:
                result["conflicts_ambiguous"] += 1
            else:
                result["conflicts_critical"] += 1

        return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MD5 file hashing | SHA-256 | 2020+ | Collision resistance for safety |
| Full file overwrite | Protected block replacement | Project start | Preserves manual edits |
| Last-write-wins | Three-tier conflict resolution | 2025+ | Reduces data loss |
| No provenance tracking | Full provenance per field | This phase | Audit trail for compliance |

**Deprecated/outdated:**
- MD5/SHA-1 for file hashing: Use SHA-256 instead
- Custom conflict resolution: Use tiered approach (safe/ambiguous/critical)
- Assuming single source of truth: Vault AND StoryGraph both matter now

---

## Open Questions

### 1. How to handle vault files deleted outside Confucius?

**What we know:**
- File deletion removes the .md file
- StoryGraph still has the entity
- No marker for deletion

**What's unclear:**
- Should deletion in vault trigger entity deletion in graph?
- Or should we flag as conflict?
- How to preserve evidence links?

**Recommendation:**
- Tier 1: Flag as CRITICAL conflict
- Prompt user: "Entity X file was deleted. Remove from StoryGraph?"
- Never auto-delete entities

### 2. Should we track mtime in addition to hash?

**What we know:**
- Hash is definitive for content changes
- mtime is faster to check (no file read)
- mtime can change without content change (touch, metadata)

**What's unclear:**
- Is performance gain worth complexity?

**Recommendation:**
- Yes, use both: check mtime first, only compute hash if mtime changed
- Store both in run_state.json
- This is what Obsidian Sync does

### 3. Real-time vs. manual sync trigger?

**What we know:**
- `watchdog` provides file system watching
- Real-time sync could prevent some conflicts
- Adds complexity and dependency

**What's unclear:**
- Is real-time worth the complexity?
- Most users will sync on `gsd build` command

**Recommendation:**
- Start with manual sync (on `gsd build`)
- Add real-time as optional feature later (Phase 3.5?)
- Don't block Phase 3 on real-time

---

## Sources

### Primary (HIGH confidence)
- Project codebase analysis - Verified existing protected block markers, VaultNoteWriter patterns
- Python hashlib documentation - SHA-256 implementation details
- REQUIREMENTS.md - UIX-01, UIX-02, INF-04 requirements

### Secondary (MEDIUM confidence)
- Two-way sync conflict resolution patterns (WebSearch, verified with multiple sources)
- Obsidian Sync architecture analysis (2025) - mtime + hash dual approach
- Markdig round-trip support analysis - Protected region patterns

### Tertiary (LOW confidence)
- AI-powered conflict resolution (2026 patent) - Future direction, not ready for implementation
- TOON serialization format - Interesting but not applicable to this use case

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, no new dependencies
- Architecture patterns: HIGH - Based on existing project patterns + verified research
- Pitfalls: HIGH - Well-documented issues in sync systems
- Conflict resolution: MEDIUM - Pattern is sound, implementation details may need adjustment

**Research date:** 2026-02-19
**Valid until:** 2026-05-19 (3 months - patterns are stable, no fast-moving dependencies)
