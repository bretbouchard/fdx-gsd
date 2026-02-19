"""Script composition module.

Transforms StoryGraph entities into ScriptGraph screenplay structure.

Components:
- ScriptBuilder: Main orchestrator for script building
- SluglineGenerator: Generates INT./EXT. LOCATION - TIME sluglines
- BeatExtractor: Extracts action beats and dialogue from text
"""
from .builder import ScriptBuilder, ScriptBuildResult, build_script
from .sluglines import SluglineGenerator, generate_slugline
from .beats import BeatExtractor, extract_beats

__all__ = [
    # Builder
    "ScriptBuilder",
    "ScriptBuildResult",
    "build_script",
    # Sluglines
    "SluglineGenerator",
    "generate_slugline",
    # Beats
    "BeatExtractor",
    "extract_beats",
]
