from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import CONTRACT_VERSION


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Detection:
    frame_index: int
    timestamp_seconds: float
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    source_model: str
    detection_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bbox_xyxy"] = list(self.bbox_xyxy)
        data["contract_version"] = CONTRACT_VERSION
        return data


@dataclass(slots=True)
class Track:
    track_id: int
    frame_index: int
    timestamp_seconds: float
    bbox_xyxy: tuple[float, float, float, float]
    class_name: str
    confidence: float
    track_age: int
    lost_count: int
    team_id: str | None = None
    team_confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bbox_xyxy"] = list(self.bbox_xyxy)
        data["contract_version"] = CONTRACT_VERSION
        return data


@dataclass(slots=True)
class FrameResult:
    frame_index: int
    timestamp_seconds: float
    detections: list[Detection]
    tracks: list[Track]
    processing_ms: float
    pitch_visible: bool
    green_ratio: float = 0.0
    tactical_view_score: float = 0.0
    debug_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "frame_index": self.frame_index,
            "timestamp_seconds": self.timestamp_seconds,
            "detections": [item.to_dict() for item in self.detections],
            "tracks": [item.to_dict() for item in self.tracks],
            "processing_ms": self.processing_ms,
            "pitch_visible": self.pitch_visible,
            "green_ratio": self.green_ratio,
            "tactical_view_score": self.tactical_view_score,
            "debug_metadata": self.debug_metadata,
        }


@dataclass(slots=True)
class RunManifest:
    input_file: str
    output_dir: str
    duration_seconds: float = 0.0
    resolution: tuple[int, int] = (0, 0)
    source_fps: float = 0.0
    processed_frames: int = 0
    skipped_frames: int = 0
    device: str = "cpu"
    model: str = "unloaded"
    versions: dict[str, str] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now)
    completed_at: str | None = None
    status: str = "pending"
    error: str | None = None
    partial_outputs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resolution"] = list(self.resolution)
        data["contract_version"] = CONTRACT_VERSION
        return data
