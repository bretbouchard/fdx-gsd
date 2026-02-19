"""Fuzzy matching for alias resolution (CAN-04).

Per ADR-0003: Use rapidfuzz for fuzzy string matching.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Fallback to simple ratio if rapidfuzz not available
    def simple_ratio(s1: str, s2: str) -> float:
        """Simple Levenshtein-like ratio fallback."""
        s1, s2 = s1.lower(), s2.lower()
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 100.0

        # Simple character overlap ratio
        common = sum(1 for c in s1 if c in s2)
        return (2.0 * common / (len(s1) + len(s2))) * 100


@dataclass
class AliasMatch:
    """A potential alias match."""
    text: str
    canonical_id: str
    canonical_name: str
    score: float
    method: str  # exact, alias, fuzzy


class FuzzyMatcher:
    """Fuzzy string matching for entity alias resolution."""

    def __init__(self, threshold: int = 70):
        """
        Initialize the fuzzy matcher.

        Args:
            threshold: Minimum score (0-100) to consider a match
        """
        self.threshold = threshold
        self._known_entities: Dict[str, str] = {}  # normalized_name -> canonical_id
        self._entity_names: Dict[str, str] = {}    # canonical_id -> canonical_name
        self._known_aliases: Dict[str, str] = {}   # alias -> canonical_id

    def add_entity(self, canonical_id: str, name: str, aliases: List[str] = None):
        """
        Register an entity for matching.

        Args:
            canonical_id: The canonical entity ID (e.g., CHAR_Fox_001)
            name: The canonical name (e.g., "Fox")
            aliases: Known aliases (e.g., ["FOX", "F.", "the fox"])
        """
        normalized = self._normalize(name)
        self._known_entities[normalized] = canonical_id
        self._entity_names[canonical_id] = name

        if aliases:
            for alias in aliases:
                alias_norm = self._normalize(alias)
                self._known_aliases[alias_norm] = canonical_id

    def load_from_confucius(self, aliases: Dict[str, str]):
        """
        Load known aliases from Confucius memory.

        Args:
            aliases: Dict mapping alias -> canonical_id
        """
        self._known_aliases.update({self._normalize(k): v for k, v in aliases.items()})

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()

    def _fuzzy_score(self, s1: str, s2: str) -> float:
        """Calculate fuzzy match score between two strings."""
        if RAPIDFUZZ_AVAILABLE:
            return fuzz.ratio(s1.lower(), s2.lower())
        else:
            return simple_ratio(s1, s2)

    def match(self, text: str) -> Optional[AliasMatch]:
        """
        Find the best match for a text string.

        Resolution order:
        1. Exact match in known entities
        2. Known alias match
        3. Fuzzy match against all entity names

        Args:
            text: Text to match

        Returns:
            AliasMatch if found, None otherwise
        """
        normalized = self._normalize(text)

        # 1. Exact match
        if normalized in self._known_entities:
            canonical_id = self._known_entities[normalized]
            return AliasMatch(
                text=text,
                canonical_id=canonical_id,
                canonical_name=self._entity_names[canonical_id],
                score=100.0,
                method="exact"
            )

        # 2. Known alias
        if normalized in self._known_aliases:
            canonical_id = self._known_aliases[normalized]
            return AliasMatch(
                text=text,
                canonical_id=canonical_id,
                canonical_name=self._entity_names.get(canonical_id, canonical_id),
                score=95.0,
                method="alias"
            )

        # 3. Fuzzy match
        best_match = None
        best_score = 0

        for entity_name, canonical_id in self._known_entities.items():
            score = self._fuzzy_score(normalized, entity_name)

            if score > best_score and score >= self.threshold:
                best_score = score
                best_match = AliasMatch(
                    text=text,
                    canonical_id=canonical_id,
                    canonical_name=self._entity_names[canonical_id],
                    score=score,
                    method="fuzzy"
                )

        return best_match

    def find_candidates(self, text: str, limit: int = 5) -> List[AliasMatch]:
        """
        Find all candidate matches above threshold.

        Args:
            text: Text to match
            limit: Maximum number of candidates to return

        Returns:
            List of candidate matches, sorted by score
        """
        normalized = self._normalize(text)
        candidates = []

        # Check exact first
        exact = self.match(text)
        if exact and exact.method == "exact":
            return [exact]

        # Find all fuzzy matches
        for entity_name, canonical_id in self._known_entities.items():
            score = self._fuzzy_score(normalized, entity_name)

            if score >= self.threshold:
                candidates.append(AliasMatch(
                    text=text,
                    canonical_id=canonical_id,
                    canonical_name=self._entity_names[canonical_id],
                    score=score,
                    method="fuzzy"
                ))

        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)

        return candidates[:limit]

    def is_confident_match(self, text: str, confidence_threshold: float = 0.95) -> Optional[str]:
        """
        Check if text matches confidently enough to auto-link.

        Args:
            text: Text to match
            confidence_threshold: Minimum confidence for auto-accept

        Returns:
            Canonical ID if confident match, None otherwise
        """
        match = self.match(text)
        if match and match.score >= confidence_threshold * 100:
            return match.canonical_id
        return None


def create_matcher(
    entities: Dict[str, Tuple[str, List[str]]] = None,
    threshold: int = 70
) -> FuzzyMatcher:
    """
    Create a fuzzy matcher with optional pre-loaded entities.

    Args:
        entities: Dict of canonical_id -> (name, [aliases])
        threshold: Minimum fuzzy match threshold

    Returns:
        Configured FuzzyMatcher
    """
    matcher = FuzzyMatcher(threshold=threshold)

    if entities:
        for canonical_id, (name, aliases) in entities.items():
            matcher.add_entity(canonical_id, name, aliases)

    return matcher
