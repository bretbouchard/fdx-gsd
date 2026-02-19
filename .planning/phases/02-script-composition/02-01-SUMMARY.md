---
phase: 02-script-composition
plan: 01
subsystem: script-generation
tags: [screenplay, sluglines, beats, dialogue, storygraph, scriptgraph]

# Dependency graph
requires:
  - phase: 01-canon-extraction
    provides: StoryGraph with scene, character, location entities
provides:
  - ScriptBuilder class for StoryGraph to ScriptGraph transformation
  - SluglineGenerator for INT./EXT. LOCATION - TIME format
  - BeatExtractor for action beats and dialogue extraction
  - Valid ScriptGraph JSON output for FDX export
affects: [03-fdx-export, 05-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Builder pattern following CanonBuilder structure
    - Deterministic JSON output with sorted arrays
    - Evidence linking for traceability

key-files:
  created:
    - core/script/__init__.py
    - core/script/builder.py
    - core/script/beats.py
    - core/script/sluglines.py
    - tests/unit/test_script_builder.py
  modified: []

key-decisions:
  - "Follow CanonBuilder pattern for ScriptBuilder consistency"
  - "All paragraphs require evidence_ids for traceability"
  - "Uppercase output for sluglines (deterministic)"
  - "Scene order derived from line_number in StoryGraph"

patterns-established:
  - "Builder pattern: load input, transform, write output"
  - "Paragraph structure: type, text, evidence_ids, meta"
  - "Links structure: characters, locations, props, wardrobe, evidence_ids"

# Metrics
duration: 15min
completed: 2026-02-19
---

# Phase 2 Plan 1: ScriptBuilder Core Summary

**ScriptBuilder transforms StoryGraph entities into ScriptGraph screenplay structure with slugline generation, beat extraction, and dialogue detection**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-19T21:54:29Z
- **Completed:** 2026-02-19T22:05:00Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments
- Created SluglineGenerator with INT./EXT. LOCATION - TIME format
- Created BeatExtractor for action beats and dialogue extraction
- Created ScriptBuilder following CanonBuilder pattern
- All 26 unit tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create slugline generator module** - `b61b580` (feat)
2. **Task 2: Create beat extractor module** - `f44f9c7` (feat)
3. **Task 3: Create ScriptBuilder class** - `0e998a7` (feat)
4. **Task 4: Add unit tests** - `37a9b4b` (test)

## Files Created/Modified
- `core/script/sluglines.py` - SluglineGenerator class for screenplay sluglines
- `core/script/beats.py` - BeatExtractor for action/dialogue extraction
- `core/script/builder.py` - ScriptBuilder orchestrating transformation
- `core/script/__init__.py` - Module exports
- `tests/unit/test_script_builder.py` - 26 comprehensive tests

## Decisions Made
- Followed CanonBuilder pattern for consistency across builders
- All paragraphs include evidence_ids for full traceability
- Scene ordering derived from line_number field in StoryGraph entities
- Location resolution looks up canonical names from StoryGraph entities

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Two test issues fixed:
1. Test used "SUNSET" which is not a valid time_of_day in schema - changed to "DUSK"
2. Deterministic output test compared timestamps - updated to compare content excluding generated_at

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- ScriptBuilder produces valid ScriptGraph JSON
- Ready for FDX export integration (Phase 3)
- Ready for CLI integration (Phase 5)

---
*Phase: 02-script-composition*
*Completed: 2026-02-19*
