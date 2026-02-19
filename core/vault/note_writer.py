"""Vault note writer - Generates Obsidian-compatible markdown notes.

Writes entity notes to vault directories with evidence links.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .templates import (
    render_character_template,
    render_location_template,
    render_scene_template,
    _slugify,
)


class VaultNoteWriter:
    """Writes entity notes to the Obsidian vault."""

    def __init__(self, vault_path: Path, build_path: Path = None):
        """
        Initialize the vault note writer.

        Args:
            vault_path: Path to the vault root
            build_path: Path to build directory (for evidence index)
        """
        self.vault_path = Path(vault_path)
        self.build_path = Path(build_path) if build_path else self.vault_path.parent / "build"
        self._evidence_index = None

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create vault subdirectories if they don't exist."""
        dirs = [
            self.vault_path / "10_Characters",
            self.vault_path / "20_Locations",
            self.vault_path / "50_Scenes",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _load_evidence_index(self) -> dict:
        """Load the evidence index for link resolution."""
        if self._evidence_index is None:
            path = self.build_path / "evidence_index.json"
            if path.exists():
                self._evidence_index = json.loads(path.read_text())
            else:
                self._evidence_index = {"evidence": {}}
        return self._evidence_index

    def format_evidence_links(self, evidence_ids: List[str]) -> str:
        """
        Convert evidence IDs to Obsidian wikilinks.

        Args:
            evidence_ids: List of block refs (e.g., ["ev_a1b2", "ev_c3d4"])

        Returns:
            Formatted markdown list of wikilinks
        """
        if not evidence_ids:
            return ""

        index = self._load_evidence_index()
        links = []

        for ev_id in evidence_ids:
            ev_data = index.get("evidence", {}).get(ev_id, {})
            source = ev_data.get("source_path", "unknown")
            link = f"[[{source}#^{ev_id}]]"
            links.append(link)

        return "\n".join(f"- {link}" for link in links)

    def write_character(self, entity: Dict[str, Any]) -> Path:
        """
        Write a character note to the vault.

        Args:
            entity: Entity dict with id, name, aliases, evidence_ids, etc.

        Returns:
            Path to the written file
        """
        name = entity.get("name", "unknown")
        slug = _slugify(name)
        file_path = self.vault_path / "10_Characters" / f"{slug}.md"

        # Format evidence links
        evidence_ids = entity.get("evidence_ids", [])
        evidence_links = self.format_evidence_links(evidence_ids)

        # Render template
        content = render_character_template(entity, evidence_links)

        # Write file
        file_path.write_text(content)
        return file_path

    def write_location(self, entity: Dict[str, Any]) -> Path:
        """
        Write a location note to the vault.

        Args:
            entity: Entity dict with id, name, attributes, evidence_ids, etc.

        Returns:
            Path to the written file
        """
        name = entity.get("name", "unknown")
        slug = _slugify(name)
        file_path = self.vault_path / "20_Locations" / f"{slug}.md"

        # Format evidence links
        evidence_ids = entity.get("evidence_ids", [])
        evidence_links = self.format_evidence_links(evidence_ids)

        # Render template
        content = render_location_template(entity, evidence_links)

        # Write file
        file_path.write_text(content)
        return file_path

    def write_scene(self, entity: Dict[str, Any]) -> Path:
        """
        Write a scene note to the vault.

        Args:
            entity: Entity dict with id, name, attributes, evidence_ids, etc.

        Returns:
            Path to the written file
        """
        scene_id = entity.get("id", "SCN_000")
        file_path = self.vault_path / "50_Scenes" / f"{scene_id}.md"

        # Format evidence links
        evidence_ids = entity.get("evidence_ids", [])
        evidence_links = self.format_evidence_links(evidence_ids)

        # Render template
        content = render_scene_template(entity, evidence_links)

        # Write file
        file_path.write_text(content)
        return file_path

    def write_entity(self, entity: Dict[str, Any]) -> Optional[Path]:
        """
        Write any entity to the appropriate vault location.

        Args:
            entity: Entity dict with 'type' field

        Returns:
            Path to written file, or None if unknown type
        """
        entity_type = entity.get("type", "")

        if entity_type == "character":
            return self.write_character(entity)
        elif entity_type == "location":
            return self.write_location(entity)
        elif entity_type == "scene":
            return self.write_scene(entity)

        return None


def write_entity_note(entity: Dict[str, Any], vault_path: Path, build_path: Path = None) -> Optional[Path]:
    """
    Convenience function to write an entity note.

    Args:
        entity: Entity dict
        vault_path: Path to vault root
        build_path: Optional path to build directory

    Returns:
        Path to written file
    """
    writer = VaultNoteWriter(vault_path, build_path)
    return writer.write_entity(entity)
