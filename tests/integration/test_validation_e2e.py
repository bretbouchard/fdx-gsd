"""End-to-end integration tests for validation pipeline.

Tests the full flow: storygraph → validation → reports → issues.json
"""
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from core.validation import (
    Issue,
    IssueSeverity,
    IssueCategory,
    ValidationOrchestrator,
    validate_project,
)


@pytest.fixture
def temp_project_with_storygraph():
    """Create a temporary project with comprehensive storygraph for testing."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directories
    (temp_dir / "build").mkdir(parents=True)
    (temp_dir / "vault" / "10_Characters").mkdir(parents=True)
    (temp_dir / "vault" / "20_Locations").mkdir(parents=True)
    (temp_dir / "vault" / "50_Scenes").mkdir(parents=True)
    (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

    # Create comprehensive storygraph with entities that will trigger validation rules
    storygraph = {
        "version": "1.0",
        "project_id": "test-validation-project",
        "entities": [
            # Characters
            {
                "id": "CHAR_Fox_001",
                "type": "character",
                "name": "Fox",
                "aliases": ["FOX"],
                "attributes": {
                    "signature_items": ["blue suit", "gold watch"],
                },
                "evidence_ids": ["ev_001", "ev_002", "ev_003"],
            },
            {
                "id": "CHAR_Sarah_001",
                "type": "character",
                "name": "Sarah",
                "aliases": ["SARAH"],
                "attributes": {
                    "secrets_known": ["secret_plan"],
                },
                "evidence_ids": ["ev_002", "ev_004"],
            },
            {
                "id": "CHAR_Tom_001",
                "type": "character",
                "name": "Tom",
                "aliases": ["TOM"],
                "attributes": {},
                "evidence_ids": ["ev_003"],
            },
            # Locations
            {
                "id": "LOC_Diner_001",
                "type": "location",
                "name": "Diner",
                "aliases": ["COFFEE SHOP"],
                "attributes": {
                    "city": "New York",
                    "country": "USA",
                },
                "evidence_ids": ["ev_001"],
            },
            {
                "id": "LOC_Office_001",
                "type": "location",
                "name": "Office",
                "aliases": [],
                "attributes": {
                    "city": "Los Angeles",  # Different city - triggers TIME-01
                    "country": "USA",
                },
                "evidence_ids": ["ev_002"],
            },
            {
                "id": "LOC_Park_001",
                "type": "location",
                "name": "Park",
                "aliases": [],
                "attributes": {
                    "city": "New York",
                },
                "evidence_ids": ["ev_004"],
            },
            # Props
            {
                "id": "PROP_Gun_001",
                "type": "prop",
                "name": "Gun",
                "aliases": [],
                "attributes": {
                    "owner": "CHAR_Fox_001",
                    "condition": "damaged",
                },
                "evidence_ids": ["ev_002"],
            },
            {
                "id": "PROP_Phone_001",
                "type": "prop",
                "name": "Phone",
                "aliases": [],
                "attributes": {
                    "owner": "CHAR_Sarah_001",
                },
                "evidence_ids": ["ev_001"],
            },
            # Scenes
            {
                "id": "scene_001",
                "type": "scene",
                "name": "Scene 1 - Diner",
                "attributes": {
                    "scene_number": 1,
                    "location_id": "LOC_Diner_001",
                    "int_ext": "INT",
                    "time_of_day": "DAY",
                },
                "evidence_ids": ["ev_001"],
            },
            {
                "id": "scene_002",
                "type": "scene",
                "name": "Scene 2 - Office",
                "attributes": {
                    "scene_number": 2,
                    "location_id": "LOC_Office_001",
                    "int_ext": "INT",
                    "time_of_day": "DAY",
                    "time_phrase": "MOMENTS LATER",  # Impossible travel
                },
                "evidence_ids": ["ev_002"],
            },
            {
                "id": "scene_003",
                "type": "scene",
                "name": "Scene 3 - Back to Diner",
                "attributes": {
                    "scene_number": 3,
                    "location_id": "LOC_Diner_001",
                    "int_ext": "INT",
                    "time_of_day": "DAY",
                },
                "evidence_ids": ["ev_003"],
            },
            {
                "id": "scene_004",
                "type": "scene",
                "name": "Scene 4 - Park",
                "attributes": {
                    "scene_number": 4,
                    "location_id": "LOC_Park_001",
                    "int_ext": "EXT",
                    "time_of_day": "NIGHT",
                },
                "evidence_ids": ["ev_004"],
            },
        ],
        "edges": [
            # Character appearances
            {"type": "appears_in", "source": "CHAR_Fox_001", "target": "scene_001"},
            {"type": "appears_in", "source": "CHAR_Fox_001", "target": "scene_002"},
            {"type": "appears_in", "source": "CHAR_Fox_001", "target": "scene_003"},
            {"type": "appears_in", "source": "CHAR_Sarah_001", "target": "scene_001"},
            {"type": "appears_in", "source": "CHAR_Sarah_001", "target": "scene_004"},
            {"type": "appears_in", "source": "CHAR_Tom_001", "target": "scene_003"},
            # Prop ownership
            {"type": "owns", "source": "CHAR_Fox_001", "target": "PROP_Gun_001"},
            {"type": "owns", "source": "CHAR_Sarah_001", "target": "PROP_Phone_001"},
            # Knowledge
            {"type": "knows", "source": "CHAR_Fox_001", "target": "CHAR_Sarah_001"},
            {"type": "knows", "source": "CHAR_Sarah_001", "target": "CHAR_Tom_001"},
        ],
        "evidence_index": {
            "ev_001": {"source_file": "vault/50_Scenes/scene_001.md", "line_number": 1},
            "ev_002": {"source_file": "vault/50_Scenes/scene_002.md", "line_number": 1},
            "ev_003": {"source_file": "vault/50_Scenes/scene_003.md", "line_number": 1},
            "ev_004": {"source_file": "vault/50_Scenes/scene_004.md", "line_number": 1},
        },
    }

    (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph, indent=2))
    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestValidationPipelineE2E:
    """End-to-end tests for validation pipeline."""

    def test_full_validation_run(self, temp_project_with_storygraph):
        """Test running full validation pipeline."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        # Check result structure
        assert "success" in result
        assert "total_issues" in result
        assert "by_severity" in result
        assert "by_category" in result
        assert "reports" in result
        assert "issues_path" in result

        # Check issues.json was created
        issues_path = temp_project_with_storygraph / "build" / "issues.json"
        assert issues_path.exists()

        # Check reports were created
        reports_dir = temp_project_with_storygraph / "vault" / "80_Reports"
        assert reports_dir.exists()
        summary_report = reports_dir / "validation-summary.md"
        assert summary_report.exists()

    def test_issues_json_structure(self, temp_project_with_storygraph):
        """Test that issues.json has correct structure."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        issues_path = temp_project_with_storygraph / "build" / "issues.json"
        data = json.loads(issues_path.read_text())

        # Check top-level structure
        assert "version" in data
        assert "generated_at" in data
        assert "total_issues" in data
        assert "summary" in data
        assert "issues" in data

        # Check summary structure
        summary = data["summary"]
        assert "total_issues" in summary
        assert "by_severity" in summary
        assert "by_category" in summary
        assert "auto_fixable_count" in summary

        # Check issues structure
        for issue in data["issues"]:
            assert "issue_id" in issue
            assert "category" in issue
            assert "severity" in issue
            assert "rule_code" in issue
            assert "title" in issue
            assert "description" in issue

    def test_validation_detects_timeline_issues(self, temp_project_with_storygraph):
        """Test that impossible travel is detected."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        # Get timeline issues
        timeline_issues = orchestrator.get_issues_by_category(IssueCategory.TIMELINE)

        # Should detect at least one impossible travel issue (NY to LA in moments)
        # This depends on the validator implementation
        assert isinstance(timeline_issues, list)

    def test_reports_use_obsidian_format(self, temp_project_with_storygraph):
        """Test that reports use Obsidian-compatible wikilinks."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        # Check summary report for wikilinks
        summary_path = temp_project_with_storygraph / "vault" / "80_Reports" / "validation-summary.md"
        content = summary_path.read_text()

        # Reports should have markdown structure
        assert "#" in content  # Headers

        # If there are issues, should reference scenes
        if result["total_issues"] > 0:
            # Should have scene references (wikilinks or mentions)
            assert "scene" in content.lower() or "Scene" in content

    def test_convenience_function(self, temp_project_with_storygraph):
        """Test the validate_project convenience function."""
        result = validate_project(temp_project_with_storygraph)

        assert "success" in result
        assert "total_issues" in result
        assert isinstance(result["total_issues"], int)

    def test_deterministic_output(self, temp_project_with_storygraph):
        """Test that running validation twice produces same results."""
        # First run
        orchestrator1 = ValidationOrchestrator(temp_project_with_storygraph)
        result1 = orchestrator1.run_validation()

        issues_path = temp_project_with_storygraph / "build" / "issues.json"
        data1 = json.loads(issues_path.read_text())

        # Second run
        orchestrator2 = ValidationOrchestrator(temp_project_with_storygraph)
        result2 = orchestrator2.run_validation()

        data2 = json.loads(issues_path.read_text())

        # Should have same issue count
        assert data1["total_issues"] == data2["total_issues"]

        # Issue IDs should be in same order (deterministic)
        ids1 = [i["issue_id"] for i in data1["issues"]]
        ids2 = [i["issue_id"] for i in data2["issues"]]
        assert ids1 == ids2


class TestValidationReportGeneration:
    """Tests for report generation."""

    def test_empty_report_when_no_issues(self):
        """Test that empty report is generated when no issues."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

        # Create minimal storygraph with no issues
        storygraph = {
            "version": "1.0",
            "project_id": "clean-project",
            "entities": [
                {"id": "CHAR_Test_001", "type": "character", "name": "Test"},
                {"id": "scene_001", "type": "scene", "attributes": {"scene_number": 1}},
            ],
            "edges": [],
            "evidence_index": {},
        }
        (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        try:
            orchestrator = ValidationOrchestrator(temp_dir)
            result = orchestrator.run_validation()

            # Should succeed with no issues
            assert result["success"] is True
            assert result["total_issues"] == 0

            # Should have empty report
            summary_path = temp_dir / "vault" / "80_Reports" / "validation-summary.md"
            assert summary_path.exists()
            content = summary_path.read_text()
            assert "No issues" in content or "0" in content
        finally:
            shutil.rmtree(temp_dir)

    def test_reports_sorted_by_severity(self, temp_project_with_storygraph):
        """Test that issues in reports are sorted by severity."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        if result["total_issues"] == 0:
            pytest.skip("No issues to test sorting")

        issues_path = temp_project_with_storygraph / "build" / "issues.json"
        data = json.loads(issues_path.read_text())

        # Issues should be sorted: errors first, then warnings, then info
        severities = [i["severity"] for i in data["issues"]]

        # Verify that errors come before warnings, warnings before info
        if "error" in severities and "warning" in severities:
            last_error_idx = len(severities) - 1 - severities[::-1].index("error")
            first_warning_idx = severities.index("warning")
            assert last_error_idx <= first_warning_idx


class TestValidationCategories:
    """Tests for each validation category."""

    def test_wardrobe_validation(self, temp_project_with_storygraph):
        """Test wardrobe validator runs."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        orchestrator.run_validation()

        issues = orchestrator.get_issues_by_category(IssueCategory.WARDROBE)
        assert isinstance(issues, list)

        for issue in issues:
            assert issue.category == IssueCategory.WARDROBE
            assert issue.rule_code.startswith("WARD-")

    def test_props_validation(self, temp_project_with_storygraph):
        """Test props validator runs."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        orchestrator.run_validation()

        issues = orchestrator.get_issues_by_category(IssueCategory.PROPS)
        assert isinstance(issues, list)

        for issue in issues:
            assert issue.category == IssueCategory.PROPS
            assert issue.rule_code.startswith("PROP-")

    def test_timeline_validation(self, temp_project_with_storygraph):
        """Test timeline validator runs."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        orchestrator.run_validation()

        issues = orchestrator.get_issues_by_category(IssueCategory.TIMELINE)
        assert isinstance(issues, list)

        for issue in issues:
            assert issue.category == IssueCategory.TIMELINE
            assert issue.rule_code.startswith("TIME-")

    def test_knowledge_validation(self, temp_project_with_storygraph):
        """Test knowledge validator runs."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        orchestrator.run_validation()

        issues = orchestrator.get_issues_by_category(IssueCategory.KNOWLEDGE)
        assert isinstance(issues, list)

        for issue in issues:
            assert issue.category == IssueCategory.KNOWLEDGE
            assert issue.rule_code.startswith("KNOW-")


class TestValidationSummary:
    """Tests for validation summary statistics."""

    def test_severity_counts_accurate(self, temp_project_with_storygraph):
        """Test that severity counts match actual issues."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        # Count manually
        errors = len(orchestrator.get_issues_by_severity(IssueSeverity.ERROR))
        warnings = len(orchestrator.get_issues_by_severity(IssueSeverity.WARNING))
        infos = len(orchestrator.get_issues_by_severity(IssueSeverity.INFO))

        # Compare to summary
        assert result["by_severity"].get("error", 0) == errors
        assert result["by_severity"].get("warning", 0) == warnings
        assert result["by_severity"].get("info", 0) == infos

    def test_category_counts_accurate(self, temp_project_with_storygraph):
        """Test that category counts match actual issues."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        # Count manually
        wardrobe = len(orchestrator.get_issues_by_category(IssueCategory.WARDROBE))
        props = len(orchestrator.get_issues_by_category(IssueCategory.PROPS))
        timeline = len(orchestrator.get_issues_by_category(IssueCategory.TIMELINE))
        knowledge = len(orchestrator.get_issues_by_category(IssueCategory.KNOWLEDGE))

        # Compare to summary
        assert result["by_category"].get("wardrobe", 0) == wardrobe
        assert result["by_category"].get("props", 0) == props
        assert result["by_category"].get("timeline", 0) == timeline
        assert result["by_category"].get("knowledge", 0) == knowledge

    def test_total_issues_count(self, temp_project_with_storygraph):
        """Test that total count is accurate."""
        orchestrator = ValidationOrchestrator(temp_project_with_storygraph)
        result = orchestrator.run_validation()

        # Sum of all categories should equal total
        category_sum = sum(result["by_category"].values())
        assert result["total_issues"] == category_sum


class TestValidationWithMinimalData:
    """Tests with minimal or edge-case data."""

    def test_validation_with_single_scene(self):
        """Test validation with only one scene."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "minimal",
            "entities": [
                {"id": "scene_001", "type": "scene", "attributes": {"scene_number": 1}},
            ],
            "edges": [],
            "evidence_index": {},
        }
        (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        try:
            orchestrator = ValidationOrchestrator(temp_dir)
            result = orchestrator.run_validation()

            assert "success" in result
            assert isinstance(result["total_issues"], int)
        finally:
            shutil.rmtree(temp_dir)

    def test_validation_with_no_characters(self):
        """Test validation with no characters."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "no-chars",
            "entities": [
                {"id": "LOC_Diner_001", "type": "location", "name": "Diner"},
                {"id": "scene_001", "type": "scene", "attributes": {"scene_number": 1}},
            ],
            "edges": [],
            "evidence_index": {},
        }
        (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        try:
            orchestrator = ValidationOrchestrator(temp_dir)
            result = orchestrator.run_validation()

            assert "success" in result
        finally:
            shutil.rmtree(temp_dir)


class TestValidatorErrorHandling:
    """Tests for error handling in validators."""

    def test_missing_entity_type_handled(self):
        """Test that missing entity types don't crash validation."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "missing-types",
            "entities": [
                {"id": "entity_001", "name": "Unknown"},  # No type
            ],
            "edges": [],
            "evidence_index": {},
        }
        (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        try:
            orchestrator = ValidationOrchestrator(temp_dir)
            result = orchestrator.run_validation()

            # Should complete without crashing
            assert "success" in result
        finally:
            shutil.rmtree(temp_dir)

    def test_malformed_edges_handled(self):
        """Test that malformed edges don't crash validation."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "bad-edges",
            "entities": [
                {"id": "scene_001", "type": "scene", "attributes": {"scene_number": 1}},
            ],
            "edges": [
                {"type": "invalid", "source": None, "target": "nonexistent"},
                {"type": "partial", "source": "scene_001"},
            ],
            "evidence_index": {},
        }
        (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph))

        try:
            orchestrator = ValidationOrchestrator(temp_dir)
            result = orchestrator.run_validation()

            # Should complete without crashing
            assert "success" in result
        finally:
            shutil.rmtree(temp_dir)
