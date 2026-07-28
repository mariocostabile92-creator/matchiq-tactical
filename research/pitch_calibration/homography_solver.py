from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class HomographyEstimate:
    matrix: np.ndarray | None
    inverse: np.ndarray | None
    inlier_mask: tuple[bool, ...]
    inlier_ratio: float
    reprojection_error_px: float | None
    condition_number: float | None
    spatial_spread: float
    failure_reason: str | None = None


def normalized_dlt(
    image_points: np.ndarray,
    pitch_points: np.ndarray,
) -> np.ndarray:
    source = _points(image_points)
    target = _points(pitch_points)
    if len(source) != len(target) or len(source) < 4:
        raise ValueError("at least four paired points are required")
    if _spatial_spread(source) <= 1.0e-4 or _spatial_spread(target) <= 1.0e-4:
        raise ValueError("points are collinear or insufficiently distributed")
    source_n, source_transform = _normalize(source)
    target_n, target_transform = _normalize(target)
    rows = []
    for (x, y), (u, v) in zip(source_n, target_n, strict=True):
        rows.extend(
            (
                [-x, -y, -1.0, 0.0, 0.0, 0.0, u * x, u * y, u],
                [0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v],
            )
        )
    _, _, vectors = np.linalg.svd(np.asarray(rows, dtype=np.float64))
    normalized = vectors[-1].reshape(3, 3)
    matrix = np.linalg.inv(target_transform) @ normalized @ source_transform
    if abs(matrix[2, 2]) < 1.0e-12:
        raise ValueError("homography normalization is unstable")
    matrix /= matrix[2, 2]
    if not np.isfinite(matrix).all():
        raise ValueError("homography contains non-finite values")
    return matrix


def estimate_homography(
    image_points: np.ndarray,
    pitch_points: np.ndarray,
    *,
    ransac_threshold_px: float = 6.0,
    seed: int = 7,
) -> HomographyEstimate:
    try:
        source = _points(image_points)
        target = _points(pitch_points)
    except ValueError as exc:
        return _failure(str(exc))
    if len(source) != len(target) or len(source) < 4:
        return _failure("insufficient_correspondences")
    spread = min(_spatial_spread(source), _spatial_spread(target))
    if spread <= 1.0e-4:
        return _failure("collinear_or_concentrated_correspondences", spread)
    cv2.setRNGSeed(int(seed))
    matrix, mask = cv2.findHomography(
        source,
        target,
        cv2.RANSAC,
        ransacReprojThreshold=float(ransac_threshold_px),
        maxIters=3000,
        confidence=0.995,
    )
    if matrix is None or mask is None:
        return _failure("homography_estimation_failed", spread)
    matrix = np.asarray(matrix, dtype=np.float64)
    if not np.isfinite(matrix).all():
        return _failure("non_finite_homography", spread)
    determinant = float(np.linalg.det(matrix))
    if abs(determinant) < 1.0e-12:
        return _failure("singular_homography", spread)
    try:
        inverse = np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return _failure("non_invertible_homography", spread)
    inliers = mask.reshape(-1).astype(bool)
    projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    errors = np.linalg.norm(projected - target, axis=1)
    used_errors = errors[inliers] if np.any(inliers) else errors
    return HomographyEstimate(
        matrix=matrix,
        inverse=inverse,
        inlier_mask=tuple(bool(value) for value in inliers),
        inlier_ratio=float(np.mean(inliers)),
        reprojection_error_px=float(np.mean(used_errors)),
        condition_number=float(np.linalg.cond(matrix)),
        spatial_spread=spread,
    )


def reprojection_errors(
    matrix: np.ndarray,
    image_points: np.ndarray,
    pitch_points: np.ndarray,
) -> np.ndarray:
    source = _points(image_points)
    target = _points(pitch_points)
    projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    return np.linalg.norm(projected - target, axis=1)


def _points(values: np.ndarray) -> np.ndarray:
    points = np.asarray(values, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError("points must be a finite Nx2 array")
    return points


def _normalize(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    center = points.mean(axis=0)
    distances = np.linalg.norm(points - center, axis=1)
    mean_distance = float(np.mean(distances))
    if mean_distance <= 1.0e-12:
        raise ValueError("points cannot be normalized")
    scale = np.sqrt(2.0) / mean_distance
    transform = np.asarray(
        [[scale, 0.0, -scale * center[0]], [0.0, scale, -scale * center[1]], [0.0, 0.0, 1.0]]
    )
    homogeneous = np.column_stack((points, np.ones(len(points))))
    normalized = (transform @ homogeneous.T).T
    return normalized[:, :2], transform


def _spatial_spread(points: np.ndarray) -> float:
    centered = points - points.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    if len(singular) < 2 or singular[0] <= 1.0e-12:
        return 0.0
    return float(singular[1] / singular[0])


def _failure(reason: str, spread: float = 0.0) -> HomographyEstimate:
    return HomographyEstimate(
        matrix=None,
        inverse=None,
        inlier_mask=(),
        inlier_ratio=0.0,
        reprojection_error_px=None,
        condition_number=None,
        spatial_spread=spread,
        failure_reason=reason,
    )
