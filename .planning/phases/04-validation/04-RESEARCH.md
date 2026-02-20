# Phase 4: Validation - Research

**Researched:** 2026-02-19
**Domain:** Continuity validation, rule-based issue detection, report generation
**Confidence:** HIGH (based on existing codebase patterns and industry research)

## Summary

This phase implements production-grade validation for screenplay/story continuity. The system must detect wardrobe inconsistencies, prop continuity errors, timeline violations, and knowledge state problems - all without ML, using deterministic rule-based logic.

**Key insight:** The project already has a robust three-tier conflict resolution system (`ConflictResolver` in Phase 3) that can be extended for validation. The same tiered approach (SAFE/AMBIGUOUS/CRITICAL) maps directly to issue severity (info/warning/error).

**Primary recommendation:** Implement four specialized validators (Wardrobe, Props, Timeline, Knowledge) that share a common `Issue` data model and report generator. Each validator runs rules against StoryGraph and ScriptGraph data, outputting to `build/issues.json` and Obsidian-compatible markdown reports.

---

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` | stdlib | Pattern matching for state detection | Already used in extraction |
| `json` | stdlib | Issue persistence | Consistent with project patterns |
| `pathlib` | stdlib | File operations | Modern Python file handling |
| `dataclasses` | stdlib | Issue data model | Type-safe, serializable |
| `enum` | stdlib | Severity classification | Already used in ConflictTier |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rapidfuzz` | 3.x+ | Fuzzy state matching | Already installed for alias resolution |
| `datetime` | stdlib | Timeline calculations | For time-based validation rules |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rule-based validation | ML classification | ML is explicitly forbidden by ADR-0002; rules are deterministic and debuggable |
| Custom issue format | JSON Schema standard | Project uses simple JSON; JSON Schema adds complexity without benefit |
| Separate issue store | Merge into conflicts.json | Issues are different from sync conflicts; separation keeps concerns clear |

**No new dependencies required** - all functionality uses existing stack.

---

## Architecture Patterns

### Recommended Project Structure

```
core/
├── validation/                  # NEW: Validation module
│   ├── __init__.py
│   ├── base.py                  # Issue data model, Validator base class
│   ├── wardrobe_validator.py    # WARD-01, WARD-02, WARD-03 rules
│   ├── props_validator.py       # PROP-01, PROP-02, PROP-03 rules
│   ├── timeline_validator.py    # TIME-01, TIME-02, TIME-04 rules
│   ├── knowledge_validator.py   # KNOW-01, KNOW-02, KNOW-03, KNOW-04 rules
│   └── report_generator.py      # Markdown report generation
├── sync/
│   └── conflict_resolver.py     # EXISTS: Pattern reference for tiered classification
└── storygraph/
    └── __init__.py              # EXISTS: Entity data source

build/
├── issues.json                  # NEW: All detected issues
└── run_state.json               # EXISTS: Validation timestamp

vault/
└── 80_Reports/                  # NEW: Human-readable markdown reports
    ├── validation-summary.md
    ├── wardrobe-issues.md
    ├── props-issues.md
    ├── timeline-issues.md
    └── knowledge-issues.md
```

### Pattern 1: Issue Data Model

**What:** Unified data model for all validation issues, following the Conflict pattern from Phase 3.

**When to use:** All validators output Issue objects.

**Example:**

```python
# Source: Pattern from core/sync/conflict_resolver.py (Conflict dataclass)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class IssueSeverity(Enum):
    """Issue severity levels - maps to conflict tiers."""
    ERROR = "error"      # CRITICAL: Must fix before production
    WARNING = "warning"  # AMBIGUOUS: Should review
    INFO = "info"        # SAFE: FYI only


class IssueCategory(Enum):
    """Issue category for grouping."""
    WARDROBE = "wardrobe"
    PROPS = "props"
    TIMELINE = "timeline"
    KNOWLEDGE = "knowledge"


@dataclass
class Issue:
    """
    Represents a detected validation issue.

    Pattern mirrors Conflict dataclass from Phase 3 for consistency.
    """
    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    rule_code: str  # e.g., "WARD-01", "PROP-02"
    title: str
    description: str

    # Location context
    scene_id: Optional[str] = None
    scene_number: Optional[int] = None
    entity_ids: List[str] = field(default_factory=list)

    # Evidence
    evidence_ids: List[str] = field(default_factory=list)
    source_paragraph: Optional[str] = None

    # Resolution
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False

    # Metadata
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
            "entity_ids": sorted(self.entity_ids),
            "evidence_ids": sorted(self.evidence_ids),
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
            detected_at=datetime.fromisoformat(data["detected_at"]),
            resolved=data.get("resolved", False),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            resolution_note=data.get("resolution_note"),
        )
```

### Pattern 2: Validator Base Class

**What:** Abstract base class for all validators, ensuring consistent interface.

**When to use:** All validators (Wardrobe, Props, Timeline, Knowledge) extend this.

**Example:**

```python
# Source: Pattern from core/canon/__init__.py (CanonBuilder)
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any
import json


class BaseValidator(ABC):
    """
    Abstract base class for all validators.

    Pattern mirrors CanonBuilder/ScriptBuilder for consistency.
    """

    def __init__(self, build_path: Path):
        self.build_path = build_path
        self._issues: List[Issue] = []
        self._storygraph: Dict[str, Any] = {}
        self._scriptgraph: Dict[str, Any] = {}
        self._issue_counter = 0

    def _load_graphs(self) -> None:
        """Load StoryGraph and ScriptGraph data."""
        storygraph_path = self.build_path / "storygraph.json"
        scriptgraph_path = self.build_path / "scriptgraph.json"

        if storygraph_path.exists():
            self._storygraph = json.loads(storygraph_path.read_text())

        if scriptgraph_path.exists():
            self._scriptgraph = json.loads(scriptgraph_path.read_text())

    def _create_issue_id(self, rule_code: str) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"issue_{rule_code.lower()}_{self._issue_counter:04d}"

    @abstractmethod
    def validate(self) -> List[Issue]:
        """
        Run all validation rules for this category.

        Returns:
            List of detected issues
        """
        pass

    def get_issues(self) -> List[Issue]:
        """Get all issues from this validator."""
        return sorted(self._issues, key=lambda i: (i.severity.value, i.scene_number or 0))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of validation results."""
        return {
            "category": self.__class__.__name__.replace("Validator", "").lower(),
            "total_issues": len(self._issues),
            "by_severity": {
                "error": len([i for i in self._issues if i.severity == IssueSeverity.ERROR]),
                "warning": len([i for i in self._issues if i.severity == IssueSeverity.WARNING]),
                "info": len([i for i in self._issues if i.severity == IssueSeverity.INFO]),
            },
            "auto_fixable": len([i for i in self._issues if i.auto_fixable]),
        }
```

### Pattern 3: Rule Implementation (Wardrobe Example)

**What:** Concrete validator implementing specific continuity rules.

**When to use:** Each validator category has its own class.

**Example:**

```python
# Source: VAL-01 requirements + industry patterns
from typing import Dict, List, Any, Optional
from .base import BaseValidator, Issue, IssueSeverity, IssueCategory


class WardrobeValidator(BaseValidator):
    """
    Validates wardrobe continuity across scenes.

    Rules:
    - WARD-01: State changes require cause beat
    - WARD-02: Conflicting wardrobe in adjacent timeline
    - WARD-03: Signature items persist
    """

    # Patterns for detecting wardrobe mentions
    WARDROBE_PATTERNS = [
        r"wearing\s+(.+?)(?:\.|,|\n)",
        r"dressed\s+in\s+(.+?)(?:\.|,|\n)",
        r"(\w+)\s+cloak",
        r"(\w+)\s+jacket",
        r"(\w+)\s+dress",
    ]

    # Characters with signature items (would be configurable per project)
    SIGNATURE_ITEMS: Dict[str, List[str]] = {}  # Populated from vault

    def validate(self) -> List[Issue]:
        """Run all wardrobe validation rules."""
        self._load_graphs()
        self._issues = []

        # Build character wardrobe timeline
        wardrobe_timeline = self._build_wardrobe_timeline()

        # WARD-01: Check for unexplained state changes
        self._check_state_changes(wardrobe_timeline)

        # WARD-02: Check for timeline conflicts
        self._check_timeline_conflicts(wardrobe_timeline)

        # WARD-03: Check signature item persistence
        self._check_signature_items(wardrobe_timeline)

        return self.get_issues()

    def _build_wardrobe_timeline(self) -> Dict[str, List[Dict]]:
        """
        Build timeline of wardrobe states per character.

        Returns:
            Dict mapping character_id -> list of {scene_id, scene_num, wardrobe_state, evidence_ids}
        """
        timeline: Dict[str, List[Dict]] = {}

        for entity in self._storygraph.get("entities", []):
            if entity.get("type") != "character":
                continue

            char_id = entity.get("id")
            timeline[char_id] = []

            # Find scenes this character appears in
            for scene in self._storygraph.get("scenes", []):
                scene_id = scene.get("id")
                scene_num = scene.get("scene_number", 0)
                characters = scene.get("characters", [])

                if char_id in characters:
                    # Extract wardrobe state from scene content
                    wardrobe_state = self._extract_wardrobe_state(scene)
                    timeline[char_id].append({
                        "scene_id": scene_id,
                        "scene_num": scene_num,
                        "wardrobe_state": wardrobe_state,
                        "evidence_ids": scene.get("evidence_ids", []),
                    })

        return timeline

    def _extract_wardrobe_state(self, scene: Dict) -> Optional[str]:
        """Extract wardrobe description from scene content."""
        import re

        content = scene.get("content", "")
        for pattern in self.WARDROBE_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _check_state_changes(self, timeline: Dict[str, List[Dict]]) -> None:
        """WARD-01: Check for unexplained wardrobe changes."""
        for char_id, states in timeline.items():
            for i in range(1, len(states)):
                prev = states[i - 1]
                curr = states[i]

                # Skip if no wardrobe mentioned
                if not prev["wardrobe_state"] or not curr["wardrobe_state"]:
                    continue

                # Check if wardrobe changed
                if prev["wardrobe_state"] != curr["wardrobe_state"]:
                    # Check if there's a cause beat (time skip, costume change mention)
                    has_cause = self._has_costume_change_cause(
                        prev["scene_id"],
                        curr["scene_id"],
                        curr["evidence_ids"]
                    )

                    if not has_cause:
                        self._issues.append(Issue(
                            issue_id=self._create_issue_id("WARD-01"),
                            category=IssueCategory.WARDROBE,
                            severity=IssueSeverity.WARNING,
                            rule_code="WARD-01",
                            title="Unexplained wardrobe change",
                            description=f"Wardrobe changed from '{prev['wardrobe_state']}' to '{curr['wardrobe_state']}' without cause beat",
                            scene_id=curr["scene_id"],
                            scene_number=curr["scene_num"],
                            entity_ids=[char_id],
                            evidence_ids=curr["evidence_ids"],
                            suggested_fix=f"Add costume change beat between scenes {prev['scene_num']} and {curr['scene_num']}",
                            auto_fixable=False,
                        ))

    def _has_costume_change_cause(
        self,
        prev_scene_id: str,
        curr_scene_id: str,
        evidence_ids: List[str]
    ) -> bool:
        """Check if there's a cause for costume change between scenes."""
        # Look for time skip markers, costume change mentions
        # This would search the scriptgraph content between scenes
        # Simplified for example
        return False

    def _check_timeline_conflicts(self, timeline: Dict[str, List[Dict]]) -> None:
        """WARD-02: Check for conflicting wardrobe in adjacent timeline."""
        for char_id, states in timeline.items():
            for i in range(1, len(states)):
                prev = states[i - 1]
                curr = states[i]

                # Check if scenes are continuous (same time period)
                if self._are_adjacent_timeline(prev["scene_id"], curr["scene_id"]):
                    if (prev["wardrobe_state"] and curr["wardrobe_state"] and
                        prev["wardrobe_state"] != curr["wardrobe_state"]):
                        self._issues.append(Issue(
                            issue_id=self._create_issue_id("WARD-02"),
                            category=IssueCategory.WARDROBE,
                            severity=IssueSeverity.ERROR,
                            rule_code="WARD-02",
                            title="Wardrobe conflict in continuous time",
                            description=f"Wardrobe changed in continuous timeline: '{prev['wardrobe_state']}' vs '{curr['wardrobe_state']}'",
                            scene_id=curr["scene_id"],
                            scene_number=curr["scene_num"],
                            entity_ids=[char_id],
                            evidence_ids=curr["evidence_ids"],
                            suggested_fix="Scenes are continuous - wardrobe cannot change without time skip",
                            auto_fixable=False,
                        ))

    def _are_adjacent_timeline(self, scene_a_id: str, scene_b_id: str) -> bool:
        """Check if two scenes are in continuous time."""
        # Would check scene metadata for CONTINUOUS, MOMENTS LATER, etc.
        return False  # Simplified

    def _check_signature_items(self, timeline: Dict[str, List[Dict]]) -> None:
        """WARD-03: Check that signature items persist across scenes."""
        for char_id, states in timeline.items():
            if char_id not in self.SIGNATURE_ITEMS:
                continue

            signature = self.SIGNATURE_ITEMS[char_id]
            for state in states:
                if state["wardrobe_state"]:
                    for item in signature:
                        if item.lower() not in state["wardrobe_state"].lower():
                            self._issues.append(Issue(
                                issue_id=self._create_issue_id("WARD-03"),
                                category=IssueCategory.WARDROBE,
                                severity=IssueSeverity.INFO,
                                rule_code="WARD-03",
                                title="Signature item missing",
                                description=f"Character's signature item '{item}' not mentioned in wardrobe description",
                                scene_id=state["scene_id"],
                                scene_number=state["scene_num"],
                                entity_ids=[char_id],
                                evidence_ids=state["evidence_ids"],
                                suggested_fix=f"Confirm '{item}' is present or explain absence",
                                auto_fixable=False,
                            ))
```

### Pattern 4: Report Generator (Obsidian-Compatible)

**What:** Generate markdown reports readable in Obsidian vault.

**When to use:** After all validators complete.

**Example:**

```python
# Source: VaultNoteWriter pattern + Obsidian markdown conventions
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class ReportGenerator:
    """Generate Obsidian-compatible validation reports."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.reports_path = vault_path / "80_Reports"
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def generate_reports(self, all_issues: List[Issue]) -> Dict[str, Path]:
        """Generate all report files."""
        reports = {}

        # Summary report
        reports["summary"] = self._generate_summary_report(all_issues)

        # Category-specific reports
        for category in IssueCategory:
            category_issues = [i for i in all_issues if i.category == category]
            if category_issues:
                reports[category.value] = self._generate_category_report(category, category_issues)

        return reports

    def _generate_summary_report(self, issues: List[Issue]) -> Path:
        """Generate main summary report."""
        filepath = self.reports_path / "validation-summary.md"

        # Group by severity
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]
        infos = [i for i in issues if i.severity == IssueSeverity.INFO]

        content = f"""# Validation Summary

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Total Issues:** {len(issues)}

## Overview

| Severity | Count | Status |
|----------|-------|--------|
| ERROR | {len(errors)} | {"✅ None" if not errors else "❌ Requires attention"} |
| WARNING | {len(warnings)} | {"✅ None" if not warnings else "⚠️ Review recommended"} |
| INFO | {len(infos)} | {"✅ None" if not infos else "ℹ️ Informational"} |

## Issues by Category

| Category | Errors | Warnings | Info | Total |
|----------|--------|----------|------|-------|
| Wardrobe | {len([i for i in errors if i.category == IssueCategory.WARDROBE])} | {len([i for i in warnings if i.category == IssueCategory.WARDROBE])} | {len([i for i in infos if i.category == IssueCategory.WARDROBE])} | {len([i for i in issues if i.category == IssueCategory.WARDROBE])} |
| Props | {len([i for i in errors if i.category == IssueCategory.PROPS])} | {len([i for i in warnings if i.category == IssueCategory.PROPS])} | {len([i for i in infos if i.category == IssueCategory.PROPS])} | {len([i for i in issues if i.category == IssueCategory.PROPS])} |
| Timeline | {len([i for i in errors if i.category == IssueCategory.TIMELINE])} | {len([i for i in warnings if i.category == IssueCategory.TIMELINE])} | {len([i for i in infos if i.category == IssueCategory.TIMELINE])} | {len([i for i in issues if i.category == IssueCategory.TIMELINE])} |
| Knowledge | {len([i for i in errors if i.category == IssueCategory.KNOWLEDGE])} | {len([i for i in warnings if i.category == IssueCategory.KNOWLEDGE])} | {len([i for i in infos if i.category == IssueCategory.KNOWLEDGE])} | {len([i for i in issues if i.category == IssueCategory.KNOWLEDGE])} |

## Critical Issues (Errors)

"""
        if errors:
            for issue in sorted(errors, key=lambda i: i.scene_number or 0):
                content += self._format_issue_entry(issue)
        else:
            content += "No critical issues found. ✅\n"

        content += """
## Detailed Reports

- [[wardrobe-issues|Wardrobe Issues]]
- [[props-issues|Props Issues]]
- [[timeline-issues|Timeline Issues]]
- [[knowledge-issues|Knowledge Issues]]
"""

        filepath.write_text(content)
        return filepath

    def _generate_category_report(self, category: IssueCategory, issues: List[Issue]) -> Path:
        """Generate category-specific report."""
        filepath = self.reports_path / f"{category.value}-issues.md"

        content = f"""# {category.value.title()} Issues

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Total Issues:** {len(issues)}

---

"""
        # Group by scene
        by_scene: Dict[int, List[Issue]] = {}
        for issue in issues:
            scene_num = issue.scene_number or 0
            if scene_num not in by_scene:
                by_scene[scene_num] = []
            by_scene[scene_num].append(issue)

        for scene_num in sorted(by_scene.keys()):
            scene_issues = by_scene[scene_num]

            if scene_num > 0:
                content += f"## Scene {scene_num}\n\n"
            else:
                content += "## General Issues\n\n"

            for issue in sorted(scene_issues, key=lambda i: i.severity.value):
                content += self._format_issue_entry(issue, detailed=True)

        filepath.write_text(content)
        return filepath

    def _format_issue_entry(self, issue: Issue, detailed: bool = False) -> str:
        """Format a single issue for markdown display."""
        severity_emoji = {
            IssueSeverity.ERROR: "❌",
            IssueSeverity.WARNING: "⚠️",
            IssueSeverity.INFO: "ℹ️",
        }

        entry = f"### {severity_emoji[issue.severity]} [{issue.rule_code}] {issue.title}\n\n"
        entry += f"{issue.description}\n\n"

        if detailed:
            if issue.scene_id:
                entry += f"**Scene:** [[{issue.scene_id}]]\n\n"

            if issue.entity_ids:
                entity_links = ", ".join(f"[[{eid}]]" for eid in issue.entity_ids)
                entry += f"**Entities:** {entity_links}\n\n"

            if issue.evidence_ids:
                ev_links = ", ".join(f"[[evidence#{eid}]]" for eid in issue.evidence_ids[:3])
                if len(issue.evidence_ids) > 3:
                    ev_links += f" (+{len(issue.evidence_ids) - 3} more)"
                entry += f"**Evidence:** {ev_links}\n\n"

            if issue.suggested_fix:
                entry += f"**Suggestion:** {issue.suggested_fix}\n\n"

        entry += "---\n\n"
        return entry
```

### Anti-Patterns to Avoid

- **Using ML for validation:** Explicitly forbidden by ADR-0002; use deterministic rules
- **Silent issue dropping:** Every detected issue must be recorded, even INFO level
- **Assuming scene order equals timeline order:** Check for flashbacks, parallel action
- **Ignoring evidence links:** Issues without evidence are untraceable and unverifiable

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Issue classification | Custom severity logic | `IssueSeverity` enum matching `ConflictTier` pattern | Consistent with Phase 3 patterns |
| Report formatting | String concatenation | Template with sections (like vault templates) | Consistent, maintainable |
| Issue persistence | Custom file format | JSON with `to_dict()`/`from_dict()` | Matches existing graph patterns |
| Scene ordering | Custom sort logic | Scene metadata (scene_number field) | Already in StoryGraph |

**Key insight:** Reuse patterns from existing codebase (ConflictResolver, VaultNoteWriter, CanonBuilder).

---

## Common Pitfalls

### Pitfall 1: False Positive Overload

**What goes wrong:** Validators flag too many issues, desensitizing users to real problems.

**Why it happens:** Rules are too strict, don't account for narrative conventions.

**How to avoid:**
1. Start conservative - prefer WARNING over ERROR
2. Allow project-specific tuning via `gsd.yaml`
3. Include confidence/strictness levels per rule
4. Provide "dismiss" functionality for false positives

**Warning signs:**
- Users ignore validation reports entirely
- Same issue flagged repeatedly across projects

### Pitfall 2: Missing Context for Issues

**What goes wrong:** Issues lack enough context to understand or fix.

**Why it happens:** Minimal data model, missing evidence links.

**How to avoid:**
1. Always include scene_id, scene_number
2. Include entity_ids for involved characters/props/locations
3. Include at least 3 evidence_ids or excerpt
4. Provide suggested_fix text

**Warning signs:**
- Users can't understand what an issue means
- Clicking evidence links shows nothing relevant

### Pitfall 3: Timeline Complexity Underestimation

**What goes wrong:** Simple "next scene = next time" assumption fails.

**Why it happens:** Screenplays have flashbacks, parallel action, non-linear structure.

**How to avoid:**
1. Use scene metadata (time_of_day, int_ext, sequential flag)
2. Track "story time" separately from "scene order"
3. Flag time markers like "THREE DAYS LATER", "FLASHBACK"
4. Don't assume adjacent scenes are temporally adjacent

**Warning signs:**
- Timeline validator flags issues that aren't actually problems
- Characters appear to be in two places but it's intentional (parallel scenes)

### Pitfall 4: Knowledge State Complexity

**What goes wrong:** KNOW-01 through KNOW-04 require tracking complex state graphs.

**Why it happens:** Character knowledge depends on scene sequence, who was present, what was revealed.

**How to avoid:**
1. Build a "knowledge state" data structure per character per scene
2. Track "present_characters" per scene in StoryGraph
3. Propagate knowledge through explicit channels (conversation, observation)
4. Accept that some knowledge states are ambiguous - flag as WARNING not ERROR

**Warning signs:**
- Validator claims character "couldn't know" something they clearly learned
- Too many false positives on knowledge validation

---

## Code Examples

### Full Validation Orchestration

```python
# Source: Pattern from ScriptBuilder + CanonBuilder orchestration
from pathlib import Path
from typing import Dict, List, Any
import json

from .base import Issue
from .wardrobe_validator import WardrobeValidator
from .props_validator import PropsValidator
from .timeline_validator import TimelineValidator
from .knowledge_validator import KnowledgeValidator
from .report_generator import ReportGenerator


class ValidationOrchestrator:
    """Orchestrate all validators and report generation."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.build_path = project_path / "build"
        self.vault_path = project_path / "vault"

        # Initialize validators
        self.validators = [
            WardrobeValidator(self.build_path),
            PropsValidator(self.build_path),
            TimelineValidator(self.build_path),
            KnowledgeValidator(self.build_path),
        ]

        self.report_generator = ReportGenerator(self.vault_path)
        self._all_issues: List[Issue] = []
        self._issue_counter = 0

    def run_validation(self) -> Dict[str, Any]:
        """
        Run all validators and generate reports.

        Returns:
            Summary dict with issue counts and report paths
        """
        self._all_issues = []

        # Run each validator
        for validator in self.validators:
            issues = validator.validate()
            # Re-number issue IDs to be globally unique
            for issue in issues:
                self._issue_counter += 1
                issue.issue_id = f"issue_{self._issue_counter:06d}"
            self._all_issues.extend(issues)

        # Save issues to JSON
        self._save_issues()

        # Generate reports
        report_paths = self.report_generator.generate_reports(self._all_issues)

        return {
            "total_issues": len(self._all_issues),
            "by_severity": {
                "error": len([i for i in self._all_issues if i.severity.value == "error"]),
                "warning": len([i for i in self._all_issues if i.severity.value == "warning"]),
                "info": len([i for i in self._all_issues if i.severity.value == "info"]),
            },
            "by_category": {
                v.__class__.__name__.replace("Validator", "").lower(): v.get_summary()
                for v in self.validators
            },
            "reports": {k: str(v) for k, v in report_paths.items()},
            "issues_path": str(self.build_path / "issues.json"),
        }

    def _save_issues(self) -> None:
        """Persist all issues to JSON."""
        issues_path = self.build_path / "issues.json"

        data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_issues": len(self._all_issues),
            "summary": self._get_summary(),
            "issues": [i.to_dict() for i in sorted(
                self._all_issues,
                key=lambda x: (x.severity.value, x.scene_number or 0)
            )],
        }

        issues_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def _get_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        return {
            "by_severity": {
                "error": len([i for i in self._all_issues if i.severity == IssueSeverity.ERROR]),
                "warning": len([i for i in self._all_issues if i.severity == IssueSeverity.WARNING]),
                "info": len([i for i in self._all_issues if i.severity == IssueSeverity.INFO]),
            },
            "by_category": {
                cat.value: len([i for i in self._all_issues if i.category == cat])
                for cat in IssueCategory
            },
            "auto_fixable": len([i for i in self._all_issues if i.auto_fixable]),
        }
```

### CLI Integration

```python
# Source: Pattern from apps/cli/cli.py (build command structure)
import argparse
from pathlib import Path

def cmd_validate(args):
    """Run validation and generate reports."""
    from core.validation import ValidationOrchestrator

    project_path = Path.cwd()
    orchestrator = ValidationOrchestrator(project_path)

    # Check prerequisites
    storygraph = project_path / "build" / "storygraph.json"
    if not storygraph.exists():
        print("ERROR: No storygraph.json found. Run 'gsd build canon' first.")
        return 1

    print("Running validation...")

    result = orchestrator.run_validation()

    print(f"\nValidation complete:")
    print(f"  Errors:   {result['by_severity']['error']}")
    print(f"  Warnings: {result['by_severity']['warning']}")
    print(f"  Info:     {result['by_severity']['info']}")

    print(f"\nReports generated in vault/80_Reports/")
    print(f"  Summary: {result['reports'].get('summary', 'N/A')}")

    # Return non-zero if errors found
    return 1 if result['by_severity']['error'] > 0 else 0

# Register command
# p_validate = subparsers.add_parser("validate", help="Validate story continuity")
# p_validate.set_defaults(func=cmd_validate)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual continuity checking | Rule-based automated validation | This phase | Catches issues early, consistent |
| Paper continuity logs | Digital issue tracking | Industry trend 2020+ | Searchable, linkable |
| Single severity level | Tiered severity (error/warning/info) | Phase 3 pattern | Prioritizes critical issues |
| Text-only reports | Obsidian wikilink reports | This phase | Navigable, contextual |

**Industry context (2025):**
- StudioBinder: Script breakdown with element tagging
- SyncOnSet: Continuity tracking in production
- Script supervisors use continuity logs with photos

**Deprecated/outdated:**
- Single monolithic validator: Use separate validators per category
- ML-based issue detection: Forbidden by ADR-0002
- Flat issue lists: Use tiered severity and categorization

---

## Open Questions

### 1. Should validators share state during validation?

**What we know:**
- Wardrobe and Timeline validators both need scene order
- Knowledge validator needs present_characters per scene
- Some rules cross categories (e.g., wardrobe + timeline)

**What's unclear:**
- Should validators have access to each other's findings?
- Or should cross-category issues be a separate pass?

**Recommendation:**
- Start with independent validators
- Add a "cross-validator" pass if needed
- Keep validators isolated for testability

### 2. How to handle "intentional" continuity breaks?

**What we know:**
- Some stories intentionally break continuity (unreliable narrator, dream sequences)
- These would trigger false positives

**What's unclear:**
- How to mark scenes as "continuity exempt"?
- Should exemptions be per-rule or per-scene?

**Recommendation:**
- Add `continuity_exempt: true` flag to scene metadata
- Support rule-specific exemptions: `exempt_rules: ["WARD-01", "TIME-01"]`
- Document in vault notes

### 3. What's the minimum StoryGraph data required?

**What we know:**
- Validators need scene data, character appearances, evidence
- Current StoryGraph may not have all needed fields

**What's unclear:**
- Do we need to extend StoryGraph schema?
- Or should validators work with what exists?

**Recommendation:**
- Document required fields per validator
- Graceful degradation: validators skip missing data
- Flag missing data as INFO issues

---

## Sources

### Primary (HIGH confidence)
- Project codebase analysis - ConflictResolver pattern, VaultNoteWriter, existing validators
- REQUIREMENTS.md - VAL-01 through VAL-05 requirements with rule codes
- ADR-0002 - No ML/NER library requirement

### Secondary (MEDIUM confidence)
- AI Film Script Analysis 2025 - 18 advances including plot hole detection
- StudioBinder script breakdown methodology - Element tagging patterns
- SyncOnSet continuity tracking - Industry standard for production continuity
- Script supervisor continuity log templates - Standard continuity fields

### Tertiary (LOW confidence)
- Causality Story Sequencer research - Advanced causality tracking (future direction)
- ML-based validation research - Forbidden by ADR-0002 but useful for comparison

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, reuses existing patterns
- Architecture patterns: HIGH - Based on existing ConflictResolver and builder patterns
- Pitfalls: MEDIUM - Based on industry research and common validation issues
- Report generation: HIGH - Follows established vault template patterns

**Research date:** 2026-02-19
**Valid until:** 2026-05-19 (3 months - patterns are stable, no fast-moving dependencies)
