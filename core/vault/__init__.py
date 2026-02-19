"""Vault module for Obsidian-compatible note generation.

This module provides tools for writing extracted entities to the vault
directory structure as formatted markdown files.
"""

from .note_writer import VaultNoteWriter
from .templates import CHARACTER_TEMPLATE, LOCATION_TEMPLATE, SCENE_TEMPLATE

__all__ = [
    "VaultNoteWriter",
    "CHARACTER_TEMPLATE",
    "LOCATION_TEMPLATE",
    "SCENE_TEMPLATE",
]
