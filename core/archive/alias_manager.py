"""Alias management for archive works.

Wraps FuzzyMatcher from core.resolution for archive-specific alias resolution.
Enables finding works by any known name (title variations, working titles, abbreviations).
"""
from typing import Optional

from core.resolution import FuzzyMatcher

from .models import AliasRegistry


class AliasManager:
    """Manages alias resolution for archive works.

    Wraps FuzzyMatcher to provide archive-specific functionality:
    - Register works with multiple aliases
    - Resolve queries to canonical IDs
    - Detect alias conflicts
    - Export/import alias registry
    """

    def __init__(self, threshold: int = 70):
        """
        Initialize the alias manager.

        Args:
            threshold: Minimum fuzzy match score (0-100) to consider a match
        """
        self.threshold = threshold
        self._matcher = FuzzyMatcher(threshold=threshold)
        self._aliases: dict[str, list[str]] = {}  # canonical_id -> [aliases]

    def register_alias(self, alias: str, canonical_id: str) -> Optional[dict]:
        """
        Register a single alias mapping.

        Args:
            alias: The alias to register
            canonical_id: The canonical work ID

        Returns:
            Conflict dict if alias already maps to different work, None otherwise
        """
        # Check for conflict
        conflict = self.detect_conflict(alias)
        if conflict and conflict["existing_id"] != canonical_id:
            return conflict

        # Add to matcher
        self._matcher._known_aliases[self._normalize(alias)] = canonical_id

        # Track aliases per canonical_id
        if canonical_id not in self._aliases:
            self._aliases[canonical_id] = []
        if alias not in self._aliases[canonical_id]:
            self._aliases[canonical_id].append(alias)

        return None

    def register_work(
        self, work_id: str, title: str, aliases: list[str] | None = None
    ) -> list[dict]:
        """
        Register a work with all its aliases.

        Args:
            work_id: The canonical work ID (e.g., work_abc12345)
            title: The canonical title
            aliases: List of alternate names/titles

        Returns:
            List of any conflicts detected
        """
        conflicts = []

        # Register canonical name as entity
        self._matcher.add_entity(work_id, title, aliases or [])

        # Track title as alias
        self._aliases.setdefault(work_id, [])
        if title not in self._aliases[work_id]:
            self._aliases[work_id].append(title)

        # Register all aliases
        if aliases:
            for alias in aliases:
                conflict = self.register_alias(alias, work_id)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def resolve(self, query: str) -> Optional[str]:
        """
        Find canonical ID from any alias (exact or fuzzy).

        Args:
            query: The name/alias to resolve

        Returns:
            Canonical ID if found, None otherwise
        """
        match = self._matcher.match(query)
        if match:
            return match.canonical_id
        return None

    def search(
        self, query: str, limit: int = 5
    ) -> list[tuple[str, str, float]]:
        """
        Fuzzy search for works by name/alias.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of (canonical_id, matched_name, score) tuples
        """
        candidates = self._matcher.find_candidates(query, limit=limit)
        return [(c.canonical_id, c.canonical_name, c.score) for c in candidates]

    def get_all_aliases(self, canonical_id: str) -> list[str]:
        """
        Get all aliases for a work.

        Args:
            canonical_id: The canonical work ID

        Returns:
            List of all registered aliases
        """
        return self._aliases.get(canonical_id, [])

    def detect_conflict(self, alias: str) -> Optional[dict]:
        """
        Check if alias already maps to a different work.

        Args:
            alias: The alias to check

        Returns:
            Conflict dict if exists, None otherwise
        """
        normalized = self._normalize(alias)

        # Check in known aliases
        if normalized in self._matcher._known_aliases:
            existing_id = self._matcher._known_aliases[normalized]
            return {
                "alias": alias,
                "existing_id": existing_id,
            }

        # Check in known entities (exact matches)
        if normalized in self._matcher._known_entities:
            existing_id = self._matcher._known_entities[normalized]
            return {
                "alias": alias,
                "existing_id": existing_id,
            }

        return None

    def export_registry(self) -> dict:
        """
        Export to AliasRegistry format.

        Returns:
            Dict suitable for AliasRegistry model
        """
        # Combine known aliases and entities
        all_aliases = {}

        # From known aliases
        for alias, canonical_id in self._matcher._known_aliases.items():
            all_aliases[alias] = canonical_id

        # From known entities (normalized name -> id)
        for name, canonical_id in self._matcher._known_entities.items():
            all_aliases[name] = canonical_id

        return {
            "version": "1.0",
            "aliases": all_aliases,
            "conflicts": [],
        }

    def import_registry(self, registry: dict | AliasRegistry) -> None:
        """
        Load from AliasRegistry format.

        Args:
            registry: AliasRegistry model or dict with 'aliases' key
        """
        if isinstance(registry, AliasRegistry):
            aliases = registry.aliases
        else:
            aliases = registry.get("aliases", {})

        for alias, canonical_id in aliases.items():
            self._matcher._known_aliases[alias.lower().strip()] = canonical_id

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()
