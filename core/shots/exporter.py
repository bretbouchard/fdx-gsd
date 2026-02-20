"""Shot list export functionality for production tools.

Exports shot lists to CSV (StudioBinder-compatible) and JSON formats.
Follows industry-standard column conventions for shot lists.
"""
import csv
from pathlib import Path
from typing import Any, Dict, List

from .models import Shot, ShotList


# Standard shot list columns (StudioBinder-compatible)
CORE_COLUMNS = [
    "scene_number",
    "shot_number",
    "description",
    "shot_size",
    "camera_angle",
    "movement",
    "subject",
    "location",
    "cast",
    "notes",
]


class ShotListExporter:
    """Exports shot lists to CSV and JSON formats.

    Produces StudioBinder-compatible CSV exports and full JSON
    exports for archiving and tool integration.
    """

    def __init__(self) -> None:
        """Initialize the exporter."""
        pass

    def export_csv(
        self,
        shot_list: ShotList,
        output_path: Path
    ) -> None:
        """Export shot list to CSV file.

        Creates a StudioBinder-compatible CSV with standard columns.

        Args:
            shot_list: ShotList to export
            output_path: Path to output CSV file
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Sort shots by scene_number, then shot_number for consistent output
        sorted_shots = sorted(
            shot_list.shots,
            key=lambda s: (s.scene_number, s.shot_number)
        )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CORE_COLUMNS)
            writer.writeheader()

            for shot in sorted_shots:
                writer.writerow({
                    "scene_number": shot.scene_number,
                    "shot_number": shot.shot_number,
                    "description": shot.description,
                    "shot_size": shot.shot_type.value,
                    "camera_angle": shot.angle.value,
                    "movement": shot.movement.value,
                    "subject": shot.subject or "",
                    "location": shot.location or "",
                    "cast": ", ".join(shot.characters) if shot.characters else "",
                    "notes": shot.notes or "",
                })

    def export_json(
        self,
        shot_list: ShotList,
        output_path: Path
    ) -> None:
        """Export shot list to JSON file.

        Uses ShotList.save() for consistent JSON output.

        Args:
            shot_list: ShotList to export
            output_path: Path to output JSON file
        """
        shot_list.save(output_path)

    def get_summary(self, shot_list: ShotList) -> Dict[str, Any]:
        """Get summary statistics about the shot list.

        Args:
            shot_list: ShotList to analyze

        Returns:
            Dict with total_shots, by_type, by_scene statistics
        """
        return shot_list.get_summary()

    def get_summary_by_type(self, shot_list: ShotList) -> Dict[str, int]:
        """Get shot count breakdown by shot type.

        Args:
            shot_list: ShotList to analyze

        Returns:
            Dict mapping shot type to count
        """
        type_counts: Dict[str, int] = {}
        for shot in shot_list.shots:
            key = shot.shot_type.value
            type_counts[key] = type_counts.get(key, 0) + 1
        return type_counts

    def get_summary_by_scene(self, shot_list: ShotList) -> Dict[int, int]:
        """Get shot count breakdown by scene.

        Args:
            shot_list: ShotList to analyze

        Returns:
            Dict mapping scene number to shot count
        """
        scene_counts: Dict[int, int] = {}
        for shot in shot_list.shots:
            scene_counts[shot.scene_number] = scene_counts.get(shot.scene_number, 0) + 1
        return scene_counts


def export_shot_list_csv(
    shot_list: ShotList,
    output_path: Path
) -> None:
    """Convenience function to export shot list to CSV.

    Args:
        shot_list: ShotList to export
        output_path: Path to output CSV file
    """
    exporter = ShotListExporter()
    exporter.export_csv(shot_list, output_path)


def export_shot_list_json(
    shot_list: ShotList,
    output_path: Path
) -> None:
    """Convenience function to export shot list to JSON.

    Args:
        shot_list: ShotList to export
        output_path: Path to output JSON file
    """
    exporter = ShotListExporter()
    exporter.export_json(shot_list, output_path)
