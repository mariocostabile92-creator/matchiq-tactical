from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import Detection
from .utils import require_cv2_numpy


@dataclass(slots=True)
class TeamAssignment:
    team_id: str
    confidence: float
    feature: tuple[float, float, float] | None
    reason: str


def extract_team_color_feature(
    frame: object,
    bbox_xyxy: tuple[float, float, float, float],
) -> tuple[float, float, float] | None:
    cv2, np = require_cv2_numpy()
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox_xyxy
    x1 = max(0, min(width - 1, int(round(x1))))
    x2 = max(0, min(width, int(round(x2))))
    y1 = max(0, min(height - 1, int(round(y1))))
    y2 = max(0, min(height, int(round(y2))))
    if x2 - x1 < 8 or y2 - y1 < 16:
        return None
    box_height = y2 - y1
    torso_top = y1 + int(box_height * 0.12)
    torso_bottom = y1 + int(box_height * 0.58)
    margin = max(1, int((x2 - x1) * 0.15))
    crop = frame[torso_top:torso_bottom, x1 + margin : x2 - margin]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, np.array([28, 25, 18]), np.array([100, 255, 255]))
    valid_pixels = crop[green == 0]
    if len(valid_pixels) < 20:
        return None
    lab_pixels = cv2.cvtColor(valid_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).reshape(-1, 3)
    median = np.median(lab_pixels, axis=0)
    return tuple(round(float(value), 3) for value in median)


class OnlineTeamClassifier:
    def __init__(
        self,
        *,
        enabled: bool = True,
        random_seed: int = 42,
        minimum_samples: int = 6,
        minimum_separation: float = 22.0,
        minimum_confidence: float = 0.58,
    ) -> None:
        self.enabled = enabled
        self.random_seed = random_seed
        self.minimum_samples = minimum_samples
        self.minimum_separation = minimum_separation
        self.minimum_confidence = minimum_confidence
        self._samples: list[tuple[float, float, float]] = []
        self._centers: list[object] = []
        self._assignments = {"team_a": 0, "team_b": 0, "unknown": 0}

    def _initialize_centers(self) -> None:
        if self._centers or len(self._samples) < self.minimum_samples:
            return
        _, np = require_cv2_numpy()
        matrix = np.array(self._samples, dtype=np.float32)
        best_distance = -1.0
        best_pair = (0, 1)
        for first in range(len(matrix)):
            for second in range(first + 1, len(matrix)):
                distance = float(np.linalg.norm(matrix[first] - matrix[second]))
                if distance > best_distance:
                    best_distance = distance
                    best_pair = (first, second)
        if best_distance < self.minimum_separation:
            return
        self._centers = [matrix[best_pair[0]].copy(), matrix[best_pair[1]].copy()]

    def classify(
        self,
        frame: object,
        bbox_xyxy: tuple[float, float, float, float],
    ) -> TeamAssignment:
        if not self.enabled:
            return TeamAssignment("unknown", 0.0, None, "disabled")
        feature = extract_team_color_feature(frame, bbox_xyxy)
        if feature is None:
            self._assignments["unknown"] += 1
            return TeamAssignment("unknown", 0.0, None, "insufficient_color_pixels")
        self._samples.append(feature)
        self._initialize_centers()
        if len(self._centers) != 2:
            self._assignments["unknown"] += 1
            return TeamAssignment("unknown", 0.0, feature, "clusters_not_stable")
        _, np = require_cv2_numpy()
        vector = np.array(feature, dtype=np.float32)
        distances = [float(np.linalg.norm(vector - center)) for center in self._centers]
        nearest = 0 if distances[0] <= distances[1] else 1
        near_distance = distances[nearest]
        far_distance = distances[1 - nearest]
        confidence = max(0.0, min(1.0, (far_distance - near_distance) / max(far_distance, 1.0)))
        if confidence < self.minimum_confidence:
            self._assignments["unknown"] += 1
            return TeamAssignment("unknown", round(confidence, 6), feature, "ambiguous_colors")
        team_id = "team_a" if nearest == 0 else "team_b"
        self._assignments[team_id] += 1
        self._centers[nearest] = (self._centers[nearest] * 0.92) + (vector * 0.08)
        return TeamAssignment(team_id, round(confidence, 6), feature, "probabilistic_color_cluster")

    def classify_detections(self, frame: object, detections: list[Detection]) -> list[Detection]:
        for detection in detections:
            if detection.class_name != "person":
                continue
            assignment = self.classify(frame, detection.bbox_xyxy)
            detection.metadata.update(
                {
                    "team_id": assignment.team_id,
                    "team_confidence": assignment.confidence,
                    "team_reason": assignment.reason,
                }
            )
        return detections

    def metadata(self) -> dict[str, Any]:
        centers = [center.tolist() for center in self._centers]
        return {
            "enabled": self.enabled,
            "method": "online_lab_two_cluster",
            "sample_count": len(self._samples),
            "centers_lab": centers,
            "assignments": dict(self._assignments),
            "minimum_confidence": self.minimum_confidence,
            "labels_are_probabilistic": True,
        }
