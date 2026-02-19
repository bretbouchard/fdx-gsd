"""Unit tests for Confucius client."""
import pytest

from core.confucius import (
    ConfuciusClient,
    MemoryEntry,
    MemoryScope,
    MemoryType,
    get_client,
    store_pattern,
    store_alias,
    store_error_solution,
)


@pytest.fixture
def client():
    """Create a fresh client for each test."""
    return ConfuciusClient("test_project")


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_create_entry(self):
        """Test creating a memory entry."""
        entry = MemoryEntry(
            type=MemoryType.PATTERN,
            content="Test pattern",
        )
        assert entry.type == MemoryType.PATTERN
        assert entry.content == "Test pattern"
        assert entry.scope == MemoryScope.SESSION  # default
        assert entry.tags == []  # default
        assert entry.confidence == 1.0  # default

    def test_entry_with_all_fields(self):
        """Test entry with all fields specified."""
        entry = MemoryEntry(
            type=MemoryType.DECISION,
            content="Use rapidfuzz",
            scope=MemoryScope.REPOSITORY,
            tags=["decision", "ADR-0003"],
            confidence=0.95,
            metadata={"adr_id": "ADR-0003"},
        )
        assert entry.scope == MemoryScope.REPOSITORY
        assert "ADR-0003" in entry.tags
        assert entry.metadata["adr_id"] == "ADR-0003"


class TestConfuciusClient:
    """Tests for ConfuciusClient."""

    def test_init(self, client):
        """Test client initialization."""
        assert client.project_id == "test_project"
        assert client._session_memory == []

    def test_store_returns_true(self, client):
        """Test that store returns True."""
        entry = MemoryEntry(type=MemoryType.PATTERN, content="Test")
        result = client.store(entry)
        assert result is True

    def test_store_adds_to_session_memory(self, client):
        """Test that store adds entry to session memory."""
        entry = MemoryEntry(type=MemoryType.PATTERN, content="Test pattern")
        client.store(entry)
        assert len(client._session_memory) == 1
        assert client._session_memory[0].content == "Test pattern"

    def test_retrieve_empty(self, client):
        """Test retrieve with no matches."""
        results = client.retrieve("nonexistent")
        assert results == []

    def test_retrieve_finds_match(self, client):
        """Test retrieve finds matching entry."""
        client.store(MemoryEntry(
            type=MemoryType.PATTERN,
            content="Character names appear in ALL CAPS",
        ))
        results = client.retrieve("character")
        assert len(results) == 1
        assert "Character" in results[0]["content"]

    def test_retrieve_scope_filter(self, client):
        """Test retrieve with scope filter."""
        client.store(MemoryEntry(
            type=MemoryType.PATTERN,
            content="Repository pattern",
            scope=MemoryScope.REPOSITORY,
        ))
        client.store(MemoryEntry(
            type=MemoryType.CONTEXT,
            content="Session context",
            scope=MemoryScope.SESSION,
        ))

        results = client.retrieve("pattern", scope=MemoryScope.REPOSITORY)
        assert len(results) == 1
        assert "Repository" in results[0]["content"]

    def test_store_pattern(self, client):
        """Test store_pattern convenience method."""
        result = client.store_pattern("Use regex for character extraction", ["extraction"])
        assert result is True
        assert len(client._session_memory) == 1

    def test_store_error_solution(self, client):
        """Test store_error_solution convenience method."""
        result = client.store_error_solution(
            error="Ambiguous reference 'the boss'",
            solution="Asked user, linked to CHAR_MobBoss"
        )
        assert result is True
        assert len(client._session_memory) == 1
        assert "Ambiguous" in client._session_memory[0].content

    def test_store_alias(self, client):
        """Test store_alias convenience method."""
        result = client.store_alias(
            canonical_id="CHAR_Richard_38348",
            alias="Ricky",
            evidence_id="ev_a1b2"
        )
        assert result is True
        entry = client._session_memory[0]
        assert "Ricky → CHAR_Richard_38348" in entry.content
        assert entry.metadata["evidence_id"] == "ev_a1b2"

    def test_get_extraction_patterns(self, client):
        """Test retrieving extraction patterns."""
        client.store_pattern("Characters in ALL CAPS", ["extraction", "character"])
        client.store_pattern("Locations after INT./EXT.", ["extraction", "location"])

        patterns = client.get_extraction_patterns()
        assert len(patterns) == 2

    def test_get_known_aliases(self, client):
        """Test retrieving known aliases as mapping."""
        client.store_alias("CHAR_Richard_38348", "Ricky", "ev_1")
        client.store_alias("CHAR_Richard_38348", "Dick", "ev_2")

        aliases = client.get_known_aliases()
        assert aliases["Ricky"] == "CHAR_Richard_38348"
        assert aliases["Dick"] == "CHAR_Richard_38348"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_client_singleton(self):
        """Test get_client returns singleton."""
        client1 = get_client("project_a")
        client2 = get_client("project_b")  # Different project_id ignored after first call
        assert client1 is client2

    def test_store_pattern_function(self):
        """Test module-level store_pattern."""
        # This uses the singleton, so it works
        result = store_pattern("Test pattern")
        assert result is True

    def test_store_alias_function(self):
        """Test module-level store_alias."""
        result = store_alias("CHAR_Test", "alias", "ev_1")
        assert result is True
