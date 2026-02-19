# PLAN: Phase 1 - Canon Extraction

**Phase:** 1
**Goal:** From raw inbox material → clean scene list + entity list
**Bead:** fdx_gsd-2
**Created:** 2026-02-19

---

## Overview

Transform raw "drunk drivel" in inbox/ into canonical entities in the Obsidian vault and StoryGraph JSON.

### Key Architecture Decisions (Already Made)

| Decision | ADR | Impact |
|----------|-----|--------|
| No ML/NER library | ADR-0002 | Use lightweight regex extraction |
| Interactive disambiguation | ADR-0002 | Always ask on ambiguity |
| rapidfuzz for fuzzy matching | ADR-0003 | Alias suggestions |
| Configurable thresholds | ADR-0004 | Per-project tuning |
| Confucius MCP for memory | ADR-0005 | Store patterns, aliases |

---

## Requirements to Deliver

| ID | Requirement | Priority |
|----|-------------|----------|
| CAN-01 | Character Extraction | P0 |
| CAN-02 | Location Extraction | P0 |
| CAN-03 | Scene Detection | P0 |
| CAN-04 | Alias Resolution | P0 |
| CAN-05 | Disambiguation Queue | P0 |
| CAN-06 | Evidence Linking | P0 |

---

## Implementation Plans

### PLAN 1: Entity Extraction Engine (CAN-01, CAN-02, CAN-03)

**Goal:** Extract characters, locations, and scenes from inbox text

**Files to Create:**
```
core/extraction/
  __init__.py
  base.py           # Base extractor class
  characters.py     # Character extraction (CAN-01)
  locations.py      # Location extraction (CAN-02)
  scenes.py         # Scene detection (CAN-03)
  patterns.py       # Regex patterns
```

**Extraction Patterns (ADR-0002):**

```python
# Characters
- Proper nouns in action/dialogue (Fox, Sarah)
- ALL CAPS in dialogue (FOX, SARAH)
- Role references (the waiter, A MAN, OLD WOMAN)
- Pronouns resolved via context (he, she, they - requires disambiguation)

# Locations
- INT./EXT. patterns (INT. DINER - NIGHT)
- "the [place]" references (the diner, the office)
- Named locations (Joe's Diner, The Rusty Anchor)
- Location possessives (Sarah's apartment, his office)

# Scenes
- Slugline patterns (INT./EXT. LOCATION - TIME)
- Scene transitions (CUT TO:, FADE TO:, LATER)
- Implicit boundaries (significant time/location jumps)
```

**Algorithm:**
1. Parse each inbox file
2. Extract candidates using patterns
3. Calculate confidence score
4. Check against known aliases (from Confucius)
5. High confidence → auto-link
6. Ambiguous → queue for disambiguation
7. Store evidence links

---

### PLAN 2: Alias Resolution System (CAN-04)

**Goal:** Resolve entity aliases with configurable confidence

**Files to Create:**
```
core/resolution/
  __init__.py
  fuzzy_matcher.py  # rapidfuzz integration
  alias_resolver.py # Main resolution logic
  confidence.py     # Confidence scoring
```

**Resolution Flow:**
```
Input: "Ricky"
  ↓
Check exact match in known entities → Found? → Link
  ↓ No
Check known aliases (Confucius) → Found? → Link
  ↓ No
Fuzzy match with rapidfuzz → Score > threshold?
  ↓ Yes                          ↓ No
Queue for disambiguation    Assume new entity
```

**Confidence Scoring:**
```python
def calculate_confidence(text: str, candidate: Entity) -> float:
    score = 0.0

    # Exact match
    if text.lower() == candidate.name.lower():
        return 1.0

    # Known alias
    if text.lower() in [a.lower() for a in candidate.aliases]:
        return 0.95

    # Fuzzy match
    fuzzy_score = fuzz.ratio(text.lower(), candidate.name.lower()) / 100

    # Context bonus (same scene, same paragraph)
    context_bonus = 0.1 if shared_context else 0.0

    return min(fuzzy_score + context_bonus, 1.0)
```

---

### PLAN 3: Disambiguation Queue System (CAN-05)

**Goal:** Manage items requiring human resolution

**Files to Create:**
```
core/queue/
  __init__.py
  queue_manager.py  # Queue CRUD operations
  queue_item.py     # Queue item model
```

**Queue Item Model:**
```python
@dataclass
class QueueItem:
    id: str                    # dq_0001
    kind: QueueItemKind        # entity_merge, reference_link, etc.
    status: Status             # open, resolved, deferred
    label: str                 # Human-readable question
    mention: str               # The ambiguous text
    context: str               # Surrounding context
    candidates: List[Candidate]  # Possible matches
    recommended_action: str    # merge, link, create
    recommended_target: str    # Suggested entity ID
    evidence_ids: List[str]    # Source evidence
    created_at: datetime
```

**CLI Commands:**
```bash
gsd resolve              # Interactive resolution (one at a time)
gsd resolve --batch 10   # Process 10 items at once
gsd resolve --all        # Process all open items
gsd queue status         # Show queue statistics
```

---

### PLAN 4: Evidence Linking (CAN-06)

**Goal:** Every extracted fact links back to source

**Files to Create:**
```
core/evidence/
  __init__.py
  evidence_linker.py  # Link entities to evidence
```

**Evidence Format:**
```markdown
<!-- In vault/10_Characters/CHAR_Fox.md -->
## Evidence
- [[inbox/2026-02-18_001#^ev_a1b2]]
- [[inbox/2026-02-18_003#^ev_c3d4]]
```

**Evidence Index (JSON):**
```json
{
  "ev_a1b2": {
    "source_path": "inbox/2026-02-18_001.md",
    "block_ref": "^ev_a1b2",
    "text_excerpt": "Fox enters the diner wearing his jacket.",
    "linked_entities": ["CHAR_Fox", "LOC_Diner", "PROP_Jacket"]
  }
}
```

---

### PLAN 5: Canon Build Command (CLI Integration)

**Goal:** Wire everything together with `gsd build canon`

**Files to Modify:**
```
apps/cli/cli.py  # Add build canon command
```

**Command Flow:**
```
gsd build canon
  ↓
1. Load config from gsd.yaml
2. Initialize Confucius client
3. Load evidence index
4. For each inbox file:
   a. Extract entities (PLAN 1)
   b. Resolve aliases (PLAN 2)
   c. Queue ambiguities (PLAN 3)
   d. Link evidence (PLAN 4)
5. Write/update vault notes
6. Update storygraph.json
7. Update disambiguation queue
8. Report statistics
```

**Output:**
```
Building canon...

Processed: 5 inbox files
Extracted:
  - 12 characters (8 new, 4 linked)
  - 5 locations (3 new, 2 linked)
  - 8 scenes

Disambiguation queue:
  - 3 items need review

Run 'gsd resolve' to process disambiguation items.
```

---

## Execution Order

| Step | Plan | Delivers | Duration |
|------|------|----------|----------|
| 1 | PLAN 1 | Entity extractors | ~2h |
| 2 | PLAN 4 | Evidence linking | ~1h |
| 3 | PLAN 2 | Alias resolution | ~1.5h |
| 4 | PLAN 3 | Disambiguation queue | ~1.5h |
| 5 | PLAN 5 | CLI integration | ~1h |
| 6 | Tests | Unit + integration | ~1h |

**Total Estimated:** 8 hours

---

## Test Strategy

### Unit Tests
```
tests/unit/
  test_character_extractor.py
  test_location_extractor.py
  test_scene_detector.py
  test_alias_resolver.py
  test_queue_manager.py
  test_evidence_linker.py
```

### Integration Tests
```
tests/integration/
  test_canon_pipeline.py   # Full ingest → canon flow
```

### Test Fixtures
```
tests/fixtures/
  sample_story_simple.md    # Already exists
  sample_story_aliases.md   # Multiple aliases for same character
  sample_story_complex.md   # Many characters, locations, scenes
  public_domain_script.md   # Real screenplay excerpt
```

---

## Exit Criteria

Phase 1 is complete when:

- [ ] `gsd build canon` runs without errors
- [ ] Characters are extracted from inbox files
- [ ] Locations are extracted from inbox files
- [ ] Scenes are detected with correct boundaries
- [ ] Aliases are resolved or queued appropriately
- [ ] Disambiguation queue is populated
- [ ] `gsd resolve` presents items interactively
- [ ] All entities have evidence links
- [ ] StoryGraph JSON is valid
- [ ] Vault notes are created/updated
- [ ] Tests pass (coverage >80%)
- [ ] CI pipeline is green

---

## Risks

| Risk | Mitigation |
|------|------------|
| Regex patterns too brittle | Test against public domain scripts, iterate |
| Too many false positives | Conservative thresholds, always queue on doubt |
| Queue grows too large | Batch processing, "accept all" for high confidence |
| Evidence links break on edit | Use stable block anchors, not line numbers |

---

## Next: Execute Plan 1

Ready to implement entity extraction engine?
