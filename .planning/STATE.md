# STATE: FDX GSD

**Last Updated:** 2026-02-19
**Session:** Phase 3 in Progress

---

## Current Position

**Phase:** 3 of 8 (round-trip-editing)
**Plan:** 1 of 3 (03-01 complete)
**Status:** In progress
**Mood:** 🟢 Executing Phase 3

**Progress:** ██████░░░░ 56% (Phase 0, 1, 2, 7 complete; Phase 3 started)

---

## Recent Activity

| When | What |
|------|------|
| 2026-02-19 | **Phase 3 Plan 01** - Sync foundation module (change detection, protected blocks, provenance) |
| 2026-02-19 | **Phase 2 COMPLETE** - All 3 plans executed |
| 2026-02-19 | **Phase 2 Plan 03** - CLI integration + 17 integration tests for full pipeline |
| 2026-02-19 | **Phase 2 Plan 02** - Dialogue formatter integration |
| 2026-02-19 | **Phase 2 Plan 01** - ScriptBuilder core with sluglines, beats, dialogue extraction |
| 2026-02-19 | **Phase 1 COMPLETE** - All 4 plans executed across 3 waves |
| 2026-02-19 | **Phase 7 COMPLETE** - Media Asset Archive System |
| 2026-02-19 | Test framework: 137 tests passing |

---

## Active Work

### Current Task
Phase 3 Plan 1 complete. Ready for Plan 2.

### Completed Phases
- ✅ Phase 0: Foundation
- ✅ Phase 1: Canon Extraction
- ✅ Phase 2: Script Composition
- ✅ Phase 7: Media Asset Archive (parallel track)

### Phase 3 Progress
- ✅ Plan 01: Sync foundation module (ChangeDetector, protected blocks, ProvenanceTracker)
- ⬜ Plan 02: Bidirectional sync implementation
- ⬜ Plan 03: CLI integration for sync

---

## Memory

### Key Decisions Made (Architecture)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-0002 | Interactive disambiguation, no ML | Zero false positives, user control |
| ADR-0003 | rapidfuzz for fuzzy matching | Fast, no ML dependency |
| ADR-0004 | Configurable thresholds per project | Flexibility for different projects |
| ADR-0005 | Confucius MCP = memory, separate orchestration | Clear separation of concerns |

### Key Decisions Made (Infrastructure)
1. Obsidian-first architecture (vault is source of truth)
2. Append-only mutation (protected blocks)
3. Evidence traceability mandatory
4. SQLite for local storage (upgradable later)
5. FDX as primary export format
6. GSD + Beads for tracking (no untracked work)
7. Pre-commit hooks enforce REQ-ID in commits
8. CI validates tests, schemas, builds
9. Deterministic builds (sorted JSON output)

### Key Decisions Made (Phase 2 - Script Composition)
1. ScriptBuilder follows CanonBuilder pattern for consistency
2. All paragraphs require evidence_ids for traceability
3. Slugline format: `{INT_EXT}. {LOCATION} - {TIME}` (uppercase)
4. Scene ordering from line_number in StoryGraph entities
5. CLI checks for storygraph.json before building
6. XML declaration quote style is flexible (ElementTree uses single quotes)
7. Character lookup uses normalized name index (exact, case-insensitive, alias matching)
8. Character paragraph meta includes: character_id, match_confidence, match_type

### Key Decisions Made (Phase 3 - Round-Trip Editing)
1. SHA-256 hashing for file content detection
2. Protected blocks use CONFUCIUS markers matching existing vault templates
3. Provenance uses append-only log pattern for audit trail integrity
4. SourceType enum for categorizing change sources (canon_build, script_build, manual_edit, etc.)

### Patterns to Remember
- Every derived fact needs evidence link
- Disambiguation queue prevents wrong merges
- Deterministic builds enable diffing
- Protected blocks preserve manual edits
- Every code change references REQ-ID
- Every session ends with bead update
- **Always ask on ambiguity - never guess silently**
- **All aliases link to ONE canonical UUID**
- **Vault notes are written during canon build with evidence links**
- **Evidence links resolve to full Obsidian wikilinks via evidence_index.json**
- **Sort JSON output (entities by type/id, queue items by id, evidence_ids) for deterministic builds**
- **ScriptBuilder pattern: load StoryGraph -> build scenes -> write ScriptGraph**
- **CLI command pattern: import builder -> check prerequisites -> run -> report results**
- **Sync pattern: ChangeDetector baseline -> detect changes -> track in ProvenanceTracker**

### Things to Avoid
- Don't use bare names when canonical entities exist
- Don't write outside managed blocks
- Don't skip evidence registration
- Don't auto-merge below confidence threshold
- Don't commit without REQ-ID
- Don't close beads without STATE.md update
- **Don't use ML/NER library - lightweight extraction only**

---

## Beads Status

| Bead ID | Title | Status |
|---------|-------|--------|
| fdx_gsd-1 | PHASE-0: Foundation Complete | ✅ Closed |
| fdx_gsd-2 | PHASE-1: Canon Extraction | ✅ Closed |
| fdx_gsd-3 | REQ-CAN-01: Character Extraction | ✅ Closed |
| fdx_gsd-4 | REQ-CAN-02: Location Extraction | ✅ Closed |
| fdx_gsd-5 | REQ-CAN-03: Scene Detection | ✅ Closed |
| fdx_gsd-6 | REQ-CAN-04: Alias Resolution | ✅ Closed |
| fdx_gsd-7 | REQ-CAN-05: Disambiguation Queue | ✅ Closed |
| fdx_gsd-8 | REQ-CAN-06: Evidence Linking | ✅ Closed |
| fdx_gsd-9 | INFRA: Test Framework Setup | ✅ Closed |
| fdx_gsd-10 | INFRA: CI Pipeline Setup | ✅ Closed |
| fdx_gsd-11 | INFRA: Pre-commit Hooks | ✅ Closed |
| fdx_gsd-12 | INFRA: Confucius MCP Integration | ✅ Closed |

---

## Next Actions

1. **Phase 3 Plan 1 COMPLETE** - Sync foundation module
2. **Next:** Phase 3 Plan 2 - Bidirectional sync implementation

---

## File Structure

```
fdx_gsd/
├── .planning/
│   ├── PROJECT.md              ✅
│   ├── REQUIREMENTS.md         ✅
│   ├── ROADMAP.md              ✅
│   ├── STATE.md                ✅ (this file)
│   └── phases/
│       ├── 01-canon-extraction/ ✅ (4 plans complete)
│       ├── 02-script-composition/ ✅ (3 plans complete)
│       ├── 03-round-trip-editing/ 🔄 (1 plan complete)
│       └── 07-media-archive/    ✅ (7 plans complete)
├── .beads/                      ✅
├── .github/workflows/ci.yml     ✅
├── apps/cli/                    ✅ (build script + export fdx commands)
├── core/
│   ├── exporters/               ✅ (FDX writer)
│   ├── extraction/              ✅ (character, location, scene)
│   ├── resolution/              ✅ (fuzzy matching)
│   ├── canon/                   ✅ (CanonBuilder, vault integration)
│   ├── vault/                   ✅ (VaultNoteWriter, templates)
│   ├── archive/                 ✅ (media asset tracking)
│   ├── storygraph/              ✅ (schema)
│   ├── scriptgraph/             ✅ (schema + validation utils)
│   ├── script/                  ✅ (ScriptBuilder, SluglineGenerator, BeatExtractor, DialogueFormatter)
│   └── sync/                    ✅ (ChangeDetector, protected_blocks, ProvenanceTracker)
├── templates/project_template/  ✅
├── tests/
│   ├── unit/                    ✅ (120 tests)
│   ├── integration/             ✅ (17 new tests for script pipeline)
│   └── fixtures/                ✅
├── docs/adr/                    ✅
├── scripts/                     ✅
├── .pre-commit-config.yaml      ✅
├── .gitignore                   ✅
├── pyproject.toml               ✅
└── README.md                    ✅
```
