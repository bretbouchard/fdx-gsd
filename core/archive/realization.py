"""Realization management for studio versions, demos, and remixes.

Provides:
- Create realizations with session/stem/master directories
- File copying for DAW sessions, stems, and masters
- List and retrieve realizations
"""
import json
import shutil
import uuid
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Realization, RealizationMetadata
from .registry import WorkRegistry


class RealizationManager:
    """Manages realizations (studio versions, demos, remixes)."""

    # Valid DAW session extensions
    SESSION_EXTENSIONS = {".als", ".flp", ".ptx", ".logic"}

    # Valid audio extensions for stems and masters
    AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".aiff", ".ogg", ".m4a"}

    def __init__(self, archive_path: Path):
        """
        Initialize the realization manager.

        Args:
            archive_path: Path to the archive directory
        """
        self.archive_path = Path(archive_path)
        self._registry = WorkRegistry(archive_path)

    def create_realization(
        self,
        work_id: str,
        name: str,
        date: date_type | None = None,
        studio: str | None = None,
        engineer: str | None = None,
        producer: str | None = None,
        version: str | None = None,
        notes: str | None = None,
    ) -> Realization:
        """
        Create a new realization.

        Args:
            work_id: Parent work ID
            name: Realization name (e.g., "Studio Version")
            date: Realization date
            studio: Studio name
            engineer: Engineer name
            producer: Producer name
            version: Version identifier
            notes: Additional notes

        Returns:
            Created Realization model

        Raises:
            ValueError: If work doesn't exist
        """
        # Verify work exists
        work = self._registry.get_work(work_id)
        if not work:
            raise ValueError(f"Work not found: {work_id}")

        # Generate ID
        realization_id = f"real_{uuid.uuid4().hex[:8]}"

        # Create metadata
        metadata = RealizationMetadata(
            name=name,
            date=date,
            studio=studio,
            engineer=engineer,
            producer=producer,
            version=version,
            notes=notes,
        )

        # Create realization
        realization = Realization(
            id=realization_id,
            work_id=work_id,
            metadata=metadata,
            sessions=[],
            stems=[],
            masters=[],
            created_at=datetime.now(),
        )

        # Create realization directory
        realization_dir = (
            self.archive_path / "works" / work_id / "realizations" / realization_id
        )
        realization_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (realization_dir / "sessions").mkdir(exist_ok=True)
        (realization_dir / "stems").mkdir(exist_ok=True)
        (realization_dir / "masters").mkdir(exist_ok=True)

        # Write metadata.json
        metadata_path = realization_dir / "metadata.json"
        metadata_path.write_text(json.dumps(realization.model_dump(), indent=2, default=str))

        # Update parent work's realizations list
        work.realizations.append(realization_id)
        work_dir = self.archive_path / "works" / work_id
        work_metadata_path = work_dir / "metadata.json"
        work_metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

        return realization

    def get_realization(self, realization_id: str) -> Optional[Realization]:
        """
        Retrieve a realization by ID.

        Args:
            realization_id: The realization ID

        Returns:
            Realization model if found, None otherwise
        """
        # Find realization directory by searching works
        works_dir = self.archive_path / "works"
        if not works_dir.exists():
            return None

        for work_dir in works_dir.iterdir():
            if not work_dir.is_dir():
                continue

            realization_dir = work_dir / "realizations" / realization_id
            metadata_path = realization_dir / "metadata.json"

            if metadata_path.exists():
                try:
                    data = json.loads(metadata_path.read_text())
                    return Realization(**data)
                except (json.JSONDecodeError, TypeError):
                    return None

        return None

    def list_realizations(self, work_id: str) -> list[Realization]:
        """
        List all realizations for a work.

        Args:
            work_id: The parent work ID

        Returns:
            List of Realization models
        """
        realizations = []
        realizations_dir = self.archive_path / "works" / work_id / "realizations"

        if not realizations_dir.exists():
            return realizations

        for real_dir in realizations_dir.iterdir():
            if not real_dir.is_dir():
                continue

            realization = self.get_realization(real_dir.name)
            if realization:
                realizations.append(realization)

        return realizations

    def add_session_file(
        self, realization_id: str, file_path: Path, filename: str | None = None
    ) -> str:
        """
        Copy a DAW session file to the realization.

        Args:
            realization_id: The realization ID
            file_path: Path to the session file
            filename: Optional new filename

        Returns:
            Relative path within archive

        Raises:
            ValueError: If realization not found or invalid file type
        """
        realization = self.get_realization(realization_id)
        if not realization:
            raise ValueError(f"Realization not found: {realization_id}")

        # Validate extension
        if file_path.suffix.lower() not in self.SESSION_EXTENSIONS:
            raise ValueError(
                f"Invalid session file type: {file_path.suffix}. "
                f"Valid types: {', '.join(self.SESSION_EXTENSIONS)}"
            )

        # Copy file
        dest_filename = filename or file_path.name
        dest_path = (
            self.archive_path
            / "works"
            / realization.work_id
            / "realizations"
            / realization_id
            / "sessions"
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

        # Update realization
        relative_path = str(dest_path.relative_to(self.archive_path))
        realization.sessions.append(relative_path)
        self._save_realization(realization)

        return relative_path

    def add_stem(
        self, realization_id: str, file_path: Path, stem_name: str | None = None
    ) -> str:
        """
        Copy a stem file to the realization.

        Args:
            realization_id: The realization ID
            file_path: Path to the stem file
            stem_name: Optional stem name (e.g., "vocals", "drums")

        Returns:
            Relative path within archive

        Raises:
            ValueError: If realization not found or invalid file type
        """
        realization = self.get_realization(realization_id)
        if not realization:
            raise ValueError(f"Realization not found: {realization_id}")

        # Validate extension
        if file_path.suffix.lower() not in self.AUDIO_EXTENSIONS:
            raise ValueError(
                f"Invalid audio file type: {file_path.suffix}. "
                f"Valid types: {', '.join(self.AUDIO_EXTENSIONS)}"
            )

        # Generate filename
        if stem_name:
            dest_filename = f"{stem_name}{file_path.suffix}"
        else:
            dest_filename = file_path.name

        dest_path = (
            self.archive_path
            / "works"
            / realization.work_id
            / "realizations"
            / realization_id
            / "stems"
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

        # Update realization
        relative_path = str(dest_path.relative_to(self.archive_path))
        realization.stems.append(relative_path)
        self._save_realization(realization)

        return relative_path

    def add_master(self, realization_id: str, file_path: Path) -> str:
        """
        Copy a master file to the realization.

        Args:
            realization_id: The realization ID
            file_path: Path to the master file

        Returns:
            Relative path within archive

        Raises:
            ValueError: If realization not found or invalid file type
        """
        realization = self.get_realization(realization_id)
        if not realization:
            raise ValueError(f"Realization not found: {realization_id}")

        # Validate extension
        if file_path.suffix.lower() not in self.AUDIO_EXTENSIONS:
            raise ValueError(
                f"Invalid audio file type: {file_path.suffix}. "
                f"Valid types: {', '.join(self.AUDIO_EXTENSIONS)}"
            )

        dest_path = (
            self.archive_path
            / "works"
            / realization.work_id
            / "realizations"
            / realization_id
            / "masters"
            / file_path.name
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

        # Update realization
        relative_path = str(dest_path.relative_to(self.archive_path))
        realization.masters.append(relative_path)
        self._save_realization(realization)

        return relative_path

    def delete_realization(self, realization_id: str) -> bool:
        """
        Delete a realization and its files.

        Args:
            realization_id: The realization ID

        Returns:
            True if deleted, False if not found
        """
        realization = self.get_realization(realization_id)
        if not realization:
            return False

        # Delete directory
        realization_dir = (
            self.archive_path
            / "works"
            / realization.work_id
            / "realizations"
            / realization_id
        )
        shutil.rmtree(realization_dir)

        # Update parent work's realizations list
        work = self._registry.get_work(realization.work_id)
        if work and realization_id in work.realizations:
            work.realizations.remove(realization_id)
            work_dir = self.archive_path / "works" / realization.work_id
            work_metadata_path = work_dir / "metadata.json"
            work_metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

        return True

    def _save_realization(self, realization: Realization) -> None:
        """Save realization to metadata.json."""
        realization_dir = (
            self.archive_path
            / "works"
            / realization.work_id
            / "realizations"
            / realization.id
        )
        metadata_path = realization_dir / "metadata.json"
        metadata_path.write_text(json.dumps(realization.model_dump(), indent=2, default=str))
