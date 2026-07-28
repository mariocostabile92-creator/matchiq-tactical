from __future__ import annotations

from typing import Any, Iterable

import cv2
import numpy as np


def as_homography(matrix: Any) -> np.ndarray:
    value = np.asarray(matrix, dtype=np.float64)
    if value.shape != (3, 3):
        raise ValueError("homography must be a 3x3 matrix")
    if not np.isfinite(value).all():
        raise ValueError("homography contains non-finite values")
    return value


def invert_homography(matrix: Any) -> np.ndarray:
    value = as_homography(matrix)
    determinant = float(np.linalg.det(value))
    if abs(determinant) < 1.0e-12:
        raise ValueError("homography is singular")
    return np.linalg.inv(value)


def project_point(matrix: Any, point_xy: Iterable[float]) -> tuple[float, float] | None:
    value = as_homography(matrix)
    point = np.asarray(list(point_xy), dtype=np.float64)
    if point.shape != (2,) or not np.isfinite(point).all():
        return None
    projected = cv2.perspectiveTransform(point.reshape(1, 1, 2), value).reshape(2)
    if not np.isfinite(projected).all():
        return None
    return float(projected[0]), float(projected[1])


def canonical_normalized(
    point_meters: tuple[float, float],
    pitch_length: float,
    pitch_width: float,
) -> tuple[float, float]:
    return point_meters[0] / pitch_length, point_meters[1] / pitch_width


def project_observations(
    observations: Iterable[dict[str, Any]],
    homography_image_to_pitch: Any | None,
    *,
    canonical_pitch_length: float,
    canonical_pitch_width: float,
    physical_pitch_length: float | None,
    physical_pitch_width: float | None,
    calibration_status: str,
    calibration_confidence: float,
    calibration_id: str | None = None,
    camera_segment_id: str | None = None,
    minimum_calibration_confidence: float = 0.0,
    valid_image_region: dict[str, Any] | None = None,
    maximum_outside_tolerance: float = 0.10,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for observation in observations:
        foot_point = observation.get("foot_point_xy")
        if not isinstance(foot_point, (list, tuple)) or len(foot_point) != 2:
            continue
        record = {
            "track_id": observation.get("track_id"),
            "frame_id": observation.get("frame_id"),
            "timestamp_seconds": observation.get("timestamp_seconds"),
            "team": observation.get("team_assignment", "UNKNOWN"),
            "team_assignment": observation.get("team_assignment", "UNKNOWN"),
            "foot_point_pixel": [float(foot_point[0]), float(foot_point[1])],
            "image_foot_point": [float(foot_point[0]), float(foot_point[1])],
            "pitch_position_normalized": None,
            "pitch_position_canonical_meters": None,
            "pitch_position_physical_meters": None,
            "canonical_normalized": None,
            "canonical_meters": None,
            "physical_meters": None,
            "calibration_status": calibration_status,
            "calibration_confidence": round(calibration_confidence, 6),
            "calibration_id": calibration_id,
            "camera_segment_id": camera_segment_id,
            "inside_valid_region": _inside_valid_region(foot_point, valid_image_region),
            "projection_valid": False,
            "exclusion_reason": None,
        }
        if calibration_status in ("AMBIGUOUS", "UNCALIBRATED", "REJECTED"):
            record["exclusion_reason"] = f"calibration_status_{calibration_status.lower()}"
            records.append(record)
            continue
        if calibration_confidence < minimum_calibration_confidence:
            record["exclusion_reason"] = "calibration_confidence_below_threshold"
            records.append(record)
            continue
        if not record["inside_valid_region"]:
            record["exclusion_reason"] = "foot_point_outside_valid_image_region"
            records.append(record)
            continue
        if homography_image_to_pitch is None:
            record["exclusion_reason"] = "missing_homography"
            records.append(record)
            continue
        point = project_point(homography_image_to_pitch, foot_point)
        if point is None:
            record["exclusion_reason"] = "numerically_unstable_projection"
            records.append(record)
            continue
        normalized = canonical_normalized(
            point, canonical_pitch_length, canonical_pitch_width
        )
        if not (
            -maximum_outside_tolerance
            <= normalized[0]
            <= 1.0 + maximum_outside_tolerance
            and -maximum_outside_tolerance
            <= normalized[1]
            <= 1.0 + maximum_outside_tolerance
        ):
            record["exclusion_reason"] = "projected_position_too_far_outside_pitch"
            records.append(record)
            continue
        physical = None
        if physical_pitch_length is not None and physical_pitch_width is not None:
            physical = [
                normalized[0] * physical_pitch_length,
                normalized[1] * physical_pitch_width,
            ]
        normalized_value = [round(normalized[0], 8), round(normalized[1], 8)]
        canonical_value = [round(point[0], 6), round(point[1], 6)]
        physical_value = [round(value, 6) for value in physical] if physical else None
        record.update(
            pitch_position_normalized=normalized_value,
            pitch_position_canonical_meters=canonical_value,
            pitch_position_physical_meters=physical_value,
            canonical_normalized=normalized_value,
            canonical_meters=canonical_value,
            physical_meters=physical_value,
            projection_valid=True,
        )
        records.append(record)
    return records


def _inside_valid_region(
    point_xy: Iterable[float],
    region: dict[str, Any] | None,
) -> bool:
    if not region:
        return True
    point = tuple(float(value) for value in point_xy)
    bbox = region.get("bbox_xyxy")
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]
    polygon = region.get("polygon")
    if isinstance(polygon, list) and len(polygon) >= 3:
        contour = np.asarray(polygon, dtype=np.float32)
        return cv2.pointPolygonTest(contour, point, False) >= 0
    return True


def inside_pitch_ratio(
    points: Iterable[tuple[float, float]],
    pitch_length: float,
    pitch_width: float,
    *,
    tolerance: float = 0.05,
) -> float | None:
    values = list(points)
    if not values:
        return None
    margin_x = pitch_length * tolerance
    margin_y = pitch_width * tolerance
    inside = sum(
        -margin_x <= x <= pitch_length + margin_x
        and -margin_y <= y <= pitch_width + margin_y
        for x, y in values
    )
    return inside / len(values)
