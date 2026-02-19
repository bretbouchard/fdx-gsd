"""Vault note writer for generating Obsidian-compatible markdown files.

This module provides the VaultNoteWriter class for writing entity notes
to the vault directory structure with proper formatting and evidence links.
"""

import re
from pathlib import Path
from typing import Any

from .templates import CHARACTER_TEMPLATE, LOCATION_TEMPLATE, SCENE_TEMPLATE


class VaultNoteWriter:
    """Writes entity notes to vault directory structure.

    Manages creation of markdown files for characters, locations, and scenes
    in the appropriate vault subdirectories with proper formatting.

    Attributes:
        vault_path: Root path to the vault directory
        characters_dir: Path to characters subdirectory
        locations_dir: Path to locations subdirectory
        scenes_dir: Path to scenes subdirectory
    """

    def __init__(self, vault_path: Path):
        """Initialize vault note writer.

        Args:
            vault_path: Root path to the vault directory
        """
        self.vault_path = Path(vault_path)
        self.characters_dir = self.vault_path / "10_Characters"
        self.locations_dir = self.vault_path / "20_Locations"
        self.scenes_dir = self.vault_path / "50_Scenes"

        # Create directories if they don't exist
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.locations_dir.mkdir(parents=True, exist_ok=True)
        self.scenes_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, name: str) -> str:
        """Convert name to URL-safe slug.

        Args:
            name: Original name (e.g., "John Smith")

        Returns:
            Slugified name (e.g., "john-smith")
        """
        # Convert to lowercase
        slug = name.lower()
        # Replace non-alphanumeric characters with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Collapse multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        return slug

    def format_evidence_links(self, evidence_ids: list[str]) -> str:
        """Convert evidence IDs to Obsidian wikilink format.

        Args:
            evidence_ids: List of evidence IDs (e.g., ["ev_001", "ev_002"])

        Returns:
            Newline-separated string of wikilinks
        """
        if not evidence_ids:
            return "  - none"

        links = []
        for eid in evidence_ids:
            # Extract source file from evidence ID (e.g., "ev_001" -> "ev")
            source_file = eid.split('_')[0]
            link = f"[[inbox/{source_file}.md#^{eid}]]"
            links.append(f"  - {link}")

        return '\n'.join(links)

    def write_character(self, entity: dict[str, Any]) -> Path:
        """Write character note to vault.

        Args:
            entity: Character entity dict with required keys:
                - id: Unique identifier
                - name: Character name
                - type: Entity type (usually "character")
                - aliases: List of alternative names
                - first_appearance: Scene or description (optional)
                - evidence_ids: List of evidence IDs

        Returns:
            Path to the created markdown file
        """
        # Generate filename from character name
        slug = self._slugify(entity['name'])
        filename = f"{slug}.md"
        filepath = self.characters_dir / filename

        # Generate markdown content
        content = CHARACTER_TEMPLATE(entity)

        # Write file
        filepath.write_text(content, encoding='utf-8')

        return filepath

    def write_location(self, entity: dict[str, Any]) -> Path:
        """Write location note to vault.

        Args:
            entity: Location entity dict with required keys:
                - id: Unique identifier
                - name: Location name
                - type: Entity type (usually "location")
                - int_ext: INT or EXT indicator
                - time_of_day: Time of day (optional)
                - evidence_ids: List of evidence IDs

        Returns:
            Path to the created markdown file
        """
        # Generate filename from location name
        slug = self._slugify(entity['name'])
        filename = f"{slug}.md"
        filepath = self.locations_dir / filename

        # Generate markdown content
        content = LOCATION_TEMPLATE(entity)

        # Write file
        filepath.write_text(content, encoding='utf-8')

        return filepath

    def write_scene(self, entity: dict[str, Any]) -> Path:
        """Write scene note to vault.

        Args:
            entity: Scene entity dict with required keys:
                - id: Unique identifier (e.g., "SCN_001")
                - scene_number: Scene number
                - location: Location name
                - int_ext: INT or EXT indicator
                - time_of_day: Time of day (optional)
                - evidence_ids: List of evidence IDs

        Returns:
            Path to the created markdown file
        """
        # Use scene ID as filename (e.g., "SCN_001.md")
        filename = f"{entity['id']}.md"
        filepath = self.scenes_dir / filename

        # Generate markdown content
        content = SCENE_TEMPLATE(entity)

        # Write file
        filepath.write_text(content, encoding='utf-8')

        return filepath
