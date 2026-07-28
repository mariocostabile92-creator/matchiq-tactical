from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class FieldPoint:
    semantic_id: str
    canonical_meters: tuple[float, float]
    kind: str = "intersection"


@dataclass(frozen=True, slots=True)
class FieldSegment:
    semantic_id: str
    start_meters: tuple[float, float]
    end_meters: tuple[float, float]
    kind: str = "line"


@dataclass(frozen=True, slots=True)
class FieldCircle:
    semantic_id: str
    center_meters: tuple[float, float]
    radius_meters: float
    kind: str = "circle"


@dataclass(frozen=True, slots=True)
class FieldArc:
    semantic_id: str
    center_meters: tuple[float, float]
    radius_meters: float
    start_degrees: float
    end_degrees: float
    kind: str = "arc"


@dataclass(frozen=True, slots=True)
class CanonicalPitchModel:
    length: float = 105.0
    width: float = 68.0
    physical_length: float | None = None
    physical_width: float | None = None

    def __post_init__(self) -> None:
        if self.length <= 0 or self.width <= 0:
            raise ValueError("pitch dimensions must be positive")
        if (self.physical_length is None) != (self.physical_width is None):
            raise ValueError("physical dimensions must be both known or omitted")

    @property
    def points(self) -> tuple[FieldPoint, ...]:
        l, w = self.length, self.width
        pa_depth, pa_half = 16.5, 20.16
        ga_depth, ga_half = 5.5, 9.16
        cy = w / 2.0
        return (
            FieldPoint("corner_top_left", (0.0, 0.0)),
            FieldPoint("corner_bottom_left", (0.0, w)),
            FieldPoint("corner_top_right", (l, 0.0)),
            FieldPoint("corner_bottom_right", (l, w)),
            FieldPoint("halfway_top", (l / 2.0, 0.0)),
            FieldPoint("halfway_bottom", (l / 2.0, w)),
            FieldPoint("center", (l / 2.0, cy), "center"),
            FieldPoint("left_penalty_top_outer", (pa_depth, cy - pa_half)),
            FieldPoint("left_penalty_bottom_outer", (pa_depth, cy + pa_half)),
            FieldPoint("left_penalty_top_goal", (0.0, cy - pa_half)),
            FieldPoint("left_penalty_bottom_goal", (0.0, cy + pa_half)),
            FieldPoint("right_penalty_top_outer", (l - pa_depth, cy - pa_half)),
            FieldPoint("right_penalty_bottom_outer", (l - pa_depth, cy + pa_half)),
            FieldPoint("right_penalty_top_goal", (l, cy - pa_half)),
            FieldPoint("right_penalty_bottom_goal", (l, cy + pa_half)),
            FieldPoint("left_goal_area_top_outer", (ga_depth, cy - ga_half)),
            FieldPoint("left_goal_area_bottom_outer", (ga_depth, cy + ga_half)),
            FieldPoint("right_goal_area_top_outer", (l - ga_depth, cy - ga_half)),
            FieldPoint("right_goal_area_bottom_outer", (l - ga_depth, cy + ga_half)),
            FieldPoint("left_penalty_spot", (11.0, cy), "spot"),
            FieldPoint("right_penalty_spot", (l - 11.0, cy), "spot"),
        )

    @property
    def segments(self) -> tuple[FieldSegment, ...]:
        l, w, cy = self.length, self.width, self.width / 2.0
        pa_depth, pa_half = 16.5, 20.16
        ga_depth, ga_half = 5.5, 9.16
        return (
            FieldSegment("touchline_top", (0.0, 0.0), (l, 0.0)),
            FieldSegment("touchline_bottom", (0.0, w), (l, w)),
            FieldSegment("goal_line_left", (0.0, 0.0), (0.0, w)),
            FieldSegment("goal_line_right", (l, 0.0), (l, w)),
            FieldSegment("halfway_line", (l / 2.0, 0.0), (l / 2.0, w)),
            *_box_segments("left_penalty", 0.0, pa_depth, cy, pa_half),
            *_box_segments("right_penalty", l, l - pa_depth, cy, pa_half),
            *_box_segments("left_goal_area", 0.0, ga_depth, cy, ga_half),
            *_box_segments("right_goal_area", l, l - ga_depth, cy, ga_half),
        )

    @property
    def circles(self) -> tuple[FieldCircle, ...]:
        return (
            FieldCircle(
                "center_circle",
                (self.length / 2.0, self.width / 2.0),
                9.15,
            ),
        )

    @property
    def arcs(self) -> tuple[FieldArc, ...]:
        center_y = self.width / 2.0
        return (
            FieldArc("left_penalty_arc", (11.0, center_y), 9.15, -53.0, 53.0),
            FieldArc(
                "right_penalty_arc",
                (self.length - 11.0, center_y),
                9.15,
                127.0,
                233.0,
            ),
        )

    @property
    def goal_structures(self) -> tuple[FieldSegment, ...]:
        center_y = self.width / 2.0
        half_goal = 7.32 / 2.0
        depth = 2.0
        return (
            FieldSegment(
                "left_goal_back",
                (-depth, center_y - half_goal),
                (-depth, center_y + half_goal),
                "goal_structure",
            ),
            FieldSegment(
                "right_goal_back",
                (self.length + depth, center_y - half_goal),
                (self.length + depth, center_y + half_goal),
                "goal_structure",
            ),
        )

    def normalized(self, point: Iterable[float]) -> tuple[float, float]:
        x, y = (float(value) for value in point)
        return x / self.length, y / self.width

    def canonical_from_normalized(self, point: Iterable[float]) -> tuple[float, float]:
        x, y = (float(value) for value in point)
        return x * self.length, y * self.width

    def physical_from_normalized(
        self, point: Iterable[float]
    ) -> tuple[float, float] | None:
        if self.physical_length is None or self.physical_width is None:
            return None
        x, y = (float(value) for value in point)
        return x * self.physical_length, y * self.physical_width

    def contains(self, point: Iterable[float], tolerance: float = 0.0) -> bool:
        x, y = (float(value) for value in point)
        return (
            -tolerance <= x <= self.length + tolerance
            and -tolerance <= y <= self.width + tolerance
        )

    def render(self, scale: float = 8.0) -> np.ndarray:
        width = max(2, int(round(self.length * scale)))
        height = max(2, int(round(self.width * scale)))
        canvas = np.full((height, width, 3), (37, 112, 65), dtype=np.uint8)
        for segment in self.segments:
            start = _pixel(segment.start_meters, scale)
            end = _pixel(segment.end_meters, scale)
            cv2.line(canvas, start, end, (245, 245, 245), 2, cv2.LINE_AA)
        center = _pixel((self.length / 2.0, self.width / 2.0), scale)
        cv2.circle(canvas, center, int(round(9.15 * scale)), (245, 245, 245), 2)
        for structure in self.goal_structures:
            cv2.line(
                canvas,
                _pixel(structure.start_meters, scale),
                _pixel(structure.end_meters, scale),
                (245, 245, 245),
                2,
                cv2.LINE_AA,
            )
        return canvas


def _box_segments(
    prefix: str,
    goal_x: float,
    outer_x: float,
    center_y: float,
    half_width: float,
) -> tuple[FieldSegment, ...]:
    top = center_y - half_width
    bottom = center_y + half_width
    return (
        FieldSegment(f"{prefix}_top", (goal_x, top), (outer_x, top)),
        FieldSegment(f"{prefix}_outer", (outer_x, top), (outer_x, bottom)),
        FieldSegment(f"{prefix}_bottom", (outer_x, bottom), (goal_x, bottom)),
    )


def _pixel(point: tuple[float, float], scale: float) -> tuple[int, int]:
    return int(round(point[0] * scale)), int(round(point[1] * scale))
