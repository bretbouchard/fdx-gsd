# Phase 4, Plan 02: WardrobeValidator - COMPLETE

## Summary

Created WardrobeValidator implementing WARD-01/02/03 continuity rules:

1. **WardrobeValidator Class** (`core/validation/wardrobe_validator.py`)
   - Extends BaseValidator
   - WARDROBE_PATTERNS: Regex patterns for costume mentions
   - TIME_SKIP_MARKERS: "LATER", "THE NEXT DAY", etc.
   - CONTINUOUS_MARKERS: "CONTINUOUS", "MOMENTS LATER", etc.

2. **Validation Rules**:
   - **WARD-01**: Unexplained wardrobe changes (WARNING)
     - Detects costume changes between consecutive scenes
     - Checks for time skip markers or costume change mentions
   - **WARD-02**: Wardrobe conflict in continuous timeline (ERROR)
     - Catches different costumes in CONTINUOUS scenes
   - **WARD-03**: Missing signature items (INFO)
     - Checks for configured signature items per character

3. **Implementation Details**:
   - `_build_wardrobe_timeline()`: Character -> [{scene, wardrobe, time_marker}]
   - `_extract_wardrobe_state()`: Extracts costume info near character name
   - `_has_costume_change_cause()`: Checks for time skips
   - `_are_adjacent_timeline()`: Detects continuous scenes

## Files Created

- `core/validation/wardrobe_validator.py` (~320 lines)

## Verification

```bash
python -c "from core.validation import WardrobeValidator, IssueCategory; print('OK')"
```
