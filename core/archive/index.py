"""Archive index management.

Maintains a searchable index of all works in the archive for quick lookups
and statistics.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .alias_manager import AliasManager
from .models import Work


class ArchiveIndex:
    """Manages the searchable archive index.

    The index provides:
    - Quick lookups by work ID
    - Search by title/alias
    - Statistics (works by type, counts)
    - Summary views
    """

    def __init__(self, archive_path: Path):
        """
        Initialize the archive index.

        Args:
            archive_path: Path to the archive directory
        """
        self.archive_path = Path(archive_path)
        self._alias_manager = AliasManager()

    @property
    def index_path(self) -> Path:
        """Path to index.json."""
        return self.archive_path / "index.json"

    def rebuild(self) -> dict:
        """
        Scan all works and rebuild the index.

        Returns:
            The rebuilt index dict
        """
        index = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "works": {},
            "by_type": {},
        }

        works_dir = self.archive_path / "works"
        if not works_dir.exists():
            self.save(index)
            return index

        # Reset alias manager
        self._alias_manager = AliasManager()

        # Scan each work directory
        for work_dir in works_dir.iterdir():
            if not work_dir.is_dir():
                continue

            metadata_path = work_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                work_data = json.loads(metadata_path.read_text())
                work_id = work_dir.name

                # Count realizations and performances
                realizations = list((work_dir / "realizations").glob("*")) if (work_dir / "realizations").exists() else []
                performances = list((work_dir / "performances").glob("*")) if (work_dir / "performances").exists() else []

                # Check for masters
                has_masters = False
                for real_dir in realizations:
                    masters_dir = real_dir / "masters"
                    if masters_dir.exists() and list(masters_dir.glob("*")):
                        has_masters = True
                        break

                # Build summary
                summary = {
                    "title": work_data.get("metadata", {}).get("title", "Unknown"),
                    "aliases": work_data.get("metadata", {}).get("aliases", []),
                    "work_type": work_data.get("work_type", "other"),
                    "realization_count": len([d for d in realizations if d.is_dir()]),
                    "performance_count": len([d for d in performances if d.is_dir()]),
                    "has_masters": has_masters,
                    "created_at": work_data.get("metadata", {}).get("created_at"),
                }

                index["works"][work_id] = summary

                # Index by type
                work_type = work_data.get("work_type", "other")
                if work_type not in index["by_type"]:
                    index["by_type"][work_type] = []
                index["by_type"][work_type].append(work_id)

                # Register with alias manager
                self._alias_manager.register_work(
                    work_id,
                    summary["title"],
                    summary["aliases"],
                )

            except (json.JSONDecodeError, KeyError) as e:
                # Skip malformed work directories
                print(f"Warning: Skipping {work_dir}: {e}")
                continue

        self.save(index)
        return index

    def load(self) -> dict:
        """
        Load index from index.json.

        Returns:
            Index dict (creates new if missing)
        """
        if not self.index_path.exists():
            return {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "works": {},
                "by_type": {},
            }

        try:
            return json.loads(self.index_path.read_text())
        except json.JSONDecodeError:
            # Corrupted, rebuild
            return self.rebuild()

    def save(self, index: dict) -> None:
        """
        Save index to index.json.

        Args:
            index: The index dict to save
        """
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index, indent=2))

    def add_work(self, work: Work) -> None:
        """
        Add a work to the index.

        Args:
            work: Work model to add
        """
        index = self.load()

        summary = {
            "title": work.metadata.title,
            "aliases": work.metadata.aliases,
            "work_type": work.work_type,
            "realization_count": 0,
            "performance_count": 0,
            "has_masters": False,
            "created_at": work.metadata.created_at.isoformat(),
        }

        index["works"][work.id] = summary
        index["updated_at"] = datetime.now().isoformat()

        # Add to by_type
        if work.work_type not in index["by_type"]:
            index["by_type"][work.work_type] = []
        index["by_type"][work.work_type].append(work.id)

        self.save(index)

        # Register with alias manager
        self._alias_manager.register_work(work.id, work.metadata.title, work.metadata.aliases)

    def remove_work(self, work_id: str) -> None:
        """
        Remove a work from the index.

        Args:
            work_id: ID of work to remove
        """
        index = self.load()

        if work_id not in index["works"]:
            return

        work_type = index["works"][work_id].get("work_type", "other")

        del index["works"][work_id]
        index["updated_at"] = datetime.now().isoformat()

        # Remove from by_type
        if work_type in index["by_type"]:
            if work_id in index["by_type"][work_type]:
                index["by_type"][work_type].remove(work_id)

        self.save(index)

    def search(self, query: str) -> list[dict]:
        """
        Search works by title/alias.

        Args:
            query: Search query

        Returns:
            List of matching work summaries
        """
        index = self.load()

        # Try exact match first
        results = []
        query_lower = query.lower().strip()

        for work_id, summary in index["works"].items():
            title = summary.get("title", "").lower()
            aliases = [a.lower() for a in summary.get("aliases", [])]

            # Exact title match
            if query_lower == title:
                results.insert(0, {"work_id": work_id, **summary, "match_type": "exact"})
                continue

            # Exact alias match
            if query_lower in aliases:
                results.append({"work_id": work_id, **summary, "match_type": "alias"})
                continue

            # Partial title match
            if query_lower in title:
                results.append({"work_id": work_id, **summary, "match_type": "partial"})
                continue

            # Partial alias match
            for alias in aliases:
                if query_lower in alias:
                    results.append({"work_id": work_id, **summary, "match_type": "alias_partial"})
                    break

        return results

    def get_work_summary(self, work_id: str) -> Optional[dict]:
        """
        Get summary of a specific work.

        Args:
            work_id: The work ID

        Returns:
            Work summary dict or None if not found
        """
        index = self.load()
        summary = index["works"].get(work_id)
        if summary:
            return {"work_id": work_id, **summary}
        return None
