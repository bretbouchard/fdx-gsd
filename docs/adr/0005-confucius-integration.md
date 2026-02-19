# ADR-0005: Confucius Integration Architecture

## Status

Accepted

## Context

The spec refers to a "Confucius" orchestration agent that runs the pipeline. We also have Confucius MCP available for hierarchical memory.

Question: Are these the same thing, separate, or related?

## Decision

**Confucius MCP IS the memory system. The orchestration agent is separate but uses Confucius MCP for memory.**

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Orchestration Agent                    │
│         (pipeline runner, no special name)          │
│                                                     │
│  Detects changes → Runs pipeline phases → Exports  │
└──────────────────────┬──────────────────────────────┘
                       │
                       │ stores patterns, decisions, errors
                       ▼
┌─────────────────────────────────────────────────────┐
│              Confucius MCP                          │
│         (hierarchical memory storage)               │
│                                                     │
│  - Pattern storage (what worked)                   │
│  - Error/solution pairs                            │
│  - Project context                                 │
│  - Session memory                                  │
└─────────────────────────────────────────────────────┘
```

### What Confucius MCP Stores

| Scope | Content |
|-------|---------|
| Repository | Project patterns, naming conventions, architecture decisions |
| Session | Current work context, open questions |
| Task | Specific extraction patterns, alias resolutions |

### How Pipeline Uses Confucius MCP

```python
# Before extraction - retrieve patterns
patterns = confucius.retrieve("character extraction patterns")

# After successful extraction - store pattern
confucius.store({
    "type": "pattern",
    "content": "Character names often appear in ALL CAPS in dialogue",
    "scope": "repository",
    "tags": ["extraction", "character", "dialogue"]
})

# On error - store for future reference
confucius.store({
    "type": "error_solution",
    "error": "Ambiguous reference 'the boss'",
    "solution": "Asked user, linked to CHAR_MobBoss",
    "confidence": 1.0
})
```

## Consequences

### Positive
- Clear separation of concerns
- Confucius MCP is just storage, not orchestration
- Orchestration logic stays simple
- Memory persists across sessions

### Negative
- Two systems to understand
- Need to ensure Confucius MCP is called at right points

## Related

- ADR-0002: NER Approach (uses Confucius for patterns)
- REQ-CAN-04: Alias Resolution (stores confirmed aliases)
