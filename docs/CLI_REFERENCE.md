# CLI Reference

## Installation

```bash
pip install -e .
```

## Global Options

```
gsd [OPTIONS] COMMAND [ARGS]

Options:
  --help     Show help message
  --version  Show version
```

## Commands

### new-project

Create a new FDX GSD project.

```bash
gsd new-project <name> [--path /custom/path]
```

**Arguments:**
- `name` - Project name (required)

**Options:**
- `--path` - Custom project path (default: `./projects/<name>`)

**Creates:**
- Project directory structure
- `gsd.yaml` configuration
- Obsidian vault with templates
- `inbox/`, `build/`, `exports/` directories

---

### ingest

Ingest raw material into the project.

```bash
gsd ingest --text "Raw content here"
gsd ingest --file notes.md
gsd ingest --dir drafts/
```

**Options:**
- `--text` - Inline text content
- `--file` - Path to file
- `--dir` - Path to directory

**Creates:**
- `inbox/YYYY-MM-DD_XXX.md` with evidence IDs

**Notes:**
- Source files are never modified
- Content is wrapped with evidence blockquotes

---

### build

Build project artifacts.

```bash
gsd build canon
gsd build script
```

**Subcommands:**

#### canon

Extract canonical entities (characters, locations, scenes).

```bash
gsd build canon [--dry-run]
```

**Options:**
- `--dry-run` - Show what would be done without writing

**Creates:**
- `build/storygraph.json`
- `vault/10_Characters/*.md`
- `vault/20_Locations/*.md`
- `vault/50_Scenes/*.md`

#### script

Generate screenplay paragraphs.

```bash
gsd build script [--dry-run]
```

**Options:**
- `--dry-run` - Show what would be done without writing

**Requires:**
- `build/storygraph.json` (run `build canon` first)

**Creates:**
- `build/scriptgraph.json`
- Updates `vault/50_Scenes/*.md`

---

### resolve

Interactive disambiguation of entities.

```bash
gsd resolve
```

**Requires:**
- Disambiguation queue in `build/disambiguation_queue.json`

**Workflow:**
1. Shows ambiguous entity
2. Presents options
3. User selects resolution
4. Updates StoryGraph and vault

---

### suggest-shots

Generate camera shot suggestions.

```bash
gsd suggest-shots [--dry-run]
```

**Options:**
- `--dry-run` - Show what would be done without writing

**Requires:**
- `build/scriptgraph.json` (run `build script` first)

**Creates:**
- `build/shotgraph.json`
- `exports/shotlist.csv`
- Updates `vault/50_Scenes/*.md` with Shot List section

---

### generate-layout

Generate layout briefs for 3D previz.

```bash
gsd generate-layout [--dry-run]
```

**Options:**
- `--dry-run` - Show what would be done without writing

**Requires:**
- `build/scriptgraph.json`
- `build/shotgraph.json` (run `suggest-shots` first)

**Creates:**
- `blender/<scene_id>/layout_brief.json`
- `build/layout_brief.json` (combined)

---

### validate

Validate story continuity and logic.

```bash
gsd validate [--fix] [--severity error|warning|info]
```

**Options:**
- `--fix` - Attempt automatic fixes
- `--severity` - Minimum severity to report (default: warning)

**Requires:**
- `build/storygraph.json`

**Creates:**
- `build/issues.json`
- `vault/80_Reports/Validation_YYYY-MM-DD.md`

**Exit Codes:**
- 0 - No issues
- 1 - Issues found
- 2 - Error during validation

---

### sync

Sync vault changes back to graphs.

```bash
gsd sync
```

**Workflow:**
1. Detects changed files in vault
2. Re-ingests changed content
3. Updates graphs
4. Flags conflicts

---

### conflicts

Show merge conflicts.

```bash
gsd conflicts [--resolve]
```

**Options:**
- `--resolve` - Interactive conflict resolution

---

### export

Export to external formats.

```bash
gsd export fdx [--output script.fdx]
```

**Subcommands:**

#### fdx

Export to Final Draft format.

```bash
gsd export fdx [--output script.fdx]
```

**Options:**
- `--output` - Output file path (default: `exports/script.fdx`)

**Requires:**
- `build/scriptgraph.json`

---

### status

Show project status.

```bash
gsd status
```

**Shows:**
- Project info
- Build status
- Unresolved issues
- Pending disambiguations

---

## Workflow Examples

### Basic Workflow

```bash
# Create project
gsd new-project my_movie
cd projects/my_movie

# Add content
gsd ingest --file ~/notes/draft.txt

# Build
gsd build canon
gsd resolve        # If needed
gsd build script
gsd suggest-shots
gsd generate-layout
gsd validate

# Export
gsd export fdx
```

### Round-Trip Editing

```bash
# Initial build
gsd build canon

# Edit in Obsidian
# (make changes to vault/50_Scenes/SCN_001.md)

# Sync changes back
gsd sync

# Check for conflicts
gsd conflicts

# Rebuild
gsd build script
```

### Validation Workflow

```bash
# Validate
gsd validate

# Review issues in Obsidian
# (open vault/80_Reports/)

# Fix issues in source
# (edit inbox/ or vault/)

# Re-validate
gsd validate
```

## Configuration

### gsd.yaml

```yaml
project:
  name: My Movie
  version: 0.1.0

settings:
  confidence_threshold: 0.8
  auto_resolve: false

validation:
  wardrobe:
    enabled: true
    strict: false
  timeline:
    enabled: true
    travel_speed_kmh: 100
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Issues found (validation) |
| 2 | Error during operation |
| 64 | Command line error |
| 65 | Data error |
| 66 | No input |
| 74 | I/O error |
