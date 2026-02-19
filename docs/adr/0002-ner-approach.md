# ADR-0002: NER Approach - Interactive Disambiguation

## Status

Accepted

## Context

We need to extract entities (characters, locations, props) from raw story text. Traditional NER approaches either:
- Auto-merge aggressively (false positives)
- Require training data (expensive)
- Miss story-specific patterns

## Decision

**Lightweight extraction + Always ask on ambiguity.**

### Extraction Rules (Minimal)

```
Characters:
- Proper nouns (Fox, Sarah, THE WAITER)
- Capitalized references in dialogue/action
- Role references (the bartender, A MAN)

Locations:
- INT./EXT. patterns
- "the [place]" references
- Named locations (Joe's Diner)

Props:
- "a/the [object]" with focus
- Named objects (the folder, his jacket)
```

### Disambiguation Behavior

When entity reference is ambiguous:

1. **Exact match** → Auto-link to existing entity
2. **Known alias** → Auto-link (Rich → Richard if previously confirmed)
3. **Fuzzy match** → ASK: "Is 'Ricky' the same as 'Richard'?"
4. **New entity** → ASK: "Is 'the waiter' a new character or an extra?"

### Canonical ID Linking

All confirmed aliases link to ONE canonical UUID:

```json
{
  "id": "CHAR_Richard_38348348",
  "name": "Richard",
  "aliases": ["Rich", "Ricky", "Dick", "R."],
  "references": [
    {"text": "Rich", "source": "inbox/001.md#^ev_a1"},
    {"text": "Ricky", "source": "inbox/002.md#^ev_b2"},
    {"text": "Dick", "source": "inbox/003.md#^ev_c3"}
  ]
}
```

### Confidence Model

| Confidence | Action |
|------------|--------|
| 100% (exact match) | Auto-link |
| 90%+ (known alias) | Auto-link, log for review |
| 50-90% (fuzzy) | Queue for disambiguation |
| <50% (new entity) | Ask: "New entity or existing?" |

## Consequences

### Positive
- Zero false positive merges
- User maintains control over canon
- System learns user's naming conventions
- Evidence always linked

### Negative
- More user interaction upfront
- Disambiguation queue can grow
- Requires good UX for queue management

### Mitigation
- Batch disambiguation (process 10 at a time)
- "Accept all" for high-confidence suggestions
- Learn from confirmed aliases

## Implementation Notes

1. Start with regex-based extraction (no ML dependency)
2. Add spaCy later for better sentence boundary detection
3. Fuzzy matching with rapidfuzz for alias suggestions
4. Disambiguation queue as first-class UI

## Related

- REQ-CAN-04: Alias Resolution
- REQ-CAN-05: Disambiguation Queue
- fdx_gsd-6, fdx_gsd-7 (Beads)
