---
phase: 01-canon-extraction
plan: 03
subsystem: cli
tags: [cli, determinism, testing, integration, vault]

# Dependency graph
requires:
  - phase: 01-01
    provides: Note templates (VaultNoteWriter)
  - phase: 01-02
    provides: CanonBuilder with vault writing integration
provides:
  - CLI reports vault_notes_written in build output
  - Deterministic canon builds with sorted output
  - End-to-end integration tests for full pipeline validation
affects: [02-script-composition, cli-users]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Deterministic JSON output via sorting (entities by type/id, queue items by id, evidence_ids sorted)
    - CLI output includes vault statistics

key-files:
  created: []
  modified:
    - apps/cli/cli.py
    - core/canon/__init__.py
    - tests/integration/test_canon_pipeline.py

key-decisions:
  - "Sort entities by (type, id) for deterministic storygraph.json output"
  - "Sort queue items by id for deterministic disambiguation_queue.json output"
  - "Sort evidence_ids in each entity for consistency"

patterns-established:
  - "Pattern: Deterministic builds - all JSON output must be sorted for diff-based change detection"

# Metrics
duration: 10min
completed: 2026-02-19
---

# Phase 1 Plan 3: CLI Polish + Deterministic Builds Summary

**CLI reports vault notes count and builds produce sorted, deterministic JSON output for diff-based change detection**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-19T21:07:31Z
- **Completed:** 2026-02-19T21:17:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- CLI `gsd build canon` now shows vault_notes_written count
- Deterministic build output enables diff-based change detection
- Comprehensive e2e tests validate full pipeline with vault output

## Task Commits

Each task was committed atomically:

1. **Task 1: Update cmd_build to show vault output** - `98f16c3` (feat)
2. **Task 2: Ensure deterministic build output** - `ed16fe3` (feat)
3. **Task 3: Add end-to-end integration tests** - `4110c7b` (test)

**Plan metadata:** (pending)

## Files Created/Modified
- `apps/cli/cli.py` - Added vault_notes_written to build output, shows vault directory locations
- `core/canon/__init__.py` - Added sorting for entities, queue items, and evidence_ids
- `tests/integration/test_canon_pipeline.py` - Added test_full_e2e_canon_build and test_deterministic_build_output

## Decisions Made
- Sort entities by (type, id) tuple for consistent ordering - characters first, then locations, then scenes
- Sort evidence_ids to ensure identical entities produce identical JSON

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI integration complete with vault output reporting
- Deterministic builds enable reliable diff-based change tracking
- All 94 tests pass including new e2e tests
- Ready for Phase 2 script composition or additional canon extraction features

---
*Phase: 01-canon-extraction*
*Plan: 03*
*Completed: 2026-02-19*
