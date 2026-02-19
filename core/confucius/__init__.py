"""Confucius MCP integration for FDX GSD.

This module provides a Python interface to Confucius MCP for:
- Storing patterns learned during extraction
- Storing error/solution pairs
- Retrieving relevant context before processing
- Session memory management

Per ADR-0005: Confucius MCP IS the memory system.
The orchestration agent uses this for all pattern/decision storage.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class MemoryScope(str, Enum):
    """Memory scope levels for Confucius storage."""
    REPOSITORY = "repository"  # Project-wide patterns
    SUBMODULE = "submodule"    # Phase-specific patterns
    SESSION = "session"        # Current session context
    TASK = "task"              # Specific task memory


class MemoryType(str, Enum):
    """Types of memory entries."""
    PATTERN = "pattern"           # Successful pattern to repeat
    ERROR_SOLUTION = "error_solution"  # Error and its resolution
    DECISION = "decision"         # Architecture decision
    CONTEXT = "context"           # Project context
    ALIAS = "alias"               # Confirmed entity alias


@dataclass
class MemoryEntry:
    """A memory entry to store in Confucius."""
    type: MemoryType
    content: str
    scope: MemoryScope = MemoryScope.SESSION
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfuciusClient:
    """
    Client for interacting with Confucius MCP.

    In production, this would call the actual MCP tools.
    For now, it provides a clean interface that can be mocked for testing.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self._session_memory: List[MemoryEntry] = []

    def store(self, entry: MemoryEntry) -> bool:
        """
        Store a memory entry in Confucius.

        Args:
            entry: The memory entry to store

        Returns:
            True if stored successfully
        """
        # In production, this would call mcp__cognee-local__cognify
        # or memory_store if available

        # For now, track in session memory
        self._session_memory.append(entry)

        # Log for debugging
        logger.debug("Stored %s: %s...", entry.type.value, entry.content[:50])

        return True

    def retrieve(self, query: str, scope: Optional[MemoryScope] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories from Confucius.

        Args:
            query: Search query
            scope: Optional scope filter

        Returns:
            List of matching memory entries
        """
        # In production, this would call mcp__cognee-local__search
        # or memory_retrieve if available

        # For now, search session memory
        results = []
        for entry in self._session_memory:
            if query.lower() in entry.content.lower():
                if scope is None or entry.scope == scope:
                    results.append({
                        "type": entry.type.value,
                        "content": entry.content,
                        "scope": entry.scope.value,
                        "tags": entry.tags,
                        "confidence": entry.confidence,
                    })

        return results

    def store_pattern(self, pattern: str, tags: List[str] = None) -> bool:
        """Convenience method to store a successful pattern."""
        return self.store(MemoryEntry(
            type=MemoryType.PATTERN,
            content=pattern,
            scope=MemoryScope.REPOSITORY,
            tags=tags or [],
        ))

    def store_error_solution(self, error: str, solution: str) -> bool:
        """Convenience method to store an error and its solution."""
        return self.store(MemoryEntry(
            type=MemoryType.ERROR_SOLUTION,
            content=f"Error: {error}\nSolution: {solution}",
            scope=MemoryScope.REPOSITORY,
            tags=["error", "solution"],
        ))

    def store_alias(self, canonical_id: str, alias: str, evidence_id: str) -> bool:
        """Store a confirmed entity alias."""
        return self.store(MemoryEntry(
            type=MemoryType.ALIAS,
            content=f"{alias} → {canonical_id}",
            scope=MemoryScope.REPOSITORY,
            tags=["alias", canonical_id.split("_")[0].lower()],
            metadata={"canonical_id": canonical_id, "evidence_id": evidence_id},
        ))

    def store_decision(self, decision: str, rationale: str, adr_id: str = None) -> bool:
        """Store an architecture decision."""
        tags = ["decision"]
        if adr_id:
            tags.append(adr_id)

        return self.store(MemoryEntry(
            type=MemoryType.DECISION,
            content=f"Decision: {decision}\nRationale: {rationale}",
            scope=MemoryScope.REPOSITORY,
            tags=tags,
        ))

    def get_by_type(self, memory_type: MemoryType, scope: Optional[MemoryScope] = None) -> List[Dict[str, Any]]:
        """Retrieve all entries of a specific type."""
        results = []
        for entry in self._session_memory:
            if entry.type == memory_type:
                if scope is None or entry.scope == scope:
                    results.append({
                        "type": entry.type.value,
                        "content": entry.content,
                        "scope": entry.scope.value,
                        "tags": entry.tags,
                        "confidence": entry.confidence,
                        "metadata": entry.metadata,
                    })
        return results

    def get_extraction_patterns(self) -> List[str]:
        """Retrieve all extraction patterns for use in pipeline."""
        results = self.get_by_type(MemoryType.PATTERN, scope=MemoryScope.REPOSITORY)
        return [r["content"] for r in results]

    def get_known_aliases(self, entity_type: str = None) -> Dict[str, str]:
        """Retrieve known aliases as a mapping."""
        results = self.get_by_type(MemoryType.ALIAS, scope=MemoryScope.REPOSITORY)
        aliases = {}
        for r in results:
            if "→" in r["content"]:
                parts = r["content"].split(" → ")
                if len(parts) == 2:
                    aliases[parts[0].strip()] = parts[1].strip()
        return aliases


# Singleton client for project
_client: Optional[ConfuciusClient] = None


def get_client(project_id: str = None) -> ConfuciusClient:
    """Get or create the Confucius client for this project."""
    global _client
    if _client is None:
        if project_id is None:
            project_id = "fdx-gsd"  # Default
        _client = ConfuciusClient(project_id)
    return _client


def store_pattern(pattern: str, tags: List[str] = None) -> bool:
    """Convenience function to store a pattern."""
    return get_client().store_pattern(pattern, tags)


def store_error_solution(error: str, solution: str) -> bool:
    """Convenience function to store error/solution."""
    return get_client().store_error_solution(error, solution)


def store_alias(canonical_id: str, alias: str, evidence_id: str) -> bool:
    """Convenience function to store alias confirmation."""
    return get_client().store_alias(canonical_id, alias, evidence_id)


def retrieve_context(query: str) -> List[Dict[str, Any]]:
    """Convenience function to retrieve context."""
    return get_client().retrieve(query)
