"""Unit tests for camera position calculation.

Tests all functions in core/layout/camera_math.py:
- calculate_camera_position()
- point_camera_at_target()
- get_camera_setup_dict()
"""
import pytest
from math import isclose

from core.layout.camera_math import (
    calculate_camera_position,
    point_camera_at_target,
    get_camera_setup_dict,
    CameraPosition,
    CameraRotation,
    SHOT_TYPE_DISTANCES,
)


class TestCalculateCameraPosition:
    """Tests for calculate_camera_position function."""

    def test_wide_shot_distance(self):
        """Test WS places camera at 5m from subject."""
        pos, rot = calculate_camera_position("WS", (0, 0, 0))

        # Camera should be 5m in front (negative Y)
        assert isclose(pos.y, -5.0, rel_tol=0.1)
        assert isclose(pos.x, 0.0, rel_tol=0.1)

    def test_medium_shot_distance(self):
        """Test MS places camera at 2.5m from subject."""
        pos, rot = calculate_camera_position("MS", (0, 0, 0))

        assert isclose(pos.y, -2.5, rel_tol=0.1)

    def test_close_up_distance(self):
        """Test CU places camera at 1.2m from subject."""
        pos, rot = calculate_camera_position("CU", (0, 0, 0))

        assert isclose(pos.y, -1.2, rel_tol=0.1)

    def test_extreme_close_up_distance(self):
        """Test ECU places camera at 0.8m from subject."""
        pos, rot = calculate_camera_position("ECU", (0, 0, 0))

        assert isclose(pos.y, -0.8, rel_tol=0.1)

    def test_insert_shot_distance(self):
        """Test INSERT places camera at 0.5m from subject."""
        pos, rot = calculate_camera_position("INSERT", (0, 0, 0))

        assert isclose(pos.y, -0.5, rel_tol=0.1)

    def test_ots_distance(self):
        """Test OTS places camera at 2.0m from subject."""
        pos, rot = calculate_camera_position("OTS", (0, 0, 0))

        assert isclose(pos.y, -2.0, rel_tol=0.1)

    def test_pov_distance(self):
        """Test POV places camera at 1.7m from subject."""
        pos, rot = calculate_camera_position("POV", (0, 0, 0))

        assert isclose(pos.y, -1.7, rel_tol=0.1)

    def test_two_shot_distance(self):
        """Test TWO places camera at 3.0m from subject."""
        pos, rot = calculate_camera_position("TWO", (0, 0, 0))

        assert isclose(pos.y, -3.0, rel_tol=0.1)

    def test_medium_close_up_distance(self):
        """Test MCU places camera at 1.8m from subject."""
        pos, rot = calculate_camera_position("MCU", (0, 0, 0))

        assert isclose(pos.y, -1.8, rel_tol=0.1)

    def test_returns_correct_types(self):
        """Test function returns CameraPosition and CameraRotation."""
        pos, rot = calculate_camera_position("MS", (0, 0, 0))

        assert isinstance(pos, CameraPosition)
        assert isinstance(rot, CameraRotation)

    def test_camera_position_to_dict(self):
        """Test CameraPosition.to_dict() returns correct dict."""
        pos = CameraPosition(1.0, 2.0, 3.0)
        result = pos.to_dict()

        assert result == {"x": 1.0, "y": 2.0, "z": 3.0}

    def test_camera_rotation_to_dict(self):
        """Test CameraRotation.to_dict() returns correct dict."""
        rot = CameraRotation(10.0, 20.0, 0.0)
        result = rot.to_dict()

        assert result == {"pitch": 10.0, "yaw": 20.0, "roll": 0.0}

    def test_unknown_shot_type_uses_default(self):
        """Test unknown shot type uses default distance."""
        pos, rot = calculate_camera_position("UNKNOWN_TYPE", (0, 0, 0))

        # Should still be in front of subject
        assert pos.y < 0

    def test_subject_offset(self):
        """Test camera maintains relative position with offset subject."""
        # Subject at (5, 5, 0)
        pos, rot = calculate_camera_position("MS", (5, 5, 0))

        # Camera should maintain relative positioning
        # X should match subject X
        assert isclose(pos.x, 5.0, rel_tol=0.1)
        # Y should be 2.5m in front of subject
        assert isclose(pos.y, 5.0 - 2.5, rel_tol=0.1)

    def test_wide_shot_raised_camera(self):
        """Test WS uses raised camera height."""
        pos, rot = calculate_camera_position("WS", (0, 0, 0))

        # WS should use 2.0m camera height
        assert isclose(pos.z, 2.0, rel_tol=0.1)

    def test_other_shots_eye_level(self):
        """Test non-WS shots use eye-level camera height."""
        pos_ms, _ = calculate_camera_position("MS", (0, 0, 0))
        pos_cu, _ = calculate_camera_position("CU", (0, 0, 0))

        # Should use 1.6m camera height (eye level)
        assert isclose(pos_ms.z, 1.6, rel_tol=0.1)
        assert isclose(pos_cu.z, 1.6, rel_tol=0.1)


class TestPointCameraAtTarget:
    """Tests for point_camera_at_target function."""

    def test_returns_camera_rotation(self):
        """Test function returns CameraRotation."""
        cam_pos = CameraPosition(0, -5, 1.6)
        rot = point_camera_at_target(cam_pos, (0, 0, 1.6))

        assert isinstance(rot, CameraRotation)

    def test_camera_pointing_forward(self):
        """Test camera in front of target has zero yaw."""
        cam_pos = CameraPosition(0, -5, 1.6)
        rot = point_camera_at_target(cam_pos, (0, 0, 1.6))

        # Yaw should be approximately 0 (pointing along positive Y)
        assert isclose(rot.yaw, 0.0, abs_tol=1.0)

    def test_roll_is_zero(self):
        """Test roll is always zero for standard shots."""
        cam_pos = CameraPosition(0, -5, 1.6)
        rot = point_camera_at_target(cam_pos, (0, 0, 1.6))

        assert isclose(rot.roll, 0.0, abs_tol=0.1)


class TestGetCameraSetupDict:
    """Tests for get_camera_setup_dict convenience function."""

    def test_returns_complete_dict(self):
        """Test function returns complete camera setup dict."""
        result = get_camera_setup_dict("MS", (0, 0, 0))

        assert "position" in result
        assert "rotation" in result
        assert "lens_mm" in result
        assert "sensor_width" in result

    def test_default_lens_values(self):
        """Test default lens and sensor values."""
        result = get_camera_setup_dict("CU", (0, 0, 0))

        assert result["lens_mm"] == 35.0
        assert result["sensor_width"] == 36.0

    def test_custom_lens_values(self):
        """Test custom lens and sensor values."""
        result = get_camera_setup_dict("CU", (0, 0, 0), lens_mm=50, sensor_width=24)

        assert result["lens_mm"] == 50.0
        assert result["sensor_width"] == 24.0


class TestShotTypeDistances:
    """Tests for SHOT_TYPE_DISTANCES constant."""

    def test_all_shot_types_defined(self):
        """Test all expected shot types have defined distances."""
        expected_types = ["WS", "MS", "MCU", "CU", "ECU", "INSERT", "OTS", "POV", "TWO"]

        for shot_type in expected_types:
            assert shot_type in SHOT_TYPE_DISTANCES
            assert SHOT_TYPE_DISTANCES[shot_type] > 0

    def test_distances_are_reasonable(self):
        """Test distances are within reasonable cinematographic ranges."""
        for shot_type, distance in SHOT_TYPE_DISTANCES.items():
            # Distances should be positive and reasonable
            assert 0.1 < distance < 20.0, f"{shot_type} distance {distance} out of range"
