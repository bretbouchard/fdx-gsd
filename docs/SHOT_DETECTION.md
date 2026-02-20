# Shot Detection System

## Overview

FDX GSD automatically suggests camera shots based on scene content. The system uses rule-based detection (no ML) to infer appropriate shot types from dialogue, action, and scene structure.

## Shot Types

| Type | Code | Distance | Use Case |
|------|------|----------|----------|
| Wide Shot | WS | 5.0m | Establishing, environment |
| Medium Shot | MS | 2.5m | Standard dialogue, movement |
| Medium Close-Up | MCU | 1.8m | Intimate dialogue |
| Close-Up | CU | 1.2m | Emotional moments, reactions |
| Extreme Close-Up | ECU | 0.8m | Intense emotion, details |
| Insert | INSERT | 0.5m | Props, objects, details |
| Over-the-Shoulder | OTS | 2.0m | Two-person dialogue |
| POV | POV | 1.7m | Character's perspective |
| Two Shot | TWO | 3.0m | Two characters in frame |

## Detection Rules

### Priority 0: Establishing Shot

**Trigger:** First shot of every scene

**Shot Type:** WS (Wide Shot)

**Rationale:** Every scene starts with an establishing shot to orient the audience.

```
Scene: INT. OFFICE - DAY
→ Shot 1: WS (Always added first)
```

### Priority 1: Emotional Dialogue

**Trigger:** Emotional keywords in dialogue

**Shot Type:** CU (Close-Up)

**Keywords:**
- love, hate, cry, tears, scream, shout
- angry, sad, happy, scared, terrified
- kiss, kill, die, death, alive

**Example:**
```
SARAH: I love you so much it hurts.
→ CU on Sarah
```

### Priority 2: Movement/Action

**Trigger:** Action verbs in descriptions

**Shot Type:** MS (Medium Shot)

**Keywords:**
- walk, run, sit, stand, turn, move
- enter, exit, approach, retreat
- fight, chase, flee, follow

**Example:**
```
Fox walks across the room.
→ MS showing movement
```

### Priority 2: Detail Insert

**Trigger:** Object mentions in action

**Shot Type:** INSERT

**Patterns:**
- "picks up the [object]"
- "looks at the [object]"
- "[object] on the table"

**Example:**
```
He picks up the letter.
→ INSERT on letter
```

### Priority 2: Over-the-Shoulder

**Trigger:** Two-character dialogue scene

**Shot Type:** OTS

**Conditions:**
- Scene has 2+ characters
- Dialogue exchange present
- No strong emotional cues

**Example:**
```
FOX: What do you think?
SARAH: I'm not sure.
→ OTS from Fox to Sarah
→ OTS from Sarah to Fox
```

### Priority 3: POV

**Trigger:** POV-related phrases

**Shot Type:** POV

**Patterns:**
- "from [character]'s perspective"
- "through [character]'s eyes"
- "[character] sees"

**Example:**
```
From Fox's perspective, the room spins.
→ POV shot
```

## Detection Process

```
1. Load ScriptGraph
2. For each scene:
   a. Add P0 establishing shot (WS)
   b. Scan paragraphs for P1 triggers (CU, MS)
   c. Scan for P2 triggers (INSERT, OTS)
   d. Scan for P3 triggers (POV)
3. Deduplicate overlapping shots
4. Sort by shot_number
5. Generate shot IDs
```

## Output Format

### ShotGraph JSON

```json
{
  "version": "1.0",
  "project_id": "my_movie",
  "total_shots": 12,
  "shots": [
    {
      "shot_id": "shot_001_001",
      "scene_id": "SCN_001",
      "scene_number": 1,
      "shot_number": 1,
      "shot_type": "WS",
      "movement": "Static",
      "description": "Establishing shot",
      "evidence_ids": []
    }
  ]
}
```

### CSV Export (StudioBinder-compatible)

```csv
scene_number,shot_number,shot_size,movement,description,start_time,end_time,notes
1,1,WS,Static,Establishing shot,,,
1,2,CU,Static,Close-up on emotional dialogue,,,
```

## CLI Usage

```bash
# Generate shot suggestions
gsd suggest-shots

# Dry run (no files written)
gsd suggest-shots --dry-run
```

## Customization

Shot detection can be customized in `gsd.yaml`:

```yaml
shots:
  # Add custom emotional keywords
  emotional_keywords:
    - desperate
    - furious
    - heartbroken

  # Add custom action verbs
  action_verbs:
    - leap
    - crawl
    - sprint

  # Disable specific rules
  disabled_rules:
    - POV  # No automatic POV shots
```

## Integration with Layout

Shot suggestions feed into layout generation:

```
gsd suggest-shots → build/shotgraph.json
gsd generate-layout → Uses shotgraph.json for camera positions
```

Each shot's `shot_type` determines camera distance in the layout brief.
