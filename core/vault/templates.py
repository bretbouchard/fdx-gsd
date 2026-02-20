"""Note templates for vault entity notes.

Templates generate Obsidian-compatible markdown with:
- YAML frontmatter
- Protected block markers for auto-generated content
- Evidence links in wikilink format
"""
from datetime import datetime
from string import Template
from typing import Dict, Any, List


def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = name.lower().strip()
    slug = slug.replace(" ", "-")
    # Remove non-alphanumeric except hyphens
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug


def format_yaml_value(value: Any) -> str:
    """Format a value for YAML frontmatter."""
    if isinstance(value, str):
        # Simple string - quote if needed
        if any(c in value for c in [":", "#", "{", "}", "[", "]", '"', "'"]):
            return f'"{value}"'
        return value
    elif isinstance(value, list):
        if not value:
            return "[]"
        return f"[{', '.join(repr(v) for v in value)}]"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    return str(value)


def render_character_template(entity: Dict[str, Any], evidence_links: str) -> str:
    """Render a character note from entity data."""
    now = datetime.now().strftime("%Y-%m-%d")
    aliases = entity.get("aliases", [])
    aliases_str = ", ".join(repr(a) for a in aliases) if aliases else "[]"

    return f"""---
id: {entity.get('id', 'unknown')}
name: {entity.get('name', 'Unknown')}
type: character
aliases: [{aliases_str}]
created_at: {now}
---

# {entity.get('name', 'Unknown Character')}

<!-- CONFUCIUS:BEGIN AUTO -->
## Aliases

{chr(10).join(f'- {a}' for a in aliases) if aliases else '*None recorded*'}

## First Appearance

*To be documented*

## Evidence

{evidence_links if evidence_links else '*No evidence links yet*'}
<!-- CONFUCIUS:END AUTO -->

## Notes

*Add your notes here...*
"""


def render_location_template(entity: Dict[str, Any], evidence_links: str) -> str:
    """Render a location note from entity data."""
    now = datetime.now().strftime("%Y-%m-%d")
    attrs = entity.get("attributes", {})
    int_ext = attrs.get("int_ext", "INT")
    time_of_day = attrs.get("time_of_day", "")
    description = attrs.get("description", "")
    props = attrs.get("props", [])
    characters = attrs.get("characters", [])
    connected_locations = attrs.get("connected_locations", [])
    scenes = attrs.get("scenes", [])

    # Format lists
    props_str = chr(10).join(f"- [[{p}]]" for p in props) if props else "*None documented*"
    chars_str = chr(10).join(f"- [[{c}]]" for c in characters) if characters else "*None documented*"
    connected_str = chr(10).join(f"- [[{loc}]]" for loc in connected_locations) if connected_locations else "*None documented*"
    scenes_str = chr(10).join(f"- [[{s}]]" for s in scenes) if scenes else "*None documented*"

    return f"""---
id: {entity.get('id', 'unknown')}
name: {entity.get('name', 'Unknown Location')}
type: location
int_ext: {int_ext}
time_of_day: {time_of_day}
aliases: [{", ".join(repr(a) for a in entity.get("aliases", []))}]
created_at: {now}
---

# {entity.get('name', 'Unknown Location')}

<!-- CONFUCIUS:BEGIN AUTO -->
## Type

**{int_ext}**{f' - {time_of_day}' if time_of_day else ''}

## Description

{description if description else '*To be documented*'}

## Props & Objects

{props_str}

## Characters Seen Here

{chars_str}

## Connected Locations

{connected_str}

## Scenes

{scenes_str}

## Evidence

{evidence_links if evidence_links else '*No evidence links yet*'}
<!-- CONFUCIUS:END AUTO -->

## Notes

*Add your notes here...*

## Sketch / Floor Plan

*Add location diagram or reference image here...*
"""


def render_scene_template(entity: Dict[str, Any], evidence_links: str) -> str:
    """Render a scene note from entity data."""
    now = datetime.now().strftime("%Y-%m-%d")
    attrs = entity.get("attributes", {})
    scene_number = entity.get("id", "SCN_000").replace("SCN_", "")
    location = attrs.get("location", "Unknown Location")
    int_ext = attrs.get("int_ext", "INT")
    time_of_day = attrs.get("time_of_day", "")
    slugline = entity.get("name", f"Scene {scene_number}")

    return f"""---
id: {entity.get('id', 'SCN_000')}
scene_number: {scene_number}
location: {location}
int_ext: {int_ext}
time_of_day: {time_of_day}
created_at: {now}
---

# {slugline}

<!-- CONFUCIUS:BEGIN AUTO -->
## Location

[[{location}]]

## Time

**{int_ext}**{f' - {time_of_day}' if time_of_day else ''}

## Characters

*To be populated from analysis*

## Evidence

{evidence_links if evidence_links else '*No evidence links yet*'}
<!-- CONFUCIUS:END AUTO -->

## Notes

*Add scene notes here...*
"""


# Template constants for import compatibility
CHARACTER_TEMPLATE = """---
id: ${id}
name: ${name}
type: character
aliases: ${aliases}
created_at: ${created_at}
---

# ${name}

<!-- CONFUCIUS:BEGIN AUTO -->
## Aliases

${aliases_list}

## First Appearance

*To be documented*

## Evidence

${evidence_links}
<!-- CONFUCIUS:END AUTO -->

## Notes

*Add your notes here...*
"""

LOCATION_TEMPLATE = """---
id: ${id}
name: ${name}
type: location
int_ext: ${int_ext}
time_of_day: ${time_of_day}
aliases: ${aliases}
created_at: ${created_at}
---

# ${name}

<!-- CONFUCIUS:BEGIN AUTO -->
## Type

**${int_ext}**${time_of_day_display}

## Description

${description}

## Props & Objects

${props}

## Characters Seen Here

${characters}

## Connected Locations

${connected_locations}

## Scenes

${scenes}

## Evidence

${evidence_links}
<!-- CONFUCIUS:END AUTO -->

## Notes

*Add your notes here...*

## Sketch / Floor Plan

*Add location diagram or reference image here...*
"""

SCENE_TEMPLATE = """---
id: ${id}
scene_number: ${scene_number}
location: ${location}
int_ext: ${int_ext}
time_of_day: ${time_of_day}
created_at: ${created_at}
---

# ${slugline}

<!-- CONFUCIUS:BEGIN AUTO -->
## Location

[[${location}]]

## Time

**${int_ext}**${time_of_day_display}

## Characters

*To be populated from analysis*

## Evidence

${evidence_links}
<!-- CONFUCIUS:END AUTO -->

## Notes

*Add scene notes here...*
"""
