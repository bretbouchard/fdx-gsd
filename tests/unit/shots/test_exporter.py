"""Unit tests for ShotListExporter."""
import csv
import json
import tempfile
from pathlib import Path

import pytest

from core.shots.types import ShotType
from core.shots.models import Shot, ShotList
from core.shots.exporter import ShotListExporter


class TestShotListExporter:
    """Tests for ShotListExporter class."""

    @pytest.fixture
    def exporter(self):
        """Create a ShotListExporter instance."""
        return ShotListExporter()

    @pytest.fixture
    def sample_shot_list(self):
        """Create a sample ShotList."""
        shot_list = ShotList(project_id="test-movie")
        shot_list.add_shot(Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.WS,
            description="Establishing - INT. OFFICE - DAY",
            characters=["JOHN", "MARY"],
        ))
        shot_list.add_shot(Shot(
            shot_id="shot_001_002",
            scene_id="scene_001",
            scene_number=1,
            shot_number=2,
            shot_type=ShotType.CU,
            description="Close-up - Emotional moment",
            subject="JOHN",
            characters=["JOHN"],
        ))
        return shot_list

    def test_exporter_initialization(self, exporter):
        """ShotListExporter creates successfully."""
        assert exporter is not None

    def test_export_csv_creates_file(self, exporter, sample_shot_list):
        """export_csv creates file at output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotlist.csv"

            exporter.export_csv(sample_shot_list, output_path)

            assert output_path.exists()

    def test_export_csv_headers(self, exporter, sample_shot_list):
        """CSV has correct column headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotlist.csv"

            exporter.export_csv(sample_shot_list, output_path)

            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)

            assert "scene_number" in headers
            assert "shot_number" in headers
            assert "description" in headers
            assert "shot_size" in headers
            assert "camera_angle" in headers
            assert "movement" in headers
            assert "subject" in headers
            assert "location" in headers
            assert "cast" in headers
            assert "notes" in headers

    def test_export_csv_row_formatting(self, exporter, sample_shot_list):
        """CSV rows have correct values and formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotlist.csv"

            exporter.export_csv(sample_shot_list, output_path)

            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 2
            assert rows[0]["scene_number"] == "1"
            assert rows[0]["shot_number"] == "1"
            assert rows[0]["shot_size"] == "WS"
            assert rows[0]["cast"] == "JOHN, MARY"
            assert rows[1]["shot_size"] == "CU"
            assert rows[1]["subject"] == "JOHN"

    def test_export_csv_empty_shot_list(self, exporter):
        """Handles empty shot list gracefully."""
        shot_list = ShotList(project_id="empty")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotlist.csv"

            exporter.export_csv(shot_list, output_path)

            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Only header row
            assert len(rows) == 1

    def test_export_json_creates_file(self, exporter, sample_shot_list):
        """export_json creates valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotgraph.json"

            exporter.export_json(sample_shot_list, output_path)

            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert data["project_id"] == "test-movie"

    def test_export_json_content(self, exporter, sample_shot_list):
        """JSON file contains correct ShotList data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotgraph.json"

            exporter.export_json(sample_shot_list, output_path)

            data = json.loads(output_path.read_text())

            assert data["project_id"] == "test-movie"
            assert data["total_shots"] == 2
            assert len(data["shots"]) == 2
            assert data["shots"][0]["shot_type"] == "WS"

    def test_get_summary(self, exporter, sample_shot_list):
        """get_summary returns correct statistics."""
        summary = exporter.get_summary(sample_shot_list)

        assert summary["total_shots"] == 2
        assert summary["by_shot_type"]["WS"] == 1
        assert summary["by_shot_type"]["CU"] == 1

    def test_get_summary_by_type(self, exporter, sample_shot_list):
        """Summary includes breakdown by shot type."""
        by_type = exporter.get_summary_by_type(sample_shot_list)

        assert by_type["WS"] == 1
        assert by_type["CU"] == 1

    def test_get_summary_by_scene(self, exporter, sample_shot_list):
        """Summary includes breakdown by scene."""
        by_scene = exporter.get_summary_by_scene(sample_shot_list)

        assert by_scene[1] == 2

    def test_csv_parent_directory_created(self, exporter, sample_shot_list):
        """Creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "shotlist.csv"

            exporter.export_csv(sample_shot_list, output_path)

            assert output_path.exists()

    def test_csv_handles_special_characters(self, exporter):
        """CSV handles special characters in description."""
        shot_list = ShotList(project_id="test")
        shot_list.add_shot(Shot(
            shot_id="shot_001_001",
            scene_id="scene_001",
            scene_number=1,
            shot_number=1,
            shot_type=ShotType.CU,
            description='Close-up - "I love you!" she said, crying.',
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shotlist.csv"

            exporter.export_csv(shot_list, output_path)

            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                row = next(reader)

            assert "I love you" in row["description"]
