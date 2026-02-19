# ROADMAP: FDX GSD

**Project:** fdx-gsd
**Version:** 0.1.0
**Last Updated:** 2026-02-19

---

## Phase Overview

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6 ──► Phase 7
Foundation    Canon       Script     Round-Trip  Validation  Shots      Blender     Archive
   ✅           ✅          ✅          📋          📋         📋         📋           ✅
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

## Phase 3: Round-Trip Editing 📋 PLANNED

**Goal:** Edit in Obsidian, Confucius adapts

**Duration:** TBD
**Depends On:** Phase 2

### Requirements
- UIX-01: Protected Blocks
- UIX-02: Re-ingestion from Vault
- INF-04: Incremental Processing

### Deliverables
- [ ] Protected block enforcement
- [ ] Vault change detection
- [ ] Re-ingestion pipeline
- [ ] Conflict flagging
- [ ] Provenance tracking (every line knows source)

### Exit Criteria
- [ ] Manual edits preserved after rebuild
- [ ] Vault changes reflected in graph
- [ ] No data loss on round-trip

---

## Phase 4: Validation 📋 PLANNED

**Goal:** Production-grade memory + issue flagging

**Duration:** TBD
**Depends On:** Phase 3

### Requirements
- VAL-01: Wardrobe Continuity
- VAL-02: Prop Continuity
- VAL-03: Timeline Validation
- VAL-04: Knowledge Validation
- VAL-05: Issue Reporting

### Deliverables
- [ ] `gsd validate` command
- [ ] `gsd report issues` command
- [ ] Wardrobe validator
- [ ] Props validator
- [ ] Timeline validator
- [ ] Knowledge validator
- [ ] Markdown reports in vault/80_Reports/
- [ ] build/issues.json

### Exit Criteria
- [ ] Continuity issues detected
- [ ] Knowledge leaks caught
- [ ] Reports readable in Obsidian

---

## Phase 5: Shot Layer 📋 PLANNED

**Goal:** "Adjust shots, layouts as needed"

**Duration:** TBD
**Depends On:** Phase 4

### Requirements
- SCR-05: Shot Detection
- SCR-06: Shot List Export

### Deliverables
- [ ] Shot suggestion engine
- [ ] Shot notes in scenes
- [ ] exports/shotlist.csv
- [ ] Spatial constraint system

### Exit Criteria
- [ ] Shot lists exportable
- [ ] Blocking notes coherent

---

## Phase 6: Blender Integration 📋 PLANNED

**Goal:** Story → spatial layout assets

**Duration:** TBD
**Depends On:** Phase 5

### Requirements
- INT-01: Layout Brief Generation

### Deliverables
- [ ] blender/<scene_id>/layout_brief.json
- [ ] Blender addon or CLI runner
- [ ] Scene scaffold generation

### Exit Criteria
- [ ] Layout briefs generated
- [ ] Blender_GSD can consume briefs

---

## Phase 7: Media Asset Archive System 📋 PLANNED

**Goal:** Archive and track all media realizations with Git LFS

**Duration:** TBD
**Status:** 📋 Ready to execute
**Plans:** 7 plans in 5 waves
**Depends On:** Phase 0 (can run parallel with Phase 1-6)

### Requirements
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
- [ ] `gsd archive init` - Initialize archive repository
- [ ] `gsd archive register` - Register new work with aliases
- [ ] `gsd archive realize` - Add a realization of a work
- [ ] `gsd archive perform` - Archive a performance
- [ ] `gsd archive status` - Show archive contents
- [ ] Git LFS configuration for binary files
- [ ] Private repository templates (GitHub/GitLab)
- [ ] Media metadata schemas (JSON)
- [ ] Alias resolution and search

### Plans
- [ ] 07-01-PLAN.md — Git LFS setup + archive models
- [ ] 07-02-PLAN.md — Alias management system
- [ ] 07-03-PLAN.md — Archive init command
- [ ] 07-04-PLAN.md — Work registration
- [ ] 07-05-PLAN.md — Realization tracking
- [ ] 07-06-PLAN.md — Performance archive
- [ ] 07-07-PLAN.md — Archive status + verification

### Directory Structure
```
archive/
├── works/
│   └── {work_id}/
│       ├── metadata.json          # Title, aliases, created, genre
│       ├── realizations/
│       │   └── {realization_id}/
│       │       ├── metadata.json  # Version, date, studio, engineer
│       │       ├── sessions/      # DAW projects (.als, .flp, .ptx)
│       │       ├── stems/         # Individual tracks
│       │       └── masters/       # Final outputs
│       ├── performances/
│       │   └── {performance_id}/
│       │       ├── metadata.json  # Date, venue, personnel
│       │       ├── audio/
│       │       └── video/
│       └── assets/
│           ├── artwork/
│           ├── graphics/
│           └── docs/
├── aliases.json                   # Global alias → canonical_id map
└── index.json                     # Searchable index of all works
```

### Git LFS Configuration
```yaml
# .gitattributes
*.wav filter=lfs diff=lfs merge=lfs -text
*.flac filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.aiff filter=lfs diff=lfs merge=lfs -text
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
*.ai filter=lfs diff=lfs merge=lfs -text
*.als filter=lfs diff=lfs merge=lfs -text
*.flp filter=lfs diff=lfs merge=lfs -text
```

### Exit Criteria
- [ ] Can create private archive repository
- [ ] Can register works with multiple aliases
- [ ] Can add realizations with full session files
- [ ] Can add performances with audio/video
- [ ] Git LFS handles all binary files
- [ ] Alias search finds correct work
- [ ] Archive status shows complete hierarchy

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

**Phase:** 3 (Round-Trip Editing) - Ready for planning
**Completed:** Phase 0, Phase 1, Phase 2, Phase 7
**Next Action:** Plan Phase 3 with `/gsd:plan-phase 3`
