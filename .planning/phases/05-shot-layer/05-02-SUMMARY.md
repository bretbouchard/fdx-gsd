# Phase 5 Wave 2 Summary: ShotDetector and ShotListExporter

**Completed:** 2026-02-19
**Status:** ✅ Complete

## Deliverables

- [x] `core/shots/detector.py` — ShotDetector with heuristic rules
- [x] `core/shots/exporter.py` — ShotListExporter for CSV/JSON

## Implementation Details

### ShotDetector Class

**Detection Rules (by priority):**

1. **Emotional Dialogue → CU (Close-Up)**
   - Keywords: cry, tears, sob, scream, whisper, gasp, shock, horror, love, hate, fear, anger, smile, laugh, grin, frown, tremble, shake, pale, flush, blush, etc.
   - Only triggers on dialogue paragraphs

2. **Movement Action → MS (Medium Shot)**
   - Verbs: walks, runs, enters, exits, moves, crosses, approaches, retreats, chases, flees, rushes, sprints, strolls, wanders, storms, strides, etc.
   - Only triggers on action paragraphs

3. **Detail Insert → INSERT**
   - Objects: ring, letter, phone, gun, knife, key, photograph, watch, blood, tear, locket, coin, map, book, note, card, flower, medal, tattoo, etc.
   - Only triggers on action paragraphs

4. **POV Phrases → POV**
   - Indicators: sees, watches, looks at, notices, spots, glimpses, stares, gazes, observes, peers, glances, etc.
   - Can trigger on any paragraph type

**Methods:**
- `detect_from_paragraph(paragraph, scene, shot_order)` — Main entry point
- `_detect_emotional_dialogue()` — Dialogue → CU
- `_detect_movement_action()` — Action → MS
- `_detect_detail_insert()` — Action → INSERT
- `_detect_pov_opportunity()` — Any → POV
- `should_add_two_shot(scene_characters)` — Two-shot detection

### ShotListExporter Class

**CSV Format (StudioBinder-compatible):**
- scene_number, shot_number, description, shot_size
- camera_angle, movement, subject, location
- cast, notes

**Methods:**
- `export_csv(shot_list, output_path)` — StudioBinder CSV
- `export_json(shot_list, output_path)` — Full JSON via ShotList.save()
- `get_summary(shot_list)` — Statistics
- `get_summary_by_type(shot_list)` — By shot type
- `get_summary_by_scene(shot_list)` — By scene

## Verification

```python
# Detector test
detector = ShotDetector()
para = {'type': 'dialogue', 'text': 'I love you!', 'evidence_ids': ['ev_001']}
scene = {'id': 'scene_001', 'order': 1, 'slugline': 'INT. OFFICE'}
shot = detector.detect_from_paragraph(para, scene, 2)
# Result: Shot with shot_type=CU, description="Close-up - Emotional moment (love)"

# Exporter test
exporter = ShotListExporter()
exporter.export_csv(shot_list, Path("exports/shotlist.csv"))
# Result: CSV with correct headers and formatted rows
```

## Commit

```
303bbdb feat(shots): Add ShotDetector and ShotListExporter (Phase 5 Wave 2)
```

## Next Steps

Wave 3: Create ShotSuggester orchestrator (05-03-PLAN.md)
