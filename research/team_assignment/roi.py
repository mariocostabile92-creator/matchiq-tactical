from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TorsoRoi:
    image: object | None
    bbox_xyxy: tuple[int, int, int, int] | None
    bbox_relative: tuple[float, float, float, float]
    status: str
    reason: str | None

    def as_report(self, *, valid_pixels: int = 0, coverage: float = 0.0) -> dict[str, object]:
        return {
            "status": self.status,
            "bbox_xyxy": list(self.bbox_xyxy) if self.bbox_xyxy else None,
            "bbox_relative_to_detection": list(self.bbox_relative),
            "valid_color_pixels": int(valid_pixels),
            "valid_color_coverage": round(float(coverage), 6),
            "reason": self.reason,
        }


def extract_torso_roi(
    image: object,
    bbox_xyxy: Sequence[float],
    *,
    x_start: float = 0.20,
    x_end: float = 0.80,
    y_start: float = 0.18,
    y_end: float = 0.58,
) -> TorsoRoi:
    if len(bbox_xyxy) != 4:
        return TorsoRoi(None, None, (x_start, y_start, x_end, y_end), "excluded", "invalid_bbox")

    height, width = image.shape[:2]
    x1, y1, x2, y2 = (float(value) for value in bbox_xyxy)
    x1 = max(0.0, min(float(width), x1))
    x2 = max(0.0, min(float(width), x2))
    y1 = max(0.0, min(float(height), y1))
    y2 = max(0.0, min(float(height), y2))
    box_width = x2 - x1
    box_height = y2 - y1
    relative = (x_start, y_start, x_end, y_end)

    if box_width < 8.0 or box_height < 18.0:
        return TorsoRoi(None, None, relative, "excluded", "detection_too_small")

    roi_x1 = max(0, min(width - 1, int(round(x1 + box_width * x_start))))
    roi_x2 = max(0, min(width, int(round(x1 + box_width * x_end))))
    roi_y1 = max(0, min(height - 1, int(round(y1 + box_height * y_start))))
    roi_y2 = max(0, min(height, int(round(y1 + box_height * y_end))))
    if roi_x2 - roi_x1 < 4 or roi_y2 - roi_y1 < 7:
        return TorsoRoi(None, None, relative, "excluded", "torso_roi_too_small")

    crop = image[roi_y1:roi_y2, roi_x1:roi_x2]
    if crop.size == 0:
        return TorsoRoi(None, None, relative, "excluded", "empty_torso_roi")
    return TorsoRoi(
        crop,
        (roi_x1, roi_y1, roi_x2, roi_y2),
        relative,
        "used",
        None,
    )

