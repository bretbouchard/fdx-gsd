# Phase 4, Plan 03: PropsValidator - COMPLETE

## Summary

Created PropsValidator implementing PROP-01/02/03 continuity rules:

1. **PropsValidator Class** (`core/validation/props_validator.py`)
   - Extends BaseValidator
   - PROP_PATTERNS: Action-based patterns for holding, taking, giving, damaging, repairing
   - INTRODUCTION_ACTIONS: holding, taking, giving
   - TRANSFER_ACTIONS: giving, taking

2. **Validation Rules**:
   - **PROP-01**: Props appearing without introduction (WARNING)
     - First appearance should have introduction action
   - **PROP-02**: Ownership transfers not shown (ERROR)
     - Detects holder changes without transfer action
   - **PROP-03**: Damage not persisting (WARNING)
     - Tracks damage state and repair events

3. **Implementation Details**:
   - `_build_prop_timeline()`: prop_name -> [{scene, action, holder}]
   - `_extract_prop_mentions()`: Finds prop references with action context
   - `_normalize_prop_name()`: Standardizes prop names
   - `_has_transfer_action()`: Checks for explicit transfers between scenes

## Files Created

- `core/validation/props_validator.py` (~350 lines)

## Verification

```bash
python -c "from core.validation import PropsValidator, IssueCategory; print('OK')"
```
