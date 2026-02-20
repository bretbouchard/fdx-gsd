"""ShotSuggester - Orchestrates shot suggestion from ScriptGraph.

Processes ScriptGraph scenes and generates shot suggestions using
the ShotDetector heuristics.

Follows the ScriptBuilder/BaseValidator pattern:
- Load ScriptGraph from build/scriptgraph.json
- Process each scene for shot opportunities
- Always add establishing wide shot as first shot of each scene
- Export via ShotListExporter
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .detector import ShotDetector
from .exporter import ShotListExporter
from .models import Shot, ShotList
from .types import CameraAngle, CameraMovement, ShotType


@dataclass
class ShotSuggestionResult:
    """Result of a shot suggestion operation."""

    success: bool
    scenes_processed: int = 0
    shots_suggested: int = 0
    errors: List[str] = field(default_factory=list)


class ShotSuggester:
    """Orchestrates shot suggestion from ScriptGraph scenes.

    Processes each scene in the ScriptGraph and generates shot
    suggestions based on dialogue emotion, action movement, and
    detail indicators. Every scene starts with an establishing
    wide shot.
    """

    def __init__(self, build_path: Path):
        """
        Initialize the shot suggester.

        Args:
            build_path: Path to build directory containing scriptgraph.json
        """
        self.build_path = Path(build_path)

        # Components
        self._detector = ShotDetector()
        self._exporter = ShotListExporter()

        # State
        self._scriptgraph: Optional[Dict] = None
        self._shots: List[Shot] = []
        self._shot_counter: int = 0
        self._project_id: str = ""

    def _load_scriptgraph(self) -> None:
        """Load scriptgraph.json from build directory."""
        scriptgraph_path = self.build_path / "scriptgraph.json"

        if not scriptgraph_path.exists():
            return

        self._scriptgraph = json.loads(
            scriptgraph_path.read_text(encoding="utf-8")
        )
        self._project_id = self._scriptgraph.get(
            "project_id", self.build_path.parent.name
        )

    def _create_shot_id(self, scene_number: int) -> str:
        """
        Create a unique shot ID.

        Format: shot_XXX_YYY where XXX is scene number, YYY is global counter.

        Args:
            scene_number: Scene number for the shot

        Returns:
            Unique shot ID string
        """
        self._shot_counter += 1
        return f"shot_{scene_number:03d}_{self._shot_counter:03d}"

    def _add_shot(
        self,
        scene: Dict[str, Any],
        shot_type: ShotType,
        description: str,
        shot_order: int,
        **kwargs
    ) -> Shot:
        """
        Create and add a shot to the list.

        Args:
            scene: Scene dict with id, order, slugline
            shot_type: Type of shot
            description: Shot description
            shot_order: Order within the scene
            **kwargs: Additional Shot fields (angle, movement, subject, etc.)

        Returns:
            The created Shot
        """
        shot = Shot(
            shot_id=self._create_shot_id(scene.get("order", 0)),
            scene_id=scene.get("id", ""),
            scene_number=scene.get("order", 0),
            shot_number=shot_order,
            shot_type=shot_type,
            angle=kwargs.get("angle", CameraAngle.EYE_LEVEL),
            movement=kwargs.get("movement", CameraMovement.STATIC),
            description=description,
            subject=kwargs.get("subject"),
            characters=kwargs.get("characters", []),
            location=kwargs.get("location", ""),
            evidence_ids=kwargs.get("evidence_ids", []),
            notes=kwargs.get("notes"),
        )
        self._shots.append(shot)
        return shot

    def _suggest_for_scene(self, scene: Dict[str, Any]) -> int:
        """
        Generate shot suggestions for a single scene.

        Always adds an establishing wide shot first, then analyzes
        paragraphs for additional shot opportunities.

        Args:
            scene: Scene dict with paragraphs

        Returns:
            Number of shots suggested for this scene
        """
        shot_count = 0
        scene_number = scene.get("order", 0)
        slugline = scene.get("slugline", f"Scene {scene_number}")

        # Always add establishing shot first
        self._add_shot(
            scene=scene,
            shot_type=ShotType.WS,
            description=f"Establishing - {slugline}",
            shot_order=1,
        )
        shot_count += 1

        # Get scene characters for two-shot detection
        scene_characters = scene.get("links", {}).get("characters", [])
        paragraphs = scene.get("paragraphs", [])

        # Track unique characters for potential two-shot
        characters_with_dialogue: List[str] = []

        # Analyze each paragraph for shot opportunities
        for paragraph in paragraphs:
            shot = self._detector.detect_from_paragraph(
                paragraph=paragraph,
                scene=scene,
                shot_order=shot_count + 1
            )

            if shot:
                # Assign proper shot_id
                shot.shot_id = self._create_shot_id(scene_number)
                shot.shot_number = shot_count + 1
                self._shots.append(shot)
                shot_count += 1

            # Track characters with dialogue
            if paragraph.get("type") == "character":
                char_text = paragraph.get("text", "").split("(")[0].strip()
                if char_text and char_text not in characters_with_dialogue:
                    characters_with_dialogue.append(char_text)

        # Add OTS/TWO shot if exactly 2 characters have dialogue
        if self._detector.should_add_two_shot(characters_with_dialogue):
            # Add OTS shot for dialogue between two characters
            self._add_shot(
                scene=scene,
                shot_type=ShotType.OTS,
                description="Over-the-shoulder - Two-character dialogue",
                shot_order=shot_count + 1,
                characters=characters_with_dialogue,
            )
            shot_count += 1

        return shot_count

    def suggest(self) -> ShotSuggestionResult:
        """
        Execute the shot suggestion pipeline.

        Returns:
            ShotSuggestionResult with statistics
        """
        result = ShotSuggestionResult(success=True)

        try:
            # Load ScriptGraph
            self._load_scriptgraph()

            if not self._scriptgraph:
                result.errors.append("No scriptgraph.json found")
                result.success = False
                return result

            scenes = self._scriptgraph.get("scenes", [])

            if not scenes:
                result.errors.append("No scenes found in scriptgraph")
                result.success = False
                return result

            # Process each scene
            for scene in scenes:
                try:
                    shots_added = self._suggest_for_scene(scene)
                    result.scenes_processed += 1
                    result.shots_suggested += shots_added
                except Exception as e:
                    scene_id = scene.get("id", "unknown")
                    result.errors.append(
                        f"Error processing scene {scene_id}: {str(e)}"
                    )

        except Exception as e:
            result.errors.append(f"Suggestion failed: {str(e)}")
            result.success = False

        return result

    def get_shots(self) -> List[Shot]:
        """
        Get all suggested shots, sorted by scene and shot number.

        Returns:
            Sorted list of Shot objects
        """
        return sorted(
            self._shots,
            key=lambda s: (s.scene_number, s.shot_number)
        )

    def get_shot_list(self) -> ShotList:
        """
        Get a ShotList containing all suggested shots.

        Returns:
            ShotList with project_id and sorted shots
        """
        shot_list = ShotList(
            project_id=self._project_id,
            shots=self.get_shots()
        )
        return shot_list

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the suggested shots.

        Returns:
            Dict with total_shots, by_type, by_scene
        """
        shot_list = self.get_shot_list()
        return shot_list.get_summary()


def suggest_shots(build_path: Path) -> ShotSuggestionResult:
    """
    Convenience function to suggest shots from ScriptGraph.

    Args:
        build_path: Path to build directory

    Returns:
        ShotSuggestionResult
    """
    suggester = ShotSuggester(build_path)
    return suggester.suggest()
