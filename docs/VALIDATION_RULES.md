# Validation Rules

## Overview

FDX GSD validates story continuity across four domains: wardrobe, props, timeline, and knowledge. Each validator implements rules that detect inconsistencies and generate issues.

## Issue Severity

| Level | Description |
|-------|-------------|
| `error` | Must fix - breaks story logic |
| `warning` | Should fix - may confuse readers |
| `info` | FYI - worth noting |

## Wardrobe Validation

### WARD-01: State Change Without Cause

**Rule:** Wardrobe state changes require a narrative cause.

**Detection:**
- Character's wardrobe changes between scenes
- No mention of change in action/description

**Example Issue:**
```
Scene 5: Fox wears leather jacket
Scene 8: Fox wears tuxedo (no transition scene)
```

**Severity:** `warning`

### WARD-02: Signature Item Disappearance

**Rule:** Signature items (wedding ring, lucky charm) should persist unless explicitly removed.

**Detection:**
- Item introduced as signature
- Item not mentioned in later scenes
- No removal action

**Example Issue:**
```
Scene 1: Sarah's wedding ring is introduced as "never takes it off"
Scene 10: Sarah's hands described with no ring
```

**Severity:** `warning`

### WARD-03: Implied Wardrobe Inconsistency

**Rule:** Actions should be possible with described wardrobe.

**Detection:**
- Character performs action requiring specific clothing
- No prior mention of that clothing

**Example Issue:**
```
Scene 3: Sarah is described in a "sundress"
Scene 4: Sarah "reaches into her pants pocket"
```

**Severity:** `info`

---

## Props Validation

### PROP-01: Phantom Prop

**Rule:** Props cannot appear without introduction.

**Detection:**
- Prop used in action
- No prior introduction in any scene

**Example Issue:**
```
Scene 7: "Fox pulls a gun"
(No prior scene mentions Fox having a gun)
```

**Severity:** `error`

### PROP-02: Prop State Persistence

**Rule:** Damage and state changes persist.

**Detection:**
- Prop damaged in scene
- Later scene shows prop undamaged
- No repair mentioned

**Example Issue:**
```
Scene 3: "The vase shatters"
Scene 12: "She picks up the vase"
```

**Severity:** `warning`

### PROP-03: Location Continuity

**Rule:** Props stay where placed unless moved.

**Detection:**
- Prop placed at location
- Later scene at same location without prop
- No removal mentioned

**Example Issue:**
```
Scene 2: "Fox leaves the letter on the desk"
Scene 5 (same location): Desk described with no letter
```

**Severity:** `info`

---

## Timeline Validation

### TIME-01: Impossible Travel

**Rule:** Characters cannot travel faster than realistic.

**Detection:**
- Character at location A in scene N
- Character at location B in scene N+1
- Travel time < realistic minimum

**Example Issue:**
```
Scene 5 (10:00 AM): Fox in New York
Scene 6 (10:30 AM): Fox in Los Angeles
(Travel time ~5 hours by plane)
```

**Severity:** `error`

### TIME-02: Simultaneous Presence

**Rule:** Character cannot be in two places at once.

**Detection:**
- Same character mentioned at different locations
- Scenes occur at same time

**Example Issue:**
```
Scene 8 (2:00 PM): Fox at the diner
Scene 9 (2:00 PM): Fox at the office
```

**Severity:** `error`

### TIME-04: Timeline Gaps

**Rule:** Significant time gaps should be acknowledged.

**Detection:**
- Large time jump between scenes
- No acknowledgment (fade, title card, etc.)

**Example Issue:**
```
Scene 10: Monday morning
Scene 11: Friday evening (no transition)
```

**Severity:** `info`

---

## Knowledge Validation

### KNOW-01: Information Leak

**Rule:** Characters cannot reference information they haven't learned.

**Detection:**
- Character references fact/dialogue
- Character wasn't present when information was revealed

**Example Issue:**
```
Scene 3: Sarah tells Fox a secret (in private)
Scene 7: Mike references Sarah's secret (wasn't in Scene 3)
```

**Severity:** `error`

### KNOW-02: Premature Knowledge

**Rule:** Characters cannot act on future information.

**Detection:**
- Character takes action based on event
- Event hasn't happened yet in timeline

**Example Issue:**
```
Scene 5 (Monday): Fox says "The meeting tomorrow was cancelled"
Scene 7 (Tuesday): Meeting is cancelled
(Fox knew about cancellation before it happened)
```

**Severity:** `warning`

### KNOW-03: Forgotten Knowledge

**Rule:** Characters should remember what they've learned.

**Detection:**
- Character learns important information
- Later acts as if unaware

**Example Issue:**
```
Scene 2: Sarah tells Fox her real name
Scene 10: Fox asks Sarah "What's your real name?"
```

**Severity:** `warning`

### KNOW-04: Secret Consistency

**Rule:** Secrets shared with specific characters stay with them.

**Detection:**
- Secret shared with character A
- Character B (not present) later knows secret
- No explanation of how B learned it

**Example Issue:**
```
Scene 4: Fox shares secret with Sarah only
Scene 9: Mike references Fox's secret
(No explanation of how Mike learned it)
```

**Severity:** `error`

---

## Configuration

Validation behavior can be configured in `gsd.yaml`:

```yaml
validation:
  wardrobe:
    enabled: true
    strict: false  # If true, all rules are errors
  props:
    enabled: true
  timeline:
    enabled: true
    travel_speed_kmh: 100  # Max travel speed for TIME-01
  knowledge:
    enabled: true
    track_secrets: true
```

## Reports

Validation results are written to:

- `build/issues.json` - Machine-readable issues
- `vault/80_Reports/Validation_YYYY-MM-DD.md` - Human-readable report

### Report Format

```markdown
# Validation Report - 2026-02-19

## Summary
- Errors: 2
- Warnings: 5
- Info: 3

## Errors

### KNOW-01: Information Leak
**Scene 7** - Mike references Sarah's secret

> Mike: "I know what you told Fox about your past."

Issue: Mike wasn't present when Sarah shared this with Fox in Scene 3.

**Evidence:** [[SCN_003]], [[SCN_007]]

## Warnings
...

## Info
...
```

## CLI Usage

```bash
# Run all validators
gsd validate

# Only show errors
gsd validate --severity error

# Show warnings and above
gsd validate --severity warning

# Attempt automatic fixes (where possible)
gsd validate --fix
```

## Extending Validators

To add a custom validator:

1. Create `core/validation/xxx_validator.py`
2. Extend `BaseValidator`
3. Implement `validate(storygraph: dict) -> List[Issue]`
4. Register in `ValidationOrchestrator`

```python
from core.validation.base import BaseValidator, Issue, IssueSeverity

class CustomValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "custom"

    def validate(self, storygraph: dict) -> list[Issue]:
        issues = []

        # Check something
        if problem_found:
            issues.append(Issue(
                rule_id="CUST-01",
                severity=IssueSeverity.WARNING,
                message="Custom issue found",
                scene_id="SCN_001",
                evidence_ids=["EV_001"]
            ))

        return issues
```
