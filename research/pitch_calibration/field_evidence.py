from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .keypoint_detection import ImageKeypoint, detect_keypoints
from .line_detection import ImageSegment, LineDetectionConfig, detect_segments


@dataclass(frozen=True, slots=True)
class EvidenceConfig:
    camera_profile: str = "fixed"
    grass_min_saturation: int = 45
    grass_min_value: int = 35
    white_max_saturation: int = 80
    white_min_value: int = 145
    minimum_grass_ratio: float = 0.18
    minimum_line_ratio: float = 0.0005
    line_detection: LineDetectionConfig = LineDetectionConfig()


@dataclass(slots=True)
class FieldEvidence:
    grass_mask: np.ndarray
    line_mask: np.ndarray
    segments: list[ImageSegment]
    keypoints: list[ImageKeypoint]
    grass_ratio: float
    line_ratio: float
    confidence: float
    valid_region: dict[str, object] | None
    optional_circles: list[dict[str, float]]
    rejection_reasons: list[str]

    def summary(self) -> dict[str, object]:
        return {
            "grass_ratio": round(self.grass_ratio, 6),
            "line_ratio": round(self.line_ratio, 6),
            "segment_count": len(self.segments),
            "keypoint_count": len(self.keypoints),
            "confidence": round(self.confidence, 6),
            "valid_region": self.valid_region,
            "optional_circles": self.optional_circles,
            "rejection_reasons": self.rejection_reasons,
            "segments": [segment.as_dict() for segment in self.segments],
            "keypoints": [keypoint.as_dict() for keypoint in self.keypoints],
        }


def extract_field_evidence(
    image: np.ndarray,
    config: EvidenceConfig | None = None,
) -> FieldEvidence:
    cfg = config or EvidenceConfig()
    if image is None or image.size == 0:
        raise ValueError("image is empty")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    green = (
        (hue >= 25)
        & (hue <= 100)
        & (saturation >= cfg.grass_min_saturation)
        & (value >= cfg.grass_min_value)
    )
    grass_mask = (green.astype(np.uint8) * 255)
    kernel = np.ones((7, 7), np.uint8)
    grass_mask = cv2.morphologyEx(grass_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    grass_mask = cv2.morphologyEx(grass_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    grass_mask = _select_field_component(grass_mask)
    grass_support = cv2.dilate(grass_mask, np.ones((13, 13), np.uint8))
    white = (
        (saturation <= cfg.white_max_saturation)
        & (value >= cfg.white_min_value)
        & (grass_support > 0)
    )
    line_mask = (white.astype(np.uint8) * 255)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    grass_ratio = float(np.count_nonzero(grass_mask) / grass_mask.size)
    line_ratio = float(np.count_nonzero(line_mask) / line_mask.size)
    segments = detect_segments(line_mask, cfg.line_detection)
    height, width = image.shape[:2]
    keypoints = detect_keypoints(segments[:24], (width, height))
    valid_region = _largest_region(grass_mask)
    circles = _detect_circles(line_mask)
    reasons: list[str] = []
    if grass_ratio < cfg.minimum_grass_ratio:
        reasons.append("insufficient_grass_coverage")
    if line_ratio < cfg.minimum_line_ratio:
        reasons.append("insufficient_white_line_evidence")
    if len(segments) < 3:
        reasons.append("insufficient_line_segments")
    components = (
        min(1.0, grass_ratio / 0.45),
        min(1.0, line_ratio / 0.01),
        min(1.0, len(segments) / 10.0),
        min(1.0, len(keypoints) / 8.0),
    )
    confidence = float(sum(components) / len(components))
    return FieldEvidence(
        grass_mask=grass_mask,
        line_mask=line_mask,
        segments=segments,
        keypoints=keypoints,
        grass_ratio=grass_ratio,
        line_ratio=line_ratio,
        confidence=confidence,
        valid_region=valid_region,
        optional_circles=circles,
        rejection_reasons=reasons,
    )


def evidence_config_dict(config: EvidenceConfig) -> dict[str, object]:
    return asdict(config)


def _largest_region(mask: np.ndarray) -> dict[str, object] | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) <= 0:
        return None
    x, y, width, height = cv2.boundingRect(contour)
    epsilon = 0.01 * cv2.arcLength(contour, True)
    polygon = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
    return {
        "bbox_xyxy": [float(x), float(y), float(x + width), float(y + height)],
        "polygon": [[float(px), float(py)] for px, py in polygon],
    }


def _select_field_component(mask: np.ndarray) -> np.ndarray:
    component_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask, connectivity=8
    )
    if component_count <= 1:
        return mask
    height, width = mask.shape[:2]
    frame_area = float(height * width)
    candidates: list[tuple[float, int]] = []
    for label in range(1, component_count):
        x, y, component_width, component_height, area = stats[label]
        bottom = y + component_height
        if area < frame_area * 0.01 or bottom < height * 0.48:
            continue
        center_y = float(centroids[label][1]) / max(1.0, float(height))
        bottom_ratio = float(bottom) / max(1.0, float(height))
        score = float(area) * (0.35 + center_y + bottom_ratio)
        candidates.append((score, label))
    if not candidates:
        return np.zeros_like(mask)
    primary_label = max(candidates)[1]
    primary = np.where(labels == primary_label, 255, 0).astype(np.uint8)
    return cv2.morphologyEx(primary, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))


def _detect_circles(mask: np.ndarray) -> list[dict[str, float]]:
    blurred = cv2.GaussianBlur(mask, (7, 7), 1.5)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.5,
        minDist=max(20, mask.shape[0] // 5),
        param1=100,
        param2=25,
        minRadius=max(8, mask.shape[0] // 40),
        maxRadius=max(12, mask.shape[0] // 3),
    )
    if circles is None:
        return []
    return [
        {"x": round(float(x), 3), "y": round(float(y), 3), "radius": round(float(radius), 3)}
        for x, y, radius in circles[0, :3]
    ]
