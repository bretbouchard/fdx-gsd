# STATE: FDX GSD

**Last Updated:** 2026-02-19
**Session:** Initial Setup + Infrastructure + Decisions

---

## Current Position

**Phase:** 1 of 10 (canon-extraction)
**Plan:** 02 of 4 complete
**Status:** In progress - vault integration complete
**Mood:** 🟢 Ready to continue

**Progress:** ██░░░░░░░░ 20%

---

## Recent Activity

| When | What |
|------|------|
| 2026-02-19 | **Phase 1 Plan 02: Vault Integration** - CanonBuilder with vault writing |
| 2026-02-19 | **Phase 1 Plan 01: Note Templates** - VaultNoteWriter created |
| 2026-02-19 | Project structure created |
| 2026-02-19 | Phase 0 CLI implemented (new-project, ingest, status) |
| 2026-02-19 | FDX writer implemented |
| 2026-02-19 | JSON schemas defined |
| 2026-02-19 | GSD planning docs created (PROJECT, REQUIREMENTS, ROADMAP) |
| 2026-02-19 | Beads tracking initialized and synced |
| 2026-02-19 | Test framework set up (pytest, fixtures) |
| 2026-02-19 | CI pipeline created (GitHub Actions) |
| 2026-02-19 | Pre-commit hooks configured |
| 2026-02-19 | **ADR-0002: NER Approach - Interactive Disambiguation** |
| 2026-02-19 | **ADR-0003: Fuzzy Matching - rapidfuzz** |
| 2026-02-19 | **ADR-0004: Confidence Thresholds - Configurable** |
| 2026-02-19 | **ADR-0005: Confucius Integration Architecture** |
| 2026-02-19 | Updated gsd.yaml with disambiguation settings |
| 2026-02-19 | Added rapidfuzz to dependencies |

---

## Active Work

### Current Task
Phase 1 Plan 02 complete - vault integration finished.

### Ready Work (from Beads)
1. `fdx_gsd-2`: PHASE-1: Canon Extraction (in progress)
2. Continue with Plan 03 or next phase

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
| fdx_gsd-2 | PHASE-1: Canon Extraction | 📋 Ready to plan |
| fdx_gsd-3 | REQ-CAN-01: Character Extraction | 🚧 Blocked by phase |
| fdx_gsd-4 | REQ-CAN-02: Location Extraction | 🚧 Blocked by phase |
| fdx_gsd-5 | REQ-CAN-03: Scene Detection | 🚧 Blocked by phase |
| fdx_gsd-6 | REQ-CAN-04: Alias Resolution | 🚧 Blocked by phase |
| fdx_gsd-7 | REQ-CAN-05: Disambiguation Queue | 🚧 Blocked by phase |
| fdx_gsd-8 | REQ-CAN-06: Evidence Linking | 🚧 Blocked by phase |
| fdx_gsd-9 | INFRA: Test Framework Setup | ✅ Closed |
| fdx_gsd-10 | INFRA: CI Pipeline Setup | ✅ Closed |
| fdx_gsd-11 | INFRA: Pre-commit Hooks | ✅ Closed |
| fdx_gsd-12 | INFRA: Confucius MCP Integration | ✅ Closed |

---

## Resolved Questions

### Q1: NER Approach ✅
**Decision:** Interactive disambiguation, no ML library
- Lightweight regex extraction
- Always ask on ambiguity
- Store aliases to canonical UUID

### Q2: Test Data Source ✅
**Decision:** Public domain screenplays
- Classic films with known character/location sets
- Validates extraction against known canon
- No copyright concerns

### Q3: Confidence Thresholds ✅
**Decision:** Configurable per project in gsd.yaml
- Default: auto_accept 0.95, auto_reject 0.30
- User can tune for project needs

### Q4: Confucius Integration ✅
**Decision:** Confucius MCP IS the memory system
- Orchestration agent is separate
- Uses Confucius MCP for pattern/decision storage
- Clear separation of concerns

### Q5: What Else Is Missing ✅
**Decision:** Nothing - ready for Phase 1

---

## Next Actions

1. **Continue Phase 1** - Execute Plan 03 if exists, or proceed to next phase
2. **Verify vault notes** - Run integration tests to confirm notes are created correctly
3. **Update beads** - Mark completed work

---

## File Structure

```
fdx_gsd/
├── .planning/
│   ├── PROJECT.md              ✅
│   ├── REQUIREMENTS.md         ✅
│   ├── ROADMAP.md              ✅
│   ├── STATE.md                ✅ (this file)
│   └── TOOLING-ASSESSMENT.md   ✅
├── .beads/                      ✅
├── .github/workflows/ci.yml     ✅
├── apps/cli/                    ✅
├── core/
│   ├── exporters/               ✅ (FDX writer)
│   ├── storygraph/              ✅ (schema)
│   ├── scriptgraph/             ✅ (schema)
│   └── build/                   ✅ (schemas)
├── templates/project_template/  ✅
├── tests/
│   ├── unit/                    ✅ (FDX tests)
│   ├── integration/             (empty)
│   └── fixtures/                ✅ (sample story)
├── docs/adr/
│   ├── README.md                ✅
│   ├── 0001-ner-approach.md     ✅
│   ├── 0002-ner-approach.md     ✅
│   ├── 0003-fuzzy-matching.md   ✅
│   ├── 0004-confidence.md       ✅
│   └── 0005-confucius.md        ✅
├── scripts/                     ✅
├── .pre-commit-config.yaml      ✅
├── .gitignore                   ✅
├── pyproject.toml               ✅
└── README.md                    ✅
```
