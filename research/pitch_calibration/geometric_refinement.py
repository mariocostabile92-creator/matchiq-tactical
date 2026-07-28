from __future__ import annotations

import cv2
import numpy as np


def refine_homography(
    matrix: np.ndarray,
    image_points: np.ndarray,
    pitch_points: np.ndarray,
    inlier_mask: tuple[bool, ...],
) -> np.ndarray:
    mask = np.asarray(inlier_mask, dtype=bool)
    source = np.asarray(image_points, dtype=np.float64)
    target = np.asarray(pitch_points, dtype=np.float64)
    if len(mask) != len(source) or np.count_nonzero(mask) < 4:
        return np.asarray(matrix, dtype=np.float64)
    refined, _ = cv2.findHomography(source[mask], target[mask], method=0)
    if refined is None or not np.isfinite(refined).all() or abs(np.linalg.det(refined)) < 1.0e-12:
        return np.asarray(matrix, dtype=np.float64)
    return np.asarray(refined, dtype=np.float64)
