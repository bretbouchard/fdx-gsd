# Phase 6: Blender Integration - Research

**Researched:** 2026-02-19
**Domain:** Blender Python API, Scene Layout Generation, Previs Pipeline
**Confidence:** MEDIUM (Blender API well-documented, layout brief format needs validation)

## Summary

Phase 6 requires generating **layout briefs** from ScriptGraph + ShotGraph data for consumption by Blender_GSD (or similar Blender integration). The research focused on:

1. **Blender Python API (bpy)** capabilities for scene automation
2. **Industry standards** for camera data, scene layout, and previs pipelines
3. **Existing tools** that perform screenplay-to-3D conversion (Blender Screenwriter, FilmAgent)
4. **Data formats** for representing camera positions, character blocking, and scene elements

**Primary recommendation:** Design a custom **Layout Brief JSON schema** that translates ShotGraph + ScriptGraph data into camera setups, character positions, and scene elements. Build a **LayoutBriefGenerator** module that outputs to `blender/<scene_id>/layout_brief.json`. For Blender consumption, provide **two paths**: (1) a standalone Blender addon that reads briefs and creates 3D scaffolds, or (2) a CLI command that generates Python scripts for batch processing.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **bpy** (Blender Python API) | 4.x/5.x | Scene manipulation, camera creation, object placement | Official API, complete scene control, no dependencies |
| **mathutils** | Built-in | Vector math, rotation calculations | Included with Blender, industry-proven |
| **json** | Stdlib | Layout brief serialization | Deterministic output, already used throughout project |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **dataclasses** | Stdlib | Layout brief model definitions | Already used in project (Shot, ShotList) |
| **pathlib** | Stdlib | File path management | Cross-platform, already used |
| **re** | Stdlib | Text parsing for blocking notes | Extract position hints from scene descriptions |

### External (Blender-side)

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| **Blender 4.x LTS** | 4.2+ | Target platform | LTS for stability, bpy compatibility |
| **fake-bpy-module** | Latest | IDE type hints | Development productivity |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom Layout Brief | USD (Universal Scene Description) | USD is industry standard but overkill for previz scaffolds; JSON is simpler and matches project patterns |
| Custom Layout Brief | glTF camera format | glTF is for interchange, not scene generation; lacks blocking/character data |
| Blender Addon | Blender CLI scripts | Addon provides UI integration; CLI scripts for batch automation; **do both** |
| Custom Format | FilmAgent position.json | FilmAgent is research project; not standardized; ours needs ShotGraph integration |

**Installation:**
```bash
# No new Python dependencies needed for layout brief generation
# Blender-side: user installs Blender 4.x LTS

# For development (optional):
pip install fake-bpy-module  # Type hints for bpy
```

## Architecture Patterns

### Recommended Project Structure

```
core/
├── layout/                    # NEW: Layout brief generation
│   ├── __init__.py
│   ├── models.py              # LayoutBrief, SceneLayout, CameraSetup, CharacterPosition
│   ├── generator.py           # LayoutBriefGenerator (reads ShotGraph + ScriptGraph)
│   ├── exporter.py            # JSON serialization
│   └── schema.json            # JSON Schema for layout brief
│
├── blender/                   # NEW: Blender integration
│   ├── __init__.py
│   ├── addon/                 # Blender addon (separate package)
│   │   ├── __init__.py        # bl_info, register/unregister
│   │   ├── operators.py       # Import layout brief operator
│   │   ├── panels.py          # UI panels
│   │   └── scene_builder.py   # Build 3D scene from brief
│   └── scripts/               # Standalone CLI scripts
│       ├── scaffold_scene.py  # Generate .blend from brief
│       └── batch_process.py   # Process multiple scenes
│
├── shots/                     # EXISTING: Shot data
│   ├── models.py
│   └── ...
└── scriptgraph/               # EXISTING: Script data
    └── schema.json
```

### Pattern 1: Layout Brief Generation

**What:** Translate ScriptGraph scenes + ShotGraph shots into spatial layout data

**When to use:** After shot suggestions are generated (Phase 5)

**Data flow:**
```
ScriptGraph (scenes, characters, locations)
          +
ShotGraph (shots, camera angles, movements)
          ↓
LayoutBriefGenerator
          ↓
LayoutBrief (scene_layouts, camera_setups, character_positions)
          ↓
    ┌─────┴─────┐
    ↓           ↓
JSON file   Blender addon
```

**Example Layout Brief Schema:**
```json
{
  "$schema": "https://fdx-gsd.local/schemas/layout_brief.json",
  "version": "1.0",
  "project_id": "string",
  "scene_layouts": [
    {
      "scene_id": "SCN_001",
      "slugline": "INT. COFFEE SHOP - DAY",
      "location_id": "LOC_coffee_shop",
      "int_ext": "INT",
      "time_of_day": "DAY",
      "environment": {
        "description": "Small urban coffee shop",
        "lighting_preset": "day_interior",
        "reference_image": "optional/path.jpg"
      },
      "characters": [
        {
          "character_id": "CHAR_john",
          "name": "JOHN",
          "position": {"x": 0.0, "y": -2.0, "z": 0.0},
          "facing": {"x": 0.0, "y": 1.0, "z": 0.0},
          "posture": "standing",
          "blocking_notes": "At counter, ordering"
        }
      ],
      "props": [
        {
          "prop_id": "PROP_coffee_cup",
          "name": "coffee cup",
          "position": {"x": 0.5, "y": -1.8, "z": 0.9}
        }
      ],
      "camera_setups": [
        {
          "setup_id": "CAM_SCN001_001",
          "shot_id": "shot_000001",
          "shot_type": "WS",
          "camera": {
            "position": {"x": 0.0, "y": 5.0, "z": 1.6},
            "rotation": {"x": -15.0, "y": 0.0, "z": 0.0},
            "lens_mm": 35,
            "sensor_width": 36.0
          },
          "target": {"x": 0.0, "y": 0.0, "z": 1.0},
          "movement": "Static",
          "description": "Establishing shot of coffee shop interior"
        }
      ],
      "evidence_ids": ["EV_001", "EV_002"]
    }
  ]
}
```

### Pattern 2: Blender Addon Architecture

**What:** Blender addon that imports layout briefs and creates scene scaffolds

**When to use:** Interactive previz workflow in Blender

**Example addon structure:**
```python
# blender/addon/__init__.py
bl_info = {
    "name": "FDX GSD Layout Importer",
    "author": "FDX GSD",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > FDX GSD",
    "category": "Scene",
}

import bpy

class FDXImportLayoutBrief(bpy.types.Operator):
    """Import FDX GSD Layout Brief"""
    bl_idname = "fdx_gsd.import_layout"
    bl_label = "Import Layout Brief"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        from .scene_builder import build_scene_from_brief
        build_scene_from_brief(self.filepath)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FDXImportLayoutBrief)

def unregister():
    bpy.utils.unregister_class(FDXImportLayoutBrief)
```

**Scene builder example:**
```python
# blender/addon/scene_builder.py
# Source: Blender Python API docs + Blender Screenwriter patterns
import bpy
import json
from mathutils import Vector, Euler
import math

def build_scene_from_brief(filepath: str):
    """Build 3D scene scaffold from layout brief JSON."""
    with open(filepath) as f:
        brief = json.load(f)

    for scene_layout in brief["scene_layouts"]:
        # Create Blender scene
        scene = bpy.data.scenes.new(name=scene_layout["scene_id"])
        bpy.context.window.scene = scene

        # Create collection for scene
        collection = bpy.data.collections.new(name=scene_layout["scene_id"])
        scene.collection.children.link(collection)

        # Add cameras
        for cam_setup in scene_layout["camera_setups"]:
            cam_data = bpy.data.cameras.new(name=cam_setup["setup_id"])
            cam_obj = bpy.data.objects.new(cam_setup["setup_id"], cam_data)

            # Set camera position
            pos = cam_setup["camera"]["position"]
            cam_obj.location = (pos["x"], pos["y"], pos["z"])

            # Set lens
            cam_data.lens = cam_setup["camera"]["lens_mm"]

            # Point at target
            target = cam_setup["target"]
            direction = Vector((target["x"], target["y"], target["z"])) - cam_obj.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            cam_obj.rotation_euler = rot_quat.to_euler()

            collection.objects.link(cam_obj)

        # Add character proxies (simple capsules)
        for char in scene_layout["characters"]:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3)
            proxy = bpy.context.active_object
            proxy.name = f"PROXY_{char['name']}"
            pos = char["position"]
            proxy.location = (pos["x"], pos["y"], pos["z"] + 1.0)  # Offset up
            proxy.scale = (0.5, 0.5, 1.8)  # Human-like proportions

        # Set lighting based on time_of_day
        # (simplified - real impl would use lighting presets)
        if scene_layout["time_of_day"] == "DAY":
            # Add sun lamp
            sun_data = bpy.data.lights.new(name="Sun", type='SUN')
            sun_obj = bpy.data.objects.new("Sun", sun_data)
            sun_obj.location = (5, 5, 10)
            collection.objects.link(sun_obj)
```

### Pattern 3: Camera Position Calculation

**What:** Convert shot type (WS, MS, CU) + subject position to camera placement

**When to use:** Generating camera positions from shot data

**Example:**
```python
# layout/camera_math.py
# Based on cinematography standards + glTF camera model
from dataclasses import dataclass
from math import tan, radians
from typing import Tuple

@dataclass
class CameraPosition:
    x: float
    y: float
    z: float

@dataclass
class CameraRotation:
    pitch: float  # X axis (degrees)
    yaw: float    # Z axis (degrees)
    roll: float   # Y axis (degrees)

def calculate_camera_position(
    shot_type: str,
    subject_position: Tuple[float, float, float],
    subject_height: float = 1.7,  # meters
    lens_mm: float = 35.0,
    sensor_width: float = 36.0
) -> Tuple[CameraPosition, CameraRotation]:
    """
    Calculate camera position and rotation based on shot type.

    Shot type distances (approximate, based on subject framing):
    - WS (Wide Shot): Shows full body + environment, ~4-6m from subject
    - MS (Medium Shot): Waist up, ~2-3m from subject
    - MCU (Medium Close-Up): Chest up, ~1.5-2m from subject
    - CU (Close-Up): Face only, ~1-1.5m from subject
    - ECU (Extreme Close-Up): Single feature, ~0.5-1m from subject
    """
    # Distance mapping based on shot type
    DISTANCES = {
        "WS": 5.0,
        "MS": 2.5,
        "MCU": 1.8,
        "CU": 1.2,
        "ECU": 0.8,
        "INSERT": 0.5,
        "OTS": 2.0,
        "POV": 1.7,  # Eye height
        "TWO": 3.0,
    }

    distance = DISTANCES.get(shot_type, 3.0)

    # Camera at eye level by default (1.6m)
    # For WS, raise camera to see more environment
    cam_height = 1.6 if shot_type != "WS" else 2.0

    # Position camera in front of subject (negative Y direction)
    cam_x = subject_position[0]
    cam_y = subject_position[1] - distance
    cam_z = cam_height

    # Calculate rotation to point at subject's face
    # Pitch angle: down from horizontal
    pitch = -radians(10)  # Slight downward angle

    # Yaw: 0 (facing positive Y)
    yaw = 0.0
    roll = 0.0

    return (
        CameraPosition(x=cam_x, y=cam_y, z=cam_z),
        CameraRotation(pitch=pitch, yaw=yaw, roll=roll)
    )
```

### Anti-Patterns to Avoid

- **Don't use bpy.ops for batch operations** - Slow, context-dependent. Use `bpy.data` direct access instead.
- **Don't assume Blender coordinate system** - Blender uses Z-up, Y-forward; document conversions.
- **Don't hand-roll USD/gLTF exporters** - Use Blender's built-in exporters if interchange needed.
- **Don't hardcode camera positions** - Use cinematography formulas based on shot type and subject.
- **Don't ignore evidence linkage** - Layout briefs should maintain evidence_ids from ScriptGraph.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Camera position from shot type | Custom distance formulas | Cinematography standards + mathutils | Proven distances, correct framing |
| Scene collection management | Manual collection linking | bpy.data.collections API | Handles parenting, instancing |
| Camera targeting | Manual rotation calculation | `Vector.to_track_quat('-Z', 'Y')` | Blender convention, correct axes |
| JSON schema validation | Custom validation code | jsonschema library | Already used in project |
| Blender addon UI | Custom OpenGL drawing | bpy.types.Panel, bpy.types.Operator | Native UI, consistent UX |

**Key insight:** Blender's Python API is comprehensive but has quirks. Study `scripts/addons_core/` (like `node_wrangler`) for patterns. The Blender Screenwriter addon provides a working example of screenplay-to-3D workflow.

## Common Pitfalls

### Pitfall 1: Blender Context Errors

**What goes wrong:** `bpy.ops` operators fail with "incorrect context" errors

**Why it happens:** Operators expect specific context (active object, edit mode, etc.)

**How to avoid:**
- Use `bpy.data` for data manipulation (context-independent)
- Override context when operators are necessary: `bpy.ops.object.select_all({'selected_objects': [obj]})`
- Prefer direct property assignment over operators

**Warning signs:**
- `RuntimeError: Operator bpy.ops.* poll() failed`
- Works in interactive Blender but fails in background mode

### Pitfall 2: Coordinate System Confusion

**What goes wrong:** Objects appear at wrong positions, cameras point wrong direction

**Why it happens:** Blender uses Z-up coordinate system; many formats use Y-up

**How to avoid:**
- Document coordinate system in code comments
- Use helper functions for conversion
- Standard convention: X=right, Y=forward (into screen), Z=up

**Warning signs:**
- Characters appearing sideways or upside down
- Cameras pointing at ceiling instead of subject

### Pitfall 3: Missing Evidence Linkage

**What goes wrong:** Layout briefs lose traceability to source screenplay

**Why it happens:** Forgetting to propagate evidence_ids through transformations

**How to avoid:**
- Every layout element should carry evidence_ids from source
- LayoutBriefGenerator must preserve evidence chain
- Validation step checks evidence presence

**Warning signs:**
- Cannot trace camera setup back to shot suggestion
- Cannot verify character position matches script

### Pitfall 4: Deterministic Output Failure

**What goes wrong:** Layout briefs change on rebuild even with same input

**Why it happens:** Unordered dictionaries, floating-point inconsistencies

**How to avoid:**
- Sort all lists/arrays in output (as done in ShotGraph)
- Round floats to reasonable precision (2-3 decimal places)
- Use deterministic UUID generation based on scene/shot IDs

**Warning signs:**
- Git shows changes in layout_brief.json without input changes
- CI tests fail intermittently

### Pitfall 5: Blender Version Incompatibility

**What goes wrong:** Addon works in Blender 4.0 but not 4.2

**Why it happens:** API changes between versions

**How to avoid:**
- Target Blender LTS version (currently 4.2)
- Specify minimum version in `bl_info`
- Test addon in target version before release
- Avoid recently added API features

**Warning signs:**
- `AttributeError: '...' object has no attribute '...'`
- Import errors on addon registration

## Code Examples

### Layout Brief Generator

```python
# layout/generator.py
# Source: Project patterns (ShotSuggester, ScriptBuilder)
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

from .models import LayoutBrief, SceneLayout, CameraSetup, CharacterPosition
from core.shots.models import ShotList, Shot
from core.scriptgraph.schema import ScriptGraph


@dataclass
class LayoutBriefGenerator:
    """
    Generate layout briefs from ScriptGraph + ShotGraph.

    Follows ShotSuggester pattern from Phase 5.
    """
    project_id: str
    scriptgraph: Dict[str, Any]  # ScriptGraph JSON
    shotgraph: Dict[str, Any]    # ShotGraph JSON

    def generate(self) -> LayoutBrief:
        """Generate complete layout brief."""
        scene_layouts = []

        for scene_data in self.scriptgraph.get("scenes", []):
            scene_id = scene_data["id"]
            shots = self._get_shots_for_scene(scene_id)

            if not shots:
                continue

            scene_layout = self._build_scene_layout(scene_data, shots)
            scene_layouts.append(scene_layout)

        # Sort by scene order for determinism
        scene_layouts.sort(key=lambda s: s.scene_id)

        return LayoutBrief(
            version="1.0",
            project_id=self.project_id,
            scene_layouts=scene_layouts
        )

    def _get_shots_for_scene(self, scene_id: str) -> List[Shot]:
        """Get all shots for a scene from ShotGraph."""
        shots = []
        for shot_data in self.shotgraph.get("shots", []):
            if shot_data["scene_id"] == scene_id:
                shots.append(Shot.from_dict(shot_data))
        return sorted(shots, key=lambda s: s.shot_number)

    def _build_scene_layout(
        self,
        scene_data: Dict[str, Any],
        shots: List[Shot]
    ) -> SceneLayout:
        """Build scene layout from scene + shots."""
        # Extract characters from scene links
        character_ids = scene_data.get("links", {}).get("characters", [])

        # Build character positions (simplified - real impl uses blocking analysis)
        characters = []
        for i, char_id in enumerate(sorted(character_ids)):
            # Space characters along X axis
            x_pos = (i - len(character_ids) / 2) * 1.5
            characters.append(CharacterPosition(
                character_id=char_id,
                name=char_id.replace("CHAR_", ""),
                position={"x": x_pos, "y": 0.0, "z": 0.0},
                facing={"x": 0.0, "y": 1.0, "z": 0.0},
                posture="standing",
                blocking_notes=""
            ))

        # Build camera setups from shots
        camera_setups = []
        for shot in shots:
            setup = self._build_camera_setup(shot, characters)
            camera_setups.append(setup)

        return SceneLayout(
            scene_id=scene_data["id"],
            slugline=scene_data.get("slugline", ""),
            location_id=scene_data.get("links", {}).get("locations", [""])[0],
            int_ext=scene_data.get("int_ext", "INT"),
            time_of_day=scene_data.get("time_of_day", "DAY"),
            environment={"description": "", "lighting_preset": "default"},
            characters=characters,
            props=[],  # TODO: Extract from scene links
            camera_setups=camera_setups,
            evidence_ids=sorted(scene_data.get("links", {}).get("evidence_ids", []))
        )

    def _build_camera_setup(
        self,
        shot: Shot,
        characters: List[CharacterPosition]
    ) -> CameraSetup:
        """Build camera setup from shot data."""
        # Determine subject position (first character or default)
        if characters:
            subject = characters[0].position
        else:
            subject = {"x": 0.0, "y": 0.0, "z": 1.0}

        # Calculate camera position based on shot type
        cam_pos, cam_rot = calculate_camera_position(
            shot_type=shot.shot_type.value,
            subject_position=(subject["x"], subject["y"], subject["z"])
        )

        return CameraSetup(
            setup_id=f"CAM_{shot.shot_id}",
            shot_id=shot.shot_id,
            shot_type=shot.shot_type.value,
            camera={
                "position": {"x": cam_pos.x, "y": cam_pos.y, "z": cam_pos.z},
                "rotation": {
                    "x": cam_rot.pitch,
                    "y": cam_rot.yaw,
                    "z": cam_rot.roll
                },
                "lens_mm": 35.0,
                "sensor_width": 36.0
            },
            target=subject,
            movement=shot.movement.value,
            description=shot.description,
            evidence_ids=sorted(shot.evidence_ids)
        )
```

### CLI Integration

```python
# apps/cli/commands/layout_command.py
# Source: Existing CLI pattern (build_command.py, validate_command.py)
import click
import json
from pathlib import Path

from core.layout.generator import LayoutBriefGenerator
from core.layout.exporter import LayoutBriefExporter


@click.group()
def layout():
    """Layout brief generation commands."""
    pass


@layout.command()
@click.option('--project', '-p', required=True, type=click.Path(exists=True),
              help='Path to project directory')
@click.option('--output', '-o', type=click.Path(), default=None,
              help='Output directory for layout briefs')
def generate(project: str, output: str):
    """Generate layout briefs from ScriptGraph + ShotGraph."""
    project_path = Path(project)
    build_path = project_path / "build"
    output_path = Path(output) if output else project_path / "blender"

    # Load ScriptGraph
    scriptgraph_path = build_path / "scriptgraph.json"
    if not scriptgraph_path.exists():
        raise click.ClickException(
            f"ScriptGraph not found. Run 'gsd build script' first."
        )
    scriptgraph = json.loads(scriptgraph_path.read_text())

    # Load ShotGraph
    shotgraph_path = build_path / "shotgraph.json"
    if not shotgraph_path.exists():
        raise click.ClickException(
            f"ShotGraph not found. Run 'gsd suggest-shots' first."
        )
    shotgraph = json.loads(shotgraph_path.read_text())

    # Generate layout brief
    project_id = scriptgraph.get("project_id", "unknown")
    generator = LayoutBriefGenerator(
        project_id=project_id,
        scriptgraph=scriptgraph,
        shotgraph=shotgraph
    )

    brief = generator.generate()

    # Export
    exporter = LayoutBriefExporter(output_path)
    exporter.export(brief)

    click.echo(f"Generated {len(brief.scene_layouts)} scene layouts")
    click.echo(f"Output: {output_path}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual camera placement | AI-assisted shot suggestions + auto-positioning | 2025-2026 | Faster previz, consistent cinematography |
| Proprietary previz tools | Blender + open formats | 2010s-present | Accessible to independents |
| Separate screenplay/3D pipelines | Unified screenplay-to-3D workflow | 2024-2026 | Single source of truth, less manual sync |
| Static blocking notes | Position.json formats with coordinates | 2024-2026 | Machine-readable blocking for automation |

**Deprecated/outdated:**
- **FBX for scene interchange**: Use USD or glTF for modern pipelines; FBX is legacy
- **Manual shot list entry**: Tools like Blender Screenwriter automate from screenplay
- **Separate camera sheets**: Camera data integrated into scene layout briefs

## Open Questions

### 1. Blocking Position Algorithm

**What we know:**
- FilmAgent provides position.json format with sit/stand/fixed_angle
- Cinematography standards define typical shot distances
- Character positions need to be inferred from dialogue/action

**What's unclear:**
- Best algorithm for converting scene descriptions to character positions
- How to handle character movement during scene
- Multi-character positioning (conversations, groups)

**Recommendation:**
- Phase 6.1: Implement simple grid-based positioning (characters spread along X axis)
- Future: Add blocking analysis from action descriptions (NLP or rule-based)

### 2. Location Template System

**What we know:**
- ScriptGraph has location entities with attributes
- Blender can use collection instances for reusable sets
- Lighting presets exist for INT/EXT + time of day

**What's unclear:**
- How to map location descriptions to 3D assets
- Whether to use asset libraries or generate simple geometry
- How detailed location scaffolds should be

**Recommendation:**
- Phase 6.1: Use simple primitive geometry (floor plane, walls for INT)
- Future: Add location asset library with Blender asset browser integration

### 3. Blender_GSD Integration

**What we know:**
- ROADMAP mentions "Blender_GSD can consume briefs"
- Blender addon is standard integration approach
- CLI scripts useful for batch processing

**What's unclear:**
- Is Blender_GSD an existing project or part of this phase?
- What level of automation is expected?
- Render output requirements (images, video, .blend files?)

**Recommendation:**
- Ask user to clarify Blender_GSD scope before planning
- Assume addon + CLI scripts for maximum flexibility
- Document both paths in RESEARCH.md for planner

## Sources

### Primary (HIGH confidence)

- **Blender Python API** - https://docs.blender.org/api/current/
  - Complete bpy API reference
  - Best practices, gotchas documentation
  - Application modules: bpy.data, bpy.ops, bpy.types
- **Blender Screenwriter addon** - https://github.com/tin2tin/Blender_Screenwriter
  - Working screenplay-to-3D implementation
  - Camera generation from [[SHOT:]] notes
  - Fountain screenplay format integration
- **Project source code** - Existing patterns:
  - `core/shots/models.py` - Shot, ShotList dataclasses
  - `core/scriptgraph/schema.json` - Scene structure
  - `apps/cli/commands/` - CLI command patterns

### Secondary (MEDIUM confidence)

- **FilmAgent position.json** - CSDN article on virtual 3D space positioning
  - Standardized position format for virtual production
  - sit/stand/fixed_angle metadata
- **glTF 2.0 camera schema** - JSON Schema for camera data
  - Perspective/orthographic camera definitions
  - focal length, FOV, clipping planes
- **WebSearch verified: Previs pipeline 2026** - CG Channel, industry articles
  - Maya 2026.1 MotionMaker for layout/previz
  - AI integration in previs workflows
  - Script-to-3D becoming standard

### Tertiary (LOW confidence)

- **WebSearch only: Layout brief formats** - No single industry standard found
  - FilmAgent closest match but research project
  - Multiple ad-hoc JSON formats in use
  - Need validation with Blender_GSD consumer

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Blender API well-documented, no new dependencies needed
- Architecture: MEDIUM - Patterns from existing project + Blender Screenwriter, but layout brief format needs validation
- Pitfalls: HIGH - Common Blender Python issues well-known
- Camera math: MEDIUM - Cinematography standards established, but blocking algorithm uncertain

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (Blender API stable, but verify LTS version compatibility)
