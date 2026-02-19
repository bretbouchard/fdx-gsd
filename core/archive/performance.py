"""Performance management for live recordings and takes.

Provides:
- Create performances with audio/video directories
- File copying for audio and video recordings
- List and retrieve performances
"""
import json
import shutil
import uuid
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Performance, PerformanceMetadata
from .registry import WorkRegistry


class PerformanceManager:
    """Manages performances (live recordings, takes)."""

    # Valid audio extensions
    AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".aiff", ".ogg", ".m4a"}

    # Valid video extensions
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    def __init__(self, archive_path: Path):
        """
        Initialize the performance manager.

        Args:
            archive_path: Path to the archive directory
        """
        self.archive_path = Path(archive_path)
        self._registry = WorkRegistry(archive_path)

    def create_performance(
        self,
        work_id: str,
        date: date_type,
        venue: str | None = None,
        city: str | None = None,
        personnel: list[str] | None = None,
        setlist_position: int | None = None,
        notes: str | None = None,
    ) -> Performance:
        """
        Create a new performance.

        Args:
            work_id: Parent work ID
            date: Performance date (required)
            venue: Venue name
            city: City
            personnel: List of performers/crew
            setlist_position: Position in setlist
            notes: Additional notes

        Returns:
            Created Performance model

        Raises:
            ValueError: If work doesn't exist
        """
        # Verify work exists
        work = self._registry.get_work(work_id)
        if not work:
            raise ValueError(f"Work not found: {work_id}")

        # Generate ID
        performance_id = f"perf_{uuid.uuid4().hex[:8]}"

        # Create metadata
        metadata = PerformanceMetadata(
            date=date,
            venue=venue,
            city=city,
            personnel=personnel or [],
            setlist_position=setlist_position,
            notes=notes,
        )

        # Create performance
        performance = Performance(
            id=performance_id,
            work_id=work_id,
            metadata=metadata,
            audio=[],
            video=[],
            created_at=datetime.now(),
        )

        # Create performance directory
        performance_dir = (
            self.archive_path / "works" / work_id / "performances" / performance_id
        )
        performance_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (performance_dir / "audio").mkdir(exist_ok=True)
        (performance_dir / "video").mkdir(exist_ok=True)

        # Write metadata.json
        metadata_path = performance_dir / "metadata.json"
        metadata_path.write_text(json.dumps(performance.model_dump(), indent=2, default=str))

        # Update parent work's performances list
        work.performances.append(performance_id)
        work_dir = self.archive_path / "works" / work_id
        work_metadata_path = work_dir / "metadata.json"
        work_metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

        return performance

    def get_performance(self, performance_id: str) -> Optional[Performance]:
        """
        Retrieve a performance by ID.

        Args:
            performance_id: The performance ID

        Returns:
            Performance model if found, None otherwise
        """
        # Find performance directory by searching works
        works_dir = self.archive_path / "works"
        if not works_dir.exists():
            return None

        for work_dir in works_dir.iterdir():
            if not work_dir.is_dir():
                continue

            performance_dir = work_dir / "performances" / performance_id
            metadata_path = performance_dir / "metadata.json"

            if metadata_path.exists():
                try:
                    data = json.loads(metadata_path.read_text())
                    return Performance(**data)
                except (json.JSONDecodeError, TypeError):
                    return None

        return None

    def list_performances(self, work_id: str) -> list[Performance]:
        """
        List all performances for a work.

        Args:
            work_id: The parent work ID

        Returns:
            List of Performance models
        """
        performances = []
        performances_dir = self.archive_path / "works" / work_id / "performances"

        if not performances_dir.exists():
            return performances

        for perf_dir in performances_dir.iterdir():
            if not perf_dir.is_dir():
                continue

            performance = self.get_performance(perf_dir.name)
            if performance:
                performances.append(performance)

        return performances

    def add_audio(
        self, performance_id: str, file_path: Path, filename: str | None = None
    ) -> str:
        """
        Copy an audio file to the performance.

        Args:
            performance_id: The performance ID
            file_path: Path to the audio file
            filename: Optional new filename

        Returns:
            Relative path within archive

        Raises:
            ValueError: If performance not found or invalid file type
        """
        performance = self.get_performance(performance_id)
        if not performance:
            raise ValueError(f"Performance not found: {performance_id}")

        # Validate extension
        if file_path.suffix.lower() not in self.AUDIO_EXTENSIONS:
            raise ValueError(
                f"Invalid audio file type: {file_path.suffix}. "
                f"Valid types: {', '.join(self.AUDIO_EXTENSIONS)}"
            )

        # Copy file
        dest_filename = filename or file_path.name
        dest_path = (
            self.archive_path
            / "works"
            / performance.work_id
            / "performances"
            / performance_id
            / "audio"
            / dest_filename
        )

        # Handle existing files
        if dest_path.exists():
            base = dest_path.stem
            ext = dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_path.parent / f"{base}_{counter}{ext}"
                counter += 1

        shutil.copy2(file_path, dest_path)

        # Update performance
        relative_path = str(dest_path.relative_to(self.archive_path))
        performance.audio.append(relative_path)
        self._save_performance(performance)

        return relative_path

    def add_video(
        self, performance_id: str, file_path: Path, filename: str | None = None
    ) -> str:
        """
        Copy a video file to the performance.

        Args:
            performance_id: The performance ID
            file_path: Path to the video file
            filename: Optional new filename

        Returns:
            Relative path within archive

        Raises:
            ValueError: If performance not found or invalid file type
        """
        performance = self.get_performance(performance_id)
        if not performance:
            raise ValueError(f"Performance not found: {performance_id}")

        # Validate extension
        if file_path.suffix.lower() not in self.VIDEO_EXTENSIONS:
            raise ValueError(
                f"Invalid video file type: {file_path.suffix}. "
                f"Valid types: {', '.join(self.VIDEO_EXTENSIONS)}"
            )

        # Copy file
        dest_filename = filename or file_path.name
        dest_path = (
            self.archive_path
            / "works"
            / performance.work_id
            / "performances"
            / performance_id
            / "video"
            / dest_filename
        )

        # Handle existing files
        if dest_path.exists():
            base = dest_path.stem
            ext = dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_path.parent / f"{base}_{counter}{ext}"
                counter += 1

        shutil.copy2(file_path, dest_path)

        # Update performance
        relative_path = str(dest_path.relative_to(self.archive_path))
        performance.video.append(relative_path)
        self._save_performance(performance)

        return relative_path

    def delete_performance(self, performance_id: str) -> bool:
        """
        Delete a performance and its files.

        Args:
            performance_id: The performance ID

        Returns:
            True if deleted, False if not found
        """
        performance = self.get_performance(performance_id)
        if not performance:
            return False

        # Delete directory
        performance_dir = (
            self.archive_path
            / "works"
            / performance.work_id
            / "performances"
            / performance_id
        )
        shutil.rmtree(performance_dir)

        # Update parent work's performances list
        work = self._registry.get_work(performance.work_id)
        if work and performance_id in work.performances:
            work.performances.remove(performance_id)
            work_dir = self.archive_path / "works" / performance.work_id
            work_metadata_path = work_dir / "metadata.json"
            work_metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

        return True

    def _save_performance(self, performance: Performance) -> None:
        """Save performance to metadata.json."""
        performance_dir = (
            self.archive_path
            / "works"
            / performance.work_id
            / "performances"
            / performance.id
        )
        metadata_path = performance_dir / "metadata.json"
        metadata_path.write_text(json.dumps(performance.model_dump(), indent=2, default=str))
