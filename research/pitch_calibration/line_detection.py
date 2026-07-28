from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class LineDetectionConfig:
    hough_threshold: int = 35
    minimum_length_ratio: float = 0.045
    maximum_gap_ratio: float = 0.025
    merge_angle_degrees: float = 5.0
    merge_distance_px: float = 18.0


@dataclass(frozen=True, slots=True)
class ImageSegment:
    segment_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    support: float = 1.0

    @property
    def length(self) -> float:
        return hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])

    @property
    def angle(self) -> float:
        value = degrees(atan2(self.end[1] - self.start[1], self.end[0] - self.start[0]))
        return value % 180.0

    def as_dict(self) -> dict[str, object]:
        return {
            "segment_id": self.segment_id,
            "start": [round(v, 3) for v in self.start],
            "end": [round(v, 3) for v in self.end],
            "length": round(self.length, 3),
            "angle_degrees": round(self.angle, 3),
            "support": round(self.support, 6),
        }


def detect_segments(
    line_mask: np.ndarray,
    config: LineDetectionConfig | None = None,
) -> list[ImageSegment]:
    cfg = config or LineDetectionConfig()
    height, width = line_mask.shape[:2]
    diagonal = hypot(width, height)
    lines = cv2.HoughLinesP(
        line_mask,
        1,
        np.pi / 180.0,
        threshold=cfg.hough_threshold,
        minLineLength=max(10, int(diagonal * cfg.minimum_length_ratio)),
        maxLineGap=max(4, int(diagonal * cfg.maximum_gap_ratio)),
    )
    if lines is None:
        return []
    raw = [
        ImageSegment(
            segment_id=f"line_{index:04d}",
            start=(float(item[0]), float(item[1])),
            end=(float(item[2]), float(item[3])),
        )
        for index, item in enumerate(lines[:, 0])
    ]
    return merge_collinear_segments(raw, cfg)


def merge_collinear_segments(
    segments: list[ImageSegment],
    config: LineDetectionConfig | None = None,
) -> list[ImageSegment]:
    cfg = config or LineDetectionConfig()
    groups: list[list[ImageSegment]] = []
    for segment in sorted(segments, key=lambda value: value.length, reverse=True):
        for group in groups:
            reference = group[0]
            if (
                _angle_distance(segment.angle, reference.angle) <= cfg.merge_angle_degrees
                and _line_distance(segment, reference) <= cfg.merge_distance_px
            ):
                group.append(segment)
                break
        else:
            groups.append([segment])
    merged: list[ImageSegment] = []
    for index, group in enumerate(groups):
        reference = max(group, key=lambda value: value.length)
        direction = np.asarray(
            [reference.end[0] - reference.start[0], reference.end[1] - reference.start[1]],
            dtype=np.float64,
        )
        norm = float(np.linalg.norm(direction))
        if norm <= 1.0e-9:
            continue
        direction /= norm
        points = np.asarray(
            [point for item in group for point in (item.start, item.end)], dtype=np.float64
        )
        center = points.mean(axis=0)
        values = (points - center) @ direction
        start = center + direction * values.min()
        end = center + direction * values.max()
        merged.append(
            ImageSegment(
                segment_id=f"merged_{index:03d}",
                start=(float(start[0]), float(start[1])),
                end=(float(end[0]), float(end[1])),
                support=float(len(group)),
            )
        )
    return sorted(merged, key=lambda value: value.length, reverse=True)


def segment_intersection(
    first: ImageSegment,
    second: ImageSegment,
    *,
    minimum_angle_degrees: float = 12.0,
) -> tuple[float, float] | None:
    if _angle_distance(first.angle, second.angle) < minimum_angle_degrees:
        return None
    p = np.asarray(first.start, dtype=np.float64)
    r = np.asarray(first.end, dtype=np.float64) - p
    q = np.asarray(second.start, dtype=np.float64)
    s = np.asarray(second.end, dtype=np.float64) - q
    cross = _cross_2d(r, s)
    if abs(cross) < 1.0e-9:
        return None
    t = _cross_2d(q - p, s) / cross
    point = p + t * r
    return float(point[0]), float(point[1])


def all_intersections(
    segments: list[ImageSegment],
    image_size: tuple[int, int],
    *,
    margin_ratio: float = 0.10,
) -> list[tuple[float, float]]:
    width, height = image_size
    margin_x, margin_y = width * margin_ratio, height * margin_ratio
    points: list[tuple[float, float]] = []
    for index, first in enumerate(segments):
        for second in segments[index + 1 :]:
            point = segment_intersection(first, second)
            if point is None:
                continue
            if -margin_x <= point[0] <= width + margin_x and -margin_y <= point[1] <= height + margin_y:
                if all(hypot(point[0] - x, point[1] - y) > 8.0 for x, y in points):
                    points.append(point)
    return points


def _angle_distance(first: float, second: float) -> float:
    value = abs(first - second) % 180.0
    return min(value, 180.0 - value)


def _line_distance(first: ImageSegment, second: ImageSegment) -> float:
    a = np.asarray(second.start, dtype=np.float64)
    b = np.asarray(second.end, dtype=np.float64)
    direction = b - a
    norm = float(np.linalg.norm(direction))
    if norm <= 1.0e-9:
        return float("inf")
    points = (np.asarray(first.start), np.asarray(first.end))
    return float(np.mean([abs(_cross_2d(direction, point - a)) / norm for point in points]))


def _cross_2d(first: np.ndarray, second: np.ndarray) -> float:
    return float(first[0] * second[1] - first[1] * second[0])
