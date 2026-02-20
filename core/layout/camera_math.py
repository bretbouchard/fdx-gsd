"""Camera position calculation for layout briefs.

Calculates camera positions and rotations based on shot types,
following cinematography standards for distance and framing.

Blender Coordinate System (Z-up):
- X: right
- Y: forward (into screen)
- Z: up

Camera is positioned in front of subject (negative Y).
"""
from dataclasses import dataclass
from math import atan2, degrees, sqrt
from typing import Tuple


@dataclass
class CameraPosition:
    """3D position of camera in Blender coordinates."""

    x: float
    y: float
    z: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "z": round(self.z, 3),
        }


@dataclass
class CameraRotation:
    """Camera rotation in degrees (Euler angles)."""

    pitch: float  # X-axis rotation (tilt up/down)
    yaw: float  # Y-axis rotation (pan left/right)
    roll: float  # Z-axis rotation (Dutch angle)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pitch": round(self.pitch, 3),
            "yaw": round(self.yaw, 3),
            "roll": round(self.roll, 3),
        }


# Distance mapping from shot type to camera distance (meters)
# Based on cinematography standards
SHOT_TYPE_DISTANCES = {
    "WS": 5.0,  # Wide Shot - establishes location, full body + environment
    "MS": 2.5,  # Medium Shot - waist up, standard dialogue
    "MCU": 1.8,  # Medium Close-Up - chest up, intimate dialogue
    "CU": 1.2,  # Close-Up - face only, emotional moments
    "ECU": 0.8,  # Extreme Close-Up - single feature (eyes, detail)
    "INSERT": 0.5,  # Insert/Detail - props, objects
    "OTS": 2.0,  # Over-the-shoulder - two-character dialogue
    "POV": 1.7,  # Point of view - eye height
    "TWO": 3.0,  # Two-shot - two characters in frame
}

# Default distance for unknown shot types
DEFAULT_DISTANCE = 2.5

# Camera height by shot type
CAMERA_HEIGHTS = {
    "WS": 2.0,  # Raised for wide shots to see more environment
    "default": 1.6,  # Eye level for most shots
}


def calculate_camera_position(
    shot_type: str,
    subject_position: Tuple[float, float, float],
    subject_height: float = 1.7,
    lens_mm: float = 35.0,
    sensor_width: float = 36.0,
) -> Tuple[CameraPosition, CameraRotation]:
    """
    Calculate camera position and rotation for a shot.

    Args:
        shot_type: Shot type code (WS, MS, MCU, CU, ECU, INSERT, OTS, POV, TWO)
        subject_position: (x, y, z) position of the subject
        subject_height: Height of subject in meters (default 1.7m for average person)
        lens_mm: Lens focal length in mm (default 35mm)
        sensor_width: Sensor width in mm (default 36mm full frame)

    Returns:
        Tuple of (CameraPosition, CameraRotation)
    """
    sx, sy, sz = subject_position

    # Get distance for shot type
    distance = SHOT_TYPE_DISTANCES.get(shot_type, DEFAULT_DISTANCE)

    # Get camera height
    camera_height = CAMERA_HEIGHTS.get(shot_type, CAMERA_HEIGHTS["default"])

    # Camera is positioned in front of subject (negative Y in Blender)
    # Subject is assumed to be facing positive Y
    camera_x = sx
    camera_y = sy - distance  # In front = negative Y
    camera_z = camera_height

    # Target point (look at subject's face/chest level)
    target_x = sx
    target_y = sy
    target_z = sz + subject_height * 0.9  # Eye level on subject

    # Calculate rotation to point camera at target
    rotation = point_camera_at_target(
        CameraPosition(camera_x, camera_y, camera_z),
        (target_x, target_y, target_z),
    )

    return CameraPosition(camera_x, camera_y, camera_z), rotation


def point_camera_at_target(
    camera_pos: CameraPosition,
    target: Tuple[float, float, float],
) -> CameraRotation:
    """
    Calculate rotation to point camera at a target.

    Uses direction vector math (no bpy dependency).

    Args:
        camera_pos: Camera position
        target: (x, y, z) target point to look at

    Returns:
        CameraRotation with pitch, yaw, roll in degrees
    """
    tx, ty, tz = target

    # Direction vector from camera to target
    dx = tx - camera_pos.x
    dy = ty - camera_pos.y
    dz = tz - camera_pos.z

    # Calculate yaw (rotation around Z axis / pan)
    # In Blender: yaw = atan2(dx, dy)
    yaw = degrees(atan2(dx, dy))

    # Calculate pitch (rotation around X axis / tilt)
    # Horizontal distance to target
    horizontal_dist = sqrt(dx * dx + dy * dy)
    pitch = degrees(atan2(dz, horizontal_dist))

    # Roll is always 0 for standard shots (no Dutch angle)
    roll = 0.0

    return CameraRotation(pitch, yaw, roll)


def get_camera_setup_dict(
    shot_type: str,
    subject_position: Tuple[float, float, float],
    lens_mm: float = 35.0,
    sensor_width: float = 36.0,
) -> dict:
    """
    Get a complete camera setup dictionary for CameraSetup.camera field.

    Convenience function that bundles position, rotation, and lens settings.

    Args:
        shot_type: Shot type code
        subject_position: (x, y, z) position of subject
        lens_mm: Lens focal length in mm
        sensor_width: Sensor width in mm

    Returns:
        Dict with position, rotation, lens_mm, sensor_width
    """
    pos, rot = calculate_camera_position(
        shot_type, subject_position, lens_mm=lens_mm, sensor_width=sensor_width
    )

    return {
        "position": pos.to_dict(),
        "rotation": rot.to_dict(),
        "lens_mm": lens_mm,
        "sensor_width": sensor_width,
    }
