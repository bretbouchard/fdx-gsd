"""Unit tests for shot type enums."""
import pytest

from core.shots.types import ShotType, CameraAngle, CameraMovement


class TestShotType:
    """Tests for ShotType enum."""

    def test_shot_type_values(self):
        """Verify all ShotType enum values are correct strings."""
        assert ShotType.WS.value == "WS"
        assert ShotType.MS.value == "MS"
        assert ShotType.MCU.value == "MCU"
        assert ShotType.CU.value == "CU"
        assert ShotType.ECU.value == "ECU"
        assert ShotType.INSERT.value == "INSERT"
        assert ShotType.OTS.value == "OTS"
        assert ShotType.POV.value == "POV"
        assert ShotType.TWO.value == "TWO"

    def test_shot_type_count(self):
        """Verify we have all expected shot types."""
        assert len(ShotType) == 9

    def test_shot_type_lookup(self):
        """Verify ShotType lookup by value works."""
        assert ShotType("CU") == ShotType.CU
        assert ShotType("WS") == ShotType.WS
        assert ShotType("OTS") == ShotType.OTS


class TestCameraAngle:
    """Tests for CameraAngle enum."""

    def test_camera_angle_values(self):
        """Verify all CameraAngle enum values."""
        assert CameraAngle.EYE_LEVEL.value == "eye-level"
        assert CameraAngle.HIGH.value == "high"
        assert CameraAngle.LOW.value == "low"
        assert CameraAngle.DUTCH.value == "dutch"

    def test_camera_angle_count(self):
        """Verify we have all expected camera angles."""
        assert len(CameraAngle) == 4

    def test_camera_angle_lookup(self):
        """Verify CameraAngle lookup by value works."""
        assert CameraAngle("eye-level") == CameraAngle.EYE_LEVEL
        assert CameraAngle("high") == CameraAngle.HIGH


class TestCameraMovement:
    """Tests for CameraMovement enum."""

    def test_camera_movement_values(self):
        """Verify all CameraMovement enum values."""
        assert CameraMovement.STATIC.value == "Static"
        assert CameraMovement.PAN.value == "Pan"
        assert CameraMovement.TILT.value == "Tilt"
        assert CameraMovement.DOLLY.value == "Dolly"
        assert CameraMovement.TRACKING.value == "Tracking"
        assert CameraMovement.HANDHELD.value == "Handheld"

    def test_camera_movement_count(self):
        """Verify we have all expected camera movements."""
        assert len(CameraMovement) == 6

    def test_camera_movement_lookup(self):
        """Verify CameraMovement lookup by value works."""
        assert CameraMovement("Static") == CameraMovement.STATIC
        assert CameraMovement("Pan") == CameraMovement.PAN
