"""ScriptBuilder - Transforms StoryGraph into ScriptGraph.

Orchestrates the transformation from canonical entities (StoryGraph)
to screenplay paragraphs (ScriptGraph).

Follows the CanonBuilder pattern:
- Load StoryGraph from build/storygraph.json
- Transform scene entities to ScriptGraph scenes
- Generate sluglines, extract beats, link characters/locations
- Write deterministic scriptgraph.json
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .beats import BeatExtractor
from .sluglines import SluglineGenerator


@dataclass
class ScriptBuildResult:
    """Result of a script build operation."""
    success: bool
    scenes_built: int = 0
    paragraphs_created: int = 0
    errors: List[str] = field(default_factory=list)


class ScriptBuilder:
    """Builds ScriptGraph from StoryGraph entities."""

    def __init__(self, project_path: Path, config: Dict[str, Any] = None):
        """
        Initialize the script builder.

        Args:
            project_path: Path to project root
            config: Project configuration from gsd.yaml
        """
        self.project_path = Path(project_path)
        self.config = config or {}

        # Paths
        self.inbox_path = self.project_path / "inbox"
        self.build_path = self.project_path / "build"

        # Components
        self.slugline_generator = SluglineGenerator()
        self.beat_extractor = BeatExtractor()

        # State
        self._storygraph: Optional[Dict] = None
        self._scriptgraph: Optional[Dict] = None

    def build(self) -> ScriptBuildResult:
        """
        Execute the full script build pipeline.

        Returns:
            ScriptBuildResult with statistics
        """
        result = ScriptBuildResult(success=True)

        try:
            # Load StoryGraph
            self._storygraph = self._load_storygraph()

            if not self._storygraph:
                result.errors.append("No storygraph.json found")
                result.success = False
                return result

            # Get all scene entities
            scenes = self._get_scene_entities()

            if not scenes:
                result.errors.append("No scene entities found in storygraph")
                result.success = False
                return result

            # Get known characters for dialogue detection
            character_names = self._get_character_names()

            # Get character entities for dialogue resolution
            character_entities = self._get_character_entities()

            # Update BeatExtractor with character entities
            self.beat_extractor.set_character_entities(character_entities)

            # Build ScriptGraph scenes
            scriptgraph_scenes = []

            for order, scene_entity in enumerate(scenes, start=1):
                try:
                    script_scene = self._build_scene(
                        scene_entity,
                        order,
                        character_names
                    )
                    scriptgraph_scenes.append(script_scene)
                    result.scenes_built += 1
                    result.paragraphs_created += len(script_scene.get("paragraphs", []))
                except Exception as e:
                    result.errors.append(
                        f"Error building scene {scene_entity.get('id')}: {str(e)}"
                    )

            # Build final ScriptGraph
            self._scriptgraph = {
                "version": "1.0",
                "project_id": self._storygraph.get("project_id", self.project_path.name),
                "generated_at": datetime.now().isoformat(),
                "scenes": sorted(scriptgraph_scenes, key=lambda s: s.get("order", 999))
            }

            # Write output
            self._write_scriptgraph(self._scriptgraph)

        except Exception as e:
            result.errors.append(f"Build failed: {str(e)}")
            result.success = False

        return result

    def _load_storygraph(self) -> Optional[Dict]:
        """Load storygraph.json from build directory."""
        storygraph_path = self.build_path / "storygraph.json"

        if not storygraph_path.exists():
            return None

        return json.loads(storygraph_path.read_text(encoding="utf-8"))

    def _get_scene_entities(self) -> List[Dict]:
        """Get all scene entities from StoryGraph, sorted by line number."""
        if not self._storygraph:
            return []

        scenes = [
            e for e in self._storygraph.get("entities", [])
            if e.get("type") == "scene"
        ]

        # Sort by line number for proper ordering
        return sorted(
            scenes,
            key=lambda s: s.get("attributes", {}).get("line_number", 0)
        )

    def _get_character_names(self) -> List[str]:
        """Get all character names from StoryGraph."""
        if not self._storygraph:
            return []

        return [
            e.get("name", "")
            for e in self._storygraph.get("entities", [])
            if e.get("type") == "character"
        ]

    def _get_character_entities(self) -> List[Dict]:
        """Get all character entities from StoryGraph."""
        if not self._storygraph:
            return []

        return [
            e for e in self._storygraph.get("entities", [])
            if e.get("type") == "character"
        ]

    def _build_scene(
        self,
        scene_entity: Dict,
        order: int,
        character_names: List[str]
    ) -> Dict:
        """
        Build a ScriptGraph scene from a StoryGraph scene entity.

        Args:
            scene_entity: Scene entity from StoryGraph
            order: Scene order (1-indexed)
            character_names: Known character names for dialogue detection

        Returns:
            ScriptGraph scene dict
        """
        scene_id = scene_entity.get("id", f"SCN_{order:03d}")
        attributes = scene_entity.get("attributes", {})

        # Generate slugline
        slugline = self.slugline_generator.generate_slugline(
            scene_entity,
            self._storygraph
        )

        # Extract paragraphs from source content
        paragraphs = self._extract_paragraphs(
            scene_entity,
            character_names
        )

        # Build links
        links = self._build_links(scene_entity, paragraphs)

        return {
            "id": scene_id,
            "order": order,
            "slugline": slugline,
            "int_ext": attributes.get("int_ext", "INT"),
            "time_of_day": attributes.get("time_of_day", "DAY"),
            "paragraphs": paragraphs,
            "links": links,
            "metadata": {
                "source_file": attributes.get("source_file", ""),
                "line_number": attributes.get("line_number", 0)
            }
        }

    def _extract_paragraphs(
        self,
        scene_entity: Dict,
        character_names: List[str]
    ) -> List[Dict]:
        """
        Extract paragraphs from scene source content.

        Args:
            scene_entity: Scene entity from StoryGraph
            character_names: Known character names

        Returns:
            List of paragraph dicts
        """
        paragraphs = []
        attributes = scene_entity.get("attributes", {})

        # Get source file and line range
        source_file = attributes.get("source_file", "")
        line_number = attributes.get("line_number", 0)

        if not source_file or not line_number:
            return paragraphs

        # Read source file
        source_path = Path(source_file)
        if not source_path.exists():
            # Try relative to inbox
            source_path = self.inbox_path / source_file
            if not source_path.exists():
                return paragraphs

        try:
            content = source_path.read_text(encoding="utf-8")
        except Exception:
            return paragraphs

        # Find scene boundaries
        # Scene starts at line_number, ends at next scene or EOF
        lines = content.split("\n")
        scene_start = line_number

        # Find next scene boundary
        scene_end = len(lines)
        all_scenes = self._get_scene_entities()
        for other_scene in all_scenes:
            other_line = other_scene.get("attributes", {}).get("line_number", 0)
            if other_line > line_number and other_line < scene_end:
                scene_end = other_line

        # Build block refs from evidence index
        block_refs = self._build_block_refs(scene_entity)

        # Extract all paragraphs (beats + dialogue)
        paragraphs = self.beat_extractor.extract_all(
            content=content,
            scene_start_line=scene_start,
            scene_end_line=scene_end,
            block_refs=block_refs,
            character_names=character_names
        )

        # Ensure all paragraphs have evidence_ids
        for para in paragraphs:
            if "evidence_ids" not in para:
                para["evidence_ids"] = []

        return paragraphs

    def _build_block_refs(self, scene_entity: Dict) -> Dict[int, str]:
        """
        Build block reference mapping from scene evidence.

        Args:
            scene_entity: Scene entity with evidence_ids

        Returns:
            Dict mapping line numbers to block refs
        """
        block_refs = {}
        evidence_ids = scene_entity.get("evidence_ids", [])

        # Map evidence IDs to lines
        # Evidence format: ev_XXXXX
        for ev_id in evidence_ids:
            # Try to extract line number from evidence index
            if self._storygraph:
                evidence_index = self._storygraph.get("evidence_index", {})
                ev_info = evidence_index.get(ev_id, {})
                line_num = ev_info.get("line_number")
                if line_num:
                    block_refs[line_num] = ev_id

        return block_refs

    def _build_links(
        self,
        scene_entity: Dict,
        paragraphs: List[Dict]
    ) -> Dict[str, List[str]]:
        """
        Build link references for a scene.

        Args:
            scene_entity: Scene entity from StoryGraph
            paragraphs: Extracted paragraphs

        Returns:
            Links dict with characters, locations, etc.
        """
        links = {
            "characters": [],
            "locations": [],
            "props": [],
            "wardrobe": [],
            "evidence_ids": sorted(scene_entity.get("evidence_ids", []))
        }

        # Extract character names from paragraphs
        for para in paragraphs:
            if para.get("type") == "character":
                # Extract character name (without extension)
                char_text = para.get("text", "")
                # Remove extension like (V.O.), (O.S.), etc.
                char_name = char_text.split("(")[0].strip()
                if char_name and char_name not in links["characters"]:
                    links["characters"].append(char_name)

            # Collect evidence_ids from all paragraphs
            for ev_id in para.get("evidence_ids", []):
                if ev_id not in links["evidence_ids"]:
                    links["evidence_ids"].append(ev_id)

        # Add location from scene entity
        attributes = scene_entity.get("attributes", {})
        location = attributes.get("location", "")
        if location:
            links["locations"].append(location)

        # Sort all lists for determinism
        links["characters"] = sorted(set(links["characters"]))
        links["locations"] = sorted(set(links["locations"]))
        links["props"] = sorted(set(links["props"]))
        links["wardrobe"] = sorted(set(links["wardrobe"]))
        links["evidence_ids"] = sorted(set(links["evidence_ids"]))

        return links

    def _write_scriptgraph(self, scriptgraph: Dict) -> None:
        """
        Write ScriptGraph to output file.

        Args:
            scriptgraph: ScriptGraph dict to write
        """
        self.build_path.mkdir(parents=True, exist_ok=True)
        scriptgraph_path = self.build_path / "scriptgraph.json"

        # Ensure deterministic output with sorted JSON
        scriptgraph_path.write_text(
            json.dumps(scriptgraph, indent=2, sort_keys=False)
        )


def build_script(project_path: Path, config: Dict = None) -> ScriptBuildResult:
    """
    Convenience function to build script.

    Args:
        project_path: Path to project root
        config: Optional project configuration

    Returns:
        ScriptBuildResult
    """
    builder = ScriptBuilder(project_path, config)
    return builder.build()
