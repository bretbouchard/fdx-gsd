---
phase: 03-round-trip-editing
plan: 03
subsystem: sync
tags: [vault, reingestion, sync, pipeline, provenance, conflict-resolution, yaml]

# Dependency graph
requires:
  - phase: 01-canon-extraction
    provides: Entity extraction, vault note templates
  - phase: 03-01
    provides: ChangeDetector, protected blocks, ProvenanceTracker
  - phase: 03-02
    provides: ConflictResolver, three-tier classification (SAFE/AMBIGUOUS/CRITICAL)
provides:
  - VaultReingester class for vault-to-StoryGraph sync
  - ReingestResult dataclass with comprehensive statistics
  - ParsedNote dataclass for vault note parsing
  - reingest_vault() convenience function
  - Full reingestion pipeline with conflict detection
affects: [CLI sync commands, future round-trip workflows]

# Tech tracking
tech-stack:
  added: [pyyaml for frontmatter parsing]
  patterns:
    - Pipeline pattern: detect -> parse -> merge -> flag -> save
    - Three-tier conflict integration (reuses ConflictResolver)
    - Provenance tracking for audit trail
    - Entity index for O(1) lookups

key-files:
  created:
    - core/sync/reingest.py
  modified:
    - core/sync/__init__.py

key-decisions:
  - "Reuse ChangeDetector, ConflictResolver, ProvenanceTracker from 03-01 and 03-02"
  - "Parse YAML frontmatter using PyYAML safe_load"
  - "Extract evidence IDs from wikilinks using regex pattern"
  - "Support both frontmatter and protected-block aliases"
  - "Auto-merge SAFE tier conflicts, flag AMBIGUOUS, block CRITICAL"

patterns-established:
  - "Pattern: VaultReingester coordinates full pipeline with dependency injection"
  - "Pattern: ReingestResult captures comprehensive statistics for reporting"
  - "Pattern: ParsedNote separates frontmatter from body for processing"
  - "Pattern: Entity index provides O(1) lookups during merge operations"

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 3 Plan 3: Reingestion Pipeline Summary

**Vault-to-StoryGraph sync with conflict detection, provenance tracking, and three-tier conflict classification**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T23:13:30Z
- **Completed:** 2026-02-19T23:17:51Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Implemented VaultReingester class for complete vault-to-StoryGraph synchronization
- Created ReingestResult dataclass with comprehensive statistics (files processed, entities updated, conflicts by tier)
- Built ParsedNote dataclass for vault note parsing (frontmatter + body + protected content + manual notes)
- Integrated three-tier conflict classification from 03-02 (SAFE auto-merge, AMBIGUOUS flag, CRITICAL block)
- Added provenance tracking for all changes with SourceType.SYNC
- Created helper functions for frontmatter parsing, entity type detection, and manual notes extraction
- Exported all new classes and functions in sync module __init__.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement reingestion pipeline** - `058edab` (feat)

**Plan metadata:** (pending)

## Files Created/Modified

- `core/sync/reingest.py` - Complete reingestion pipeline (VaultReingester, ReingestResult, ParsedNote, EntityUpdate)
- `core/sync/__init__.py` - Updated exports for all new classes and functions

## Decisions Made

1. **Reuse existing components** - VaultReingester uses ChangeDetector, ConflictResolver, and ProvenanceTracker rather than reimplementing
2. **YAML frontmatter parsing** - Use PyYAML safe_load for security and compatibility
3. **Evidence ID extraction** - Parse wikilinks with regex pattern `\[\[[^\]]*#\^(ev_[a-z0-9]+)\]\]`
4. **Dual alias sources** - Merge aliases from both frontmatter and protected block content
5. **Pipeline architecture** - Single VaultReingester class coordinates all stages with clear separation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all imports verified successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Sync module complete with full round-trip editing support
- Ready for CLI integration to expose sync commands
- ChangeDetector + ConflictResolver + ProvenanceTracker + VaultReingester provide complete pipeline

---
*Phase: 03-round-trip-editing*
*Completed: 2026-02-19*
