# Phase 6 Summary: Blender Integration

**Status:** ✅ COMPLETE
**Duration:** 2026-02-19
**Plans Executed:** 4 plans in 4 waves

---

## Overview

Phase 6 implemented the layout brief generation system for Blender integration. This phase created the `core/layout/` module that transforms ScriptGraph and ShotGraph data into spatial layout briefs suitable for 3D previz.

---

## Deliverables

### Files Created

| File | Purpose |
|------|---------|
| `core/layout/models.py` | Data models for LayoutBrief, SceneLayout, CameraSetup, CharacterPosition, PropPosition |
| `core/layout/camera_math.py` | Camera position calculation from shot types with cinematography standards |
| `core/layout/generator.py` | LayoutBriefGenerator orchestrating the layout generation |
| `core/layout/exporter.py` | LayoutBriefExporter for JSON output to blender/ directory |
| `core/layout/__init__.py` | Module exports |
| `tests/unit/test_layout_models.py` | Unit tests for layout models (16 tests) |
| `tests/unit/test_layout_camera_math.py` | Unit tests for camera math (26 tests) |
| `tests/unit/test_layout_generator.py` | Unit tests for generator (33 tests) |
| `tests/integration/test_layout_workflow.py` | Integration tests for workflow (19 tests) |

### Files Modified

| File | Changes |
|------|---------|
| `apps/cli/cli.py` | Added `cmd_generate_layout` function and subparser |
| `.planning/ROADMAP.md` | Updated Phase 6 status to complete |

### CLI Command

```bash
gsd generate-layout
```

Creates:
- `blender/<scene_id>/layout_brief.json` - Per-scene layout files
- `build/layout_brief.json` - Combined brief

---

## Requirements Delivered

### INT-01: Layout Brief Generation

- ✅ LayoutBrief with version, project_id, generated_at
- ✅ SceneLayout with scene_id, slugline, characters, camera_setups, props, environment
- ✅ CameraSetup with calculated position, rotation, lens settings
- ✅ CharacterPosition with spatial coordinates and facing direction
- ✅ Evidence chain preserved from ScriptGraph/ShotGraph

---

## Camera Math Implementation

### Shot Type Distances

| Shot Type | Distance | Camera Height | Use Case |
|-----------|----------|---------------|----------|
| WS | 5.0m | 2.0m (raised) | Establishing, full body + environment |
| MS | 2.5m | 1.6m (eye level) | Waist up, standard dialogue |
| MCU | 1.8m | 1.6m (eye level) | Chest up, intimate dialogue |
| CU | 1.2m | 1.6m (eye level) | Face only, emotional moments |
| ECU | 0.8m | 1.6m (eye level) | Single feature |
| INSERT | 0.5m | 1.6m (eye level) | Props, objects |
| OTS | 2.0m | 1.6m (eye level) | Over-the-shoulder |
| POV | 1.7m | 1.7m (subject height) | Eye height matching |
| TWO | 3.0m | 1.6m (eye level) | Two characters in frame |

### Coordinate System

- **X-axis:** Right (+) / Left (-)
- **Y-axis:** Forward (+) / Back (-)
- **Z-axis:** Up (+) / Down (-)
- Camera placed in front of subject (negative Y)

---

## Key Decisions

1. **No new dependencies** - Uses only Python stdlib (json, dataclasses, math)
2. **Pattern following** - LayoutBriefGenerator follows ShotSuggester pattern
3. **Deterministic output** - All lists sorted, JSON with sort_keys=True
4. **Simple character layout** - Grid spacing (1.5m apart along X-axis)
5. **Props extraction deferred** - Future work from blocking analysis

---

## Test Results

```
86 tests passed in 0.37s

Unit Tests:
- test_layout_models.py: 16 tests
- test_layout_camera_math.py: 26 tests
- test_layout_generator.py: 33 tests

Integration Tests:
- test_layout_workflow.py: 19 tests
```

### Coverage Areas

- ✅ All 9 shot types with correct distances
- ✅ Camera position calculation
- ✅ Camera height variation (WS raised, others eye level)
- ✅ Character position grid layout
- ✅ Evidence chain propagation
- ✅ JSON serialization/deserialization
- ✅ Determinism (sorted output)
- ✅ Edge cases (empty scenes, missing data)
- ✅ 50-scene performance test

---

## Integration Points

### Input
- `build/scriptgraph.json` - Scene data with characters, locations, evidence
- `build/shotgraph.json` - Shot data with shot_types, evidence

### Output
- `blender/<scene_id>/layout_brief.json` - Per-scene layout
- `build/layout_brief.json` - Combined brief for all scenes

### Layout Brief Schema

```json
{
  "version": "1.0",
  "project_id": "my-project",
  "generated_at": "2026-02-19T12:00:00",
  "scene_layouts": [
    {
      "scene_id": "SCN_001",
      "slugline": "INT. OFFICE - DAY",
      "location_id": "LOC_office",
      "int_ext": "INT",
      "time_of_day": "DAY",
      "environment": {
        "description": "INT - DAY",
        "lighting_preset": "interior_day"
      },
      "characters": [...],
      "props": [],
      "camera_setups": [...],
      "evidence_ids": ["EV_001"]
    }
  ]
}
```

---

## Council of Ricks Review

**Result:** ✅ APPROVED

- 0 Critical issues
- 0 High issues
- 3 Medium issues (non-blocking)
- 2 Low issues

Key validations:
- Camera math correct for all 9 shot types
- Evidence chain preserved
- Pattern adherence to ShotSuggester/ShotListExporter
- SLC compliance

---

## Lessons Learned

1. **Camera height variation matters** - WS uses 2.0m (raised) while others use 1.6m (eye level)
2. **Coordinate system clarity** - Blender uses Y-forward, which differs from some engines
3. **Determinism is critical** - Sorted lists and sort_keys=True ensure reproducible builds
4. **Simple layout works** - Grid spacing for characters is sufficient for previz

---

## Future Work (Out of Scope)

- Blender addon implementation (requires bpy)
- Complex blocking analysis from action descriptions
- Location asset library
- Actual 3D scene rendering
- Character facing/pose inference from dialogue

---

## Exit Criteria Verification

- [x] Layout briefs generated to blender/<scene_id>/layout_brief.json
- [x] Camera positions calculated from shot types
- [x] Evidence IDs propagated from ScriptGraph/ShotGraph
- [x] Layout brief JSON schema valid for Blender_GSD consumption
- [x] All 86 tests passing

---

## Completion

**Phase 6 is complete.** All planned phases (0-7) are now finished. The FDX GSD project is ready for production use.

```
All Phases: ✅ COMPLETE
Phase 0: Foundation ✅
Phase 1: Canon Extraction ✅
Phase 2: Script Composition ✅
Phase 3: Round-Trip Editing ✅
Phase 4: Validation ✅
Phase 5: Shot Layer ✅
Phase 6: Blender Integration ✅
Phase 7: Media Archive ✅
```
