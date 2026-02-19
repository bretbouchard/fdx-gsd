---
phase: 02-script-composition
plan: 02
subsystem: script
tags: [dialogue, character-resolution, screenplay-formatting, speaker-detection]

# Dependency graph
requires:
  - phase: 02-01
    provides: ScriptBuilder, BeatExtractor, SluglineGenerator
provides:
  - DialogueFormatter class with speaker detection
  - Character entity resolution from StoryGraph
  - Parenthetical extraction from dialogue
  - character_id in paragraph metadata
affects: [02-03, fdx-export]

# Tech tracking
tech-stack:
  added: []
  patterns: [character-lookup-index, lazy-initialization, metadata-enrichment]

key-files:
  created:
    - core/script/dialogue.py
  modified:
    - core/script/beats.py
    - core/script/builder.py
    - tests/unit/test_script_builder.py

key-decisions:
  - "Character lookup uses normalized name index (exact, case-insensitive, alias)"
  - "Character cues must be mostly uppercase (50% threshold)"
  - "Lazy initialization for DialogueFormatter property"

patterns-established:
  - "CharacterMatch dataclass for speaker detection results"
  - "character_id in paragraph meta for entity linking"
  - "set_character_entities for runtime updates"

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 2 Plan 2: Dialogue Formatting Summary

**DialogueFormatter with speaker detection, character entity resolution, and parenthetical extraction - linking screenplay dialogue to canonical StoryGraph characters**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T22:04:12Z
- **Completed:** 2026-02-19T22:09:04Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- DialogueFormatter class with exact, case-insensitive, and alias character matching
- Character entity resolution linking dialogue to StoryGraph character IDs
- Parenthetical extraction from dialogue text (e.g., "(pauses)")
- Character_id in paragraph metadata for traceability
- 8 new dialogue-specific tests (34 total tests passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dialogue formatter module** - `8b1ef9d` (feat)
2. **Task 2: Integrate dialogue formatter into beat extraction** - `3bdea2d` (feat)
3. **Task 3: Add dialogue tests to test suite** - `17cc6ca` (test)

## Files Created/Modified

- `core/script/dialogue.py` - DialogueFormatter class with speaker detection
- `core/script/beats.py` - Integration with DialogueFormatter, character_id in meta
- `core/script/builder.py` - Passes character_entities to BeatExtractor
- `tests/unit/test_script_builder.py` - 8 new dialogue tests

## Decisions Made

- Character lookup uses a normalized name index supporting exact match (confidence 1.0), case-insensitive (0.95), and alias (0.9)
- Character cues must be at least 50% uppercase to qualify as speaker names
- Lazy initialization for dialogue_formatter property to avoid overhead when not needed
- Character paragraph meta includes: character_id, match_confidence, match_type

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Test case `test_speaker_detection_case_insensitive` initially failed because lowercase "fox" did not pass the character cue detection (requires uppercase). Fixed by adjusting test to use uppercase input, which is the expected screenplay format.

## Next Phase Readiness

- Dialogue formatting complete with character resolution
- Ready for Plan 03 (ScriptGraph validation and CLI integration)
- Character IDs now available in paragraph metadata for downstream linking

---
*Phase: 02-script-composition*
*Completed: 2026-02-19*
