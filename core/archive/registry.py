"""Work registry for managing creative works.

Provides:
- Work registration with UUID generation
- Work retrieval by ID or alias
- Work updates and deletion
- Integration with AliasManager and ArchiveIndex
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .alias_manager import AliasManager
from .index import ArchiveIndex
from .models import Work, WorkMetadata


class WorkRegistry:
    """Manages work registration and retrieval."""

    def __init__(self, archive_path: Path):
        """
        Initialize the work registry.

        Args:
            archive_path: Path to the archive directory
        """
        self.archive_path = Path(archive_path)
        self._alias_manager = AliasManager()
        self._index = ArchiveIndex(archive_path)

    def register_work(
        self,
        title: str,
        work_type: str = "song",
        aliases: list[str] | None = None,
        genre: str | None = None,
        year: int | None = None,
        isrc: str | None = None,
        isbn: str | None = None,
        notes: str | None = None,
    ) -> Work:
        """
        Register a new work in the archive.

        Args:
            title: Canonical title of the work
            work_type: Type of work (song, composition, script, other)
            aliases: List of alternate names/titles
            genre: Genre classification
            year: Year of creation/release
            isrc: ISRC code (for songs)
            isbn: ISBN (for compositions)
            notes: Additional notes

        Returns:
            Created Work model

        Raises:
            ValueError: If title is empty
        """
        if not title or not title.strip():
            raise ValueError("Work title cannot be empty")

        # Generate ID
        work_id = f"work_{uuid.uuid4().hex[:8]}"

        # Create metadata
        now = datetime.now()
        metadata = WorkMetadata(
            title=title.strip(),
            aliases=aliases or [],
            genre=genre,
            year=year,
            isrc=isrc,
            isbn=isbn,
            created_at=now,
            updated_at=now,
            notes=notes,
        )

        # Create work
        work = Work(
            id=work_id,
            work_type=work_type,
            metadata=metadata,
            realizations=[],
            performances=[],
            assets=[],
        )

        # Create work directory
        work_dir = self.archive_path / "works" / work_id
        work_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (work_dir / "realizations").mkdir(exist_ok=True)
        (work_dir / "performances").mkdir(exist_ok=True)
        (work_dir / "assets").mkdir(exist_ok=True)

        # Write metadata.json
        metadata_path = work_dir / "metadata.json"
        metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

        # Update aliases
        self._alias_manager.register_work(work_id, title, aliases or [])

        # Update index
        self._index.add_work(work)

        return work

    def get_work(self, work_id: str) -> Optional[Work]:
        """
        Retrieve a work by ID.

        Args:
            work_id: The canonical work ID

        Returns:
            Work model if found, None otherwise
        """
        work_dir = self.archive_path / "works" / work_id
        metadata_path = work_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            data = json.loads(metadata_path.read_text())
            return Work(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def get_work_by_alias(self, alias: str) -> Optional[Work]:
        """
        Find a work by any alias.

        Args:
            alias: Alias or title to search for

        Returns:
            Work model if found, None otherwise
        """
        # First, load existing aliases into manager
        self._load_aliases()

        canonical_id = self._alias_manager.resolve(alias)
        if canonical_id:
            return self.get_work(canonical_id)
        return None

    def update_work(self, work_id: str, **updates) -> Optional[Work]:
        """
        Update work metadata.

        Args:
            work_id: The canonical work ID
            **updates: Fields to update in metadata

        Returns:
            Updated Work model if found, None otherwise
        """
        work = self.get_work(work_id)
        if not work:
            return None

        # Update metadata fields
        metadata_dict = work.metadata.model_dump()
        for key, value in updates.items():
            if key in metadata_dict:
                metadata_dict[key] = value

        metadata_dict["updated_at"] = datetime.now()
        work.metadata = WorkMetadata(**metadata_dict)

        # Save
        work_dir = self.archive_path / "works" / work_id
        metadata_path = work_dir / "metadata.json"
        metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

        # Update index
        self._index.add_work(work)

        return work

    def add_alias(self, work_id: str, alias: str) -> bool:
        """
        Add a new alias to an existing work.

        Args:
            work_id: The canonical work ID
            alias: New alias to add

        Returns:
            True if added, False if work not found
        """
        work = self.get_work(work_id)
        if not work:
            return False

        if alias not in work.metadata.aliases:
            work.metadata.aliases.append(alias)
            work.metadata.updated_at = datetime.now()

            # Save
            work_dir = self.archive_path / "works" / work_id
            metadata_path = work_dir / "metadata.json"
            metadata_path.write_text(json.dumps(work.model_dump(), indent=2, default=str))

            # Update alias manager
            self._alias_manager.register_alias(alias, work_id)

            # Update index
            self._index.add_work(work)

        return True

    def list_works(self, work_type: str | None = None) -> list[Work]:
        """
        List all works, optionally filtered by type.

        Args:
            work_type: Optional type filter

        Returns:
            List of Work models
        """
        works = []
        works_dir = self.archive_path / "works"

        if not works_dir.exists():
            return works

        for work_dir in works_dir.iterdir():
            if not work_dir.is_dir():
                continue

            work = self.get_work(work_dir.name)
            if work:
                if work_type is None or work.work_type == work_type:
                    works.append(work)

        return works

    def delete_work(self, work_id: str) -> bool:
        """
        Delete a work and its directory.

        Args:
            work_id: The canonical work ID

        Returns:
            True if deleted, False if not found
        """
        import shutil

        work = self.get_work(work_id)
        if not work:
            return False

        work_dir = self.archive_path / "works" / work_id
        shutil.rmtree(work_dir)

        # Update index
        self._index.remove_work(work_id)

        return True

    def _load_aliases(self):
        """Load aliases from all works into the alias manager."""
        aliases_path = self.archive_path / "aliases.json"

        if aliases_path.exists():
            try:
                data = json.loads(aliases_path.read_text())
                self._alias_manager.import_registry(data)
            except json.JSONDecodeError:
                pass

        # Also load from works directory
        works_dir = self.archive_path / "works"
        if not works_dir.exists():
            return

        for work_dir in works_dir.iterdir():
            if not work_dir.is_dir():
                continue

            metadata_path = work_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                data = json.loads(metadata_path.read_text())
                work_id = work_dir.name
                title = data.get("metadata", {}).get("title", "")
                aliases = data.get("metadata", {}).get("aliases", [])
                self._alias_manager.register_work(work_id, title, aliases)
            except (json.JSONDecodeError, KeyError):
                continue
