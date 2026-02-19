# Phase 2: Script Composition - Research

**Researched:** 2026-02-19
**Domain:** Screenplay formatting, narrative-to-script transformation, FDX export
**Confidence:** HIGH

## Summary

Phase 2 transforms the canonical data extracted in Phase 1 (characters, locations, scenes in StoryGraph) into actual screenplay paragraphs (sluglines, action beats, dialogue) structured as a ScriptGraph JSON that can be exported to FDX format.

The good news: **The FDX writer is already complete and tested**. Phase 2's challenge is building the `ScriptBuilder` class that transforms inbox content + StoryGraph entities into valid ScriptGraph paragraphs with proper typing and evidence linking.

**Primary recommendation:** Follow the existing `CanonBuilder` pattern - create `ScriptBuilder` that reads inbox content, uses existing scene boundaries from Phase 1, and generates typed paragraphs with evidence IDs.

## Standard Stack

### Core (Already Implemented - Do Not Rebuild)

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| FDXWriter | `core/exporters/fdx_writer.py` | ScriptGraph JSON → .fdx file | Complete |
| ScriptGraph Schema | `core/scriptgraph/schema.json` | Scene/paragraph structure | Complete |
| SceneExtractor | `core/extraction/scenes.py` | Slugline detection, boundaries | Complete |
| VaultNoteWriter | `core/vault/note_writer.py` | Obsidian note generation | Complete |
| StoryGraph Schema | `core/storygraph/schema.json` | Canonical entities | Complete |

### What We Need to Build

| Component | Purpose | Dependencies |
|-----------|---------|--------------|
| ScriptBuilder | Transform inbox → ScriptGraph | StoryGraph, SceneExtractor |
| BeatExtractor | Extract action beats from narrative | Existing extraction patterns |
| DialogueFormatter | Format dialogue with character names | Character entities |
| `gsd build script` | CLI command for script composition | ScriptBuilder, FDXWriter |

### Supporting Libraries (Already In Use)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | (existing) | Fuzzy matching for entity resolution | Character name linking |
| xml.etree.ElementTree | stdlib | FDX XML generation | Already in FDXWriter |
| json | stdlib | ScriptGraph/StoryGraph files | File I/O |
| re | stdlib | Pattern matching | Beat/dialogue detection |

**No new dependencies needed.** All required libraries are already in use.

## Architecture Patterns

### Recommended Project Structure

```
core/
├── script/                    # NEW - Script composition module
│   ├── __init__.py           # ScriptBuilder, build_script()
│   ├── builder.py            # ScriptBuilder class
│   ├── beats.py              # Beat extraction from narrative
│   └── dialogue.py           # Dialogue formatting
├── exporters/
│   └── fdx_writer.py         # EXISTING - FDX export
├── extraction/
│   └── scenes.py             # EXISTING - Scene boundaries
├── canon/
│   └── __init__.py           # EXISTING - CanonBuilder pattern to follow
└── scriptgraph/
    └── schema.json           # EXISTING - Target schema
```

### Pattern 1: ScriptBuilder (Follow CanonBuilder Pattern)

**What:** Transform inbox content into ScriptGraph, similar to how CanonBuilder produces StoryGraph
**When to use:** This is the primary Phase 2 implementation

**Example (based on CanonBuilder in `core/canon/__init__.py`):**
```python
# Follow this exact pattern from CanonBuilder
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any

@dataclass
class ScriptBuildResult:
    """Result of a script build operation."""
    success: bool
    scenes_processed: int = 0
    paragraphs_generated: int = 0
    dialogue_blocks: int = 0
    action_beats: int = 0
    errors: List[str] = field(default_factory=list)


class ScriptBuilder:
    """Builds ScriptGraph from inbox content + StoryGraph."""

    def __init__(self, project_path: Path, config: Dict[str, Any] = None):
        self.project_path = Path(project_path)
        self.config = config or {}

        # Paths
        self.inbox_path = self.project_path / "inbox"
        self.vault_path = self.project_path / "vault"
        self.build_path = self.project_path / "build"

        # Load StoryGraph (from Phase 1)
        self.storygraph = self._load_storygraph()

        # Scene data from StoryGraph
        self._scenes = self._extract_scenes_from_storygraph()

        # Evidence index
        self._evidence_index = self._load_evidence_index()

    def build(self) -> ScriptBuildResult:
        """Execute the full script build pipeline."""
        result = ScriptBuildResult(success=True)

        # Process each inbox file within scene boundaries
        scenes = []

        for scene_entity in self._scenes:
            scene_data = self._build_scene(scene_entity)
            scenes.append(scene_data)
            result.paragraphs_generated += len(scene_data.get("paragraphs", []))

        # Sort scenes by order for determinism
        scenes.sort(key=lambda s: s.get("order", 999))

        # Generate ScriptGraph
        scriptgraph = {
            "version": "1.0",
            "project_id": self.storygraph.get("project_id"),
            "generated_at": datetime.now().isoformat(),
            "scenes": scenes
        }

        # Write with sorted output (deterministic)
        self._write_scriptgraph(scriptgraph)

        return result
```

### Pattern 2: Beat Extraction from Narrative

**What:** Extract action beats from prose narrative within scenes
**When to use:** Transforming inbox narrative text into screenplay action paragraphs

**Example:**
```python
# In core/script/beats.py
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ActionBeat:
    """A single action beat extracted from narrative."""
    text: str
    order: int
    evidence_ids: List[str]
    character_refs: List[str] = None


def extract_beats_from_content(
    content: str,
    scene_start_line: int,
    scene_end_line: int,
    block_refs: Dict[int, str]  # line_number -> block_ref
) -> List[ActionBeat]:
    """
    Extract action beats from narrative content within a scene.

    Strategy:
    1. Split content by newlines
    2. Filter to scene boundaries
    3. Skip dialogue lines (character + dialogue patterns)
    4. Convert remaining narrative to action beats
    """
    lines = content.split("\n")
    scene_lines = lines[scene_start_line:scene_end_line]

    beats = []
    beat_order = 0

    # Dialogue patterns to skip
    dialogue_char_pattern = re.compile(r'^[A-Z][A-Z\s]+$')  # ALL CAPS name
    dialogue_cont_pattern = re.compile(r'^\s*\(.*\)\s*$')   # (continuing)

    for i, line in enumerate(scene_lines):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip block ref-only lines
        if re.match(r'^\^[a-z0-9_]+$', line):
            continue

        # Skip sluglines (already handled)
        if re.match(r'^(INT\.|EXT\.)', line, re.IGNORECASE):
            continue

        # Skip dialogue character names
        if dialogue_char_pattern.match(line):
            continue

        # Skip parentheticals
        if dialogue_cont_pattern.match(line):
            continue

        # Extract block ref if present
        block_ref = block_refs.get(scene_start_line + i, "")

        # This is an action beat
        beat_order += 1
        beats.append(ActionBeat(
            text=line,
            order=beat_order,
            evidence_ids=[block_ref] if block_ref else []
        ))

    return beats
```

### Pattern 3: Dialogue Detection and Formatting

**What:** Identify dialogue in inbox content and format per screenplay standards
**When to use:** Transforming dialogue patterns into character/dialogue paragraphs

**Example:**
```python
# In core/script/dialogue.py
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class DialogueBlock:
    """A formatted dialogue block."""
    character: str
    character_id: Optional[str]  # Link to canonical entity
    parenthetical: Optional[str]
    dialogue: str
    evidence_ids: List[str]


def detect_dialogue_blocks(
    content: str,
    scene_start: int,
    scene_end: int,
    character_map: Dict[str, str],  # name -> canonical_id
    block_refs: Dict[int, str]
) -> List[Tuple[int, DialogueBlock]]:
    """
    Detect and format dialogue blocks from content.

    Input patterns (from inbox):
    - JOHN
      Hey, Mary!

    - SARAH (O.S.)
      (whispering)
      Over here!

    Output: Typed paragraphs for ScriptGraph
    """
    lines = content.split("\n")
    scene_lines = lines[scene_start:scene_end]

    dialogue_blocks = []
    i = 0

    character_pattern = re.compile(
        r'^([A-Z][A-Z\s]+?)(?:\s*\(([A-Z.]+)\))?$'
    )
    parenthetical_pattern = re.compile(r'^\s*\((.+?)\)\s*$')

    while i < len(scene_lines):
        line = scene_lines[i].strip()

        # Check for character cue
        char_match = character_pattern.match(line)
        if char_match:
            character_name = char_match.group(1).strip()
            extension = char_match.group(2)  # V.O., O.S., etc.

            # Resolve to canonical ID
            char_id = character_map.get(character_name.upper())

            # Get parenthetical (optional)
            parenthetical = None
            dialogue_lines = []

            j = i + 1
            # Check for parenthetical
            if j < len(scene_lines):
                paren_match = parenthetical_pattern.match(scene_lines[j].strip())
                if paren_match:
                    parenthetical = paren_match.group(1)
                    j += 1

            # Collect dialogue lines until empty or new character
            while j < len(scene_lines):
                dlg_line = scene_lines[j].strip()
                if not dlg_line:
                    break
                if character_pattern.match(dlg_line):
                    break
                dialogue_lines.append(dlg_line)
                j += 1

            # Get evidence refs
            evidence_ids = []
            for k in range(i, j):
                ref = block_refs.get(scene_start + k)
                if ref:
                    evidence_ids.append(ref)

            dialogue_blocks.append((
                scene_start + i,  # line number
                DialogueBlock(
                    character=character_name,
                    character_id=char_id,
                    parenthetical=parenthetical,
                    dialogue=" ".join(dialogue_lines),
                    evidence_ids=evidence_ids
                )
            ))

            i = j
            continue

        i += 1

    return dialogue_blocks
```

### Pattern 4: Slugline Generation from Scene Entity

**What:** Generate valid slugline from StoryGraph scene entity
**When to use:** Creating scene_heading paragraphs

**Example:**
```python
def generate_slugline(scene_entity: Dict[str, Any], location_entities: Dict[str, Dict]) -> str:
    """
    Generate slugline from scene entity.

    Format: INT./EXT. LOCATION - TIME

    Scene entity from StoryGraph has:
    - attributes.int_ext: "INT", "EXT", "INT/EXT"
    - attributes.location: "DINER" (raw text)
    - attributes.time_of_day: "DAY", "NIGHT", etc.
    """
    attrs = scene_entity.get("attributes", {})

    int_ext = attrs.get("int_ext", "INT")
    location = attrs.get("location", "UNKNOWN LOCATION")
    time_of_day = attrs.get("time_of_day", "DAY")

    # Normalize time of day
    time_normalizations = {
        "MORNING": "MORNING",
        "AFTERNOON": "AFTERNOON",
        "EVENING": "EVENING",
        "DAWN": "DAWN",
        "DUSK": "DUSK",
        "CONTINUOUS": "CONTINUOUS",
        "LATER": "LATER",
    }
    normalized_time = time_normalizations.get(time_of_day.upper(), "DAY")

    # Format: INT./EXT. LOCATION - TIME
    slugline = f"{int_ext}. {location.upper()} - {normalized_time}"

    return slugline
```

### Anti-Patterns to Avoid

- **Don't re-parse everything:** Use the scenes and entities already extracted in Phase 1. The StoryGraph is the source of truth.
- **Don't create new entity IDs:** Character/location IDs come from StoryGraph. ScriptGraph only links to them.
- **Don't forget evidence:** Every paragraph must have `evidence_ids` from the original inbox content.
- **Don't sort after linking:** Evidence IDs must be sorted for deterministic output, but link resolution happens first.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slugline detection | New regex patterns | `SceneExtractor.detect_boundaries()` | Already tested, handles edge cases |
| Character name matching | Custom fuzzy logic | `FuzzyMatcher` from Phase 1 | Consistent with CanonBuilder |
| FDX XML generation | Manual XML building | `FDXWriter` class | Complete, tested, validated |
| Evidence linking | Manual block tracking | `evidence_index.json` from Phase 1 | Already populated during ingest |

**Key insight:** Phase 1 already did the heavy lifting. Phase 2 is primarily transformation, not extraction.

## Common Pitfalls

### Pitfall 1: Scene Boundary Mismatch

**What goes wrong:** Script scenes don't align with StoryGraph scenes, causing duplicate or missing content.
**Why it happens:** Scene boundaries detected independently instead of using StoryGraph scene entities.
**How to avoid:** Always use `scene_entity["attributes"]["line_number"]` to determine scene content boundaries.
**Warning signs:** Paragraph counts don't match inbox line counts, characters appear in wrong scenes.

### Pitfall 2: Lost Evidence Links

**What goes wrong:** Generated paragraphs have no `evidence_ids`, breaking traceability.
**Why it happens:** Block refs stripped during text processing, or not extracted before transformation.
**How to avoid:** Extract block refs first, then transform text. Keep evidence IDs in all intermediate structures.
**Warning signs:** Empty `evidence_ids` arrays in ScriptGraph, "no source" links in vault.

### Pitfall 3: Dialogue Character Not Linked

**What goes wrong:** Character names in dialogue don't link to canonical entities.
**Why it happens:** Character name in inbox (JOHN) doesn't match StoryGraph entity ID (CHAR_John_abc123).
**How to avoid:** Build character name -> canonical ID map from StoryGraph before processing dialogue.
**Warning signs:** `character_id` is null in dialogue blocks, character wikilinks broken in vault.

### Pitfall 4: Non-Deterministic Output

**What goes wrong:** Running `gsd build script` twice produces different ScriptGraph JSON.
**Why it happens:** Unsorted entities, random ordering in dictionaries, or timestamps in output.
**How to avoid:** Sort all arrays (scenes by order, evidence_ids alphabetically) before writing. Use same pattern as CanonBuilder's `_update_storygraph`.
**Warning signs:** `git diff` shows changes after rebuild with no input changes.

### Pitfall 5: Missing Scene Order

**What goes wrong:** Scenes appear in wrong order in FDX export.
**Why it happens:** Scene `order` field not set correctly or not used when sorting.
**How to avoid:** Set `order` from StoryGraph scene entity position (SCN_001 = order 1). Always sort scenes before writing.
**Warning signs:** FDX scenes out of sequence, vault notes show different order than export.

## Code Examples

### Complete ScriptBuilder Scene Building

```python
# In core/script/builder.py
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

from ..extraction import SceneExtractor
from ..canon import CanonBuildResult


def build_scene(
    self,
    scene_entity: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build a single scene's ScriptGraph data from StoryGraph entity.

    Input: Scene entity from StoryGraph
    Output: Scene dict for ScriptGraph with paragraphs
    """
    attrs = scene_entity.get("attributes", {})

    # Generate slugline
    slugline = self._generate_slugline(scene_entity)

    # Get scene content from inbox
    scene_start = attrs.get("line_number", 0)
    scene_end = self._find_scene_end(scene_start)

    # Read inbox content
    content = self._read_scene_content(scene_start, scene_end)

    # Extract block refs
    block_refs = self._extract_block_refs(content)

    # Build character map
    character_map = self._build_character_map()

    # Extract dialogue blocks
    dialogue_blocks = detect_dialogue_blocks(
        content, 0, len(content.split("\n")),
        character_map, block_refs
    )

    # Extract action beats (non-dialogue content)
    beat_lines = self._get_non_dialogue_lines(content, dialogue_blocks)
    action_beats = extract_beats_from_content(
        content, 0, len(content.split("\n")), block_refs
    )
    # Filter out dialogue lines from action beats
    dialogue_line_nums = {db[0] for db in dialogue_blocks}
    action_beats = [b for b in action_beats if b.order not in dialogue_line_nums]

    # Build paragraphs in order
    paragraphs = []

    # Track all characters mentioned in scene
    scene_characters = set()

    # Combine dialogue and action, sorted by line number
    all_elements = []
    for line_num, block in dialogue_blocks:
        all_elements.append((line_num, "dialogue", block))
    for beat in action_beats:
        # Approximate line from order
        all_elements.append((beat.order, "action", beat))

    all_elements.sort(key=lambda x: x[0])

    for _, elem_type, elem in all_elements:
        if elem_type == "dialogue":
            block: DialogueBlock = elem

            # Character cue
            paragraphs.append({
                "type": "character",
                "text": block.character,
                "evidence_ids": block.evidence_ids[:1] if block.evidence_ids else []
            })

            # Parenthetical (optional)
            if block.parenthetical:
                paragraphs.append({
                    "type": "parenthetical",
                    "text": f"({block.parenthetical})",
                    "evidence_ids": []
                })

            # Dialogue
            paragraphs.append({
                "type": "dialogue",
                "text": block.dialogue,
                "evidence_ids": block.evidence_ids
            })

            if block.character_id:
                scene_characters.add(block.character_id)

        else:  # action
            beat: ActionBeat = elem
            paragraphs.append({
                "type": "action",
                "text": beat.text,
                "evidence_ids": beat.evidence_ids
            })

    # Build links from StoryGraph
    location_id = self._resolve_location_id(attrs.get("location", ""))

    return {
        "id": scene_entity.get("id", "SCN_000"),
        "order": int(scene_entity.get("id", "SCN_000").replace("SCN_", "")),
        "slugline": slugline,
        "int_ext": attrs.get("int_ext", "INT"),
        "time_of_day": attrs.get("time_of_day", "DAY"),
        "paragraphs": paragraphs,
        "links": {
            "characters": sorted(list(scene_characters)),
            "locations": [location_id] if location_id else [],
            "props": [],  # Phase 4
            "wardrobe": [],  # Phase 4
            "evidence_ids": sorted(list(set(
                ev_id for p in paragraphs for ev_id in p.get("evidence_ids", [])
            )))
        }
    }
```

### CLI Command Implementation

```python
# In apps/cli/cli.py - add to cmd_build function

elif what == "script":
    from core.script import build_script

    print("Building script...")
    print(f"Project: {config['project']['name']}")
    print()

    # Check for storygraph
    storygraph_path = project_path / "build" / "storygraph.json"
    if not storygraph_path.exists():
        print("Error: No storygraph.json found. Run 'gsd build canon' first.")
        return 1

    # Run script builder
    result = build_script(project_path, config)

    # Report results
    print()
    print("=== Script Build Results ===")
    print(f"Scenes processed: {result.scenes_processed}")
    print(f"Paragraphs generated: {result.paragraphs_generated}")
    print(f"  - Dialogue blocks: {result.dialogue_blocks}")
    print(f"  - Action beats: {result.action_beats}")

    if result.errors:
        print()
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")

    print()
    print(f"ScriptGraph: build/scriptgraph.json")
    print(f"Next: gsd export fdx")

    return 0 if result.success else 1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual screenplay formatting | FDXWriter auto-generation | Phase 0 | Zero formatting errors |
| Separate extraction steps | CanonBuilder pipeline | Phase 1 | Consistent entity extraction |
| Unsorted JSON output | Deterministic builds (sorted) | Phase 1 | Git-diffable, reproducible |
| Raw text in paragraphs | Typed paragraphs (action, dialogue, etc.) | Phase 2 | Proper FDX mapping |

**Deprecated/outdated:**
- Hand-written FDX XML: Use FDXWriter class
- Custom scene detection in script build: Use SceneExtractor from Phase 1
- Direct character name lookup: Use FuzzyMatcher with StoryGraph entities

## Open Questions

### 1. Beat Ordering Within Scenes

**What we know:** Beats need to be ordered within scenes for correct screenplay flow.
**What's unclear:** Should order be based on line numbers or a separate "beat sequence" derived from narrative structure?
**Recommendation:** Use line numbers as primary ordering (deterministic, matches source). Future enhancement could add narrative-aware reordering.

### 2. Multi-Line Dialogue Handling

**What we know:** Dialogue can span multiple lines in inbox content.
**What's unclear:** Should multi-line dialogue be merged into one paragraph or kept as separate dialogue blocks?
**Recommendation:** Merge consecutive dialogue lines from same character into single paragraph (standard screenplay format). The test fixture shows this pattern.

### 3. Empty Scenes

**What we know:** Some scenes in StoryGraph might have no paragraphs (just slugline).
**What's unclear:** Should empty scenes be included in ScriptGraph?
**Recommendation:** Include empty scenes with just slugline (matches Final Draft behavior). FDXWriter already handles this.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis:
  - `core/exporters/fdx_writer.py` - FDXWriter implementation
  - `core/scriptgraph/schema.json` - Target schema
  - `core/canon/__init__.py` - CanonBuilder pattern
  - `core/extraction/scenes.py` - SceneExtractor
  - `tests/unit/test_fdx_writer.py` - FDX test patterns

### Secondary (MEDIUM confidence)
- Test fixtures analysis:
  - `tests/fixtures/sample_story_simple.md` - Expected input format
  - `tests/integration/test_canon_pipeline.py` - Integration patterns

### Tertiary (LOW confidence)
- N/A - All findings from codebase analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components already exist or follow established patterns
- Architecture: HIGH - CanonBuilder provides clear template to follow
- Pitfalls: HIGH - Derived from existing codebase patterns and Phase 1 lessons

**Research date:** 2026-02-19
**Valid until:** 30 days (stable patterns from existing codebase)
