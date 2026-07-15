from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


VALID_DEVICES = {"auto", "cpu", "cuda"}
VALID_DETECTORS = {"opencv_hog", "fake"}


@dataclass(slots=True)
class TrackerSettings:
    iou_threshold: float = 0.25
    max_lost: int = 8
    min_hits: int = 2

    def validate(self) -> None:
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise ValueError("tracker iou_threshold must be between 0 and 1")
        if self.max_lost < 0:
            raise ValueError("tracker max_lost cannot be negative")
        if self.min_hits < 1:
            raise ValueError("tracker min_hits must be at least 1")


@dataclass(slots=True)
class VisionSpikeConfig:
    input_video: Path
    output_dir: Path
    detector_backend: str = "opencv_hog"
    model_path: Path | None = None
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.45
    frame_stride: int = 5
    max_frames: int | None = None
    start_seconds: float = 0.0
    max_seconds: float = 60.0
    device: str = "auto"
    output_fps: float | None = None
    overlay_enabled: bool = True
    team_clustering_enabled: bool = True
    ball_detection_enabled: bool = False
    pitch_detection_enabled: bool = True
    save_debug_frames: bool = False
    random_seed: int = 42
    detector_width: int = 960
    tracker: TrackerSettings = field(default_factory=TrackerSettings)

    def validate(self, *, require_input: bool = True) -> None:
        if require_input and (not self.input_video.exists() or not self.input_video.is_file()):
            raise ValueError(f"input video not found: {self.input_video}")
        if self.detector_backend not in VALID_DETECTORS:
            raise ValueError(f"unsupported detector backend: {self.detector_backend}")
        if self.device not in VALID_DEVICES:
            raise ValueError(f"unsupported device: {self.device}")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")
        if self.frame_stride < 1:
            raise ValueError("frame_stride must be at least 1")
        if self.max_frames is not None and self.max_frames < 1:
            raise ValueError("max_frames must be positive")
        if self.start_seconds < 0:
            raise ValueError("start_seconds cannot be negative")
        if self.max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        if self.output_fps is not None and self.output_fps <= 0:
            raise ValueError("output_fps must be positive")
        if self.detector_width < 320:
            raise ValueError("detector_width must be at least 320")
        self.tracker.validate()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["input_video"] = str(self.input_video.resolve())
        data["output_dir"] = str(self.output_dir.resolve())
        data["model_path"] = str(self.model_path.resolve()) if self.model_path else None
        return data
