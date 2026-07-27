from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    file_name: str
    path: str
    duration_seconds: float
    fps: float
    width: int
    height: int
    frame_count: int


@dataclass(frozen=True, slots=True)
class SampledCandidate:
    index: int
    timestamp_seconds: float
    jpeg_bytes: bytes
    data_url: str
    local_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SampleBatch:
    video: VideoMetadata
    candidates: tuple[SampledCandidate, ...]


@dataclass(frozen=True, slots=True)
class SelectionObservation:
    raw_result: dict[str, Any]
    validated_result: dict[str, Any]
    ai_seconds: float
    validation_seconds: float


class CandidateSampler(Protocol):
    def sample(self, video_path: Path, *, focus: str, desired_count: int) -> SampleBatch:
        ...


class PipelineSelector(Protocol):
    def select(
        self,
        batch: SampleBatch,
        *,
        focus: str,
        desired_count: int,
        context: dict[str, Any],
    ) -> SelectionObservation:
        ...
