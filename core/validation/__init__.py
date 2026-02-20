"""Validation module for story continuity checking.

Provides validators for checking wardrobe, props, timeline, and knowledge
continuity in screenplays.

Usage:
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
    )

    # Create a custom validator
    class MyValidator(BaseValidator):
        def validate(self) -> List[Issue]:
            # Implement validation logic
            return self._issues

    # Generate reports
    generator = ReportGenerator(vault_path)
    reports = generator.generate_reports(all_issues)
"""

from .base import (
    BaseValidator,
    Issue,
    IssueCategory,
    IssueSeverity,
)
from .report_generator import ReportGenerator
from .wardrobe_validator import WardrobeValidator
from .props_validator import PropsValidator
from .timeline_validator import TimelineValidator
from .knowledge_validator import KnowledgeValidator
from .orchestrator import ValidationOrchestrator, validate_project

__all__ = [
    # Issue data model
    "Issue",
    "IssueSeverity",
    "IssueCategory",
    # Base validator
    "BaseValidator",
    # Report generation
    "ReportGenerator",
    # Specialized validators
    "WardrobeValidator",
    "PropsValidator",
    "TimelineValidator",
    "KnowledgeValidator",
    # Orchestrator
    "ValidationOrchestrator",
    "validate_project",
]
