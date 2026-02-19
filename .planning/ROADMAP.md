# ROADMAP: FDX GSD

**Project:** fdx-gsd
**Version:** 0.1.0
**Last Updated:** 2026-02-19

---

## Phase Overview

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
Foundation    Canon       Script     Round-Trip  Validation  Shots      Blender
   ✅           🚧          📋          📋          📋         📋         📋
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

## Phase 1: Canon Extraction 🚧 IN PROGRESS

**Goal:** From vomit → clean scene list + entity list

**Duration:** TBD
**Status:** 🚧 In Progress

### Requirements
- CAN-01: Character Extraction
- CAN-02: Location Extraction
- CAN-03: Scene Detection
- CAN-04: Alias Resolution
- CAN-05: Disambiguation Queue
- CAN-06: Evidence Linking

### Key Questions to Answer
1. **NER Approach** - Library vs custom?
2. **Confidence Threshold** - What's auto-accept vs queue?
3. **Test Data** - Where do sample stories come from?

### Deliverables
- [ ] `gsd build canon` command
- [ ] Character extraction pipeline
- [ ] Location extraction pipeline
- [ ] Scene detection heuristics
- [ ] Alias resolution with fuzzy matching
- [ ] Disambiguation queue system
- [ ] `gsd resolve` interactive command

### Exit Criteria
- [ ] Ingest → Characters, Locations, Scenes in vault
- [ ] Disambiguation queue populated
- [ ] All entities have evidence links
- [ ] StoryGraph JSON valid

---

## Phase 2: Script Composition 📋 PLANNED

**Goal:** Generate real screenplay paragraphs + export .fdx

**Duration:** TBD
**Depends On:** Phase 1

### Requirements
- SCR-01: Slugline Generation
- SCR-02: Beat Sheet Composition
- SCR-03: Dialogue Formatting
- SCR-04: ScriptGraph Generation
- INF-03: Deterministic Builds

### Deliverables
- [ ] `gsd build script` command
- [ ] Scene → paragraphs mapping
- [ ] Dialogue formatting rules
- [ ] ScriptGraph generation
- [ ] Fountain export (optional)
- [ ] Test suite for FDX correctness

### Exit Criteria
- [ ] ScriptGraph JSON valid
- [ ] FDX export opens in Final Draft
- [ ] Deterministic rebuild works

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

## Dependency Graph

```
Phase 0 ──┬──► Phase 1 ──┬──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
          │              │
          │              └──► (parallel testing)
          │
          └──► (infrastructure: INF-03, INF-04, INF-05)
```

---

## Critical Path

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4
            ▲
            │
            └── BLOCKED ON: NER approach decision
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

---

## Current Position

**Phase:** 0 (Complete), moving to Phase 1
**Next Action:** Answer Phase 1 key questions, then plan Phase 1

---

## Questions Before Proceeding

### MUST ANSWER for Phase 1:

1. **NER Library Choice**
   - Option A: spaCy (fast, good docs, rule-based fallback)
   - Option B: transformers/HuggingFace (accurate, slower, heavier)
   - Option C: Custom regex + rules (lightweight, story-specific)
   - **Recommendation needed**

2. **Test Data Source**
   - Create synthetic test stories?
   - Use public domain scripts?
   - Use existing personal notes?
   - **Need: 3-5 test stories for validation**

3. **Confidence Threshold**
   - Auto-accept at 0.85?
   - Auto-reject below 0.5?
   - Queue between 0.5-0.85?
   - **Configurable or hardcoded?**

4. **Fuzzy Matching Library**
   - rapidfuzz? (fast)
   - thefuzz? (simple)
   - custom Levenshtein?
   - **Need recommendation**

5. **Confucius MCP Integration**
   - Use existing Confucius MCP for pattern memory?
   - Separate "Confucius" orchestration agent?
   - How do they interact?
   - **Architecture decision needed**
