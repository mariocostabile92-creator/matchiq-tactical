from __future__ import annotations

from typing import Any


def _rounded(values: tuple[float, ...], digits: int = 4) -> list[float]:
    return [round(float(value), digits) for value in values]


def clamp_bbox_xyxy(
    bbox_xyxy: tuple[float, float, float, float],
    *,
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    if width < 1 or height < 1:
        raise ValueError("image dimensions must be positive")
    x1, y1, x2, y2 = (float(value) for value in bbox_xyxy)
    x1 = min(max(x1, 0.0), float(width))
    y1 = min(max(y1, 0.0), float(height))
    x2 = min(max(x2, x1), float(width))
    y2 = min(max(y2, y1), float(height))
    return x1, y1, x2, y2


def describe_bbox(
    bbox_xyxy: tuple[float, float, float, float],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    x1, y1, x2, y2 = clamp_bbox_xyxy(bbox_xyxy, width=width, height=height)
    box_width = x2 - x1
    box_height = y2 - y1
    center = (x1 + box_width / 2.0, y1 + box_height / 2.0)
    foot_point = (center[0], y2)
    normalized_xyxy = (x1 / width, y1 / height, x2 / width, y2 / height)
    normalized_center = (center[0] / width, center[1] / height)
    normalized_foot_point = (foot_point[0] / width, foot_point[1] / height)
    return {
        "bbox_xyxy": _rounded((x1, y1, x2, y2), 2),
        "bbox_xywh": _rounded((x1, y1, box_width, box_height), 2),
        "center_xy": _rounded(center, 2),
        "foot_point_xy": _rounded(foot_point, 2),
        "normalized_bbox_xyxy": _rounded(normalized_xyxy, 6),
        "normalized_center_xy": _rounded(normalized_center, 6),
        "normalized_foot_point_xy": _rounded(normalized_foot_point, 6),
    }
