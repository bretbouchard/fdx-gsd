"""Change detection for vault synchronization.

Provides file hash calculation and change detection for tracking
modifications to vault notes and generated content.
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileState:
    """Represents the state of a tracked file."""

    path: Path
    hash: str
    last_modified: datetime
    size: int

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "hash": self.hash,
            "last_modified": self.last_modified.isoformat(),
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "FileState":
        """Create from dictionary."""
        return cls(
            path=Path(data["path"]),
            hash=data["hash"],
            last_modified=datetime.fromisoformat(data["last_modified"]),
            size=data["size"],
        )


@dataclass
class ChangeRecord:
    """Represents a detected change."""

    path: Path
    change_type: str  # "added", "modified", "deleted"
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "change_type": self.change_type,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "timestamp": self.timestamp.isoformat(),
        }


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file's contents.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal hash string

    Raises:
        FileNotFoundError: If file does not exist
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class ChangeDetector:
    """
    Detects changes between current file states and a baseline.

    Tracks file modifications using content hashes to identify
    added, modified, and deleted files.
    """

    def __init__(self, baseline: Optional[Dict[str, FileState]] = None):
        """
        Initialize the change detector.

        Args:
            baseline: Optional dict mapping path strings to FileState objects
        """
        self.baseline: Dict[str, FileState] = baseline or {}

    def get_file_state(self, file_path: Path) -> FileState:
        """
        Get current state of a file.

        Args:
            file_path: Path to the file

        Returns:
            FileState object with current file info
        """
        file_path = Path(file_path)
        stat = file_path.stat()
        return FileState(
            path=file_path,
            hash=calculate_file_hash(file_path),
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size,
        )

    def detect_changes(
        self,
        current_paths: List[Path],
        track_deletions: bool = True,
    ) -> List[ChangeRecord]:
        """
        Detect changes between baseline and current file set.

        Args:
            current_paths: List of paths to check
            track_deletions: Whether to track files removed from baseline

        Returns:
            List of ChangeRecord objects describing detected changes
        """
        changes = []
        current_path_set = {str(p) for p in current_paths}

        # Check for added and modified files
        for path in current_paths:
            path_str = str(path)
            current_state = self.get_file_state(path)

            if path_str not in self.baseline:
                # New file
                changes.append(
                    ChangeRecord(
                        path=path,
                        change_type="added",
                        old_hash=None,
                        new_hash=current_state.hash,
                    )
                )
            elif self.baseline[path_str].hash != current_state.hash:
                # Modified file
                changes.append(
                    ChangeRecord(
                        path=path,
                        change_type="modified",
                        old_hash=self.baseline[path_str].hash,
                        new_hash=current_state.hash,
                    )
                )

        # Check for deleted files
        if track_deletions:
            for path_str, old_state in self.baseline.items():
                if path_str not in current_path_set:
                    changes.append(
                        ChangeRecord(
                            path=old_state.path,
                            change_type="deleted",
                            old_hash=old_state.hash,
                            new_hash=None,
                        )
                    )

        return changes

    def update_baseline(self, file_states: Dict[str, FileState]) -> None:
        """
        Update baseline with new file states.

        Args:
            file_states: Dict mapping path strings to FileState objects
        """
        self.baseline.update(file_states)

    def set_baseline(self, file_states: Dict[str, FileState]) -> None:
        """
        Replace entire baseline with new file states.

        Args:
            file_states: Dict mapping path strings to FileState objects
        """
        self.baseline = file_states.copy()

    def save_baseline(self, output_path: Path) -> None:
        """
        Save baseline to JSON file.

        Args:
            output_path: Path to write baseline JSON
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "baseline": {
                path_str: state.to_dict()
                for path_str, state in self.baseline.items()
            },
        }

        output_path.write_text(
            __import__("json").dumps(data, indent=2, sort_keys=True)
        )

    @classmethod
    def load_baseline(cls, input_path: Path) -> "ChangeDetector":
        """
        Load baseline from JSON file.

        Args:
            input_path: Path to baseline JSON file

        Returns:
            ChangeDetector with loaded baseline
        """
        input_path = Path(input_path)
        if not input_path.exists():
            return cls()

        data = __import__("json").loads(input_path.read_text())
        baseline = {
            path_str: FileState.from_dict(state_data)
            for path_str, state_data in data.get("baseline", {}).items()
        }
        return cls(baseline=baseline)

    def has_changes(self, current_paths: List[Path]) -> bool:
        """
        Quick check if any changes exist.

        Args:
            current_paths: List of paths to check

        Returns:
            True if any changes detected, False otherwise
        """
        return len(self.detect_changes(current_paths, track_deletions=False)) > 0

    def get_files_by_change_type(
        self,
        current_paths: List[Path],
        change_type: str,
    ) -> List[Path]:
        """
        Get files filtered by change type.

        Args:
            current_paths: List of paths to check
            change_type: Type of change ("added", "modified", "deleted")

        Returns:
            List of paths matching the change type
        """
        changes = self.detect_changes(current_paths)
        return [
            change.path for change in changes if change.change_type == change_type
        ]
