from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


SCHEMA_VERSION = "matchiq.ve-005b.pitch-calibration.v1"


class CalibrationStatus(StrEnum):
    VALIDATED = "VALIDATED"
    ESTIMATED = "ESTIMATED"
    AMBIGUOUS = "AMBIGUOUS"
    UNCALIBRATED = "UNCALIBRATED"
    REJECTED = "REJECTED"


class DimensionsType(StrEnum):
    CANONICAL = "CANONICAL"
    PHYSICAL = "PHYSICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CalibrationConfig:
    output_dir: Path
    canonical_pitch_length: float = 105.0
    canonical_pitch_width: float = 68.0
    physical_pitch_length: float | None = None
    physical_pitch_width: float | None = None
    sample_interval_seconds: float = 2.0
    maximum_frames: int | None = None
    render_debug: bool = True
    minimum_model_confidence: float = 0.45
    minimum_geometric_confidence: float = 0.45
    maximum_condition_number: float = 1.0e8
    maximum_reprojection_error_px: float = 20.0
    maximum_temporal_corner_jump: float = 0.18
    minimum_projected_player_inside_ratio: float = 0.60
    minimum_projection_confidence: float = 0.45
    camera_profile: str = "fixed"
    random_seed: int = 7
    keyframe_frequency: int = 1
    minimum_evidence_confidence: float = 0.35
    minimum_correspondence_confidence: float = 0.30

    def validate(self) -> None:
        if self.canonical_pitch_length <= 0 or self.canonical_pitch_width <= 0:
            raise ValueError("canonical pitch dimensions must be positive")
        if (self.physical_pitch_length is None) != (self.physical_pitch_width is None):
            raise ValueError("physical pitch dimensions must be both known or both omitted")
        if self.physical_pitch_length is not None and (
            self.physical_pitch_length <= 0 or self.physical_pitch_width <= 0
        ):
            raise ValueError("physical pitch dimensions must be positive")
        if self.sample_interval_seconds <= 0:
            raise ValueError("sample_interval_seconds must be positive")
        if self.maximum_frames is not None and self.maximum_frames < 1:
            raise ValueError("maximum_frames must be at least 1")
        if self.camera_profile not in {"fixed", "smartphone"}:
            raise ValueError("camera_profile must be fixed or smartphone")
        if self.keyframe_frequency < 1:
            raise ValueError("keyframe_frequency must be at least 1")
        for name, value in (
            ("minimum_model_confidence", self.minimum_model_confidence),
            ("minimum_geometric_confidence", self.minimum_geometric_confidence),
            ("minimum_projected_player_inside_ratio", self.minimum_projected_player_inside_ratio),
            ("minimum_projection_confidence", self.minimum_projection_confidence),
            ("minimum_evidence_confidence", self.minimum_evidence_confidence),
            ("minimum_correspondence_confidence", self.minimum_correspondence_confidence),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def dimensions_type(self) -> DimensionsType:
        if self.physical_pitch_length is not None:
            return DimensionsType.PHYSICAL
        return DimensionsType.CANONICAL


@dataclass(frozen=True, slots=True)
class CalibrationFrame:
    sequence_index: int
    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_path: Path
    source_manifest: Path | None = None
    source: dict[str, Any] = field(default_factory=dict)
    observations: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class AdapterResult:
    status: CalibrationStatus
    homography_image_to_pitch: list[list[float]] | None
    homography_pitch_to_image: list[list[float]] | None
    camera_parameters: dict[str, Any] | None
    model_confidence: float | None
    reprojection_error_px: float | None
    coverage_score: float | None = None
    valid_image_region: dict[str, Any] | None = None
    calibration_origin: str = "external_adapter"
    detected_field_elements: tuple[dict[str, Any], ...] = ()
    ambiguity_flags: tuple[str, ...] = ()
    failure_reason: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    evidence_confidence: float | None = None
    correspondence_confidence: float | None = None
    projection_confidence: float | None = None
    accepted_correspondences: tuple[dict[str, Any], ...] = ()
    rejected_correspondences: tuple[dict[str, Any], ...] = ()
    artifact_images: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


class CalibrationAdapter(Protocol):
    name: str
    version: str

    def inspect_environment(self) -> dict[str, Any]:
        ...

    def calibrate(self, frame: CalibrationFrame) -> AdapterResult:
        ...


@dataclass(frozen=True, slots=True)
class CalibrationRun:
    manifest_path: Path
    projected_tracks_path: Path
    benchmark_path: Path
    html_path: Path
    manifest: dict[str, Any]
    evidence_path: Path | None = None
    correspondence_path: Path | None = None
