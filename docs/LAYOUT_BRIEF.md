# Layout Brief Specification

## Overview

The Layout Brief is a JSON format for exchanging spatial layout data between FDX GSD and 3D applications like Blender. It provides camera positions, character placements, and scene metadata for previz generation.

## Version

Current version: **1.0**

## File Locations

- Per-scene: `blender/<scene_id>/layout_brief.json`
- Combined: `build/layout_brief.json`

## Schema

### LayoutBrief (Root)

```json
{
  "version": "1.0",
  "project_id": "string",
  "generated_at": "ISO 8601 datetime",
  "scene_layouts": [SceneLayout]
}
```

### SceneLayout

```json
{
  "scene_id": "SCN_001",
  "slugline": "INT. OFFICE - DAY",
  "location_id": "LOC_office",
  "int_ext": "INT | EXT",
  "time_of_day": "DAY | NIGHT | DAWN | DUSK",
  "environment": {
    "description": "string",
    "lighting_preset": "string"
  },
  "characters": [CharacterPosition],
  "props": [PropPosition],
  "camera_setups": [CameraSetup],
  "evidence_ids": ["string"]
}
```

### CharacterPosition

```json
{
  "character_id": "CHAR_fox",
  "name": "Fox",
  "position": {"x": 0, "y": 0, "z": 0},
  "facing": {"x": 0, "y": 1, "z": 0},
  "posture": "standing | sitting | lying",
  "blocking_notes": "string",
  "evidence_ids": ["string"]
}
```

### PropPosition

```json
{
  "prop_id": "PROP_gun",
  "name": "Gun",
  "position": {"x": 0, "y": 0, "z": 0},
  "rotation": {"x": 0, "y": 0, "z": 0},
  "state": "string",
  "evidence_ids": ["string"]
}
```

### CameraSetup

```json
{
  "setup_id": "CAM_shot_001_001",
  "shot_id": "shot_001_001",
  "shot_type": "WS | MS | MCU | CU | ECU | INSERT | OTS | POV | TWO",
  "camera": {
    "position": {"x": 0, "y": -5, "z": 2},
    "rotation": {"pitch": -15, "yaw": 0, "roll": 0},
    "lens_mm": 35,
    "sensor_width": 36
  },
  "target": {"x": 0, "y": 0, "z": 1.6},
  "movement": "Static | Pan | Tilt | Dolly | Crane | Handheld",
  "description": "string",
  "evidence_ids": ["string"]
}
```

## Coordinate System

Uses Blender's coordinate system:

- **X-axis**: Right (+) / Left (-)
- **Y-axis**: Forward (+) / Back (-)
- **Z-axis**: Up (+) / Down (-)

Camera is typically placed in front of subject (negative Y).

## Shot Type Distances

| Shot Type | Distance | Camera Height | Use Case |
|-----------|----------|---------------|----------|
| WS | 5.0m | 2.0m (raised) | Establishing, full body + environment |
| MS | 2.5m | 1.6m (eye level) | Waist up, standard dialogue |
| MCU | 1.8m | 1.6m (eye level) | Chest up, intimate dialogue |
| CU | 1.2m | 1.6m (eye level) | Face only, emotional moments |
| ECU | 0.8m | 1.6m (eye level) | Single feature |
| INSERT | 0.5m | 1.6m (eye level) | Props, objects |
| OTS | 2.0m | 1.6m (eye level) | Over-the-shoulder |
| POV | 1.7m | 1.7m (subject height) | Eye height matching |
| TWO | 3.0m | 1.6m (eye level) | Two characters in frame |

## Camera Math

### Position Calculation

```python
def calculate_camera_position(shot_type, subject_position, subject_height=1.7):
    distance = SHOT_TYPE_DISTANCES[shot_type]

    # Camera in front of subject (negative Y in Blender)
    x = subject_position[0]
    y = subject_position[1] - distance
    z = 2.0 if shot_type == "WS" else 1.6  # Raised for WS

    return (x, y, z)
```

### Rotation Calculation

Camera points at subject's eye level:

```python
def point_camera_at_target(camera_pos, target_pos):
    dx = target_pos[0] - camera_pos[0]
    dy = target_pos[1] - camera_pos[1]
    dz = target_pos[2] - camera_pos[2]

    distance = sqrt(dx*dx + dy*dy + dz*dz)

    yaw = atan2(dx, dy)      # Horizontal rotation
    pitch = asin(dz / distance)  # Vertical rotation
    roll = 0

    return (pitch, yaw, roll)
```

## Evidence Chain

Every position and setup includes `evidence_ids` linking back to source material:

```json
{
  "camera_setups": [{
    "setup_id": "CAM_shot_001_001",
    "evidence_ids": ["EV_001", "EV_002"]
  }]
}
```

This enables traceability from 3D previz back to original script notes.

## Example

```json
{
  "version": "1.0",
  "project_id": "my_movie",
  "generated_at": "2026-02-19T12:00:00",
  "scene_layouts": [
    {
      "scene_id": "SCN_001",
      "slugline": "INT. JOE'S DINER - DAY",
      "location_id": "LOC_joes_diner",
      "int_ext": "INT",
      "time_of_day": "DAY",
      "environment": {
        "description": "INT - DAY",
        "lighting_preset": "interior_day"
      },
      "characters": [
        {
          "character_id": "CHAR_fox",
          "name": "Fox",
          "position": {"x": -0.75, "y": 0, "z": 0},
          "facing": {"x": 0, "y": 1, "z": 0},
          "posture": "standing",
          "blocking_notes": "",
          "evidence_ids": ["EV_001"]
        },
        {
          "character_id": "CHAR_sarah",
          "name": "Sarah",
          "position": {"x": 0.75, "y": 0, "z": 0},
          "facing": {"x": 0, "y": 1, "z": 0},
          "posture": "sitting",
          "blocking_notes": "",
          "evidence_ids": ["EV_002"]
        }
      ],
      "props": [],
      "camera_setups": [
        {
          "setup_id": "CAM_shot_001_001",
          "shot_id": "shot_001_001",
          "shot_type": "WS",
          "camera": {
            "position": {"x": 0, "y": -5.0, "z": 2.0},
            "rotation": {"pitch": -11.3, "yaw": 0, "roll": 0},
            "lens_mm": 35,
            "sensor_width": 36
          },
          "target": {"x": 0, "y": 0, "z": 1.6},
          "movement": "Static",
          "description": "Establishing shot of diner",
          "evidence_ids": []
        },
        {
          "setup_id": "CAM_shot_001_002",
          "shot_id": "shot_001_002",
          "shot_type": "CU",
          "camera": {
            "position": {"x": -0.75, "y": -1.2, "z": 1.6},
            "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
            "lens_mm": 50,
            "sensor_width": 36
          },
          "target": {"x": -0.75, "y": 0, "z": 1.6},
          "movement": "Static",
          "description": "Close-up on Fox",
          "evidence_ids": ["EV_003"]
        }
      ],
      "evidence_ids": ["EV_001", "EV_002"]
    }
  ]
}
```

## Blender Integration

The layout brief is designed for consumption by Blender_GSD or similar tools:

1. **Load JSON**: Parse layout_brief.json
2. **Create Scene**: Set up scene with lighting preset
3. **Place Characters**: Instantiate at CharacterPosition coordinates
4. **Setup Cameras**: Create camera objects with CameraSetup parameters
5. **Animate**: Use movement field to create camera animation

## Determinism

Layout briefs are deterministic:

- Characters sorted by ID
- Camera setups sorted by shot_id
- JSON output with `sort_keys=True`
- Same input always produces same output
