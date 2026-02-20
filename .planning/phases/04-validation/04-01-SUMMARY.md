# Phase 4, Plan 01: Validation Foundation - COMPLETE

## Summary

Created the validation foundation module with:

1. **Issue Data Model** (`core/validation/base.py`)
   - `IssueSeverity` enum: ERROR, WARNING, INFO (maps to ConflictTier)
   - `IssueCategory` enum: WARDROBE, PROPS, TIMELINE, KNOWLEDGE
   - `Issue` dataclass with to_dict/from_dict for JSON serialization
   - Fields: issue_id, category, severity, rule_code, title, description, scene_id, scene_number, entity_ids, evidence_ids, source_paragraph, suggested_fix, auto_fixable, detected_at, resolved, resolved_at, resolution_note

2. **BaseValidator Abstract Class** (`core/validation/base.py`)
   - Abstract `validate()` method for subclass implementation
   - `_load_graphs()` loads storygraph.json and scriptgraph.json
   - `_create_issue_id()` generates unique IDs like "issue_wardrobe_000001"
   - `_add_issue()` helper for creating and adding issues
   - Helper methods: `get_entities_by_type()`, `get_entity_by_id()`, `get_scenes_sorted()`, `get_characters()`, `get_locations()`

3. **ReportGenerator** (`core/validation/report_generator.py`)
   - Creates reports in `vault/80_Reports/`
   - `validation-summary.md`: Overview with severity/category tables, critical issues
   - `{category}-issues.md`: Detailed reports grouped by scene
   - Obsidian-compatible wikilinks: `[[scene_id]]`, `[[entity_id]]`, `[[evidence#^block]]`
   - Severity emojis: ERROR=❌, WARNING=⚠️, INFO=ℹ️

4. **Module Exports** (`core/validation/__init__.py`)
   - Exports: Issue, IssueSeverity, IssueCategory, BaseValidator, ReportGenerator

## Verification

```bash
python -c "from core.validation import Issue, IssueSeverity, IssueCategory, BaseValidator, ReportGenerator; print('OK')"
# Output: OK
```

## Files Created

- `core/validation/__init__.py`
- `core/validation/base.py` (~230 lines)
- `core/validation/report_generator.py` (~280 lines)

## Design Patterns

- Follows `ConflictResolver` pattern from Phase 3
- Issue/IssueSeverity mirrors Conflict/ConflictTier
- BaseValidator follows CanonBuilder patterns
- ReportGenerator creates Obsidian-compatible output
