"""Note templates for vault markdown generation.

This module provides deterministic templates for generating Obsidian-compatible
markdown notes for characters, locations, and scenes.
"""

from datetime import datetime
from typing import Any


def CHARACTER_TEMPLATE(entity: dict[str, Any]) -> str:
    """Generate character note markdown.

    Args:
        entity: Dict with keys: id, name, type, aliases (list),
                first_appearance (optional), evidence_ids (list)

    Returns:
        Formatted markdown string with YAML frontmatter and body.
    """
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Process aliases
    aliases = entity.get("aliases", [])
    aliases_str = "\n".join([f"  - {alias}" for alias in aliases]) if aliases else "  - none"

    # Process first appearance
    first_appearance = entity.get("first_appearance", "Unknown")

    # Process evidence links
    evidence_ids = entity.get("evidence_ids", [])
    evidence_links = "\n".join([f"  - [[inbox/{eid.split('_')[0]}.md#^{eid}]]" for eid in evidence_ids]) if evidence_ids else "  - none"

    return f"""---
id: {entity['id']}
name: {entity['name']}
type: {entity.get('type', 'character')}
aliases:
{aliases_str}
created_at: {now}
---

# {entity['name']}

<!-- CONFUCIUS:BEGIN AUTO -->

## Aliases

{chr(10).join(['- ' + alias for alias in aliases]) if aliases else '- None'}

## First Appearance

{first_appearance}

## Evidence

{evidence_links}

<!-- CONFUCIUS:END AUTO -->
"""


def LOCATION_TEMPLATE(entity: dict[str, Any]) -> str:
    """Generate location note markdown.

    Args:
        entity: Dict with keys: id, name, type, int_ext (INT/EXT),
                time_of_day (optional), evidence_ids (list)

    Returns:
        Formatted markdown string with YAML frontmatter and body.
    """
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Process INT/EXT
    int_ext = entity.get("int_ext", "UNKNOWN")

    # Process time of day
    time_of_day = entity.get("time_of_day")
    time_str = f"\ntime_of_day: {time_of_day}" if time_of_day else ""

    # Process evidence links
    evidence_ids = entity.get("evidence_ids", [])
    evidence_links = "\n".join([f"  - [[inbox/{eid.split('_')[0]}.md#^{eid}]]" for eid in evidence_ids]) if evidence_ids else "  - none"

    return f"""---
id: {entity['id']}
name: {entity['name']}
type: {entity.get('type', 'location')}
int_ext: {int_ext}{time_str}
created_at: {now}
---

# {entity['name']}

<!-- CONFUCIUS:BEGIN AUTO -->

## Type

{int_ext}

## Description

<!-- Add manual description here -->

## Evidence

{evidence_links}

<!-- CONFUCIUS:END AUTO -->
"""


def SCENE_TEMPLATE(entity: dict[str, Any]) -> str:
    """Generate scene note markdown.

    Args:
        entity: Dict with keys: id, scene_number, location, int_ext,
                time_of_day (optional), evidence_ids (list)

    Returns:
        Formatted markdown string with YAML frontmatter and body.
    """
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Process time of day
    time_of_day = entity.get("time_of_day")
    time_str = f"\ntime_of_day: {time_of_day}" if time_of_day else ""

    # Process location link
    location = entity.get("location", "Unknown")
    location_link = f"[[{location}]]" if location != "Unknown" else location

    # Process evidence links
    evidence_ids = entity.get("evidence_ids", [])
    evidence_links = "\n".join([f"  - [[inbox/{eid.split('_')[0]}.md#^{eid}]]" for eid in evidence_ids]) if evidence_ids else "  - none"

    return f"""---
id: {entity['id']}
scene_number: {entity['scene_number']}
location: {location}
int_ext: {entity.get('int_ext', 'UNKNOWN')}{time_str}
created_at: {now}
---

# {entity.get('int_ext', 'UNKNOWN')}. {location} - {time_of_day if time_of_day else 'UNKNOWN'}

<!-- CONFUCIUS:BEGIN AUTO -->

## Slugline

Scene {entity['scene_number']}: {location_link}

## Characters

<!-- Characters will be populated here -->

## Evidence

{evidence_links}

<!-- CONFUCIUS:END AUTO -->
"""
