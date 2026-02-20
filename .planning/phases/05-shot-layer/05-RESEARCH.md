# Phase 5: Shot Layer - Research

**Researched:** 2026-02-19
**Domain:** Cinematography / Shot Lists / Blocking Notes / Screenplay Analysis
**Confidence:** MEDIUM (domain knowledge verified, technical approach novel)

## Summary

Phase 5 implements the Shot Layer, which bridges screenplay text to production-ready shot lists. This involves detecting shot opportunities from narrative text, suggesting appropriate camera shots based on content analysis, and exporting industry-standard shot list formats.

The core challenge is that screenplays rarely contain explicit shot directions (modern spec scripts avoid camera angles). The system must **infer shots** from action descriptions, dialogue emotional intensity, and scene structure. This requires rule-based heuristics rather than ML - consistent with project patterns from Phase 1-4.

**Primary recommendation:** Build a ShotSuggester following BaseValidator/ScriptBuilder patterns - rule-based, deterministic, evidence-linked, with CSV export matching StudioBinder's column schema.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (csv) | 3.10+ | CSV export | Built-in, deterministic output |
| Python stdlib (re) | 3.10+ | Pattern matching | Already used in BeatExtractor |
| Python stdlib (dataclasses) | 3.10+ | Data models | Consistent with Issue, Paragraph patterns |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | existing | Fuzzy character matching | Resolve character names in shot subjects |
| json (stdlib) | existing | Output serialization | ShotGraph persistence |

### No New Dependencies
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom heuristics | ML/NLP models | Rule-based = deterministic, no false positives from ML |
| Standard CSV | Excel formats | CSV universal, diffable, works with all tools |
| Built-in re | spaCy NLP | Overkill for shot detection, adds heavy dependency |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure
```
core/
├── shots/                    # NEW module
│   ├── __init__.py
│   ├── suggester.py          # ShotSuggester (main orchestrator)
│   ├── detector.py           # ShotDetector (heuristic patterns)
│   ├── types.py              # ShotType, CameraAngle, Movement enums
│   ├── models.py             # Shot, ShotList dataclasses
│   └── exporter.py           # CSV export (StudioBinder-compatible)
├── scriptgraph/
│   └── schema.json           # EXTENDED with shots array in scene
```

### Pattern 1: ShotSuggester (Follows BaseValidator Pattern)

**What:** Orchestrates shot detection from ScriptGraph scenes
**When to use:** When processing completed ScriptGraph for shot suggestions
**Example:**
```python
# Source: Pattern from core/validation/base.py
class ShotSuggester:
    """Suggests shots for scenes based on content analysis.

    Follows BaseValidator pattern:
    - _load_graphs() for loading scriptgraph.json
    - suggest() for scene-by-scene analysis
    - get_shot_list() and get_summary() for results
    """

    def __init__(self, build_path: Path):
        self.build_path = Path(build_path)
        self._scriptgraph: Optional[Dict] = None
        self._shots: List[Shot] = []
        self._shot_counter = 0

    def _load_graphs(self) -> None:
        """Load scriptgraph.json from build directory."""
        scriptgraph_path = self.build_path / "scriptgraph.json"
        if scriptgraph_path.exists():
            self._scriptgraph = json.loads(scriptgraph_path.read_text())

    def suggest(self) -> List[Shot]:
        """Run shot suggestion for all scenes."""
        if not self._scriptgraph:
            self._load_graphs()

        for scene in self._scriptgraph.get("scenes", []):
            self._suggest_for_scene(scene)

        return self._shots

    def _suggest_for_scene(self, scene: Dict) -> None:
        """Suggest shots for a single scene."""
        # Establishing shot (always first)
        self._add_shot(
            scene=scene,
            shot_type=ShotType.WIDE,
            description=f"Establishing - {scene['slugline']}",
            order=1
        )

        # Analyze paragraphs for shot opportunities
        order = 2
        for para in scene.get("paragraphs", []):
            suggested = self._detect_shot_opportunity(para, scene)
            if suggested:
                suggested.order = order
                self._shots.append(suggested)
                order += 1
```

### Pattern 2: Shot Detection Heuristics

**What:** Rule-based detection of shot opportunities from paragraph content
**When to use:** When analyzing action/dialogue for shot suggestions
**Example:**
```python
# Source: Pattern from core/script/beats.py
class ShotDetector:
    """Detects shot opportunities from screenplay content.

    Rule-based heuristics (no ML):
    - Dialogue with emotional keywords -> Close-up
    - Action with movement verbs -> Medium/Wide
    - Object detail mentions -> Insert/ECU
    - Multiple characters in dialogue -> Over-the-shoulder
    """

    EMOTIONAL_KEYWORDS = {
        "cry", "tears", "sob", "scream", "whisper", "gasp",
        "shock", "horror", "love", "hate", "fear", "anger"
    }

    MOVEMENT_VERBS = {
        "walks", "runs", "enters", "exits", "moves", "crosses",
        "approaches", "retreats", "chases", "flees"
    }

    DETAIL_INDICATORS = {
        "ring", "letter", "phone", "gun", "knife", "key",
        "photograph", "watch", "blood", "tear"
    }

    def detect_from_paragraph(
        self,
        paragraph: Dict,
        scene: Dict
    ) -> Optional[Shot]:
        """Detect shot opportunity from a paragraph."""
        text = paragraph.get("text", "").lower()
        para_type = paragraph.get("type", "")

        # Dialogue with emotional content -> Close-up
        if para_type == "dialogue":
            if any(kw in text for kw in self.EMOTIONAL_KEYWORDS):
                return self._create_shot(
                    shot_type=ShotType.CU,
                    angle=CameraAngle.EYE_LEVEL,
                    description=f"Emotional beat - {self._extract_character(para)}",
                    evidence_ids=paragraph.get("evidence_ids", [])
                )

        # Action with movement -> Medium or Wide
        if para_type == "action":
            if any(verb in text for verb in self.MOVEMENT_VERBS):
                return self._create_shot(
                    shot_type=ShotType.MS,
                    description=f"Movement - {text[:50]}...",
                    evidence_ids=paragraph.get("evidence_ids", [])
                )

            # Detail focus -> Insert
            if any(det in text for det in self.DETAIL_INDICATORS):
                return self._create_shot(
                    shot_type=ShotType.INSERT,
                    description=f"Detail insert - {self._extract_detail(text)}",
                    evidence_ids=paragraph.get("evidence_ids", [])
                )

        return None
```

### Pattern 3: CSV Export (StudioBinder-Compatible)

**What:** Export shot list to industry-standard CSV format
**When to use:** When generating exports/shotlist.csv
**Example:**
```python
# Source: StudioBinder standard columns
class ShotListExporter:
    """Exports ShotList to CSV format compatible with StudioBinder."""

    # Standard columns (minimal set)
    CORE_COLUMNS = [
        "scene_number",
        "shot_number",
        "description",
        "shot_size",
        "camera_angle",
        "movement",
        "subject",
        "location",
        "cast",
        "notes"
    ]

    def export_csv(self, shot_list: ShotList, output_path: Path) -> None:
        """Export shot list to CSV."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.CORE_COLUMNS)
            writer.writeheader()

            for shot in shot_list.shots:
                writer.writerow({
                    "scene_number": shot.scene_number,
                    "shot_number": shot.shot_number,
                    "description": shot.description,
                    "shot_size": shot.shot_type.value,
                    "camera_angle": shot.angle.value,
                    "movement": shot.movement.value,
                    "subject": shot.subject or "",
                    "location": shot.location,
                    "cast": ", ".join(shot.characters),
                    "notes": shot.notes or ""
                })
```

### Anti-Patterns to Avoid
- **Using ML for shot detection:** Breaks determinism, adds heavy dependencies, inconsistent with project patterns
- **Storing shots in StoryGraph:** Shots are derived from ScriptGraph, not canonical entities - store separately
- **Over-prescriptive shot suggestions:** User should be able to edit/override in Obsidian - use protected blocks
- **Complex camera movements early:** Start with Static, Pan, Tilt, Dolly - defer Crane/Steadicam etc.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV formatting | Custom CSV writer | Python csv.DictWriter | Handles escaping, quoting, Unicode |
| Shot type enum | String constants | Enum class | Type safety, IDE support, serialization |
| Shot numbering | Manual counters | ShotSuggester._create_shot_id() | Deterministic, scoped to scene |

**Key insight:** The pattern is already established - ShotSuggester should mirror BaseValidator's structure exactly.

## Common Pitfalls

### Pitfall 1: Over-Shot Detection
**What goes wrong:** Suggesting a shot for every paragraph creates overwhelming lists
**Why it happens:** Too aggressive heuristics without filtering
**How to avoid:** Limit to meaningful shot changes - emotional peaks, movement, detail reveals
**Warning signs:** Shot list has 50+ shots for a 3-page scene

### Pitfall 2: Ignoring Scene Context
**What goes wrong:** Same heuristics apply to intimate dialogue scene and action sequence
**Why it happens:** ShotDetector doesn't consider scene metadata (int_ext, time_of_day)
**How to avoid:** Scene-level parameters adjust detection thresholds
**Warning signs:** Exterior action scenes get same density as interior dialogue

### Pitfall 3: Non-Deterministic Output
**What goes wrong:** Running `gsd suggest-shots` twice produces different results
**Why it happens:** Using unordered data structures or random elements
**How to avoid:** Always sort lists, use deterministic counters, no randomness
**Warning signs:** Git diff shows changes on rebuild with same input

### Pitfall 4: Breaking Evidence Traceability
**What goes wrong:** Shots generated without evidence_ids pointing to source
**Why it happens:** Detector creates shots without propagating paragraph evidence
**How to avoid:** Every Shot must include evidence_ids from source paragraphs
**Warning signs:** Shot notes can't link back to inbox source

## Code Examples

Verified patterns from existing codebase:

### Shot Type Enum
```python
# Source: Pattern from core/validation/base.py (IssueSeverity, IssueCategory)
from enum import Enum

class ShotType(Enum):
    """Shot size/type following industry standard terminology."""
    WS = "WS"      # Wide Shot
    MS = "MS"      # Medium Shot
    MCU = "MCU"    # Medium Close-Up
    CU = "CU"      # Close-Up
    ECU = "ECU"    # Extreme Close-Up
    INSERT = "INSERT"  # Insert/Detail shot
    OTS = "OTS"    # Over-the-shoulder
    POV = "POV"    # Point of view
    TWO = "TWO"    # Two-shot

class CameraAngle(Enum):
    """Camera angle relative to subject."""
    EYE_LEVEL = "eye-level"
    HIGH = "high"
    LOW = "low"
    DUTCH = "dutch"  # Tilted

class CameraMovement(Enum):
    """Camera movement type."""
    STATIC = "Static"
    PAN = "Pan"
    TILT = "Tilt"
    DOLLY = "Dolly"
    TRACKING = "Tracking"
    HANDHELD = "Handheld"
```

### Shot Dataclass
```python
# Source: Pattern from core/validation/base.py (Issue dataclass)
@dataclass
class Shot:
    """Represents a single shot suggestion."""
    shot_id: str
    scene_id: str
    scene_number: int
    shot_number: int  # Within scene
    shot_type: ShotType
    angle: CameraAngle = CameraAngle.EYE_LEVEL
    movement: CameraMovement = CameraMovement.STATIC
    description: str = ""
    subject: Optional[str] = None
    characters: List[str] = field(default_factory=list)
    location: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    suggested_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "shot_id": self.shot_id,
            "scene_id": self.scene_id,
            "scene_number": self.scene_number,
            "shot_number": self.shot_number,
            "shot_type": self.shot_type.value,
            "angle": self.angle.value,
            "movement": self.movement.value,
            "description": self.description,
            "subject": self.subject,
            "characters": sorted(self.characters),
            "location": self.location,
            "evidence_ids": sorted(self.evidence_ids),
            "notes": self.notes,
            "suggested_at": self.suggested_at.isoformat()
        }
```

### CLI Command Pattern
```python
# Source: Pattern from apps/cli/build.py and apps/cli/validate.py
# gsd suggest-shots command structure

def suggest_shots_command(args):
    """CLI command to generate shot suggestions."""
    project_path = Path(args.project) if args.project else Path.cwd()
    build_path = project_path / "build"

    # Check prerequisites
    if not (build_path / "scriptgraph.json").exists():
        print("Error: No scriptgraph.json found. Run 'gsd build script' first.")
        return 1

    # Run shot suggester
    suggester = ShotSuggester(build_path)
    shots = suggester.suggest()

    # Write shotgraph.json
    shot_list = ShotList(
        project_id=suggester._scriptgraph.get("project_id"),
        shots=shots
    )
    shot_list.save(build_path / "shotgraph.json")

    # Export CSV
    exporter = ShotListExporter()
    exports_path = project_path / "exports"
    exporter.export_csv(shot_list, exports_path / "shotlist.csv")

    print(f"Generated {len(shots)} shots across {len(set(s.scene_id for s in shots))} scenes")
    print(f"Exported to: {exports_path / 'shotlist.csv'}")

    return 0
```

## Shot Detection Rules

Based on filmmaking conventions and industry standards:

### Rule: Establishing Shot
**When:** First shot of every scene
**Type:** WS (Wide Shot)
**Description:** Establishes location from slugline
**Priority:** P0 (always)

### Rule: Emotional Dialogue
**When:** Dialogue contains emotional keywords
**Type:** CU (Close-Up)
**Detection:** Keywords: cry, tears, whisper, gasp, shock, love, hate
**Priority:** P1 (high confidence)

### Rule: Character Movement
**When:** Action contains movement verbs
**Type:** MS (Medium Shot)
**Detection:** Verbs: walks, runs, enters, exits, crosses, approaches
**Priority:** P1 (high confidence)

### Rule: Detail Insert
**When:** Action mentions specific objects
**Type:** INSERT
**Detection:** Objects: ring, letter, phone, gun, key, photograph
**Priority:** P2 (medium confidence)

### Rule: Two-Character Dialogue
**When:** Scene has exactly 2 speaking characters
**Type:** OTS (Over-the-shoulder)
**Detection:** Count unique character names in scene
**Priority:** P2 (medium confidence)

### Rule: POV Opportunity
**When:** Text explicitly describes character perspective
**Type:** POV
**Detection:** Phrases: "sees", "watches", "looks at", "notices"
**Priority:** P3 (low confidence - requires user confirmation)

## Blocking Notes Integration

Blocking notes track character positioning and movement within a scene:

### Blocking Note Structure
```python
@dataclass
class BlockingNote:
    """Character positioning/movement note within a scene."""
    note_id: str
    scene_id: str
    character_id: str
    character_name: str
    position: Optional[str] = None  # "center", "stage left", "upstage"
    movement: Optional[str] = None  # "enters from door", "crosses to window"
    interaction: Optional[str] = None  # "to JOHN", "away from SARAH"
    evidence_ids: List[str] = field(default_factory=list)
```

### Detection Patterns
```python
# Position keywords
POSITION_KEYWORDS = {
    "center stage", "stage left", "stage right",
    "upstage", "downstage", "upstage left", "upstage right",
    "downstage left", "downstage right"
}

# Movement patterns
MOVEMENT_PATTERNS = [
    r"(\w+) (enters|exits|crosses|moves|walks) (from|to|toward|away from) (.+)",
    r"(\w+) (sits|stands|rises|falls) (at|by|on|next to) (.+)"
]
```

## Spatial Constraint System (Deferred)

The ROADMAP mentions "spatial constraint system" but this is complex:

### What It Would Do
- Track character positions across shots
- Validate blocking consistency (character can't be stage left in shot 2 if stage right in shot 1 without movement)
- Generate floor plans for Blender_GSD integration

### Why Defer to Phase 6
- Requires 2D coordinate system
- Needs location geometry model
- Integration with Blender_GSD is Phase 6
- MVP: Just store blocking notes as text, not coordinates

### MVP Approach
Store blocking notes as free-form text in scene metadata:
```json
{
  "metadata": {
    "blocking_notes": [
      "John enters from door stage right",
      "Sarah seated at desk center stage"
    ]
  }
}
```

## ScriptGraph Schema Extension

Add shots array to scene in schema.json:

```json
{
  "shots": {
    "type": "array",
    "items": { "$ref": "#/$defs/shot" },
    "description": "Suggested shots for this scene"
  },
  "blocking_notes": {
    "type": "array",
    "items": { "type": "string" },
    "description": "Character staging notes"
  }
}
```

## Vault Template Update

Add Shot List section to SCN_Template.md:

```markdown
<!-- CONFUCIUS:BEGIN AUTO -->
## Cast

## Beat Sheet

## Shot List
<!-- Shot suggestions generated by gsd suggest-shots -->

## Blocking Notes

## Props / Wardrobe / Lighting

## Dialogue Draft

## Continuity Notes

## Issues

## Evidence

<!-- CONFUCIUS:END AUTO -->
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-written shot lists | Software-generated suggestions | 2010s | Faster pre-production |
| Paper blocking diagrams | Digital stage notation | 2000s | Easier collaboration |
| Director intuition only | AI-assisted suggestions | 2020s | More options to consider |

**Deprecated/outdated:**
- Camera directions in spec scripts: Modern screenwriting avoids ANGLE ON, CLOSE UP, etc. - let director decide. Shot suggestions are for production, not spec script inclusion.

## Open Questions

### 1. User Override Mechanism
- **What we know:** Shots need to be editable by user in Obsidian
- **What's unclear:** Should edits be preserved on rebuild, or always regenerated?
- **Recommendation:** Use protected blocks pattern - user can edit Shot List section, Confucius appends new suggestions rather than overwriting

### 2. Shot Density Threshold
- **What we know:** Too many shots overwhelm; too few miss opportunities
- **What's unclear:** Optimal shots-per-scene ratio
- **Recommendation:** Configurable in gsd.yaml with sensible default (3-5 shots per page)

### 3. Character Position Tracking
- **What we know:** Blocking notes are valuable for continuity
- **What's unclear:** How deeply to integrate with spatial constraints
- **Recommendation:** Start with text notes; defer coordinate system to Phase 6

## Key Decisions for User (/gsd:discuss-phase)

These decisions should be discussed before planning:

1. **Shot Suggestion Aggressiveness**
   - Conservative: Only high-confidence suggestions (emotional dialogue, movement)
   - Moderate: Include medium-confidence (two-shots, detail inserts)
   - Aggressive: All potential opportunities
   - **Recommendation:** Moderate with configurable thresholds

2. **Export Format**
   - CSV only (StudioBinder-compatible)
   - CSV + JSON (shotgraph.json for programmatic access)
   - **Recommendation:** Both - CSV for production, JSON for integration

3. **Blocking Notes Depth**
   - Simple text notes in vault
   - Structured data with character/position/movement fields
   - Full spatial coordinate system
   - **Recommendation:** Start with simple text, add structure if needed

4. **Vault Integration**
   - Auto-populate Shot List section in scene notes
   - Separate 60_Shots/ folder with shot notes
   - **Recommendation:** Auto-populate scene notes with protected blocks

## Claude's Discretion (Implementation Details)

These can be decided during implementation:

1. **Shot numbering scheme** - SCN_001_S001 or scene-scoped counter
2. **Detection keyword lists** - Tune based on test fixtures
3. **CSV column order** - Match StudioBinder defaults
4. **Evidence ID propagation** - Follow Paragraph pattern exactly
5. **Error handling** - Follow existing CLI patterns

## Sources

### Primary (HIGH confidence)
- StudioBinder Shot List Guide (fetched via webReader) - Industry standard columns and terminology
- core/validation/base.py - Pattern for suggester/validator classes
- core/script/beats.py - Pattern for content detection heuristics
- core/script/builder.py - Pattern for builder orchestration

### Secondary (MEDIUM confidence)
- WebSearch: Shot list CSV format - Verified StudioBinder is industry standard
- WebSearch: Blocking notes/filmmaking - Blocking terminology and methods
- templates/project_template/vault/50_Scenes/SCN_Template.md - Existing vault structure

### Tertiary (LOW confidence)
- WebSearch: Automatic shot detection from screenplay - Results focused on video analysis, not text analysis (novel approach required)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, follows existing patterns exactly
- Architecture: HIGH - Mirrors BaseValidator and ScriptBuilder patterns
- Shot types/terminology: HIGH - Industry standard from StudioBinder
- Detection heuristics: MEDIUM - Novel approach, needs tuning with real scripts
- Spatial constraints: LOW - Complex feature deferred to Phase 6

**Research date:** 2026-02-19
**Valid until:** 30 days (stable domain, established patterns)
