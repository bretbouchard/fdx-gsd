"""Base validation module for story continuity checking.

Provides the Issue data model, severity classification, and BaseValidator
abstract class that all specialized validators extend.

This follows the ConflictResolver pattern from Phase 3:
- IssueSeverity maps to ConflictTier
- Issue dataclass mirrors Conflict dataclass
- BaseValidator follows CanonBuilder patterns
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import json


class IssueSeverity(Enum):
    """Severity level for validation issues.

    Maps to ConflictTier from Phase 3:
    - ERROR -> CRITICAL (must fix)
    - WARNING -> AMBIGUOUS (should review)
    - INFO -> SAFE (FYI only)
    """

    ERROR = "error"  # Must fix before production
    WARNING = "warning"  # Should review
    INFO = "info"  # Informational only


class IssueCategory(Enum):
    """Category of validation issue."""

    WARDROBE = "wardrobe"  # Costume/wardrobe continuity
    PROPS = "props"  # Prop consistency
    TIMELINE = "timeline"  # Temporal/logistics issues
    KNOWLEDGE = "knowledge"  # Information flow issues


@dataclass
class Issue:
    """
    Represents a detected validation issue in the story.

    Tracks the rule violated, severity, location, and suggested fix.
    Mirrors the Conflict dataclass pattern from Phase 3.
    """

    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    rule_code: str  # e.g., "WARD-01", "PROP-02"
    title: str
    description: str
    scene_id: Optional[str] = None
    scene_number: Optional[int] = None
    entity_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    source_paragraph: Optional[str] = None
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "issue_id": self.issue_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "rule_code": self.rule_code,
            "title": self.title,
            "description": self.description,
            "scene_id": self.scene_id,
            "scene_number": self.scene_number,
            "entity_ids": sorted(self.entity_ids) if self.entity_ids else [],
            "evidence_ids": sorted(self.evidence_ids) if self.evidence_ids else [],
            "source_paragraph": self.source_paragraph,
            "suggested_fix": self.suggested_fix,
            "auto_fixable": self.auto_fixable,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Issue":
        """Create from dictionary."""
        return cls(
            issue_id=data["issue_id"],
            category=IssueCategory(data["category"]),
            severity=IssueSeverity(data["severity"]),
            rule_code=data["rule_code"],
            title=data["title"],
            description=data["description"],
            scene_id=data.get("scene_id"),
            scene_number=data.get("scene_number"),
            entity_ids=data.get("entity_ids", []),
            evidence_ids=data.get("evidence_ids", []),
            source_paragraph=data.get("source_paragraph"),
            suggested_fix=data.get("suggested_fix"),
            auto_fixable=data.get("auto_fixable", False),
            detected_at=(
                datetime.fromisoformat(data["detected_at"])
                if data.get("detected_at")
                else datetime.now()
            ),
            resolved=data.get("resolved", False),
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"])
                if data.get("resolved_at")
                else None
            ),
            resolution_note=data.get("resolution_note"),
        )


class BaseValidator(ABC):
    """
    Abstract base class for all validators.

    Follows the CanonBuilder pattern with:
    - _load_graphs() for loading storygraph.json and scriptgraph.json
    - validate() abstract method for subclass implementation
    - get_issues() and get_summary() for results
    """

    def __init__(self, build_path: Path):
        """
        Initialize the validator.

        Args:
            build_path: Path to the build directory containing storygraph.json
        """
        self.build_path = Path(build_path)
        self._issues: List[Issue] = []
        self._storygraph: Optional[Dict[str, Any]] = None
        self._scriptgraph: Optional[Dict[str, Any]] = None
        self._issue_counter = 0

    def _load_graphs(self) -> None:
        """Load storygraph.json and scriptgraph.json from build directory."""
        # Load storygraph
        storygraph_path = self.build_path / "storygraph.json"
        if storygraph_path.exists():
            self._storygraph = json.loads(storygraph_path.read_text())
        else:
            self._storygraph = {"entities": [], "edges": [], "evidence_index": {}}

        # Load scriptgraph (optional)
        scriptgraph_path = self.build_path / "scriptgraph.json"
        if scriptgraph_path.exists():
            self._scriptgraph = json.loads(scriptgraph_path.read_text())
        else:
            self._scriptgraph = None

    def _create_issue_id(self, rule_code: str) -> str:
        """
        Generate a unique issue ID.

        Args:
            rule_code: The rule code (e.g., "WARD-01")

        Returns:
            Unique issue ID like "issue_wardrobe_000001"
        """
        self._issue_counter += 1
        # Extract category prefix from rule code
        prefix = rule_code.split("-")[0].lower()
        return f"issue_{prefix}_{self._issue_counter:06d}"

    def _add_issue(
        self,
        rule_code: str,
        title: str,
        description: str,
        severity: IssueSeverity = IssueSeverity.WARNING,
        scene_id: Optional[str] = None,
        scene_number: Optional[int] = None,
        entity_ids: Optional[List[str]] = None,
        evidence_ids: Optional[List[str]] = None,
        source_paragraph: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        auto_fixable: bool = False,
    ) -> Issue:
        """
        Create and add an issue to the issues list.

        Args:
            rule_code: Rule code (e.g., "WARD-01")
            title: Short title for the issue
            description: Detailed description
            severity: Issue severity (default: WARNING)
            scene_id: Scene identifier
            scene_number: Scene sequence number
            entity_ids: Related entity IDs
            evidence_ids: Related evidence IDs
            source_paragraph: Source text that triggered the issue
            suggested_fix: Suggested fix for the issue
            auto_fixable: Whether this can be auto-fixed

        Returns:
            The created Issue object
        """
        # Determine category from rule code
        category_prefix = rule_code.split("-")[0].upper()
        category_map = {
            "WARD": IssueCategory.WARDROBE,
            "PROP": IssueCategory.PROPS,
            "TIME": IssueCategory.TIMELINE,
            "KNOW": IssueCategory.KNOWLEDGE,
        }
        category = category_map.get(category_prefix, IssueCategory.TIMELINE)

        issue = Issue(
            issue_id=self._create_issue_id(rule_code),
            category=category,
            severity=severity,
            rule_code=rule_code,
            title=title,
            description=description,
            scene_id=scene_id,
            scene_number=scene_number,
            entity_ids=entity_ids or [],
            evidence_ids=evidence_ids or [],
            source_paragraph=source_paragraph,
            suggested_fix=suggested_fix,
            auto_fixable=auto_fixable,
        )

        self._issues.append(issue)
        return issue

    @abstractmethod
    def validate(self) -> List[Issue]:
        """
        Run validation and return list of issues.

        Subclasses must implement this method to perform
        category-specific validation checks.

        Returns:
            List of Issue objects detected by this validator
        """
        pass

    def get_issues(self) -> List[Issue]:
        """
        Get all issues detected by this validator.

        Returns:
            List of Issue objects
        """
        return list(self._issues)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of validation results.

        Returns:
            Dict with counts by severity and rule code
        """
        severity_counts: Dict[str, int] = {}
        rule_counts: Dict[str, int] = {}

        for issue in self._issues:
            sev_key = issue.severity.value
            severity_counts[sev_key] = severity_counts.get(sev_key, 0) + 1

            rule_counts[issue.rule_code] = rule_counts.get(issue.rule_code, 0) + 1

        return {
            "total_issues": len(self._issues),
            "by_severity": severity_counts,
            "by_rule": rule_counts,
            "auto_fixable_count": sum(1 for i in self._issues if i.auto_fixable),
        }

    def clear_issues(self) -> None:
        """Clear all detected issues."""
        self._issues = []
        self._issue_counter = 0

    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        Get all entities of a specific type from storygraph.

        Args:
            entity_type: Entity type (e.g., "character", "location", "scene")

        Returns:
            List of entity dictionaries
        """
        if not self._storygraph:
            self._load_graphs()

        return [
            e
            for e in self._storygraph.get("entities", [])
            if e.get("type") == entity_type
        ]

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an entity by its ID from storygraph.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity dictionary or None if not found
        """
        if not self._storygraph:
            self._load_graphs()

        for entity in self._storygraph.get("entities", []):
            if entity.get("id") == entity_id:
                return entity
        return None

    def get_scenes_sorted(self) -> List[Dict[str, Any]]:
        """
        Get all scenes sorted by scene number.

        Returns:
            List of scene entities sorted by scene_number
        """
        scenes = self.get_entities_by_type("scene")
        return sorted(
            scenes,
            key=lambda s: s.get("attributes", {}).get("scene_number", 0) or 0,
        )

    def get_characters(self) -> List[Dict[str, Any]]:
        """Get all character entities."""
        return self.get_entities_by_type("character")

    def get_locations(self) -> List[Dict[str, Any]]:
        """Get all location entities."""
        return self.get_entities_by_type("location")
