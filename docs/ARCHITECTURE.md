# Architecture Overview

## System Design

FDX GSD follows a pipeline architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│                     apps/cli/cli.py                              │
├─────────────────────────────────────────────────────────────────┤
│                      Core Pipeline                               │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐        │
│  │ Ingest  │──►│  Canon  │──►│ Script  │──►│  Shots  │        │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘        │
│       │             │             │             │               │
│       ▼             ▼             ▼             ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Validation Layer                      │   │
│  │  Wardrobe │ Props │ Timeline │ Knowledge │ Orchestrator │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     Layout Layer                         │   │
│  │  Camera Math │ Generator │ Exporter                      │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                       Data Models                                │
│  StoryGraph │ ScriptGraph │ ShotGraph │ LayoutBrief │ Issues   │
├─────────────────────────────────────────────────────────────────┤
│                       Storage Layer                              │
│  inbox/ │ vault/ │ build/ │ blender/ │ exports/                 │
└─────────────────────────────────────────────────────────────────┘
```

## Core Modules

### core/extraction/

Entity extraction from raw text:

- **CanonBuilder**: Orchestrates extraction pipeline
- **CharacterExtractor**: NER for character names
- **LocationExtractor**: NER for locations
- **SceneDetector**: Scene boundary detection
- **AliasResolver**: Fuzzy matching for aliases

### core/script/

Screenplay composition:

- **ScriptBuilder**: Transforms StoryGraph to ScriptGraph
- **BeatExtractor**: Action beats from inbox content
- **DialogueFormatter**: Character dialogue formatting
- **SluglineGenerator**: Scene headings

### core/shots/

Shot suggestion system:

- **ShotSuggester**: Orchestrates shot detection
- **ShotDetector**: Rule-based shot detection
- **ShotListExporter**: CSV/JSON export
- **ShotType**: Enum for shot types

### core/layout/

Layout brief generation:

- **LayoutBriefGenerator**: Transforms ScriptGraph + ShotGraph to LayoutBrief
- **LayoutBriefExporter**: JSON export to blender/
- **Camera Math**: Position calculation from shot types
- **Models**: LayoutBrief, SceneLayout, CameraSetup, CharacterPosition

### core/validation/

Continuity validation:

- **ValidationOrchestrator**: Coordinates all validators
- **BaseValidator**: Abstract base class
- **WardrobeValidator**: Wardrobe state tracking
- **PropsValidator**: Prop continuity
- **TimelineValidator**: Temporal consistency
- **KnowledgeValidator**: Information flow
- **ReportGenerator**: Markdown reports

## Data Flow

### Ingestion Flow

```
Raw Text ──► Ingest ──► inbox/xxx.md (with evidence IDs)
```

### Canon Build Flow

```
inbox/*.md ──► CanonBuilder ──► StoryGraph
                              ──► vault/10_Characters/*.md
                              ──► vault/20_Locations/*.md
                              ──► vault/50_Scenes/*.md
```

### Script Build Flow

```
StoryGraph ──► ScriptBuilder ──► ScriptGraph
                               ──► vault/50_Scenes/*.md (updated)
```

### Shot Suggestion Flow

```
ScriptGraph ──► ShotSuggester ──► ShotGraph
                               ──► exports/shotlist.csv
                               ──► vault/50_Scenes/*.md (updated)
```

### Layout Generation Flow

```
ScriptGraph + ShotGraph ──► LayoutBriefGenerator ──► LayoutBrief
                                                     ──► blender/*/layout_brief.json
```

### Validation Flow

```
StoryGraph ──► ValidationOrchestrator ──► Issues
            ──► WardrobeValidator
            ──► PropsValidator
            ──► TimelineValidator
            ──► KnowledgeValidator
                                        ──► vault/80_Reports/*.md
```

## Data Models

### StoryGraph

Canonical entity graph:

```json
{
  "version": "1.0",
  "project_id": "string",
  "characters": [Character],
  "locations": [Location],
  "scenes": [Scene],
  "aliases": [Alias]
}
```

### ScriptGraph

Screenplay with paragraphs:

```json
{
  "version": "1.0",
  "project_id": "string",
  "scenes": [{
    "id": "SCN_001",
    "paragraphs": [Paragraph]
  }]
}
```

### ShotGraph

Camera shots:

```json
{
  "version": "1.0",
  "project_id": "string",
  "shots": [Shot],
  "total_shots": 0
}
```

### LayoutBrief

Spatial layout:

```json
{
  "version": "1.0",
  "project_id": "string",
  "scene_layouts": [SceneLayout]
}
```

### Issues

Validation issues:

```json
{
  "version": "1.0",
  "project_id": "string",
  "issues": [Issue],
  "by_severity": {"error": 0, "warning": 0, "info": 0}
}
```

## Key Patterns

### Builder Pattern

All builders follow the same interface:

```python
class SomeBuilder:
    def __init__(self, build_path: Path):
        self.build_path = build_path
        self._state = None

    def build(self) -> BuildResult:
        # Load input
        # Process
        # Return result
        pass

    def get_output(self) -> OutputType:
        return self._state
```

### Validator Pattern

All validators extend BaseValidator:

```python
class SomeValidator(BaseValidator):
    def validate(self, storygraph: dict) -> List[Issue]:
        issues = []
        # Check rules
        return issues
```

### Exporter Pattern

All exporters follow the same interface:

```python
class SomeExporter:
    def export(self, data: DataType, path: Path) -> Path:
        # Write to file
        return path
```

## Determinism

All builds are deterministic:

1. Sorted lists (by ID, order, etc.)
2. `sort_keys=True` for JSON
3. No random values
4. Timestamps only in metadata

This enables:
- Diff-friendly outputs
- Reproducible builds
- Version control friendliness

## Evidence Traceability

Every derived fact has `evidence_ids`:

```python
# In CanonBuilder
entity.evidence_ids = ["EV_001", "EV_002"]

# Propagates through:
StoryGraph → ScriptGraph → ShotGraph → LayoutBrief
```

This enables:
- Source attribution
- Impact analysis
- Audit trails

## Extension Points

### Adding a New Validator

1. Create `core/validation/xxx_validator.py`
2. Extend `BaseValidator`
3. Implement `validate()` method
4. Register in `ValidationOrchestrator`

### Adding a New Export Format

1. Create exporter class
2. Follow exporter pattern
3. Add CLI subcommand

### Adding a New Shot Type

1. Add to `ShotType` enum
2. Add distance to `SHOT_TYPE_DISTANCES`
3. Add detection rule to `ShotDetector`
