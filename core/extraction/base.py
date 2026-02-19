"""Base extractor class for entity extraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from .patterns import ExtractionPattern


@dataclass
class ExtractionCandidate:
    """A candidate entity extracted from text."""
    text: str                      # Original matched text
    normalized: str                # Normalized name
    entity_type: str               # character, location, scene
    confidence: float              # 0.0 to 1.0
    pattern_name: str              # Which pattern matched
    source_file: str               # Path to source file
    line_number: int               # Line in source file
    block_ref: str                 # Evidence block reference
    context: str                   # Surrounding context (for disambiguation)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "normalized": self.normalized,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "pattern_name": self.pattern_name,
            "source_file": self.source_file,
            "line_number": self.line_number,
            "block_ref": self.block_ref,
            "context": self.context,
            "metadata": self.metadata,
        }


class BaseExtractor(ABC):
    """Abstract base class for entity extractors."""

    def __init__(self, patterns: List[ExtractionPattern]):
        self.patterns = patterns
        self._seen: Set[str] = set()  # Track seen candidates

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type this extractor handles."""
        pass

    @abstractmethod
    def is_valid(self, text: str) -> bool:
        """Check if extracted text is a valid entity candidate."""
        pass

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Normalize the extracted text to canonical form."""
        pass

    def extract_from_line(
        self,
        line: str,
        source_file: str,
        line_number: int,
        block_ref: str,
        context_lines: List[str] = None
    ) -> List[ExtractionCandidate]:
        """
        Extract entities from a single line.

        Args:
            line: The text line to extract from
            source_file: Path to source file
            line_number: Line number in source
            block_ref: Evidence block reference
            context_lines: Surrounding lines for context

        Returns:
            List of extraction candidates
        """
        candidates = []
        context = "\n".join(context_lines) if context_lines else line

        for pattern in self.patterns:
            matches = pattern.pattern.finditer(line)

            for match in matches:
                # Get matched text (handle multi-group patterns)
                if match.lastindex and match.lastindex > 1:
                    # Multi-group pattern - combine relevant groups
                    text = " ".join(g for g in match.groups() if g)
                else:
                    text = match.group(1) if match.lastindex else match.group(0)

                text = text.strip()

                if not text or not self.is_valid(text):
                    continue

                normalized = self.normalize(text)

                # Skip duplicates within same extraction run
                dedupe_key = f"{normalized}:{source_file}:{line_number}"
                if dedupe_key in self._seen:
                    continue
                self._seen.add(dedupe_key)

                # Calculate confidence with context bonus
                confidence = pattern.confidence_base

                candidate = ExtractionCandidate(
                    text=text,
                    normalized=normalized,
                    entity_type=self.entity_type,
                    confidence=confidence,
                    pattern_name=pattern.name,
                    source_file=source_file,
                    line_number=line_number,
                    block_ref=block_ref,
                    context=context,
                    metadata=self.extract_metadata(match, line, pattern),
                )

                candidates.append(candidate)

        return candidates

    def extract_metadata(self, match: Any, line: str, pattern: ExtractionPattern = None) -> Dict[str, Any]:
        """
        Extract additional metadata from the match.
        Override in subclasses for entity-specific metadata.
        """
        return {}

    def extract_from_file(self, file_path: Path) -> List[ExtractionCandidate]:
        """
        Extract entities from a file.

        Args:
            file_path: Path to the file

        Returns:
            List of extraction candidates
        """
        candidates = []
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        source_file = str(file_path)

        # Find block refs in lines
        block_ref = ""
        for i, line in enumerate(lines):
            # Look for block ref at end of line (^ev_xxxx)
            import re
            ref_match = re.search(r'\^([a-z0-9_]+)$', line)
            if ref_match:
                block_ref = ref_match.group(1)

            # Get context (surrounding lines)
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 3)
            context_lines = lines[context_start:context_end]

            line_candidates = self.extract_from_line(
                line=line,
                source_file=source_file,
                line_number=i + 1,
                block_ref=block_ref,
                context_lines=context_lines,
            )
            candidates.extend(line_candidates)

        return candidates

    def reset(self):
        """Reset the seen set for a new extraction run."""
        self._seen.clear()
