"""Scene detection (CAN-03).

Detects scene boundaries from screenplay text using lightweight patterns.
Per ADR-0002: No ML library, interactive disambiguation.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base import BaseExtractor, ExtractionCandidate
from .patterns import (
    SCENE_PATTERNS,
    ExtractionPattern,
    get_time_of_day,
    get_int_ext,
)


@dataclass
class SceneBoundary:
    """Represents a detected scene boundary."""
    line_number: int
    scene_type: str              # slugline, transition, time_jump
    slugline: Optional[str]      # Full slugline text if applicable
    location: Optional[str]      # Extracted location name
    int_ext: Optional[str]       # INT, EXT, or INT./EXT
    time_of_day: Optional[str]   # DAY, NIGHT, etc.
    confidence: float
    block_ref: str
    context: str


class SceneExtractor(BaseExtractor):
    """Extract scene boundaries from text."""

    def __init__(self):
        super().__init__(SCENE_PATTERNS)
        self._scene_number = 0

    @property
    def entity_type(self) -> str:
        return "scene"

    def is_valid(self, text: str) -> bool:
        """Scenes are always valid when detected by patterns."""
        return len(text.strip()) > 0

    def normalize(self, text: str) -> str:
        """Normalize scene to a standard format."""
        # For scenes, we return the slugline or transition marker
        return text.strip().upper()

    def extract_metadata(self, match: Any, line: str, pattern: ExtractionPattern = None) -> Dict[str, Any]:
        """Extract scene-specific metadata."""
        metadata = {}

        # Extract time of day
        time = get_time_of_day(line)
        if time:
            metadata["time_of_day"] = time

        # Extract INT/EXT
        int_ext = get_int_ext(line)
        if int_ext:
            metadata["int_ext"] = int_ext

        # Use pattern name to determine scene type
        if pattern:
            if "slugline" in pattern.name:
                metadata["scene_type"] = "slugline"
                if match.lastindex and match.lastindex >= 2:
                    metadata["location"] = match.group(2).strip()
                    metadata["slugline"] = match.group(0).strip()

            elif "transition" in pattern.name:
                metadata["scene_type"] = "transition"
                metadata["transition"] = match.group(1).strip()

            elif "time_jump" in pattern.name:
                metadata["scene_type"] = "time_jump"
                metadata["time_marker"] = match.group(1).strip()

        return metadata

    def extract_from_line(
        self,
        line: str,
        source_file: str,
        line_number: int,
        block_ref: str,
        context_lines: List[str] = None
    ) -> List[ExtractionCandidate]:
        """
        Extract scene boundaries from a line.

        Extends base to handle scene numbering.
        """
        candidates = super().extract_from_line(
            line=line,
            source_file=source_file,
            line_number=line_number,
            block_ref=block_ref,
            context_lines=context_lines,
        )

        # Add scene number to metadata for sluglines
        for candidate in candidates:
            if candidate.metadata.get("scene_type") == "slugline":
                self._scene_number += 1
                candidate.metadata["scene_number"] = self._scene_number

        return candidates

    def reset(self):
        """Reset extractor state including scene counter."""
        super().reset()
        self._scene_number = 0

    def detect_boundaries(self, content: str, source_file: str = "") -> List[SceneBoundary]:
        """
        Detect all scene boundaries in content.

        Args:
            content: Full text content
            source_file: Source file path

        Returns:
            List of scene boundaries
        """
        boundaries = []
        lines = content.split("\n")

        # Reset scene counter
        self._scene_number = 0

        # Find block refs
        block_ref = ""
        for i, line in enumerate(lines):
            import re
            ref_match = re.search(r'\^([a-z0-9_]+)$', line)
            if ref_match:
                block_ref = ref_match.group(1)

            # Get context
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 3)
            context = "\n".join(lines[context_start:context_end])

            # Check for slugline (primary scene boundary)
            slugline_match = SCENE_PATTERNS[0].pattern.search(line)
            if slugline_match:
                self._scene_number += 1
                boundaries.append(SceneBoundary(
                    line_number=i + 1,
                    scene_type="slugline",
                    slugline=slugline_match.group(0).strip(),
                    location=slugline_match.group(2).strip() if slugline_match.lastindex >= 2 else None,
                    int_ext=get_int_ext(line),
                    time_of_day=get_time_of_day(line),
                    confidence=0.95,
                    block_ref=block_ref,
                    context=context,
                ))
                continue

            # Check for transition markers
            transition_match = SCENE_PATTERNS[1].pattern.search(line)
            if transition_match:
                boundaries.append(SceneBoundary(
                    line_number=i + 1,
                    scene_type="transition",
                    slugline=None,
                    location=None,
                    int_ext=None,
                    time_of_day=None,
                    confidence=0.9,
                    block_ref=block_ref,
                    context=context,
                ))
                continue

            # Check for time jumps (lower confidence)
            time_jump_match = SCENE_PATTERNS[2].pattern.search(line)
            if time_jump_match:
                boundaries.append(SceneBoundary(
                    line_number=i + 1,
                    scene_type="time_jump",
                    slugline=None,
                    location=None,
                    int_ext=None,
                    time_of_day=time_jump_match.group(1),
                    confidence=0.7,
                    block_ref=block_ref,
                    context=context,
                ))

        return boundaries


def detect_scenes(
    text: str,
    source_file: str = ""
) -> List[SceneBoundary]:
    """
    Convenience function to detect scene boundaries.

    Args:
        text: Text to analyze
        source_file: Source file path

    Returns:
        List of scene boundaries
    """
    extractor = SceneExtractor()
    return extractor.detect_boundaries(text, source_file)
