"""Layout brief export functionality for Blender integration.

Exports layout briefs to JSON format for Blender consumption.
Follows the ShotListExporter pattern from core/shots/exporter.py.

Output structure:
- blender/<scene_id>/layout_brief.json - Per-scene layout files
- build/layout_brief.json - Combined brief with all scenes
"""
import json
from pathlib import Path
from typing import Dict

from .models import LayoutBrief, SceneLayout


class LayoutBriefExporter:
    """Exports layout briefs to JSON format for Blender.

    Creates per-scene JSON files in blender/ directory structure
    and a combined brief in build/ directory.
    """

    def __init__(self, output_path: Path):
        """
        Initialize the exporter.

        Args:
            output_path: Root path for output (project directory)
        """
        self.output_path = Path(output_path)

    def export(self, brief: LayoutBrief) -> Dict[str, Path]:
        """
        Export layout brief to per-scene JSON files.

        Creates:
        - blender/<scene_id>/layout_brief.json for each scene
        - build/layout_brief.json for combined brief

        Args:
            brief: LayoutBrief to export

        Returns:
            Dict mapping scene_id to output file path
        """
        paths = {}

        # Create blender/ directory
        blender_path = self.output_path / "blender"
        blender_path.mkdir(parents=True, exist_ok=True)

        # Export per-scene files
        for scene_layout in brief.scene_layouts:
            scene_dir = blender_path / scene_layout.scene_id
            scene_dir.mkdir(parents=True, exist_ok=True)

            scene_file = scene_dir / "layout_brief.json"
            self._export_scene(scene_layout, scene_file)
            paths[scene_layout.scene_id] = scene_file

        # Export combined brief to build/
        self.export_combined(brief)

        return paths

    def _export_scene(self, scene: SceneLayout, path: Path) -> None:
        """
        Export single scene to JSON.

        Args:
            scene: SceneLayout to export
            path: Output file path
        """
        data = scene.to_dict()
        path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def export_combined(self, brief: LayoutBrief) -> Path:
        """
        Export combined brief to single file.

        Args:
            brief: LayoutBrief to export

        Returns:
            Path to combined brief file
        """
        build_path = self.output_path / "build"
        build_path.mkdir(parents=True, exist_ok=True)

        combined_path = build_path / "layout_brief.json"
        brief.save(combined_path)

        return combined_path


def export_layout_brief(brief: LayoutBrief, output_path: Path) -> Dict[str, Path]:
    """
    Convenience function to export layout brief.

    Args:
        brief: LayoutBrief to export
        output_path: Root path for output

    Returns:
        Dict mapping scene_id to output file path
    """
    exporter = LayoutBriefExporter(output_path)
    return exporter.export(brief)
