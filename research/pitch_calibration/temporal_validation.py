from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class TemporalDecision:
    compatible: bool
    visual_jump: bool
    homography_jump: float | None
    confidence: float
    camera_segment_increment: bool
    reason: str | None = None


def visual_histogram(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    return cv2.normalize(histogram, histogram).reshape(-1)


def histogram_distance(first: np.ndarray, second: np.ndarray) -> float:
    return float(cv2.compareHist(first.astype(np.float32), second.astype(np.float32), cv2.HISTCMP_BHATTACHARYYA))


def assess_temporal_pair(
    previous_matrix: np.ndarray | None,
    current_matrix: np.ndarray | None,
    previous_histogram: np.ndarray | None,
    current_histogram: np.ndarray | None,
    *,
    visual_jump_threshold: float = 0.48,
    homography_jump_threshold: float = 0.18,
) -> TemporalDecision:
    visual_jump = False
    if previous_histogram is not None and current_histogram is not None:
        visual_jump = histogram_distance(previous_histogram, current_histogram) > visual_jump_threshold
    jump = _corner_jump(previous_matrix, current_matrix)
    matrix_jump = jump is not None and jump > homography_jump_threshold
    compatible = not visual_jump and not matrix_jump
    confidence = 1.0
    if jump is not None:
        confidence *= max(0.0, 1.0 - jump / max(homography_jump_threshold, 1.0e-9))
    if visual_jump:
        confidence = 0.0
    reason = "visual_cut" if visual_jump else ("homography_jump" if matrix_jump else None)
    return TemporalDecision(
        compatible=compatible,
        visual_jump=visual_jump,
        homography_jump=jump,
        confidence=float(confidence),
        camera_segment_increment=not compatible,
        reason=reason,
    )


def smooth_compatible_homographies(
    previous: np.ndarray,
    current: np.ndarray,
    *,
    current_weight: float = 0.65,
) -> np.ndarray:
    if not 0.0 <= current_weight <= 1.0:
        raise ValueError("current_weight must be between 0 and 1")
    value = (1.0 - current_weight) * np.asarray(previous) + current_weight * np.asarray(current)
    if abs(value[2, 2]) > 1.0e-12:
        value = value / value[2, 2]
    return value


def decay_confidence(confidence: float, missing_frames: int, *, factor: float = 0.78) -> float:
    if missing_frames < 0:
        raise ValueError("missing_frames cannot be negative")
    return float(max(0.0, min(1.0, confidence)) * factor**missing_frames)


def _corner_jump(previous: np.ndarray | None, current: np.ndarray | None) -> float | None:
    if previous is None or current is None:
        return None
    reference = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
    try:
        first = cv2.perspectiveTransform(reference.reshape(-1, 1, 2), previous).reshape(-1, 2)
        second = cv2.perspectiveTransform(reference.reshape(-1, 1, 2), current).reshape(-1, 2)
    except cv2.error:
        return None
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        return None
    return float(np.mean(np.linalg.norm(first - second, axis=1)) / np.linalg.norm([105.0, 68.0]))
