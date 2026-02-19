# PROJECT: FDX GSD - Story Operating System

**Project ID:** fdx-gsd
**Created:** 2026-02-19
**Status:** Phase 0 - Foundation
**Repository:** /Users/bretbouchard/apps/fdx_gsd

---

## Vision

A Confucius-powered system that transforms messy creative notes ("drunk drivel") into production-ready screenplays with full continuity tracking, validation, and export capabilities.

**Core Promise:** Never lose a story detail. Every fact is traced back to source. Every continuity issue is caught.

---

## Problem Statement

Writers and filmmakers have:
- Scattered notes (voice memos, napkin scribbles, chat logs)
- No systematic way to track continuity (wardrobe, props, timeline)
- Manual, error-prone script formatting
- Lost story details between drafts
- No "photographic memory" for their own stories

---

## Solution

A story operating system with:

1. **Ingestion Pipeline** - Accept any raw input, preserve as immutable evidence
2. **Canon Extraction** - NER + fuzzy matching to build canonical entities
3. **Graph-Based Memory** - StoryGraph (world) + ScriptGraph (screenplay)
4. **Continuity Validation** - Rule-based issue detection
5. **Disambiguation Queue** - Human-in-the-loop resolution
6. **Export Layer** - FDX, Fountain, sidecar reports
7. **Obsidian Integration** - Living vault as source of truth

---

## Success Metrics

| Metric | Target |
|--------|--------|
| FDX files open in Final Draft | 100% |
| Evidence traceability | Every derived fact linked |
| Continuity issues caught | >90% before user review |
| Round-trip edit preservation | Zero manual edit loss |
| Disambiguation accuracy | >85% auto-resolved |

---

## Stakeholders

| Role | Name | Responsibility |
|------|------|----------------|
| Product Owner | Bret | Vision, requirements, UAT |
| AI Assistant | Claude + Confucius | Implementation, orchestration |
| Review Council | Council of Ricks | Quality gates |

---

## Constraints

### Technical
- Python 3.10+ for core
- Obsidian-compatible Markdown (future-proof)
- SQLite for local graph storage (upgradable)
- No external API dependencies for core functionality

### Business
- Private by default (local-first)
- Git-friendly outputs (diffable, mergeable)
- Must work offline

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| NER accuracy too low | Medium | High | Disambiguation queue, confidence thresholds |
| FDX format changes | Low | Medium | Minimal XML surface, test against multiple apps |
| Performance on large stories | Medium | Medium | Incremental builds, caching |
| User edit conflicts | High | High | Protected blocks, merge strategy |

---

## Dependencies

### Already Available
- GSD (Get-Shit-Done) - Project management
- Beads - Task tracking
- Confucius MCP - Hierarchical memory
- Council of Ricks - Quality review

### Needs Investigation
- NER library for entity extraction (spaCy? custom?)
- Fuzzy matching library for aliasing (rapidfuzz?)
- LangGraph-style orchestration for Confucius loop?

---

## Open Questions

### HIGH PRIORITY - Need Answers Before Phase 1

1. **NLP/NER Approach**
   - Use existing library (spaCy, transformers) or build custom?
   - How much training data needed for story-specific entities?
   - What's the confidence threshold for auto-accept?

2. **Confucius Orchestration**
   - Is LangGraph the right tool, or simpler state machine?
   - How does Confucius MCP integrate with this project's "Confucius" agent?
   - What's the state persistence model?

3. **StoryGraph Storage**
   - SQLite + edges table sufficient for MVP?
   - Need to plan migration path to graph DB?
   - How do we handle schema evolution?

4. **Testing Strategy**
   - What test stories/datasets exist?
   - Need to create synthetic test cases?
   - How do we validate FDX output correctness?

### MEDIUM PRIORITY

5. **Obsidian Integration Depth**
   - Dataview queries for reports?
   - Graph view useful for visualization?
   - Sync strategy for multi-device?

6. **Import Sources**
   - Import from existing FDX files?
   - Import from Fountain?
   - Import from other tools (Scrivener, etc.)?

7. **Multi-project Support**
   - Shared canon across projects?
   - Template system for story types?

### LOW PRIORITY (Future Phases)

8. **Collaboration**
   - Multi-user editing?
   - Conflict resolution?

9. **Blender Integration**
   - Layout brief generation format?
   - Two-way sync or one-way?

---

## Current State

### Completed (Phase 0)
- [x] Project directory structure
- [x] GSD configuration (gsd.yaml)
- [x] JSON schemas (StoryGraph, ScriptGraph, Issues, Queue)
- [x] Obsidian vault templates
- [x] Phase 0 CLI (new-project, ingest, status)
- [x] FDX writer module
- [x] Beads tracking initialized

### In Progress
- [ ] GSD planning documents (this file, REQUIREMENTS, ROADMAP)

### Blocked
- None currently

---

## Related Projects

| Project | Relationship |
|---------|--------------|
| Blender_GSD | Phase 6 integration target |
| Bret's AI Stack | Uses GSD, Beads, Confucius, Council |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-19 | Project initialized, Phase 0 foundation complete |
