# ADR-0003: Fuzzy Matching Library

## Status

Accepted

## Context

We need fuzzy string matching for alias resolution (Rich/Ricky/Dick → same person).

Options considered:
- rapidfuzz (fast, comprehensive)
- thefuzz (simple, slower)
- custom Levenshtein (minimal dependency)

## Decision

**Use rapidfuzz** for fuzzy matching.

### Rationale

1. **Speed** - Written in C++, significantly faster than pure Python
2. **Features** - Multiple algorithms (Levenshtein, Jaro-Winkler, etc.)
3. **Active maintenance** - Well-maintained, Python 3.10+ support
4. **No ML dependency** - Pure string matching, no model downloads

### Usage Pattern

```python
from rapidfuzz import fuzz, process

# Check if "Ricky" matches "Richard"
score = fuzz.ratio("Ricky", "Richard")  # Returns 0-100

# Find best match in candidates
candidates = ["Richard", "Sarah", "Fox"]
result = process.extractOne("Ricky", candidates, scorer=fuzz.ratio)
# Returns ("Richard", 71.0, 0)
```

## Consequences

### Positive
- Fast enough for interactive use
- No external API calls
- Deterministic results

### Negative
- Additional dependency
- May need tuning for story-specific patterns

## Related

- ADR-0002: NER Approach
- REQ-CAN-04: Alias Resolution
