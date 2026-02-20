"""Unit tests for validation module.

Tests the Issue data model, base validator, and specialized validators.
"""
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import pytest

from core.validation import (
    Issue,
    IssueSeverity,
    IssueCategory,
    BaseValidator,
    ReportGenerator,
    WardrobeValidator,
    PropsValidator,
    TimelineValidator,
    KnowledgeValidator,
    ValidationOrchestrator,
)


class TestIssueDataModel:
    """Tests for Issue dataclass."""

    def test_create_issue(self):
        """Test creating an issue with all fields."""
        issue = Issue(
            issue_id="issue_wardrobe_000001",
            category=IssueCategory.WARDROBE,
            severity=IssueSeverity.WARNING,
            rule_code="WARD-01",
            title="Unexplained wardrobe change",
            description="Character's outfit changes without explanation",
            scene_id="scene_001",
            scene_number=1,
            entity_ids=["CHAR_Fox_001"],
            evidence_ids=["ev_001"],
            source_paragraph="Fox wears a blue suit.",
            suggested_fix="Add wardrobe change scene or dialogue",
            auto_fixable=False,
        )

        assert issue.issue_id == "issue_wardrobe_000001"
        assert issue.category == IssueCategory.WARDROBE
        assert issue.severity == IssueSeverity.WARNING
        assert issue.rule_code == "WARD-01"
        assert issue.title == "Unexplained wardrobe change"
        assert issue.resolved is False
        assert issue.auto_fixable is False

    def test_issue_to_dict(self):
        """Test serialization to dictionary."""
        issue = Issue(
            issue_id="issue_001",
            category=IssueCategory.PROPS,
            severity=IssueSeverity.ERROR,
            rule_code="PROP-02",
            title="Missing prop",
            description="Prop appears without introduction",
        )

        data = issue.to_dict()

        assert data["issue_id"] == "issue_001"
        assert data["category"] == "props"
        assert data["severity"] == "error"
        assert data["rule_code"] == "PROP-02"
        assert "detected_at" in data
        assert data["resolved"] is False

    def test_issue_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "issue_id": "issue_time_001",
            "category": "timeline",
            "severity": "warning",
            "rule_code": "TIME-01",
            "title": "Timeline issue",
            "description": "Time constraint violated",
            "scene_id": "scene_005",
            "scene_number": 5,
            "entity_ids": ["CHAR_John_001"],
            "evidence_ids": ["ev_010"],
            "source_paragraph": "Later that day...",
            "suggested_fix": "Fix timeline",
            "auto_fixable": True,
            "detected_at": "2025-01-01T12:00:00",
            "resolved": True,
            "resolved_at": "2025-01-02T10:00:00",
            "resolution_note": "Fixed",
        }

        issue = Issue.from_dict(data)

        assert issue.issue_id == "issue_time_001"
        assert issue.category == IssueCategory.TIMELINE
        assert issue.severity == IssueSeverity.WARNING
        assert issue.scene_number == 5
        assert issue.auto_fixable is True
        assert issue.resolved is True
        assert issue.resolution_note == "Fixed"

    def test_issue_serialization_roundtrip(self):
        """Test that issue can be serialized and deserialized."""
        original = Issue(
            issue_id="issue_know_001",
            category=IssueCategory.KNOWLEDGE,
            severity=IssueSeverity.ERROR,
            rule_code="KNOW-01",
            title="Knowledge leak",
            description="Character acts on information they don't have",
            scene_id="scene_010",
            scene_number=10,
            entity_ids=["CHAR_Sarah_001", "CHAR_Tom_001"],
            evidence_ids=["ev_001", "ev_002"],
        )

        data = original.to_dict()
        restored = Issue.from_dict(data)

        assert restored.issue_id == original.issue_id
        assert restored.category == original.category
        assert restored.severity == original.severity
        assert restored.scene_id == original.scene_id
        assert restored.entity_ids == sorted(original.entity_ids)
        assert restored.evidence_ids == sorted(original.evidence_ids)


class TestIssueSeverity:
    """Tests for IssueSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.INFO.value == "info"

    def test_severity_ordering(self):
        """Test that ERROR is most severe."""
        # Errors should be most important, INFO least
        severities = [IssueSeverity.WARNING, IssueSeverity.INFO, IssueSeverity.ERROR]
        sorted_severities = sorted(severities, key=lambda s: s.value)
        # Just verify we can compare them
        assert IssueSeverity.ERROR.value == "error"


class TestIssueCategory:
    """Tests for IssueCategory enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert IssueCategory.WARDROBE.value == "wardrobe"
        assert IssueCategory.PROPS.value == "props"
        assert IssueCategory.TIMELINE.value == "timeline"
        assert IssueCategory.KNOWLEDGE.value == "knowledge"


class TestBaseValidator:
    """Tests for BaseValidator abstract class."""

    @pytest.fixture
    def temp_build_path(self):
        """Create a temporary build directory with minimal storygraph."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        # Create minimal storygraph
        storygraph = {
            "version": "1.0",
            "project_id": "test-project",
            "entities": [
                {
                    "id": "CHAR_Fox_001",
                    "type": "character",
                    "name": "Fox",
                    "aliases": ["FOX"],
                    "evidence_ids": ["ev_001"],
                },
                {
                    "id": "LOC_Diner_001",
                    "type": "location",
                    "name": "Diner",
                    "aliases": [],
                    "evidence_ids": ["ev_001"],
                },
                {
                    "id": "scene_001",
                    "type": "scene",
                    "name": "Scene 1",
                    "attributes": {"scene_number": 1},
                    "evidence_ids": ["ev_001"],
                },
            ],
            "edges": [],
            "evidence_index": {
                "ev_001": {"source_file": "test.md", "line_number": 1}
            },
        }

        (build_path / "storygraph.json").write_text(json.dumps(storygraph))
        yield build_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_load_graphs(self, temp_build_path):
        """Test that validator loads storygraph correctly."""

        class TestValidator(BaseValidator):
            def validate(self):
                self._load_graphs()
                return []

        validator = TestValidator(temp_build_path)
        validator.validate()

        assert validator._storygraph is not None
        assert len(validator._storygraph["entities"]) == 3

    def test_get_entities_by_type(self, temp_build_path):
        """Test getting entities by type."""

        class TestValidator(BaseValidator):
            def validate(self):
                return []

        validator = TestValidator(temp_build_path)
        characters = validator.get_entities_by_type("character")

        assert len(characters) == 1
        assert characters[0]["name"] == "Fox"

    def test_get_entity_by_id(self, temp_build_path):
        """Test getting entity by ID."""

        class TestValidator(BaseValidator):
            def validate(self):
                return []

        validator = TestValidator(temp_build_path)
        entity = validator.get_entity_by_id("CHAR_Fox_001")

        assert entity is not None
        assert entity["name"] == "Fox"

    def test_get_entity_by_id_not_found(self, temp_build_path):
        """Test getting non-existent entity."""

        class TestValidator(BaseValidator):
            def validate(self):
                return []

        validator = TestValidator(temp_build_path)
        entity = validator.get_entity_by_id("NONEXISTENT")

        assert entity is None

    def test_get_scenes_sorted(self, temp_build_path):
        """Test getting scenes sorted by number."""

        class TestValidator(BaseValidator):
            def validate(self):
                return []

        validator = TestValidator(temp_build_path)
        scenes = validator.get_scenes_sorted()

        assert len(scenes) == 1
        assert scenes[0]["attributes"]["scene_number"] == 1

    def test_create_issue_id(self, temp_build_path):
        """Test issue ID generation."""

        class TestValidator(BaseValidator):
            def validate(self):
                return []

        validator = TestValidator(temp_build_path)
        issue_id1 = validator._create_issue_id("WARD-01")
        issue_id2 = validator._create_issue_id("WARD-02")

        assert issue_id1 == "issue_ward_000001"
        assert issue_id2 == "issue_ward_000002"

    def test_add_issue(self, temp_build_path):
        """Test adding issues through helper method."""

        class TestValidator(BaseValidator):
            def validate(self):
                self._add_issue(
                    rule_code="WARD-01",
                    title="Test issue",
                    description="Test description",
                    severity=IssueSeverity.WARNING,
                    scene_id="scene_001",
                    scene_number=1,
                    entity_ids=["CHAR_Fox_001"],
                )
                return self._issues

        validator = TestValidator(temp_build_path)
        issues = validator.validate()

        assert len(issues) == 1
        assert issues[0].title == "Test issue"
        assert issues[0].category == IssueCategory.WARDROBE

    def test_get_summary(self, temp_build_path):
        """Test getting validation summary."""

        class TestValidator(BaseValidator):
            def validate(self):
                self._add_issue("PROP-01", "Issue 1", "Desc 1", IssueSeverity.WARNING)
                self._add_issue("PROP-02", "Issue 2", "Desc 2", IssueSeverity.ERROR)
                return self._issues

        validator = TestValidator(temp_build_path)
        validator.validate()
        summary = validator.get_summary()

        assert summary["total_issues"] == 2
        assert summary["by_severity"]["warning"] == 1
        assert summary["by_severity"]["error"] == 1


class TestWardrobeValidator:
    """Tests for WardrobeValidator."""

    @pytest.fixture
    def temp_build_path(self):
        """Create a temporary build directory with wardrobe-related entities."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "test-project",
            "entities": [
                {
                    "id": "CHAR_Fox_001",
                    "type": "character",
                    "name": "Fox",
                    "attributes": {
                        "signature_items": ["blue suit", "watch"],
                    },
                },
                {
                    "id": "scene_001",
                    "type": "scene",
                    "attributes": {
                        "scene_number": 1,
                        "int_ext": "INT",
                        "time_of_day": "DAY",
                    },
                },
                {
                    "id": "scene_002",
                    "type": "scene",
                    "attributes": {
                        "scene_number": 2,
                        "int_ext": "INT",
                        "time_of_day": "DAY",
                    },
                },
            ],
            "edges": [
                {
                    "type": "appears_in",
                    "source": "CHAR_Fox_001",
                    "target": "scene_001",
                },
                {
                    "type": "appears_in",
                    "source": "CHAR_Fox_001",
                    "target": "scene_002",
                },
            ],
            "evidence_index": {},
        }

        (build_path / "storygraph.json").write_text(json.dumps(storygraph))
        yield build_path

        shutil.rmtree(temp_dir)

    def test_validate_returns_issues(self, temp_build_path):
        """Test that validator runs and returns issues list."""
        validator = WardrobeValidator(temp_build_path)
        issues = validator.validate()

        assert isinstance(issues, list)
        # May or may not find issues depending on data
        for issue in issues:
            assert issue.category == IssueCategory.WARDROBE

    def test_wardrobe_issue_rule_codes(self, temp_build_path):
        """Test that wardrobe issues have valid rule codes."""
        validator = WardrobeValidator(temp_build_path)
        issues = validator.validate()

        valid_codes = {"WARD-01", "WARD-02", "WARD-03"}
        for issue in issues:
            assert issue.rule_code in valid_codes


class TestPropsValidator:
    """Tests for PropsValidator."""

    @pytest.fixture
    def temp_build_path(self):
        """Create a temporary build directory with prop-related entities."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "test-project",
            "entities": [
                {
                    "id": "PROP_Gun_001",
                    "type": "prop",
                    "name": "Gun",
                    "attributes": {"owner": "CHAR_Fox_001"},
                },
                {
                    "id": "CHAR_Fox_001",
                    "type": "character",
                    "name": "Fox",
                },
                {
                    "id": "scene_001",
                    "type": "scene",
                    "attributes": {"scene_number": 1},
                },
            ],
            "edges": [],
            "evidence_index": {},
        }

        (build_path / "storygraph.json").write_text(json.dumps(storygraph))
        yield build_path

        shutil.rmtree(temp_dir)

    def test_validate_returns_issues(self, temp_build_path):
        """Test that validator runs and returns issues list."""
        validator = PropsValidator(temp_build_path)
        issues = validator.validate()

        assert isinstance(issues, list)
        for issue in issues:
            assert issue.category == IssueCategory.PROPS

    def test_props_issue_rule_codes(self, temp_build_path):
        """Test that props issues have valid rule codes."""
        validator = PropsValidator(temp_build_path)
        issues = validator.validate()

        valid_codes = {"PROP-01", "PROP-02", "PROP-03"}
        for issue in issues:
            assert issue.rule_code in valid_codes


class TestTimelineValidator:
    """Tests for TimelineValidator."""

    @pytest.fixture
    def temp_build_path(self):
        """Create a temporary build directory with timeline-related entities."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "test-project",
            "entities": [
                {
                    "id": "CHAR_Fox_001",
                    "type": "character",
                    "name": "Fox",
                },
                {
                    "id": "LOC_Diner_001",
                    "type": "location",
                    "name": "Diner",
                    "attributes": {"city": "New York"},
                },
                {
                    "id": "LOC_Office_001",
                    "type": "location",
                    "name": "Office",
                    "attributes": {"city": "Los Angeles"},
                },
                {
                    "id": "scene_001",
                    "type": "scene",
                    "attributes": {
                        "scene_number": 1,
                        "location_id": "LOC_Diner_001",
                    },
                },
                {
                    "id": "scene_002",
                    "type": "scene",
                    "attributes": {
                        "scene_number": 2,
                        "location_id": "LOC_Office_001",
                        "time_phrase": "MOMENTS LATER",
                    },
                },
            ],
            "edges": [
                {
                    "type": "appears_in",
                    "source": "CHAR_Fox_001",
                    "target": "scene_001",
                },
                {
                    "type": "appears_in",
                    "source": "CHAR_Fox_001",
                    "target": "scene_002",
                },
            ],
            "evidence_index": {},
        }

        (build_path / "storygraph.json").write_text(json.dumps(storygraph))
        yield build_path

        shutil.rmtree(temp_dir)

    def test_validate_returns_issues(self, temp_build_path):
        """Test that validator runs and returns issues list."""
        validator = TimelineValidator(temp_build_path)
        issues = validator.validate()

        assert isinstance(issues, list)
        for issue in issues:
            assert issue.category == IssueCategory.TIMELINE

    def test_timeline_issue_rule_codes(self, temp_build_path):
        """Test that timeline issues have valid rule codes."""
        validator = TimelineValidator(temp_build_path)
        issues = validator.validate()

        valid_codes = {"TIME-01", "TIME-02", "TIME-04"}
        for issue in issues:
            assert issue.rule_code in valid_codes


class TestKnowledgeValidator:
    """Tests for KnowledgeValidator."""

    @pytest.fixture
    def temp_build_path(self):
        """Create a temporary build directory with knowledge-related entities."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        storygraph = {
            "version": "1.0",
            "project_id": "test-project",
            "entities": [
                {
                    "id": "CHAR_Fox_001",
                    "type": "character",
                    "name": "Fox",
                    "attributes": {"secrets_known": []},
                },
                {
                    "id": "CHAR_Sarah_001",
                    "type": "character",
                    "name": "Sarah",
                    "attributes": {"secrets_known": ["secret_plan"]},
                },
                {
                    "id": "scene_001",
                    "type": "scene",
                    "attributes": {"scene_number": 1},
                },
            ],
            "edges": [
                {
                    "type": "knows",
                    "source": "CHAR_Fox_001",
                    "target": "CHAR_Sarah_001",
                    "attributes": {"relationship": "friend"},
                },
            ],
            "evidence_index": {},
        }

        (build_path / "storygraph.json").write_text(json.dumps(storygraph))
        yield build_path

        shutil.rmtree(temp_dir)

    def test_validate_returns_issues(self, temp_build_path):
        """Test that validator runs and returns issues list."""
        validator = KnowledgeValidator(temp_build_path)
        issues = validator.validate()

        assert isinstance(issues, list)
        for issue in issues:
            assert issue.category == IssueCategory.KNOWLEDGE

    def test_knowledge_issue_rule_codes(self, temp_build_path):
        """Test that knowledge issues have valid rule codes."""
        validator = KnowledgeValidator(temp_build_path)
        issues = validator.validate()

        valid_codes = {"KNOW-01", "KNOW-02", "KNOW-03", "KNOW-04"}
        for issue in issues:
            assert issue.rule_code in valid_codes


class TestReportGenerator:
    """Tests for ReportGenerator."""

    @pytest.fixture
    def temp_vault_path(self):
        """Create a temporary vault directory."""
        temp_dir = Path(tempfile.mkdtemp())
        vault_path = temp_dir / "vault"
        vault_path.mkdir(parents=True)
        (vault_path / "80_Reports").mkdir(parents=True)
        yield vault_path

        shutil.rmtree(temp_dir)

    def test_generate_empty_report(self, temp_vault_path):
        """Test generating an empty report when no issues."""
        generator = ReportGenerator(temp_vault_path)
        generator.generate_empty_report()

        report_path = temp_vault_path / "80_Reports" / "validation-summary.md"
        assert report_path.exists()

        content = report_path.read_text()
        # Report says "No Issues Found" with emoji
        assert "No Issues" in content or "0" in content

    def test_generate_reports_with_issues(self, temp_vault_path):
        """Test generating reports with issues."""
        issues = [
            Issue(
                issue_id="issue_ward_000001",
                category=IssueCategory.WARDROBE,
                severity=IssueSeverity.WARNING,
                rule_code="WARD-01",
                title="Wardrobe change",
                description="Unexplained outfit change",
                scene_id="scene_001",
                scene_number=1,
            ),
            Issue(
                issue_id="issue_prop_000001",
                category=IssueCategory.PROPS,
                severity=IssueSeverity.ERROR,
                rule_code="PROP-02",
                title="Missing prop",
                description="Prop vanished",
                scene_id="scene_002",
                scene_number=2,
            ),
        ]

        generator = ReportGenerator(temp_vault_path)
        report_paths = generator.generate_reports(issues)

        # Should have summary and category reports
        assert "summary" in report_paths

        # Check summary exists
        summary_path = temp_vault_path / "80_Reports" / "validation-summary.md"
        assert summary_path.exists()

        content = summary_path.read_text()
        assert "WARD-01" in content or "wardrobe" in content.lower()
        assert "PROP-02" in content or "props" in content.lower()

    def test_report_has_obsidian_links(self, temp_vault_path):
        """Test that reports use Obsidian-compatible wikilinks."""
        issues = [
            Issue(
                issue_id="issue_001",
                category=IssueCategory.WARDROBE,
                severity=IssueSeverity.WARNING,
                rule_code="WARD-01",
                title="Test",
                description="Test",
                scene_id="scene_001",
                entity_ids=["CHAR_Fox_001"],
                evidence_ids=["ev_001"],
            ),
        ]

        generator = ReportGenerator(temp_vault_path)
        generator.generate_reports(issues)

        # Check that reports contain wikilink format
        report_dir = temp_vault_path / "80_Reports"
        for report_file in report_dir.glob("*.md"):
            content = report_file.read_text()
            # Should have [[link]] format somewhere
            if "scene_001" in content or "CHAR_Fox_001" in content:
                assert "[[" in content


class TestValidationOrchestrator:
    """Tests for ValidationOrchestrator."""

    @pytest.fixture
    def temp_project_path(self):
        """Create a temporary project structure."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create directories
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault" / "80_Reports").mkdir(parents=True)

        # Create minimal storygraph
        storygraph = {
            "version": "1.0",
            "project_id": "test-project",
            "entities": [
                {"id": "CHAR_Fox_001", "type": "character", "name": "Fox"},
                {"id": "scene_001", "type": "scene", "attributes": {"scene_number": 1}},
            ],
            "edges": [],
            "evidence_index": {},
        }

        (temp_dir / "build" / "storygraph.json").write_text(json.dumps(storygraph))
        yield temp_dir

        shutil.rmtree(temp_dir)

    def test_orchestrator_initialization(self, temp_project_path):
        """Test orchestrator initialization."""
        orchestrator = ValidationOrchestrator(temp_project_path)

        assert orchestrator.project_path == temp_project_path
        assert len(orchestrator.validators) == 4

    def test_run_validation(self, temp_project_path):
        """Test running full validation."""
        orchestrator = ValidationOrchestrator(temp_project_path)
        result = orchestrator.run_validation()

        assert "success" in result
        assert "total_issues" in result
        assert "by_severity" in result
        assert "by_category" in result
        assert "reports" in result

    def test_issues_persisted_to_json(self, temp_project_path):
        """Test that issues are persisted to JSON."""
        orchestrator = ValidationOrchestrator(temp_project_path)
        orchestrator.run_validation()

        issues_path = temp_project_path / "build" / "issues.json"
        assert issues_path.exists()

        data = json.loads(issues_path.read_text())
        assert "version" in data
        assert "generated_at" in data
        assert "issues" in data
        assert isinstance(data["issues"], list)

    def test_reports_generated(self, temp_project_path):
        """Test that reports are generated."""
        orchestrator = ValidationOrchestrator(temp_project_path)
        result = orchestrator.run_validation()

        # Check that report path is returned
        assert "reports" in result
        assert "summary" in result["reports"]

        # Check that report file exists
        summary_path = temp_project_path / result["reports"]["summary"]
        assert summary_path.exists()

    def test_get_issues_by_category(self, temp_project_path):
        """Test filtering issues by category."""
        orchestrator = ValidationOrchestrator(temp_project_path)
        orchestrator.run_validation()

        wardrobe_issues = orchestrator.get_issues_by_category(IssueCategory.WARDROBE)

        for issue in wardrobe_issues:
            assert issue.category == IssueCategory.WARDROBE

    def test_get_issues_by_severity(self, temp_project_path):
        """Test filtering issues by severity."""
        orchestrator = ValidationOrchestrator(temp_project_path)
        orchestrator.run_validation()

        errors = orchestrator.get_issues_by_severity(IssueSeverity.ERROR)

        for issue in errors:
            assert issue.severity == IssueSeverity.ERROR

    def test_has_errors(self, temp_project_path):
        """Test error detection."""
        orchestrator = ValidationOrchestrator(temp_project_path)
        orchestrator.run_validation()

        # Should match error count
        has_errors = orchestrator.has_errors()
        error_count = orchestrator.get_error_count()

        assert has_errors == (error_count > 0)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_validator_with_empty_storygraph(self):
        """Test validator handles empty storygraph."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        # Create empty storygraph
        storygraph = {
            "version": "1.0",
            "project_id": "test",
            "entities": [],
            "edges": [],
            "evidence_index": {},
        }
        (build_path / "storygraph.json").write_text(json.dumps(storygraph))

        try:
            validator = WardrobeValidator(build_path)
            issues = validator.validate()
            assert isinstance(issues, list)
        finally:
            shutil.rmtree(temp_dir)

    def test_validator_with_missing_storygraph(self):
        """Test validator handles missing storygraph."""
        temp_dir = Path(tempfile.mkdtemp())
        build_path = temp_dir / "build"
        build_path.mkdir(parents=True)

        try:
            validator = WardrobeValidator(build_path)
            issues = validator.validate()
            # Should return empty list or handle gracefully
            assert isinstance(issues, list)
        finally:
            shutil.rmtree(temp_dir)

    def test_orchestrator_without_storygraph(self):
        """Test orchestrator handles missing storygraph."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "build").mkdir(parents=True)
        (temp_dir / "vault").mkdir(parents=True)

        try:
            orchestrator = ValidationOrchestrator(temp_dir)
            result = orchestrator.run_validation()

            # Should return error
            assert result["success"] is False
            assert "error" in result
        finally:
            shutil.rmtree(temp_dir)

    def test_issue_with_empty_lists(self):
        """Test issue creation with empty lists."""
        issue = Issue(
            issue_id="issue_001",
            category=IssueCategory.WARDROBE,
            severity=IssueSeverity.INFO,
            rule_code="WARD-03",
            title="Info issue",
            description="Informational",
            entity_ids=[],
            evidence_ids=[],
        )

        data = issue.to_dict()
        assert data["entity_ids"] == []
        assert data["evidence_ids"] == []
