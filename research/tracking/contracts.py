from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class TrackingConfig:
    output_dir: Path
    fps: float
    high_detection_threshold: float = 0.60
    low_detection_threshold: float = 0.20
    match_threshold: float = 0.10
    lost_buffer: int = 30
    minimum_confirmed_frames: int = 2
    maximum_detections: int = 80
    minimum_box_area: float = 64.0
    render_debug: bool = True

    def validate(self) -> None:
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if not 0.0 <= self.low_detection_threshold <= self.high_detection_threshold <= 1.0:
            raise ValueError("detection thresholds must satisfy 0 <= low <= high <= 1")
        if not 0.0 <= self.match_threshold <= 1.0:
            raise ValueError("match_threshold must be between 0 and 1")
        if self.lost_buffer < 1:
            raise ValueError("lost_buffer must be at least 1")
        if self.minimum_confirmed_frames < 1:
            raise ValueError("minimum_confirmed_frames must be at least 1")
        if self.maximum_detections < 1:
            raise ValueError("maximum_detections must be at least 1")
        if self.minimum_box_area < 0:
            raise ValueError("minimum_box_area must be non-negative")


@dataclass(frozen=True, slots=True)
class SequenceFrame:
    sequence_index: int
    frame_index: int
    timestamp_seconds: float
    segment_id: str
    image_path: Path
    source_report_path: Path
    source: dict[str, Any]
    detections: tuple[dict[str, Any], ...]
    timing_source: str


@dataclass(frozen=True, slots=True)
class TrackedDetection:
    raw_tracker_id: int
    source_detection_id: str
    bbox_xyxy: tuple[float, float, float, float]
    foot_point_xy: tuple[float, float]
    detection_confidence: float
    association_stage: str
    team_assignment: str
    team_confidence: float
    dominant_color: Any
    cluster_id: int | None
    roi_used: Any


@dataclass(frozen=True, slots=True)
class TrackingUpdate:
    tracked: tuple[TrackedDetection, ...]
    tentative_count: int
    input_count: int


class TrackerAdapter(Protocol):
    name: str
    version: str
    emits_predicted_observations: bool

    def reset_segment(self) -> None:
        ...

    def update(self, detections: list[dict[str, Any]]) -> TrackingUpdate:
        ...


@dataclass(frozen=True, slots=True)
class TrackingRun:
    manifest_path: Path
    html_path: Path
    manifest: dict[str, Any]
