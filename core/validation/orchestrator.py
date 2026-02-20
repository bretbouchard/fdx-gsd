"""Validation orchestrator for coordinating all validators.

Runs all validators, collects issues, persists to JSON, and generates reports.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Issue, IssueCategory, IssueSeverity
from .wardrobe_validator import WardrobeValidator
from .props_validator import PropsValidator
from .timeline_validator import TimelineValidator
from .knowledge_validator import KnowledgeValidator
from .report_generator import ReportGenerator


class ValidationOrchestrator:
    """
    Coordinates all validators and aggregates results.

    Workflow:
    1. Run all validators
    2. Collect and re-number issues
    3. Persist to build/issues.json
    4. Generate markdown reports
    5. Return summary dict
    """

    def __init__(self, project_path: Path):
        """
        Initialize validation orchestrator.

        Args:
            project_path: Path to project root
        """
        self.project_path = Path(project_path)
        self.build_path = self.project_path / "build"
        self.vault_path = self.project_path / "vault"
        self.issues_path = self.build_path / "issues.json"

        # Initialize validators
        self.validators = [
            WardrobeValidator(self.build_path),
            PropsValidator(self.build_path),
            TimelineValidator(self.build_path),
            KnowledgeValidator(self.build_path),
        ]

        # Initialize report generator
        self.report_generator = ReportGenerator(self.vault_path)

        # Issue tracking
        self._all_issues: List[Issue] = []
        self._issue_counter = 0

    def run_validation(self) -> Dict[str, Any]:
        """
        Run all validators and return summary.

        Returns:
            Dict with success, total_issues, by_severity, by_category, reports
        """
        # Check prerequisites
        storygraph_path = self.build_path / "storygraph.json"
        if not storygraph_path.exists():
            return {
                "success": False,
                "error": "No storygraph.json found. Run 'gsd build canon' first.",
                "total_issues": 0,
            }

        # Clear previous issues
        self._all_issues = []
        self._issue_counter = 0

        # Run each validator
        for validator in self.validators:
            try:
                issues = validator.validate()
                # Re-number issues globally
                for issue in issues:
                    self._issue_counter += 1
                    # Update issue_id with global numbering
                    new_id = f"issue_{self._issue_counter:06d}"
                    # Create new issue with updated ID
                    issue.issue_id = new_id
                    self._all_issues.append(issue)
            except Exception as e:
                # Log error but continue with other validators
                print(f"Warning: {validator.__class__.__name__} failed: {e}")

        # Sort issues deterministically
        self._all_issues = self._sort_issues(self._all_issues)

        # Save issues to JSON
        self._save_issues()

        # Generate reports
        report_paths = self.report_generator.generate_reports(self._all_issues)

        # If no issues, generate empty report
        if not self._all_issues:
            self.report_generator.generate_empty_report()
            report_paths = {"summary": self.vault_path / "80_Reports" / "validation-summary.md"}

        # Build summary
        summary = self._get_summary()

        # Add report paths to summary
        summary["reports"] = {
            name: str(path.relative_to(self.project_path))
            for name, path in report_paths.items()
        }
        summary["issues_path"] = str(self.issues_path.relative_to(self.project_path))

        # Determine success (no errors)
        error_count = summary["by_severity"].get("error", 0)
        summary["success"] = error_count == 0

        return summary

    def _sort_issues(self, issues: List[Issue]) -> List[Issue]:
        """
        Sort issues deterministically.

        Order: severity (error first), then scene_number, then issue_id
        """
        severity_order = {
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 1,
            IssueSeverity.INFO: 2,
        }

        return sorted(
            issues,
            key=lambda i: (
                severity_order.get(i.severity, 99),
                i.scene_number or 9999,
                i.issue_id,
            ),
        )

    def _save_issues(self) -> None:
        """Persist issues to JSON file."""
        self.issues_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_issues": len(self._all_issues),
            "summary": self._get_summary(),
            "issues": [issue.to_dict() for issue in self._all_issues],
        }

        self.issues_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def _get_summary(self) -> Dict[str, Any]:
        """
        Build summary statistics.

        Returns:
            Dict with counts by severity, category, and auto_fixable
        """
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        auto_fixable = 0

        for issue in self._all_issues:
            # Count by severity
            sev_key = issue.severity.value
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1

            # Count by category
            cat_key = issue.category.value
            by_category[cat_key] = by_category.get(cat_key, 0) + 1

            # Count auto-fixable
            if issue.auto_fixable:
                auto_fixable += 1

        return {
            "total_issues": len(self._all_issues),
            "by_severity": by_severity,
            "by_category": by_category,
            "auto_fixable_count": auto_fixable,
        }

    def get_issues_by_category(self, category: IssueCategory) -> List[Issue]:
        """Get all issues of a specific category."""
        return [i for i in self._all_issues if i.category == category]

    def get_issues_by_severity(self, severity: IssueSeverity) -> List[Issue]:
        """Get all issues of a specific severity."""
        return [i for i in self._all_issues if i.severity == severity]

    def get_error_count(self) -> int:
        """Get count of error-severity issues."""
        return len(self.get_issues_by_severity(IssueSeverity.ERROR))

    def has_errors(self) -> bool:
        """Check if any errors exist."""
        return self.get_error_count() > 0


def validate_project(project_path: Path) -> Dict[str, Any]:
    """
    Convenience function to validate a project.

    Args:
        project_path: Path to project root

    Returns:
        Validation summary dict
    """
    orchestrator = ValidationOrchestrator(project_path)
    return orchestrator.run_validation()
