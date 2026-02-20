"""LayoutBriefGenerator - Generates layout briefs from ScriptGraph + ShotGraph.

Processes ScriptGraph scenes and ShotGraph shots to produce spatial layout
data for Blender 3D previz.

Follows the ShotSuggester pattern:
- Load ScriptGraph from build/scriptgraph.json
- Load ShotGraph from build/shotgraph.json
- For each scene: create SceneLayout with characters, cameras, props
- Export via LayoutBriefExporter
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .camera_math import calculate_camera_position, get_camera_setup_dict
from .models import (
    CameraSetup,
    CharacterPosition,
    LayoutBrief,
    PropPosition,
    SceneLayout,
)


@dataclass
class LayoutGenerationResult:
    """Result of a layout brief generation operation."""

    success: bool
    scenes_processed: int = 0
    layouts_generated: int = 0
    errors: List[str] = field(default_factory=list)


class LayoutBriefGenerator:
    """Generates layout briefs from ScriptGraph + ShotGraph.

    Creates spatial layout data for Blender consumption:
    - Character positions (simple grid layout for now)
    - Camera setups (from shot suggestions)
    - Scene environment metadata
    """

    def __init__(self, build_path: Path):
        """
        Initialize the layout generator.

        Args:
            build_path: Path to build directory containing scriptgraph.json
                        and shotgraph.json
        """
        self.build_path = Path(build_path)

        # State
        self._scriptgraph: Optional[Dict] = None
        self._shotgraph: Optional[Dict] = None
        self._project_id: str = ""
        self._scene_layouts: List[SceneLayout] = []

    def _load_source_data(self) -> None:
        """Load scriptgraph.json and shotgraph.json from build directory."""
        # Load ScriptGraph
        scriptgraph_path = self.build_path / "scriptgraph.json"
        if scriptgraph_path.exists():
            self._scriptgraph = json.loads(
                scriptgraph_path.read_text(encoding="utf-8")
            )
            self._project_id = self._scriptgraph.get(
                "project_id", self.build_path.parent.name
            )
        else:
            self._scriptgraph = None

        # Load ShotGraph
        shotgraph_path = self.build_path / "shotgraph.json"
        if shotgraph_path.exists():
            self._shotgraph = json.loads(
                shotgraph_path.read_text(encoding="utf-8")
            )
        else:
            self._shotgraph = None

    def _get_shots_for_scene(self, scene_id: str) -> List[Dict[str, Any]]:
        """
        Get all shots for a scene from ShotGraph.

        Args:
            scene_id: Scene identifier

        Returns:
            List of shot dictionaries for the scene
        """
        if not self._shotgraph:
            return []

        shots = []
        for shot in self._shotgraph.get("shots", []):
            if shot.get("scene_id") == scene_id:
                shots.append(shot)

        # Sort by shot_number
        return sorted(shots, key=lambda s: s.get("shot_number", 0))

    def _build_character_positions(
        self, scene_data: Dict[str, Any]
    ) -> List[CharacterPosition]:
        """
        Create character positions from scene character links.

        Uses simple grid layout (characters spaced along X axis).
        Props extraction is deferred to future work (blocking analysis).

        Args:
            scene_data: Scene dict with character links

        Returns:
            List of CharacterPosition objects
        """
        characters = []

        # Get character IDs from scene links
        char_ids = scene_data.get("links", {}).get("characters", [])

        if not char_ids:
            return characters

        # Space characters along X axis
        # Position: x = (index - count/2) * 1.5, y = 0, z = 0
        # This centers the group around x=0
        count = len(char_ids)
        spacing = 1.5  # 1.5 meters between characters

        for idx, char_id in enumerate(sorted(char_ids)):  # Sort for determinism
            # Calculate position
            x = (idx - (count - 1) / 2) * spacing
            y = 0.0
            z = 0.0

            # Extract character name from ID (CHAR_name -> name)
            name = char_id.replace("CHAR_", "").replace("_", " ").title()

            # Get evidence IDs from scene
            scene_evidence = scene_data.get("links", {}).get("evidence_ids", [])

            char_pos = CharacterPosition(
                character_id=char_id,
                name=name,
                position={"x": x, "y": y, "z": z},
                facing={"x": 0, "y": 1, "z": 0},  # Facing forward (positive Y)
                posture="standing",
                blocking_notes="",
                evidence_ids=scene_evidence,
            )
            characters.append(char_pos)

        return characters

    def _build_camera_setup(
        self, shot: Dict[str, Any], characters: List[CharacterPosition]
    ) -> CameraSetup:
        """
        Build camera setup from shot using camera_math.

        Args:
            shot: Shot dict with shot_type, shot_id, etc.
            characters: List of character positions (for subject)

        Returns:
            CameraSetup object
        """
        shot_type = shot.get("shot_type", "MS")
        shot_id = shot.get("shot_id", "unknown")

        # Get subject position (first character or default)
        if characters:
            subject_pos = (
                characters[0].position["x"],
                characters[0].position["y"],
                characters[0].position["z"],
            )
            target = characters[0].position.copy()
        else:
            subject_pos = (0.0, 0.0, 0.0)
            target = {"x": 0, "y": 0, "z": 1.6}  # Eye level

        # Calculate camera position
        camera_dict = get_camera_setup_dict(shot_type, subject_pos)

        # Build CameraSetup
        setup = CameraSetup(
            setup_id=f"CAM_{shot_id}",
            shot_id=shot_id,
            shot_type=shot_type,
            camera=camera_dict,
            target=target,
            movement=shot.get("movement", "Static"),
            description=shot.get("description", ""),
            evidence_ids=shot.get("evidence_ids", []),
        )

        return setup

    def _build_scene_layout(
        self, scene_data: Dict[str, Any], shots: List[Dict[str, Any]]
    ) -> SceneLayout:
        """
        Build scene layout from scene + shots.

        Args:
            scene_data: Scene dict with metadata
            shots: List of shot dicts for this scene

        Returns:
            SceneLayout object
        """
        scene_id = scene_data.get("id", "")

        # Build character positions
        characters = self._build_character_positions(scene_data)

        # Build camera setups from shots
        camera_setups = []
        for shot in shots:
            cam_setup = self._build_camera_setup(shot, characters)
            camera_setups.append(cam_setup)

        # Props extraction deferred (empty for now)
        # Future: extract from action descriptions, prop mentions
        props: List[PropPosition] = []

        # Build environment dict
        int_ext = scene_data.get("int_ext", "INT")
        time_of_day = scene_data.get("time_of_day", "DAY")

        # Lighting preset based on int_ext and time
        if int_ext == "EXT":
            if time_of_day == "DAY":
                lighting = "outdoor_day"
            elif time_of_day == "NIGHT":
                lighting = "outdoor_night"
            else:
                lighting = "outdoor"
        else:
            if time_of_day == "NIGHT":
                lighting = "interior_night"
            else:
                lighting = "interior_day"

        environment = {
            "description": f"{int_ext} - {time_of_day}",
            "lighting_preset": lighting,
        }

        # Get location ID from links
        location_id = ""
        loc_links = scene_data.get("links", {}).get("locations", [])
        if loc_links:
            location_id = loc_links[0]

        # Get evidence IDs from scene
        evidence_ids = scene_data.get("links", {}).get("evidence_ids", [])

        return SceneLayout(
            scene_id=scene_id,
            slugline=scene_data.get("slugline", ""),
            location_id=location_id,
            int_ext=int_ext,
            time_of_day=time_of_day,
            environment=environment,
            characters=characters,
            props=props,
            camera_setups=camera_setups,
            evidence_ids=evidence_ids,
        )

    def generate(self) -> LayoutBrief:
        """
        Execute the layout generation pipeline.

        Returns:
            LayoutBrief with all scene layouts
        """
        # Load source data
        self._load_source_data()

        if not self._scriptgraph:
            raise ValueError("No scriptgraph.json found")

        scenes = self._scriptgraph.get("scenes", [])

        if not scenes:
            raise ValueError("No scenes found in scriptgraph")

        # Process each scene
        self._scene_layouts = []

        for scene_data in scenes:
            scene_id = scene_data.get("id", "")

            # Get shots for this scene
            shots = self._get_shots_for_scene(scene_id)

            # Build scene layout
            scene_layout = self._build_scene_layout(scene_data, shots)
            self._scene_layouts.append(scene_layout)

        # Build LayoutBrief
        brief = LayoutBrief(
            version="1.0",
            project_id=self._project_id,
            scene_layouts=self._scene_layouts,
            generated_at=datetime.now(),
        )

        return brief

    def get_layout_brief(self) -> LayoutBrief:
        """
        Get the generated LayoutBrief.

        Must call generate() first.

        Returns:
            LayoutBrief with all scene layouts
        """
        if not self._scene_layouts:
            raise ValueError("No layouts generated. Call generate() first.")

        return LayoutBrief(
            version="1.0",
            project_id=self._project_id,
            scene_layouts=self._scene_layouts,
            generated_at=datetime.now(),
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the generated layouts.

        Returns:
            Dict with total_scenes, characters, cameras, etc.
        """
        if not self._scene_layouts:
            return {
                "total_scenes": 0,
                "total_characters": 0,
                "total_props": 0,
                "total_cameras": 0,
            }

        return {
            "total_scenes": len(self._scene_layouts),
            "total_characters": sum(len(s.characters) for s in self._scene_layouts),
            "total_props": sum(len(s.props) for s in self._scene_layouts),
            "total_cameras": sum(len(s.camera_setups) for s in self._scene_layouts),
        }


def generate_layout_brief(build_path: Path) -> LayoutGenerationResult:
    """
    Convenience function to generate layout brief.

    Args:
        build_path: Path to build directory

    Returns:
        LayoutGenerationResult with statistics
    """
    result = LayoutGenerationResult(success=True)

    try:
        generator = LayoutBriefGenerator(build_path)
        generator.generate()
        result.scenes_processed = len(generator._scene_layouts)
        result.layouts_generated = len(generator._scene_layouts)
    except Exception as e:
        result.errors.append(str(e))
        result.success = False

    return result
