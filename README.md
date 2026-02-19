# FDX GSD - Story Operating System

A Confucius-powered system that turns "drunk drivel" into polished screenplays.

## Overview

FDX GSD is a GSD-native story development system that:

- **Ingests** raw notes (text, voice transcripts, messy brainstorming)
- **Extracts** canonical entities (characters, locations, props, wardrobe)
- **Tracks** continuity (wardrobe states, prop locations, timeline)
- **Validates** story logic (knowledge leaks, timeline issues, spatial contradictions)
- **Composes** screenplay artifacts (scenes, beats, dialogue)
- **Exports** to Final Draft (.fdx) format

## Quick Start

```bash
# Create a new project
gsd new-project my_movie

# Enter project directory
cd projects/my_movie

# Ingest raw material
gsd ingest --text "Fox meets Sarah at the diner. He's wearing his jacket."

# Build canonical entities (Phase 1)
gsd build canon

# Build screenplay (Phase 2)
gsd build script

# Export to FDX
gsd export fdx
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
│   ├── storygraph.json
│   ├── scriptgraph.json
│   ├── disambiguation_queue.json
│   └── issues.json
└── exports/
    └── script.fdx
```

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ | Project creation + ingest |
| 1 | 🚧 | Canon extraction (characters, locations, scenes) |
| 2 | 🚧 | Script composition + FDX export |
| 3 | 📋 | Round-trip editing |
| 4 | 📋 | Continuity validation |
| 5 | 📋 | Shot lists + spatial reasoning |
| 6 | 📋 | Blender_GSD integration |

## Key Concepts

### Obsidian-First

Everything is Markdown. The vault is the source of truth. All entities are linkable with `[[CHAR_Fox]]` syntax.

### Append-Only Mutation

Confucius only writes inside managed blocks:

```markdown
<!-- CONFUCIUS:BEGIN AUTO -->
## Appears In
- [[SCN_001]]
<!-- CONFUCIUS:END AUTO -->
```

### Evidence Traceability

Every derived fact links back to source evidence:

```markdown
## Evidence
- [[inbox/2026-02-18_001#^ev_a13f]]
```

## Validator Rules

| Category | Rules |
|----------|-------|
| Wardrobe | State changes require cause, signature items persist |
| Props | Cannot appear without introduction, damage persists |
| Timeline | Impossible travel, character in two places |
| Knowledge | Cannot reference unlearned information |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type check
mypy apps core
```

## License

MIT
