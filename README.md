# FDX GSD - Story Operating System

A Confucius-powered system that turns "drunk drivel" into polished screenplays with full continuity tracking and 3D previz integration.

## Overview

FDX GSD is a GSD-native story development system that:

- **Ingests** raw notes (text, voice transcripts, messy brainstorming)
- **Extracts** canonical entities (characters, locations, props, wardrobe)
- **Tracks** continuity (wardrobe states, prop locations, timeline)
- **Validates** story logic (knowledge leaks, timeline issues, spatial contradictions)
- **Composes** screenplay artifacts (scenes, beats, dialogue)
- **Suggests** camera shots based on scene content
- **Generates** layout briefs for 3D previz (Blender integration)
- **Exports** to Final Draft (.fdx) format

## Installation

```bash
# Clone the repository
git clone https://github.com/bretbouchard/fdx-gsd.git
cd fdx-gsd

# Install with pip
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

```bash
# Create a new project
gsd new-project my_movie

# Enter project directory
cd projects/my_movie

# Ingest raw material
gsd ingest --text "Fox meets Sarah at the diner. He's wearing his jacket."

# Build canonical entities (characters, locations, scenes)
gsd build canon

# Resolve any disambiguation issues
gsd resolve

# Build screenplay with proper formatting
gsd build script

# Suggest camera shots
gsd suggest-shots

# Generate layout briefs for Blender
gsd generate-layout

# Validate continuity and story logic
gsd validate

# Export to Final Draft
gsd export fdx

# Check project status
gsd status
```

## Project Structure

```
projects/my_movie/
├── gsd.yaml              # Project configuration
├── inbox/                # Raw drivel dumps (immutable)
│   └── 2026-02-18_001.md
├── vault/                # Obsidian vault (source of truth)
│   ├── 00_Index/
│   │   ├── Home.md
│   │   ├── Open_Issues.md
│   │   └── Timeline.md
│   ├── 10_Characters/
│   │   └── CHAR_Fox.md
│   ├── 20_Locations/
│   │   └── LOC_Joes_Diner.md
│   ├── 50_Scenes/
│   │   └── SCN_001.md
│   └── 80_Reports/
├── build/                # Machine-generated (rebuildable)
│   ├── storygraph.json   # Entity graph
│   ├── scriptgraph.json  # Screenplay paragraphs
│   ├── shotgraph.json    # Camera shots
│   ├── layout_brief.json # Layout for Blender
│   └── issues.json       # Validation issues
├── blender/              # Layout briefs for 3D previz
│   └── SCN_001/
│       └── layout_brief.json
└── exports/
    ├── script.fdx        # Final Draft export
    └── shotlist.csv      # StudioBinder-compatible
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `gsd new-project <name>` | Create a new project |
| `gsd ingest --text "..."` | Ingest raw material |
| `gsd ingest --file notes.md` | Ingest from file |
| `gsd build canon` | Extract characters, locations, scenes |
| `gsd build script` | Generate screenplay paragraphs |
| `gsd resolve` | Interactive disambiguation |
| `gsd suggest-shots` | Generate shot suggestions |
| `gsd generate-layout` | Create layout briefs for Blender |
| `gsd validate` | Check continuity and story logic |
| `gsd sync` | Sync vault changes to graph |
| `gsd conflicts` | Show merge conflicts |
| `gsd export fdx` | Export to Final Draft |
| `gsd status` | Show project status |

## Phases (All Complete)

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ | Project creation + ingest |
| 1 | ✅ | Canon extraction (characters, locations, scenes) |
| 2 | ✅ | Script composition + FDX export |
| 3 | ✅ | Round-trip editing (vault sync) |
| 4 | ✅ | Continuity validation |
| 5 | ✅ | Shot lists + camera suggestions |
| 6 | ✅ | Blender layout brief generation |
| 7 | ✅ | Media asset archive system |

## Key Concepts

### Obsidian-First

Everything is Markdown. The vault is the source of truth. All entities are linkable with `[[CHAR_Fox]]` syntax.

### Protected Blocks

Confucius only writes inside managed blocks, preserving your manual edits:

```markdown
<!-- CONFUCIUS:BEGIN AUTO -->
## Appears In
- [[SCN_001]]
<!-- CONFUCIUS:END AUTO -->

## My Notes
This section is preserved - Confucius won't touch it.
```

### Evidence Traceability

Every derived fact links back to source evidence:

```markdown
## Evidence
- [[inbox/2026-02-18_001#^ev_a13f]]
```

### Deterministic Builds

All builds are reproducible. Running the same command twice produces identical output.

## Validation Rules

| Category | Rules |
|----------|-------|
| **Wardrobe** | State changes require cause, signature items persist |
| **Props** | Cannot appear without introduction, damage persists |
| **Timeline** | Impossible travel, character in two places |
| **Knowledge** | Cannot reference unlearned information |

## Shot Detection

Automatic shot suggestions based on scene content:

| Shot Type | Trigger | Distance |
|-----------|---------|----------|
| WS (Wide) | First shot of scene | 5.0m |
| MS (Medium) | Movement, action | 2.5m |
| CU (Close-Up) | Emotional dialogue | 1.2m |
| ECU (Extreme) | Intense emotion | 0.8m |
| INSERT | Object mentions | 0.5m |
| OTS | Two-character dialogue | 2.0m |
| POV | POV phrases | 1.7m |
| TWO | Two characters | 3.0m |

## Layout Brief Format

The layout brief provides spatial data for Blender previz:

```json
{
  "version": "1.0",
  "scene_layouts": [{
    "scene_id": "SCN_001",
    "characters": [{
      "character_id": "CHAR_fox",
      "position": {"x": -0.75, "y": 0, "z": 0},
      "facing": {"x": 0, "y": 1, "z": 0}
    }],
    "camera_setups": [{
      "setup_id": "CAM_shot_001_001",
      "shot_type": "WS",
      "camera": {
        "position": {"x": 0, "y": -5.0, "z": 2.0},
        "rotation": {"pitch": -15, "yaw": 0, "roll": 0}
      }
    }]
  }]
}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test modules
pytest tests/unit/test_layout_models.py
pytest tests/integration/test_layout_workflow.py

# Type check
mypy apps core

# Run with coverage
pytest --cov=core --cov=apps
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (apps/cli)                          │
├─────────────────────────────────────────────────────────────┤
│  canon  │ script │ shots │ layout │ validate │ export      │
├─────────────────────────────────────────────────────────────┤
│                      Core Modules                            │
│  ─────────────────────────────────────────────────────────  │
│  extraction │ script │ shots │ layout │ validation         │
├─────────────────────────────────────────────────────────────┤
│                      Data Layer                              │
│  ─────────────────────────────────────────────────────────  │
│  StoryGraph │ ScriptGraph │ ShotGraph │ LayoutBrief        │
├─────────────────────────────────────────────────────────────┤
│                      Storage                                 │
│  ─────────────────────────────────────────────────────────  │
│  inbox/ │ vault/ │ build/ │ blender/ │ exports/            │
└─────────────────────────────────────────────────────────────┘
```

## License

MIT
