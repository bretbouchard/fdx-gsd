# Phase 4, Plan 04: TimelineValidator - COMPLETE

## Summary

Created TimelineValidator implementing TIME-01/02/04 continuity rules:

1. **TimelineValidator Class** (`core/validation/timeline_validator.py`)
   - Extends BaseValidator
   - TIME_SKIP_MARKERS: "LATER", "THE NEXT DAY", "HOURS LATER", etc.
   - CONTINUOUS_MARKERS: "CONTINUOUS", "MOMENTS LATER", "SAME TIME", "MEANWHILE"
   - RELATIVE_TIME_PHRASES: Patterns like "later that day", "the following morning"

2. **Validation Rules**:
   - **TIME-01**: Impossible travel (ERROR)
     - Detects character location changes without travel time
     - Uses configurable location_distances for travel time estimates
   - **TIME-02**: Unresolved time phrases (WARNING)
     - Flags relative time references without clear anchors
   - **TIME-04**: Character location conflicts (ERROR)
     - Catches characters in different locations during simultaneous scenes

3. **Implementation Details**:
   - `_build_scene_timeline()`: Ordered scenes with location/time metadata
   - `_build_character_timeline()`: Character -> [{scene, location, time_marker}]
   - `_get_travel_time()`: Estimates or looks up travel times
   - `_find_simultaneous_scenes()`: Groups CONTINUOUS/SAME_TIME scenes

## Files Created

- `core/validation/timeline_validator.py` (~380 lines)

## Verification

```bash
python -c "from core.validation import TimelineValidator, IssueCategory; print('OK')"
```
