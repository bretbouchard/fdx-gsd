"""Shot type enums for the Shot Layer.

Defines the standard shot types, camera angles, and camera movements
used in cinematography and shot list generation.

Following the IssueSeverity pattern from core/validation/base.py.
"""
from enum import Enum


class ShotType(Enum):
    """Shot size/type following industry standard terminology.

    These represent the framing of the subject within the shot.
    """

    WS = "WS"  # Wide Shot (establishes location, shows full body)
    MS = "MS"  # Medium Shot (waist up, standard dialogue)
    MCU = "MCU"  # Medium Close-Up (chest up, intimate dialogue)
    CU = "CU"  # Close-Up (face only, emotional moments)
    ECU = "ECU"  # Extreme Close-Up (eyes, detail focus)
    INSERT = "INSERT"  # Insert/Detail shot (props, objects)
    OTS = "OTS"  # Over-the-shoulder (two-character dialogue)
    POV = "POV"  # Point of view (character perspective)
    TWO = "TWO"  # Two-shot (two characters in frame)


class CameraAngle(Enum):
    """Camera angle relative to subject.

    The vertical positioning of the camera affects the
    psychological impact of the shot.
    """

    EYE_LEVEL = "eye-level"  # Neutral, standard perspective
    HIGH = "high"  # Looking down, diminishes subject
    LOW = "low"  # Looking up, empowers subject
    DUTCH = "dutch"  # Tilted/canted, creates unease


class CameraMovement(Enum):
    """Camera movement type during the shot.

    Movement adds dynamism and can follow action or
    reveal information.
    """

    STATIC = "Static"  # Camera doesn't move
    PAN = "Pan"  # Horizontal rotation on tripod
    TILT = "Tilt"  # Vertical rotation on tripod
    DOLLY = "Dolly"  # Camera moves through space
    TRACKING = "Tracking"  # Follows moving subject
    HANDHELD = "Handheld"  # Organic, documentary feel
