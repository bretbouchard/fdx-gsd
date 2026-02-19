"""Vault module - Obsidian-compatible note generation.

Provides note writing functionality for extracted entities.
"""
from .note_writer import VaultNoteWriter, write_entity_note
from .templates import (
    CHARACTER_TEMPLATE,
    LOCATION_TEMPLATE,
    SCENE_TEMPLATE,
    render_character_template,
    render_location_template,
    render_scene_template,
)

__all__ = [
    "VaultNoteWriter",
    "write_entity_note",
    "CHARACTER_TEMPLATE",
    "LOCATION_TEMPLATE",
    "SCENE_TEMPLATE",
    "render_character_template",
    "render_location_template",
    "render_scene_template",
]
