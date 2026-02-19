# ADR-0004: Confidence Thresholds - Configurable Per Project

## Status

Accepted

## Context

The system needs to decide when to auto-link entities vs. queue for disambiguation. Different projects may want different levels of automation.

## Decision

**Make thresholds configurable per project in gsd.yaml.**

### Default Configuration

```yaml
# gsd.yaml
disambiguation:
  # Confidence thresholds (0.0 - 1.0)
  auto_accept: 0.95      # Auto-link if confidence >= this
  auto_reject: 0.30      # Assume new entity if confidence < this
  queue_range: [0.30, 0.95]  # Queue for review in this range

  # Behavior
  always_ask_new: true   # Always ask before creating new entity
  batch_size: 10         # How many items to show in resolve UI
  learn_aliases: true    # Remember confirmed aliases
```

### Per-Project Override

```yaml
# For a project with consistent naming (high confidence)
disambiguation:
  auto_accept: 0.85
  auto_reject: 0.40

# For a project with messy notes (conservative)
disambiguation:
  auto_accept: 0.98
  auto_reject: 0.50
  always_ask_new: true
```

### Threshold Behavior

| Confidence | Default Behavior | Configurable |
|------------|-----------------|--------------|
| ≥ auto_accept | Auto-link to existing | Yes |
| In queue_range | Queue for review | Yes |
| < auto_reject | Assume new entity | Yes |

## Consequences

### Positive
- Flexibility for different project types
- User controls automation level
- Can start conservative, relax later

### Negative
- More configuration surface
- Need good defaults

## Related

- ADR-0002: NER Approach
- REQ-CAN-04: Alias Resolution
- REQ-CAN-05: Disambiguation Queue
