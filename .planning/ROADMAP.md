# ROADMAP: FDX GSD

**Project:** fdx-gsd
**Version:** 0.1.0
**Last Updated:** 2026-02-19

---

## Phase Overview

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6 ──► Phase 7
Foundation    Canon       Script     Round-Trip  Validation  Shots      Blender     Archive
   ✅           ✅          ✅          ✅          ✅         ✅         ✅           ✅
                                     │
                                     └──► Phase 7 (parallel track for media archive)
```

---

## Phase 0: Foundation ✅ COMPLETE

**Goal:** Project skeleton, ingest, and FDX export capability

**Duration:** Complete
**Status:** ✅ Complete

### Requirements Delivered
- INF-01: Project Initialization
- ING-01: Raw Material Ingestion
- INF-02: Project Status Visibility
- EXP-01: FDX Export

### Deliverables
- [x] `gsd new-project` command
- [x] `gsd ingest` command
- [x] `gsd status` command
- [x] FDX writer module
- [x] JSON schemas (StoryGraph, ScriptGraph, Issues, Queue)
- [x] Obsidian vault templates
- [x] gsd.yaml configuration

### Exit Criteria
- [x] Can create new project
- [x] Can ingest text with evidence tracking
- [x] Can export empty FDX file

---

## Phase 1: Canon Extraction ✅ COMPLETE

**Goal:** From vomit → clean scene list + entity list

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 4 plans in 3 waves (all executed)

### Requirements Delivered
- CAN-01: Character Extraction
- CAN-02: Location Extraction
- CAN-03: Scene Detection
- CAN-04: Alias Resolution
- CAN-05: Disambiguation Queue
- CAN-06: Evidence Linking

### Key Decisions (LOCKED)
- ADR-0002: NER Approach - Interactive Disambiguation (no ML)
- ADR-0003: Fuzzy Matching - rapidfuzz
- ADR-0004: Confidence Thresholds - Configurable per project
- ADR-0005: Confucius Integration Architecture

### Deliverables
- [x] `gsd build canon` command with vault writing
- [x] Character extraction pipeline (core extraction module)
- [x] Location extraction pipeline (core extraction module)
- [x] Scene detection heuristics (core extraction module)
- [x] Alias resolution with fuzzy matching (core resolution module)
- [x] Disambiguation queue system with vault integration
- [x] `gsd resolve` interactive command with vault updates
- [x] VaultNoteWriter for Obsidian-compatible notes
- [x] Deterministic builds (sorted output)

### Plans
- [x] 01-01-PLAN.md — Vault note templates and writer
- [x] 01-02-PLAN.md — CanonBuilder vault integration
- [x] 01-03-PLAN.md — CLI polish and deterministic builds
- [x] 01-04-PLAN.md — Disambiguation workflow completion

### Exit Criteria
- [x] Ingest → Characters, Locations, Scenes in vault
- [x] Disambiguation queue populated
- [x] All entities have evidence links
- [x] StoryGraph JSON valid

---

## Phase 2: Script Composition ✅ COMPLETE

**Goal:** Generate real screenplay paragraphs + export .fdx

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 3 plans in 2 waves (all executed)
**Depends On:** Phase 1

### Requirements Delivered
- SCR-01: Slugline Generation
- SCR-02: Beat Sheet Composition
- SCR-03: Dialogue Formatting
- SCR-04: ScriptGraph Generation
- INF-03: Deterministic Builds (already implemented)

### Key Decisions
- Follow CanonBuilder pattern for ScriptBuilder
- FDXWriter already complete - only needs ScriptGraph input
- No new dependencies needed
- Scene boundaries from Phase 1 (StoryGraph scene entities)
- Evidence traceability mandatory - every paragraph needs evidence_ids
- Character lookup uses normalized name index (exact, case-insensitive, alias matching)
- XML declaration quote style is flexible (ElementTree uses single quotes)

### Deliverables
- [x] `gsd build script` command
- [x] ScriptBuilder class (reads StoryGraph, produces ScriptGraph)
- [x] Beat extraction (action beats from inbox content)
- [x] Dialogue detection and formatting
- [x] ScriptGraph generation with full evidence linking
- [x] Test suite for FDX correctness (17 integration tests + 34 unit tests)

### Plans
- [x] 02-01-PLAN.md — ScriptBuilder + beat extraction + sluglines
- [x] 02-02-PLAN.md — Dialogue formatting + character resolution
- [x] 02-03-PLAN.md — CLI integration + end-to-end testing

### Exit Criteria
- [x] ScriptGraph JSON valid
- [x] FDX export opens in Final Draft
- [x] Deterministic rebuild works
- [x] All paragraphs have evidence_ids

---

## Phase 3: Round-Trip Editing ✅ COMPLETE

**Goal:** Edit in Obsidian, Confucius adapts

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 5 plans in 5 waves (all executed)
**Depends On:** Phase 2

### Requirements Delivered
- UIX-01: Protected Blocks
- UIX-02: Re-ingestion from Vault
- INF-04: Incremental Processing

### Key Decisions
- SHA-256 + mtime for change detection (no new dependencies)
- Three-tier conflict resolution: SAFE (auto-merge) / AMBIGUOUS (flag) / CRITICAL (block)
- Protected block replacement preserves manual edits
- Provenance tracking for audit trail
- VaultNoteWriter updated to use protected block replacement

### Deliverables
- [x] Protected block enforcement
- [x] Vault change detection (SHA-256 + mtime)
- [x] Re-ingestion pipeline (VaultReingester)
- [x] Conflict flagging (three-tier)
- [x] Provenance tracking (every line knows source)
- [x] `gsd sync` CLI command
- [x] `gsd conflicts` CLI command
- [x] 58 tests (46 unit + 12 integration)

### Plans
- [x] 03-01-PLAN.md — Change detector + protected blocks + provenance
- [x] 03-02-PLAN.md — Conflict resolver (three-tier)
- [x] 03-03-PLAN.md — Vault re-ingester
- [x] 03-04-PLAN.md — VaultNoteWriter update + unit tests
- [x] 03-05-PLAN.md — CLI integration + round-trip tests

### Exit Criteria
- [x] Manual edits preserved after rebuild
- [x] Vault changes reflected in graph
- [x] No data loss on round-trip

---

## Phase 4: Validation ✅ COMPLETE

**Goal:** Production-grade memory + issue flagging

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 6 plans in 3 waves (all executed)
**Depends On:** Phase 3

### Requirements Delivered
- VAL-01: Wardrobe Continuity (WARD-01/02/03 rules)
- VAL-02: Prop Continuity (PROP-01/02/03 rules)
- VAL-03: Timeline Validation (TIME-01/02/04 rules)
- VAL-04: Knowledge Validation (KNOW-01/02/03/04 rules)
- VAL-05: Issue Reporting

### Key Decisions
- No new dependencies - uses existing Python stdlib + rapidfuzz
- Extend Phase 3 three-tier pattern (SAFE/AMBIGUOUS/CRITICAL) to IssueSeverity (info/warning/error)
- Four specialized validators extending BaseValidator
- Obsidian-compatible reports with wikilinks in vault/80_Reports/
- Rule-based, deterministic validation (no ML)

### Deliverables
- [x] `gsd validate` command
- [x] ValidationOrchestrator coordinating all validators
- [x] WardrobeValidator (WARD-01/02/03)
- [x] PropsValidator (PROP-01/02/03)
- [x] TimelineValidator (TIME-01/02/04)
- [x] KnowledgeValidator (KNOW-01/02/03/04)
- [x] ReportGenerator for markdown reports
- [x] Markdown reports in vault/80_Reports/
- [x] build/issues.json (deterministic output)
- [x] Unit and integration tests (55 new tests)

### Plans
- [x] 04-01-PLAN.md — Issue model + BaseValidator + ReportGenerator (Wave 1)
- [x] 04-02-PLAN.md — WardrobeValidator (Wave 2)
- [x] 04-03-PLAN.md — PropsValidator (Wave 2)
- [x] 04-04-PLAN.md — TimelineValidator (Wave 2)
- [x] 04-05-PLAN.md — KnowledgeValidator (Wave 2)
- [x] 04-06-PLAN.md — CLI integration + ValidationOrchestrator + tests (Wave 3)

### Exit Criteria
- [x] Continuity issues detected
- [x] Knowledge leaks caught
- [x] Reports readable in Obsidian
- [x] `gsd validate` returns non-zero on errors (CI-friendly)

---

## Phase 5: Shot Layer ✅ COMPLETE

**Goal:** Shot lists exportable, blocking notes coherent

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 5 plans in 5 waves (all executed)
**Depends On:** Phase 4

### Requirements Delivered
- SCR-05: Shot Detection
- SCR-06: Shot List Export

### Key Decisions
- No new dependencies - Python stdlib only (csv, re, dataclasses)
- ShotSuggester follows BaseValidator pattern
- Rule-based shot detection (no ML) - infer from dialogue/action
- Export both CSV (StudioBinder-compatible) and JSON formats
- Simple text blocking notes (coordinates deferred to Phase 6)
- Auto-populate Shot List section in scene vault notes

### Deliverables
- [x] `gsd suggest-shots` command
- [x] ShotSuggester orchestrator (follows BaseValidator pattern)
- [x] ShotDetector with heuristic rules
- [x] ShotListExporter for CSV/JSON
- [x] core/shots/ module (types, models, detector, exporter, suggester)
- [x] exports/shotlist.csv (StudioBinder-compatible)
- [x] build/shotgraph.json
- [x] Updated SCN_Template.md with Shot List section
- [x] Unit and integration tests (76 tests)

### Plans
- [x] 05-01-PLAN.md — Shot types and models (Wave 1)
- [x] 05-02-PLAN.md — ShotDetector + ShotListExporter (Wave 2)
- [x] 05-03-PLAN.md — ShotSuggester orchestrator (Wave 3)
- [x] 05-04-PLAN.md — CLI integration + vault template (Wave 4)
- [x] 05-05-PLAN.md — Tests (Wave 5)

### Shot Types
- WS (Wide Shot), MS (Medium Shot), MCU (Medium Close-Up)
- CU (Close-Up), ECU (Extreme Close-Up)
- INSERT, OTS (Over-the-shoulder), POV, TWO

### Detection Rules
- Establishing: Always first shot of scene (P0)
- Emotional dialogue: Keywords -> CU (P1)
- Movement: Action verbs -> MS (P1)
- Detail insert: Object mentions -> INSERT (P2)
- Two-character dialogue -> OTS (P2)
- POV phrases -> POV (P3)

### Exit Criteria
- [x] Shot lists exportable to CSV
- [x] Shot lists exportable to JSON
- [x] Blocking notes in scene metadata
- [x] `gsd suggest-shots` generates shots from scriptgraph

---

## Phase 6: Blender Integration ✅ COMPLETE

**Goal:** Story → spatial layout assets

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 4 plans in 4 waves (all executed)
**Depends On:** Phase 5

### Requirements Delivered
- INT-01: Layout Brief Generation

### Scope Decision
**IN SCOPE:**
- Layout Brief Generation (core/layout/ module)
- LayoutBrief, SceneLayout, CameraSetup, CharacterPosition models
- Camera position calculation from shot types
- CLI command `gsd generate-layout`
- JSON export to blender/<scene_id>/layout_brief.json
- Unit and integration tests

**OUT OF SCOPE (deferred):**
- Blender addon implementation (requires bpy, different distribution)
- Actual 3D scene rendering
- Location asset library
- Complex blocking analysis from action descriptions

### Key Decisions
- No new dependencies - Python stdlib only (json, dataclasses, math)
- LayoutBriefGenerator follows ShotSuggester pattern
- Camera position calculation based on cinematography standards
- Deterministic JSON output with sorted lists
- Layout brief format is the integration point for Blender_GSD (external)

### Deliverables
- [x] `gsd generate-layout` command
- [x] core/layout/ module (models, camera_math, generator, exporter)
- [x] blender/<scene_id>/layout_brief.json per scene
- [x] build/layout_brief.json (combined)
- [x] Unit and integration tests (86 tests)

### Plans
- [x] 06-01-PLAN.md — Layout models and camera math (Wave 1)
- [x] 06-02-PLAN.md — LayoutBriefGenerator (Wave 2)
- [x] 06-03-PLAN.md — CLI integration + JSON export (Wave 3)
- [x] 06-04-PLAN.md — Tests (Wave 4)

### Camera Distance Standards
- WS: 5.0m (establishing, full body + environment)
- MS: 2.5m (waist up, standard dialogue)
- MCU: 1.8m (chest up, intimate dialogue)
- CU: 1.2m (face only, emotional moments)
- ECU: 0.8m (single feature)
- INSERT: 0.5m (props, objects)
- OTS: 2.0m (over-the-shoulder)
- POV: 1.7m (eye height)
- TWO: 3.0m (two characters in frame)

### Exit Criteria
- [x] Layout briefs generated to blender/<scene_id>/layout_brief.json
- [x] Camera positions calculated from shot types
- [x] Evidence IDs propagated from ScriptGraph/ShotGraph
- [x] Layout brief JSON schema valid for Blender_GSD consumption

---

## Phase 7: Media Asset Archive System ✅ COMPLETE

**Goal:** Archive and track all media realizations with Git LFS

**Duration:** Complete (2026-02-19)
**Status:** ✅ Complete
**Plans:** 7 plans in 5 waves (all executed)
**Depends On:** Phase 0 (can run parallel with Phase 1-6)

### Requirements Delivered
- ARC-01: Song/Work Registration
- ARC-02: Realization Tracking
- ARC-03: Performance Archive
- ARC-04: Alias Management
- ARC-05: Media Storage (Git LFS)
- ARC-06: Private Repository Management

### Key Concepts

**Work Hierarchy:**
```
Work (Song/Composition)
├── Realizations (Studio recordings, Demo versions, Remixes)
│   ├── Sessions (DAW project files)
│   ├── Stems (Individual tracks)
│   └── Masters (Final mixes)
├── Performances (Live recordings, Takes)
│   ├── Audio (WAV, FLAC, MP3)
│   ├── Video (MP4, MOV)
│   └── Metadata (Date, venue, personnel)
└── Assets (Artwork, Graphics, Documentation)
    ├── Cover Art (PNG, JPG, SVG)
    ├── Graphics (Logos, promotional)
    └── Docs (Lyrics, credits, notes)
```

**Alias Tracking:**
- Works can have multiple titles/aliases
- Artists can have stage names vs real names
- Locations can have alternate names
- Cross-reference all aliases to canonical IDs

### Deliverables
- [x] `gsd archive init` - Initialize archive repository
- [x] `gsd archive register` - Register new work with aliases
- [x] `gsd archive realize` - Add a realization of a work
- [x] `gsd archive perform` - Archive a performance
- [x] `gsd archive status` - Show archive contents
- [x] Git LFS configuration for binary files
- [x] Private repository templates (GitHub/GitLab)
- [x] Media metadata schemas (JSON)
- [x] Alias resolution and search

### Plans
- [x] 07-01-PLAN.md — Git LFS setup + archive models
- [x] 07-02-PLAN.md — Alias management system
- [x] 07-03-PLAN.md — Archive init command
- [x] 07-04-PLAN.md — Work registration
- [x] 07-05-PLAN.md — Realization tracking
- [x] 07-06-PLAN.md — Performance archive
- [x] 07-07-PLAN.md — Archive status + verification

### Exit Criteria
- [x] Can create private archive repository
- [x] Can register works with multiple aliases
- [x] Can add realizations with full session files
- [x] Can add performances with audio/video
- [x] Git LFS handles all binary files
- [x] Alias search finds correct work
- [x] Archive status shows complete hierarchy

---

## Dependency Graph

```
Phase 0 ──┬──► Phase 1 ──┬──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
          │              │
          │              └──► (parallel testing)
          │
          ├──► Phase 7 (Media Archive - parallel track)
          │
          └──► (infrastructure: INF-03, INF-04, INF-05)
```

---

## Risk Mitigation by Phase

| Phase | Key Risk | Mitigation |
|-------|----------|------------|
| 1 | NER accuracy | Disambiguation queue, test fixtures |
| 2 | FDX correctness | Test against Final Draft, Fade In |
| 3 | Edit conflicts | Protected blocks, merge strategy |
| 4 | False positives | Confidence thresholds, user tuning |
| 5 | Over-complexity | Start with shot lists, defer spatial |
| 6 | API instability | Minimal interface, version pinning |
| 7 | Storage costs | Git LFS bandwidth limits, compression |

---

## Current Position

**Phase:** All phases complete! 🎉
**Completed:** Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7
**Next Action:** Project complete - ready for production use
