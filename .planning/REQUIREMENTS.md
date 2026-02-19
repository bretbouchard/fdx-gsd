# REQUIREMENTS: FDX GSD

**Version:** 0.1.0
**Last Updated:** 2026-02-19

---

## Requirement Format

Each requirement follows: `REQ-{DOMAIN}-{NUMBER}`

Domains:
- `ING` - Ingestion
- `CAN` - Canon/Entity Management
- `SCR` - Script Composition
- `VAL` - Validation
- `EXP` - Export
- `UIX` - User Experience
- `INT` - Integration
- `INF` - Infrastructure

---

## Phase 0 Requirements (Foundation)

### ING-01: Raw Material Ingestion
**Priority:** P0 | **Status:** ✅ Complete

The system MUST accept raw text input and register it as immutable evidence.

**Acceptance Criteria:**
- [x] `gsd ingest --text "..."` creates timestamped file in inbox/
- [x] Each paragraph gets a unique block anchor (^ev_xxxx)
- [x] Evidence is registered in evidence_index.json
- [x] Original text is preserved verbatim

### INF-01: Project Initialization
**Priority:** P0 | **Status:** ✅ Complete

The system MUST create a valid project structure from a template.

**Acceptance Criteria:**
- [x] `gsd new-project <name>` creates full directory structure
- [x] Git repository is initialized
- [x] gsd.yaml is configured with project metadata
- [x] Empty build files are created (storygraph, scriptgraph, queue)

### INF-02: Project Status Visibility
**Priority:** P0 | **Status:** ✅ Complete

The system MUST show current project state.

**Acceptance Criteria:**
- [x] `gsd status` shows: inbox count, vault entities, evidence count, queue items
- [x] Pipeline phases enabled are listed

---

## Phase 1 Requirements (Canon Extraction)

### CAN-01: Character Extraction
**Priority:** P0 | **Status:** 📋 Planned

The system MUST identify and extract characters from inbox material.

**Acceptance Criteria:**
- [ ] Names are recognized (proper nouns, capitalized words)
- [ ] Aliases are detected (John, Johnny, J.)
- [ ] Character notes are created in vault/10_Characters/
- [ ] Each character has: id, name, aliases, evidence_ids
- [ ] Low-confidence extractions go to disambiguation queue

### CAN-02: Location Extraction
**Priority:** P0 | **Status:** 📋 Planned

The system MUST identify and extract locations from inbox material.

**Acceptance Criteria:**
- [ ] Location references are recognized (the diner, Joe's Diner, INT. DINER)
- [ ] Location notes are created in vault/20_Locations/
- [ ] INT/EXT indicators are captured
- [ ] Spatial notes (if present) are preserved

### CAN-03: Scene Detection
**Priority:** P0 | **Status:** 📋 Planned

The system MUST detect scene boundaries and create scene notes.

**Acceptance Criteria:**
- [ ] INT./EXT. patterns trigger scene detection
- [ ] Scene transitions ("CUT TO:", "LATER") are recognized
- [ ] Scenes are numbered SCN_001, SCN_002, etc.
- [ ] Time-of-day is extracted from sluglines
- [ ] Scene order is maintained

### CAN-04: Alias Resolution
**Priority:** P0 | **Status:** 📋 Planned

The system MUST resolve entity aliases with configurable confidence.

**Acceptance Criteria:**
- [ ] Fuzzy matching on names (Sarah/Sara/S.)
- [ ] Confidence score calculated for each match
- [ ] Above threshold: auto-merge
- [ ] Below threshold: add to disambiguation queue

### CAN-05: Disambiguation Queue
**Priority:** P0 | **Status:** 📋 Planned

The system MUST maintain a queue of items requiring human resolution.

**Acceptance Criteria:**
- [ ] Queue stored in build/disambiguation_queue.json
- [ ] Each item has: id, kind, label, candidates, recommended_action
- [ ] `gsd resolve` presents items interactively
- [ ] Resolved items update vault + graph
- [ ] Queue is incremental (only new ambiguities added)

### CAN-06: Evidence Linking
**Priority:** P0 | **Status:** 📋 Planned

Every extracted fact MUST link back to source evidence.

**Acceptance Criteria:**
- [ ] All entities have evidence_ids array
- [ ] Evidence links are Obsidian-compatible: [[inbox/file#^block]]
- [ ] Clicking evidence shows original text
- [ ] Evidence index is kept in sync

---

## Phase 2 Requirements (Script Composition)

### SCR-01: Slugline Generation
**Priority:** P0 | **Status:** 📋 Planned

The system MUST generate valid sluglines from scene data.

**Acceptance Criteria:**
- [ ] Format: INT./EXT. LOCATION - TIME
- [ ] Location names use canonical entity names
- [ ] Time-of-day is normalized (DAY, NIGHT, CONTINUOUS, etc.)

### SCR-02: Beat Sheet Composition
**Priority:** P0 | **Status:** 📋 Planned

The system MUST compose beat sheets from inbox material.

**Acceptance Criteria:**
- [ ] Action beats extracted from narrative text
- [ ] Beats are ordered within scene
- [ ] Each beat links to source evidence

### SCR-03: Dialogue Formatting
**Priority:** P0 | **Status:** 📋 Planned

The system MUST format dialogue according to screenplay standards.

**Acceptance Criteria:**
- [ ] Character names in ALL CAPS, centered
- [ ] Dialogue indented properly
- [ ] Parentheticals supported
- [ ] Character names link to canonical entities

### SCR-04: ScriptGraph Generation
**Priority:** P0 | **Status:** 📋 Planned

The system MUST generate a valid ScriptGraph JSON.

**Acceptance Criteria:**
- [ ] All scenes present with correct order
- [ ] Paragraphs typed correctly (scene_heading, action, character, dialogue)
- [ ] Links to all referenced entities
- [ ] Evidence IDs on all derived content

### EXP-01: FDX Export
**Priority:** P0 | **Status:** ✅ Complete

The system MUST export valid Final Draft XML files.

**Acceptance Criteria:**
- [x] Generated .fdx opens in Final Draft
- [x] Paragraph types map correctly
- [x] UTF-8 encoding preserved
- [x] Empty paragraphs between scenes

---

## Phase 3 Requirements (Round-Trip Editing)

### UIX-01: Protected Blocks
**Priority:** P1 | **Status:** 📋 Planned

The system MUST preserve manual edits in protected regions.

**Acceptance Criteria:**
- [ ] `<!-- CONFUCIUS:BEGIN AUTO -->` and `<!-- CONFUCIUS:END AUTO -->` markers
- [ ] Confucius only writes inside markers
- [ ] User prose outside markers is never modified
- [ ] Missing markers are appended at end of file

### UIX-02: Re-ingestion from Vault
**Priority:** P1 | **Status:** 📋 Planned

The system MUST re-ingest changes made in Obsidian vault.

**Acceptance Criteria:**
- [ ] Detect modified vault files
- [ ] Extract new/changed entities
- [ ] Update StoryGraph without losing manual annotations
- [ ] Flag conflicts for review

---

## Phase 4 Requirements (Validation)

### VAL-01: Wardrobe Continuity
**Priority:** P1 | **Status:** 📋 Planned

The system MUST validate wardrobe state changes.

**Rules:**
- WARD-01: State changes require cause beat
- WARD-02: Conflicting wardrobe in adjacent timeline
- WARD-03: Signature items persist

**Acceptance Criteria:**
- [ ] Issues written to build/issues.json
- [ ] Severity: error, warning, info
- [ ] Suggestions for fixes included

### VAL-02: Prop Continuity
**Priority:** P1 | **Status:** 📋 Planned

The system MUST validate prop appearance and state.

**Rules:**
- PROP-01: Cannot appear without introduction
- PROP-02: Ownership transfer must be shown
- PROP-03: Damage persists

### VAL-03: Timeline Validation
**Priority:** P1 | **Status:** 📋 Planned

The system MUST validate timeline consistency.

**Rules:**
- TIME-01: Impossible travel given location distance
- TIME-02: Unresolved relative phrases
- TIME-04: Character in two places at once

### VAL-04: Knowledge Validation
**Priority:** P1 | **Status:** 📋 Planned

The system MUST validate character knowledge states.

**Rules:**
- KNOW-01: Cannot reference unlearned information
- KNOW-02: Secrets propagate only through shown channels
- KNOW-03: Motive/goal consistency
- KNOW-04: Relationship continuity

### VAL-05: Issue Reporting
**Priority:** P1 | **Status:** 📋 Planned

The system MUST generate human-readable issue reports.

**Acceptance Criteria:**
- [ ] Markdown reports in vault/80_Reports/
- [ ] Grouped by severity, then scene
- [ ] Links to scenes and entities
- [ ] Evidence block references
- [ ] Suggested patches

---

## Phase 5 Requirements (Shot Layer)

### SCR-05: Shot Detection
**Priority:** P2 | **Status:** 📋 Planned

The system MUST detect and suggest shots.

### SCR-06: Shot List Export
**Priority:** P2 | **Status:** 📋 Planned

The system MUST export shot lists.

---

## Phase 6 Requirements (Blender Integration)

### INT-01: Layout Brief Generation
**Priority:** P2 | **Status:** 📋 Planned

The system MUST generate layout briefs for Blender_GSD.

---

## Infrastructure Requirements

### INF-03: Deterministic Builds
**Priority:** P0 | **Status:** 📋 Planned

Same inputs MUST produce identical outputs.

**Acceptance Criteria:**
- [ ] Running `gsd build canon` twice produces same storygraph.json
- [ ] Running `gsd build script` twice produces same scriptgraph.json
- [ ] Hash-based change detection

### INF-04: Incremental Processing
**Priority:** P1 | **Status:** 📋 Planned

Only changed inputs trigger reprocessing.

**Acceptance Criteria:**
- [ ] File hashes tracked in build/run_state.json
- [ ] Only dirty files reprocessed
- [ ] Downstream dependencies updated

### INF-05: Test Coverage
**Priority:** P0 | **Status:** 📋 Planned

Core functionality MUST have test coverage.

**Acceptance Criteria:**
- [ ] Unit tests for FDX writer
- [ ] Unit tests for entity extraction
- [ ] Integration tests for full pipeline
- [ ] Test fixtures (sample stories)

---

## Non-Functional Requirements

### NFR-01: Performance
- Ingest: <1s for typical note
- Canon build: <10s for 100 inbox files
- FDX export: <5s for 120-page script

### NFR-02: Reliability
- Zero data loss on crash
- Graceful degradation (queue instead of crash)

### NFR-03: Usability
- CLI commands are discoverable
- Error messages are actionable
- Obsidian vault is immediately usable

---

## Requirement Summary by Phase

| Phase | Requirements | P0 | P1 | P2 |
|-------|--------------|----|----|-----|
| 0 - Foundation | 3 | 3 | - | - |
| 1 - Canon | 6 | 6 | - | - |
| 2 - Script | 5 | 4 | 1 | - |
| 3 - Round-Trip | 2 | - | 2 | - |
| 4 - Validation | 5 | - | 5 | - |
| 5 - Shots | 2 | - | - | 2 |
| 6 - Blender | 1 | - | - | 1 |

**Total:** 24 requirements (13 P0, 8 P1, 3 P2)
