"""Report generator for validation issues.

Creates Obsidian-compatible markdown reports in vault/80_Reports/
with wikilinks to scenes, entities, and evidence.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Issue, IssueCategory, IssueSeverity


class ReportGenerator:
    """
    Generates Obsidian-compatible markdown reports for validation issues.

    Creates:
    - validation-summary.md: Overview of all issues
    - {category}-issues.md: Detailed category-specific reports
    """

    def __init__(self, vault_path: Path):
        """
        Initialize the report generator.

        Args:
            vault_path: Path to the vault directory
        """
        self.vault_path = Path(vault_path)
        self.reports_path = self.vault_path / "80_Reports"
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def generate_reports(self, all_issues: List[Issue]) -> Dict[str, Path]:
        """
        Generate all validation reports.

        Args:
            all_issues: List of all detected issues

        Returns:
            Dict mapping report names to their file paths
        """
        reports = {}

        # Generate summary report
        summary_path = self._generate_summary_report(all_issues)
        reports["summary"] = summary_path

        # Generate category-specific reports
        for category in IssueCategory:
            category_issues = [i for i in all_issues if i.category == category]
            if category_issues:
                category_path = self._generate_category_report(category, category_issues)
                reports[category.value] = category_path

        return reports

    def _generate_summary_report(self, all_issues: List[Issue]) -> Path:
        """
        Generate the main validation summary report.

        Args:
            all_issues: List of all detected issues

        Returns:
            Path to the generated report
        """
        report_path = self.reports_path / "validation-summary.md"

        # Calculate statistics
        total = len(all_issues)
        severity_counts = self._count_by_severity(all_issues)
        category_counts = self._count_by_category(all_issues)
        auto_fixable = sum(1 for i in all_issues if i.auto_fixable)

        # Get errors (most critical)
        errors = [i for i in all_issues if i.severity == IssueSeverity.ERROR]

        # Build report content
        lines = [
            "# Validation Summary",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Overview",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| **Total Issues** | {total} |",
            f"| ❌ Errors | {severity_counts.get('error', 0)} |",
            f"| ⚠️ Warnings | {severity_counts.get('warning', 0)} |",
            f"| ℹ️ Info | {severity_counts.get('info', 0)} |",
            f"| 🔧 Auto-fixable | {auto_fixable} |",
            "",
            "---",
            "",
            "## Issues by Category",
            "",
            "| Category | Count | Report |",
            "|----------|-------|--------|",
        ]

        for category in IssueCategory:
            count = category_counts.get(category.value, 0)
            if count > 0:
                report_link = f"[[{category.value}-issues|View Details]]"
                lines.append(f"| {category.value.title()} | {count} | {report_link} |")

        if not category_counts:
            lines.append("| (none) | 0 | - |")

        # Add critical errors section
        if errors:
            lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## ❌ Critical Issues (Errors)",
                    "",
                    "The following issues must be fixed before production:",
                    "",
                ]
            )

            # Group by scene
            errors_by_scene = self._group_by_scene(errors)
            for scene_num in sorted(errors_by_scene.keys()):
                lines.append(f"### Scene {scene_num or 'Unknown'}")
                lines.append("")
                for issue in errors_by_scene[scene_num]:
                    lines.append(self._format_issue_brief(issue))
                lines.append("")

        # Add link to detailed reports
        lines.extend(
            [
                "---",
                "",
                "## Detailed Reports",
                "",
                "See category-specific reports for full details:",
                "",
            ]
        )

        for category in IssueCategory:
            cat_issues = [i for i in all_issues if i.category == category]
            if cat_issues:
                lines.append(f"- [[{category.value}-issues|{category.value.title()} Issues]] ({len(cat_issues)})")

        # Write report
        report_path.write_text("\n".join(lines))
        return report_path

    def _generate_category_report(
        self, category: IssueCategory, issues: List[Issue]
    ) -> Path:
        """
        Generate a detailed category-specific report.

        Args:
            category: The issue category
            issues: List of issues in this category

        Returns:
            Path to the generated report
        """
        report_path = self.reports_path / f"{category.value}-issues.md"

        # Build report content
        lines = [
            f"# {category.value.title()} Issues",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Total Issues:** {len(issues)}",
            "",
            "---",
            "",
        ]

        # Group by scene
        issues_by_scene = self._group_by_scene(issues)

        for scene_num in sorted(issues_by_scene.keys()):
            if scene_num is not None:
                lines.append(f"## Scene {scene_num}")
            else:
                lines.append("## Unspecified Scene")
            lines.append("")

            for issue in issues_by_scene[scene_num]:
                lines.extend(self._format_issue_detailed(issue))
                lines.append("")

        # Write report
        report_path.write_text("\n".join(lines))
        return report_path

    def _format_issue_brief(self, issue: Issue) -> str:
        """
        Format a brief one-line issue description.

        Args:
            issue: The issue to format

        Returns:
            Formatted string
        """
        severity_emoji = self._get_severity_emoji(issue.severity)
        scene_link = f"[[{issue.scene_id}]]" if issue.scene_id else ""
        return f"- {severity_emoji} **{issue.rule_code}**: {issue.title} {scene_link}"

    def _format_issue_detailed(self, issue: Issue) -> List[str]:
        """
        Format a detailed issue entry.

        Args:
            issue: The issue to format

        Returns:
            List of formatted lines
        """
        severity_emoji = self._get_severity_emoji(issue.severity)
        lines = [
            f"### {severity_emoji} {issue.rule_code}: {issue.title}",
            "",
            f"**Severity:** {issue.severity.value.upper()}",
            "",
            f"{issue.description}",
            "",
        ]

        # Add scene link
        if issue.scene_id:
            lines.append(f"**Scene:** [[{issue.scene_id}]]")
            lines.append("")

        # Add entity links
        if issue.entity_ids:
            entity_links = ", ".join(f"[[{eid}]]" for eid in issue.entity_ids)
            lines.append(f"**Entities:** {entity_links}")
            lines.append("")

        # Add evidence links
        if issue.evidence_ids:
            evidence_links = ", ".join(
                f"[[inbox/note.md#^{eid}]]" for eid in issue.evidence_ids[:3]
            )
            if len(issue.evidence_ids) > 3:
                evidence_links += f" (+{len(issue.evidence_ids) - 3} more)"
            lines.append(f"**Evidence:** {evidence_links}")
            lines.append("")

        # Add source paragraph
        if issue.source_paragraph:
            lines.extend(
                [
                    "**Source:**",
                    f"> {issue.source_paragraph[:200]}{'...' if len(issue.source_paragraph) > 200 else ''}",
                    "",
                ]
            )

        # Add suggested fix
        if issue.suggested_fix:
            lines.extend(
                [
                    "**💡 Suggested Fix:**",
                    f"{issue.suggested_fix}",
                    "",
                ]
            )

        # Add auto-fixable indicator
        if issue.auto_fixable:
            lines.append("*🔧 This issue can be auto-fixed*")
            lines.append("")

        return lines

    def _get_severity_emoji(self, severity: IssueSeverity) -> str:
        """Get emoji for severity level."""
        emoji_map = {
            IssueSeverity.ERROR: "❌",
            IssueSeverity.WARNING: "⚠️",
            IssueSeverity.INFO: "ℹ️",
        }
        return emoji_map.get(severity, "❓")

    def _count_by_severity(self, issues: List[Issue]) -> Dict[str, int]:
        """Count issues by severity."""
        counts: Dict[str, int] = {}
        for issue in issues:
            key = issue.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_category(self, issues: List[Issue]) -> Dict[str, int]:
        """Count issues by category."""
        counts: Dict[str, int] = {}
        for issue in issues:
            key = issue.category.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _group_by_scene(self, issues: List[Issue]) -> Dict[Optional[int], List[Issue]]:
        """Group issues by scene number."""
        groups: Dict[Optional[int], List[Issue]] = {}
        for issue in issues:
            scene_num = issue.scene_number
            if scene_num not in groups:
                groups[scene_num] = []
            groups[scene_num].append(issue)
        return groups

    def generate_empty_report(self) -> Path:
        """
        Generate an empty validation report when no issues are found.

        Returns:
            Path to the generated report
        """
        report_path = self.reports_path / "validation-summary.md"

        lines = [
            "# Validation Summary",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## ✅ No Issues Found",
            "",
            "All validation checks passed. Your story continuity looks good!",
            "",
            "---",
            "",
            "## Statistics",
            "",
            "| Metric | Count |",
            "|--------|-------|",
            "| Total Issues | 0 |",
            "| Errors | 0 |",
            "| Warnings | 0 |",
            "| Info | 0 |",
        ]

        report_path.write_text("\n".join(lines))
        return report_path
