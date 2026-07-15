from __future__ import annotations

from dataclasses import dataclass

from .utils import require_cv2_numpy


@dataclass(slots=True)
class PitchAnalysis:
    pitch_visible: bool
    green_ratio: float
    largest_green_region_ratio: float
    tactical_view_score: float
    mask: object | None = None

    def to_dict(self) -> dict[str, float | bool]:
        return {
            "pitch_visible": self.pitch_visible,
            "green_ratio": self.green_ratio,
            "largest_green_region_ratio": self.largest_green_region_ratio,
            "tactical_view_score": self.tactical_view_score,
        }


class PitchDetector:
    def __init__(self, *, minimum_green_ratio: float = 0.18) -> None:
        self.minimum_green_ratio = minimum_green_ratio

    def analyze(self, frame: object, *, include_mask: bool = False) -> PitchAnalysis:
        cv2, np = require_cv2_numpy()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([28, 25, 18], dtype=np.uint8)
        upper = np.array([100, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        height, width = mask.shape[:2]
        total = float(max(1, width * height))
        green_ratio = float(cv2.countNonZero(mask)) / total
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_ratio = max((cv2.contourArea(item) / total for item in contours), default=0.0)
        landscape_bonus = 1.0 if width >= height else 0.4
        coverage_score = min(1.0, green_ratio / 0.55)
        continuity_score = min(1.0, largest_ratio / 0.45)
        tactical_score = (coverage_score * 0.55) + (continuity_score * 0.35) + (landscape_bonus * 0.10)
        pitch_visible = green_ratio >= self.minimum_green_ratio and largest_ratio >= 0.10
        return PitchAnalysis(
            pitch_visible=pitch_visible,
            green_ratio=round(green_ratio, 6),
            largest_green_region_ratio=round(largest_ratio, 6),
            tactical_view_score=round(max(0.0, min(1.0, tactical_score)), 6),
            mask=mask if include_mask else None,
        )
