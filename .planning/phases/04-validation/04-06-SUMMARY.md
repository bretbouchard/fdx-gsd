# Phase 4, Plan 06: CLI Integration & Tests - COMPLETE

## Summary

Integrated validation into CLI and created comprehensive test suite.

## Files Created/Modified

1. **`core/validation/orchestrator.py`** (created in 04-05 continuation)
   - ValidationOrchestrator class coordinates all validators
   - Runs all validators, collects issues, persists to JSON
   - Generates markdown reports via ReportGenerator
   - Provides filtering methods by category/severity
   - `validate_project()` convenience function

2. **`core/validation/__init__.py`** (updated)
   - Added exports: ValidationOrchestrator, validate_project

3. **`apps/cli/cli.py`** (updated)
   - Added `cmd_validate()` function (~80 lines)
   - Added validate subparser with `--format` and `--category` options
   - Returns exit code 0 for success (no errors), 1 if errors found

4. **`tests/unit/test_validation.py`** (created, ~700 lines)
   - TestIssueDataModel: Issue creation, serialization, roundtrip
   - TestIssueSeverity/TestIssueCategory: Enum tests
   - TestBaseValidator: Graph loading, entity access, issue creation
   - TestWardrobeValidator/TestPropsValidator/TestTimelineValidator/TestKnowledgeValidator
   - TestReportGenerator: Empty reports, reports with issues, Obsidian links
   - TestValidationOrchestrator: Full pipeline, filtering, persistence
   - TestEdgeCases: Empty storygraph, missing files, malformed data

5. **`tests/integration/test_validation_e2e.py`** (created, ~500 lines)
   - TestValidationPipelineE2E: Full validation runs, JSON structure
   - TestValidationReportGeneration: Empty reports, severity sorting
   - TestValidationCategories: Each validator category
   - TestValidationSummary: Count accuracy
   - TestValidationWithMinimalData: Single scene, no characters
   - TestValidatorErrorHandling: Missing types, malformed edges

## Verification

```bash
# Import verification
python -c "from core.validation import ValidationOrchestrator, validate_project; print('OK')"
# Output: OK

# CLI integration
gsd validate --help
# Shows validate command options

# Test suite
python -m pytest tests/unit/test_validation.py tests/integration/test_validation_e2e.py -v
# 55 passed, 1 skipped

# Full test suite
python -m pytest tests/ -v
# 258 passed, 1 skipped
```

## CLI Usage

```bash
# Run validation
gsd validate

# JSON output
gsd validate --format json

# Specific category
gsd validate --category wardrobe

# All options
gsd validate --format json --category timeline
```

## Design Patterns

- ValidationOrchestrator follows CanonBuilder pattern
- Issue filtering methods follow Resolver patterns
- Reports use ReportGenerator with Obsidian wikilinks
- Tests follow existing project test patterns
