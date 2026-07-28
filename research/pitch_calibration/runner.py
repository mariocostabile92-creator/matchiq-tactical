from __future__ import annotations

import platform
import hashlib
import sys
import time
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .adapters.base import ExternalCalibrationError
from .contracts import (
    SCHEMA_VERSION,
    AdapterResult,
    CalibrationAdapter,
    CalibrationConfig,
    CalibrationRun,
    CalibrationStatus,
)
from .projection import project_observations
from .quality_gate import assess_calibration
from .renderer import render_diagnostic, render_minimap
from .reports import write_csv, write_html_report, write_json
from .sequence_loader import load_source
from .temporal_validation import (
    assess_temporal_pair,
    decay_confidence,
    histogram_distance,
    smooth_compatible_homographies,
    visual_histogram,
)


class PitchCalibrationRunner:
    def __init__(self, adapter: CalibrationAdapter) -> None:
        self.adapter = adapter

    def run(self, source: Path, config: CalibrationConfig) -> CalibrationRun:
        config.validate()
        output = config.output_dir.resolve()
        frames, source_meta = load_source(
            source,
            sample_interval_seconds=config.sample_interval_seconds,
            maximum_frames=config.maximum_frames,
            extracted_frames_dir=output / "sampled_frames",
        )
        environment = self.adapter.inspect_environment()
        frame_results: list[dict[str, Any]] = []
        projected_tracks: list[dict[str, Any]] = []
        evidence_records: list[dict[str, Any]] = []
        correspondence_records: list[dict[str, Any]] = []
        previous_homography: Any | None = None
        previous_adapter_result: AdapterResult | None = None
        previous_histogram: np.ndarray | None = None
        frames_since_keyframe = 0
        camera_segment = 1
        manifest_segment: str | None = None
        segment_ids: set[str] = set()
        total_start = time.perf_counter()

        for frame in frames:
            started = time.perf_counter()
            image = cv2.imread(str(frame.image_path))
            current_histogram = visual_histogram(image) if image is not None else None
            requested_segment = frame.source.get("camera_segment_id")
            if requested_segment is not None and str(requested_segment) != manifest_segment:
                manifest_segment = str(requested_segment)
                previous_homography = None
                previous_adapter_result = None
                previous_histogram = None
            visual_cut_before_calibration = bool(
                previous_histogram is not None
                and current_histogram is not None
                and histogram_distance(previous_histogram, current_histogram) > 0.48
            )
            is_keyframe = (
                previous_adapter_result is None
                or visual_cut_before_calibration
                or frame.sequence_index % config.keyframe_frequency == 0
            )
            if is_keyframe:
                try:
                    adapter_result = self.adapter.calibrate(frame)
                except ExternalCalibrationError as exc:
                    adapter_result = AdapterResult(
                        status=CalibrationStatus.UNCALIBRATED,
                        homography_image_to_pitch=None,
                        homography_pitch_to_image=None,
                        camera_parameters=None,
                        model_confidence=None,
                        reprojection_error_px=None,
                        failure_reason=str(exc),
                        diagnostics={"adapter_error": True},
                    )
                frames_since_keyframe = 0
            else:
                frames_since_keyframe += 1
                adapter_result = replace(
                    previous_adapter_result,
                    status=CalibrationStatus.ESTIMATED,
                    model_confidence=decay_confidence(
                        previous_adapter_result.model_confidence or 0.0,
                        frames_since_keyframe,
                    ),
                    diagnostics={
                        **previous_adapter_result.diagnostics,
                        "temporal_propagation": True,
                        "source_keyframe_distance": frames_since_keyframe,
                    },
                    artifact_images={},
                )
            temporal_pair = assess_temporal_pair(
                np.asarray(previous_homography, dtype=np.float64)
                if previous_homography is not None
                else None,
                np.asarray(adapter_result.homography_image_to_pitch, dtype=np.float64)
                if adapter_result.homography_image_to_pitch is not None
                else None,
                previous_histogram,
                current_histogram,
                homography_jump_threshold=config.maximum_temporal_corner_jump,
            )
            if (
                self.adapter.name == "matchiq-hybrid"
                and is_keyframe
                and temporal_pair.compatible
                and previous_homography is not None
                and adapter_result.status is CalibrationStatus.ESTIMATED
                and adapter_result.homography_image_to_pitch is not None
            ):
                smoothed = smooth_compatible_homographies(
                    np.asarray(previous_homography, dtype=np.float64),
                    np.asarray(adapter_result.homography_image_to_pitch, dtype=np.float64),
                )
                try:
                    smoothed_inverse = np.linalg.inv(smoothed)
                except np.linalg.LinAlgError:
                    smoothed_inverse = None
                if smoothed_inverse is not None and np.isfinite(smoothed_inverse).all():
                    adapter_result = replace(
                        adapter_result,
                        homography_image_to_pitch=smoothed.tolist(),
                        homography_pitch_to_image=smoothed_inverse.tolist(),
                        diagnostics={
                            **adapter_result.diagnostics,
                            "temporal_smoothing": {
                                "applied": True,
                                "current_weight": 0.65,
                                "reason": "compatible_consecutive_keyframes",
                            },
                        },
                    )
            cut_started_new_segment = (
                requested_segment is None and temporal_pair.visual_jump
            )
            if cut_started_new_segment:
                camera_segment += 1
                previous_homography = None
                previous_adapter_result = None
            assessment = assess_calibration(
                adapter_result,
                frame.observations,
                config,
                previous_homography=previous_homography,
            )
            if (
                requested_segment is None
                and not cut_started_new_segment
                and "temporal_jump" in assessment.flags
            ):
                camera_segment += 1
            segment_id = (
                manifest_segment
                if requested_segment is not None
                else f"camera_segment_{camera_segment:03d}"
            )
            segment_ids.add(segment_id)
            source_id = _stable_id(str(source.resolve()))
            calibration_id = _stable_id(
                f"{source_id}:{frame.frame_id}:{self.adapter.name}:{self.adapter.version}"
            )
            calibration_id_value = f"cal_{calibration_id}"
            observations = [
                {**item, "frame_id": frame.frame_id}
                for item in frame.observations
                if item.get("observation_type", "detected") == "detected"
            ]
            projection_records = project_observations(
                observations,
                adapter_result.homography_image_to_pitch,
                canonical_pitch_length=config.canonical_pitch_length,
                canonical_pitch_width=config.canonical_pitch_width,
                physical_pitch_length=config.physical_pitch_length,
                physical_pitch_width=config.physical_pitch_width,
                calibration_status=assessment.status.value,
                calibration_confidence=assessment.overall_confidence,
                calibration_id=calibration_id_value,
                camera_segment_id=segment_id,
                minimum_calibration_confidence=config.minimum_projection_confidence,
                valid_image_region=adapter_result.valid_image_region,
            )
            projected_tracks.extend(projection_records)
            projected = [item for item in projection_records if item["projection_valid"]]
            if (
                adapter_result.homography_image_to_pitch is not None
                and assessment.status
                in (
                    CalibrationStatus.VALIDATED,
                    CalibrationStatus.ESTIMATED,
                )
            ):
                previous_homography = adapter_result.homography_image_to_pitch
                previous_adapter_result = adapter_result
            previous_histogram = current_histogram

            debug_path = None
            minimap_path = None
            artifact_paths: dict[str, str] = {}
            if config.render_debug:
                artifact_paths = _write_artifacts(
                    {
                        **({"original": image} if image is not None else {}),
                        **adapter_result.artifact_images,
                    },
                    output / "diagnostics",
                    frame.frame_id,
                    output,
                )
                debug_path = output / "diagnostics" / f"{frame.frame_id}_calibration.jpg"
                render_diagnostic(
                    frame.image_path,
                    debug_path,
                    homography_image_to_pitch=adapter_result.homography_image_to_pitch,
                    observations=frame.observations,
                    detected_field_elements=adapter_result.detected_field_elements,
                    status=assessment.status.value,
                    confidence=assessment.overall_confidence,
                    flags=assessment.flags,
                    pitch_length=config.canonical_pitch_length,
                    pitch_width=config.canonical_pitch_width,
                )
                if projected:
                    minimap_path = output / "diagnostics" / f"{frame.frame_id}_minimap.jpg"
                    render_minimap(
                        minimap_path,
                        projected,
                        pitch_length=config.canonical_pitch_length,
                        pitch_width=config.canonical_pitch_width,
                    )
            height, width = image.shape[:2] if image is not None else (None, None)
            evidence_summary = dict(adapter_result.diagnostics.get("evidence") or {})
            evidence_records.append(
                {
                    "calibration_id": calibration_id_value,
                    "frame_id": frame.frame_id,
                    "timestamp_seconds": frame.timestamp_seconds,
                    "camera_segment_id": segment_id,
                    "is_keyframe": is_keyframe,
                    "confidence": adapter_result.evidence_confidence,
                    "summary": evidence_summary,
                    "artifacts": artifact_paths,
                }
            )
            correspondence_records.append(
                {
                    "calibration_id": calibration_id_value,
                    "frame_id": frame.frame_id,
                    "timestamp_seconds": frame.timestamp_seconds,
                    "camera_segment_id": segment_id,
                    "confidence": adapter_result.correspondence_confidence,
                    "accepted": list(adapter_result.accepted_correspondences),
                    "rejected": list(adapter_result.rejected_correspondences),
                }
            )
            frame_results.append(
                {
                    "schema_version": _schema_version(self.adapter.name),
                    "calibration_id": calibration_id_value,
                    "source_id": f"src_{source_id}",
                    "frame_id": frame.frame_id,
                    "sequence_index": frame.sequence_index,
                    "frame_index": frame.frame_index,
                    "timestamp_seconds": frame.timestamp_seconds,
                    "timestamp": frame.timestamp_seconds,
                    "source_image": str(frame.image_path),
                    "source_manifest": str(frame.source_manifest) if frame.source_manifest else None,
                    "image_size": {"width": width, "height": height},
                    "image_width": width,
                    "image_height": height,
                    "camera_segment_id": segment_id,
                    "status": assessment.status.value,
                    "calibration_status": assessment.status.value,
                    "calibrator_name": self.adapter.name,
                    "calibrator_version": self.adapter.version,
                    "calibration_origin": adapter_result.calibration_origin,
                    "field_model": "canonical_football_pitch",
                    "field_length": config.canonical_pitch_length,
                    "field_width": config.canonical_pitch_width,
                    "dimensions_type": config.dimensions_type.value,
                    "canonical_pitch_dimensions": {
                        "length": config.canonical_pitch_length,
                        "width": config.canonical_pitch_width,
                    },
                    "physical_pitch_dimensions": (
                        {
                            "length": config.physical_pitch_length,
                            "width": config.physical_pitch_width,
                        }
                        if config.physical_pitch_length is not None
                        else None
                    ),
                    "homography_image_to_pitch": adapter_result.homography_image_to_pitch,
                    "homography_pitch_to_image": adapter_result.homography_pitch_to_image,
                    "image_to_pitch_matrix": adapter_result.homography_image_to_pitch,
                    "pitch_to_image_matrix": adapter_result.homography_pitch_to_image,
                    "camera_parameters": adapter_result.camera_parameters,
                    "confidence": {
                        "evidence": assessment.evidence_confidence,
                        "correspondence": assessment.correspondence_confidence,
                        "model": assessment.model_confidence,
                        "geometric": assessment.geometric_confidence,
                        "temporal": assessment.temporal_confidence,
                        "projection": assessment.projection_confidence,
                        "overall": assessment.overall_confidence,
                    },
                    "quality_metrics": {
                        **assessment.metrics,
                        "visual_jump": temporal_pair.visual_jump,
                        "temporal_pair_confidence": temporal_pair.confidence,
                        "temporal_pair_reason": temporal_pair.reason,
                    },
                    "reprojection_error": adapter_result.reprojection_error_px,
                    "coverage_score": adapter_result.coverage_score,
                    "geometric_confidence": assessment.geometric_confidence,
                    "temporal_confidence": assessment.temporal_confidence,
                    "overall_confidence": assessment.overall_confidence,
                    "quality_flags": list(assessment.flags),
                    "ambiguity_flags": (
                        list(assessment.flags)
                        if assessment.status is CalibrationStatus.AMBIGUOUS
                        else list(adapter_result.ambiguity_flags)
                    ),
                    "rejection_reasons": (
                        list(assessment.flags)
                        if assessment.status
                        in (CalibrationStatus.REJECTED, CalibrationStatus.UNCALIBRATED)
                        else []
                    ),
                    "failure_reason": adapter_result.failure_reason,
                    "diagnostics": adapter_result.diagnostics,
                    "detected_field_elements": list(adapter_result.detected_field_elements),
                    "valid_image_region": adapter_result.valid_image_region,
                    "projected_observations": len(projected),
                    "projection_records": len(projection_records),
                    "debug_image": _relative(debug_path, output),
                    "minimap_image": _relative(minimap_path, output),
                    "diagnostic_artifacts": artifact_paths,
                    "processing_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "processing_time_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "device": environment.get("device") or environment.get("runtime") or "unknown",
                }
            )

        status_counts = Counter(item["status"] for item in frame_results)
        research_status, status_reason = _research_status(environment, frame_results)
        best_frame = _ranked_frame(frame_results, reverse=True)
        worst_frame = _ranked_frame(frame_results, reverse=False)
        selected_hypotheses = [
            _selected_hypothesis(item.get("diagnostics") or {})
            for item in frame_results
        ]
        manifest = {
            "schema_version": _schema_version(self.adapter.name),
            "run": {
                "created_at": datetime.now(UTC).isoformat(),
                "module": "VE-005C" if self.adapter.name == "matchiq-hybrid" else "VE-005B",
                "adapter": self.adapter.name,
                "adapter_version": self.adapter.version,
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "total_processing_ms": round((time.perf_counter() - total_start) * 1000.0, 3),
            },
            "source": source_meta,
            "environment": environment,
            "configuration": {
                "canonical_pitch_length": config.canonical_pitch_length,
                "canonical_pitch_width": config.canonical_pitch_width,
                "physical_pitch_length": config.physical_pitch_length,
                "physical_pitch_width": config.physical_pitch_width,
                "sample_interval_seconds": config.sample_interval_seconds,
                "maximum_frames": config.maximum_frames,
                "camera_profile": config.camera_profile,
                "random_seed": config.random_seed,
                "keyframe_frequency": config.keyframe_frequency,
                "quality_thresholds": {
                    "minimum_model_confidence": config.minimum_model_confidence,
                    "minimum_geometric_confidence": config.minimum_geometric_confidence,
                    "maximum_condition_number": config.maximum_condition_number,
                    "maximum_reprojection_error_px": config.maximum_reprojection_error_px,
                    "maximum_temporal_corner_jump": config.maximum_temporal_corner_jump,
                    "minimum_projected_player_inside_ratio": (
                        config.minimum_projected_player_inside_ratio
                    ),
                    "minimum_projection_confidence": config.minimum_projection_confidence,
                    "minimum_evidence_confidence": config.minimum_evidence_confidence,
                    "minimum_correspondence_confidence": (
                        config.minimum_correspondence_confidence
                    ),
                },
            },
            "aggregate": {
                "frames_processed": len(frame_results),
                "camera_segments": len(segment_ids),
                "projected_observations": sum(
                    bool(item["projection_valid"]) for item in projected_tracks
                ),
                "projection_records": len(projected_tracks),
                "accepted_correspondences": sum(
                    len(item["accepted"]) for item in correspondence_records
                ),
                "rejected_correspondences": sum(
                    len(item["rejected"]) for item in correspondence_records
                ),
                "average_segment_count": _average(
                    (item.get("diagnostics") or {})
                    .get("evidence", {})
                    .get("segment_count")
                    for item in frame_results
                ),
                "average_keypoint_count": _average(
                    (item.get("diagnostics") or {})
                    .get("evidence", {})
                    .get("keypoint_count")
                    for item in frame_results
                ),
                "average_inlier_ratio": _average(
                    item.get("inlier_ratio")
                    for item in selected_hypotheses
                    if item is not None
                ),
                "average_temporal_confidence": _average(
                    item["confidence"].get("temporal") for item in frame_results
                ),
                "visual_jumps": sum(
                    bool(item["quality_metrics"].get("visual_jump"))
                    for item in frame_results
                ),
                "status_distribution": dict(status_counts),
            },
            "frames": frame_results,
            "limitations": [
                "Research-only output; no production API or frontend integration.",
                "Canonical coordinates are not claimed as physical measurements.",
                "Physical meters are null unless real pitch dimensions are supplied.",
                (
                    "TVCalib runtime requires independently verified upstream code and weights."
                    if self.adapter.name == "tvcalib"
                    else "The MatchIQ hybrid calibrator is experimental classical geometry, not measured ground truth."
                ),
            ],
        }
        benchmark = {
            "schema_version": (
                "matchiq.ve-005c.benchmark.v1"
                if self.adapter.name == "matchiq-hybrid"
                else "matchiq.ve-005b.benchmark.v1"
            ),
            "research_status": research_status,
            "status_reason": status_reason,
            "frames_processed": len(frame_results),
            "status_distribution": dict(status_counts),
            "average_overall_confidence": _average(
                item["confidence"]["overall"] for item in frame_results
            ),
            "average_evidence_confidence": _average(
                item["confidence"]["evidence"] for item in frame_results
            ),
            "average_correspondence_confidence": _average(
                item["confidence"]["correspondence"] for item in frame_results
            ),
            "average_reprojection_error": _average(
                item["reprojection_error"] for item in frame_results
            ),
            "average_segment_count": manifest["aggregate"]["average_segment_count"],
            "average_keypoint_count": manifest["aggregate"]["average_keypoint_count"],
            "accepted_correspondences": manifest["aggregate"][
                "accepted_correspondences"
            ],
            "rejected_correspondences": manifest["aggregate"][
                "rejected_correspondences"
            ],
            "average_inlier_ratio": manifest["aggregate"]["average_inlier_ratio"],
            "average_temporal_confidence": manifest["aggregate"][
                "average_temporal_confidence"
            ],
            "camera_segments": manifest["aggregate"]["camera_segments"],
            "visual_jumps": manifest["aggregate"]["visual_jumps"],
            "best_frame": best_frame,
            "worst_frame": worst_frame,
            "projected_observations": sum(
                bool(item["projection_valid"]) for item in projected_tracks
            ),
            "projection_records": len(projected_tracks),
            "source_kind": source_meta["kind"],
            "environment_ready": bool(environment.get("ready")),
            "timing_ms": _timing_summary(frame_results),
            "status_rates": _status_rates(status_counts, len(frame_results)),
            "accuracy_statement": (
                "No measured accuracy is claimed because no ground-truth "
                "homographies are available."
            ),
            "assessment": {
                "execution": "measured",
                "plausibility": "quality-gated",
                "visual_alignment": (
                    "diagnostic artifacts generated; human review required"
                ),
                "measured_accuracy": "unavailable without ground truth",
                "memory_usage": "not measured in this research runner",
            },
            "technical_success_definition": (
                "A frame is technically successful only when the selected adapter "
                "returns a usable homography and the configured quality gate accepts it."
            ),
            "next_sprint_decision": (
                "Do not proceed to VE-006. Improve semantic correspondence and "
                "orientation disambiguation, then repeat this benchmark."
                if research_status == "BLOCKED"
                else "Review accepted calibrations against ground truth before VE-006."
            ),
        }
        manifest_path = write_json(manifest, output / "calibration_manifest.json")
        projected_path = write_json(
            {
                "schema_version": "matchiq.ve-005b.projected-tracks.v1",
                "dimensions_type": config.dimensions_type.value,
                "observations": projected_tracks,
            },
            output / "projected_tracks.json",
        )
        benchmark_path = write_json(benchmark, output / "benchmark_summary.json")
        evidence_path = write_json(
            {
                "schema_version": "matchiq.ve-005c.field-evidence.v1",
                "adapter": self.adapter.name,
                "frames": evidence_records,
            },
            output / "evidence_manifest.json",
        )
        correspondence_path = write_json(
            {
                "schema_version": "matchiq.ve-005c.correspondences.v1",
                "adapter": self.adapter.name,
                "frames": correspondence_records,
            },
            output / "correspondence_manifest.json",
        )
        write_csv(_csv_rows(frame_results), output / "calibration_frames.csv")
        html_path = write_html_report(manifest, benchmark, output / "report.html")
        return CalibrationRun(
            manifest_path=manifest_path,
            projected_tracks_path=projected_path,
            benchmark_path=benchmark_path,
            html_path=html_path,
            manifest=manifest,
            evidence_path=evidence_path,
            correspondence_path=correspondence_path,
        )


def _relative(path: Path | None, root: Path) -> str | None:
    return path.relative_to(root).as_posix() if path else None


def _average(values: Any) -> float | None:
    items = [float(value) for value in values if value is not None]
    return round(sum(items) / len(items), 6) if items else None


def _selected_hypothesis(diagnostics: dict[str, Any]) -> dict[str, Any] | None:
    selected_id = diagnostics.get("selected_hypothesis")
    for hypothesis in diagnostics.get("hypotheses") or ():
        if hypothesis.get("hypothesis_id") == selected_id:
            return hypothesis
    return None


def _ranked_frame(
    frames: list[dict[str, Any]],
    *,
    reverse: bool,
) -> dict[str, Any] | None:
    if not frames:
        return None
    ranked = sorted(
        frames,
        key=lambda item: float(item["confidence"].get("overall") or 0.0),
        reverse=reverse,
    )
    item = ranked[0]
    return {
        "frame_id": item["frame_id"],
        "timestamp_seconds": item["timestamp_seconds"],
        "status": item["status"],
        "overall_confidence": item["confidence"].get("overall"),
        "failure_reason": item.get("failure_reason"),
        "debug_image": item.get("debug_image"),
    }


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _schema_version(adapter_name: str) -> str:
    if adapter_name == "matchiq-hybrid":
        return "matchiq.ve-005c.pitch-calibration.v1"
    return SCHEMA_VERSION


def _write_artifacts(
    artifacts: dict[str, Any],
    directory: Path,
    frame_id: str,
    root: Path,
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for name, image in sorted(artifacts.items()):
        if not isinstance(image, np.ndarray) or image.size == 0:
            continue
        suffix = ".png" if image.ndim == 2 else ".jpg"
        target = directory / f"{frame_id}_{name}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(target), image):
            raise RuntimeError(f"cannot write diagnostic artifact: {target}")
        paths[name] = target.relative_to(root).as_posix()
    return paths


def _timing_summary(frames: list[dict[str, Any]]) -> dict[str, float | None]:
    values = sorted(float(item["processing_ms"]) for item in frames)
    if not values:
        return {"mean": None, "p50": None, "p95": None}
    return {
        "mean": round(sum(values) / len(values), 3),
        "p50": round(_percentile(values, 0.50), 3),
        "p95": round(_percentile(values, 0.95), 3),
    }


def _percentile(values: list[float], quantile: float) -> float:
    index = (len(values) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def _status_rates(counts: Counter[str], total: int) -> dict[str, float]:
    return {
        status.value: round(counts.get(status.value, 0) / total, 6) if total else 0.0
        for status in CalibrationStatus
    }


def _research_status(
    environment: dict[str, Any],
    frames: list[dict[str, Any]],
) -> tuple[str, str]:
    if not environment.get("ready"):
        reasons = "; ".join(environment.get("blocking_reasons") or ())
        return "BLOCKED", reasons or "external runtime is not ready"
    validated = sum(item["status"] == CalibrationStatus.VALIDATED.value for item in frames)
    if validated == len(frames) and frames:
        return "COMPLETED", "all processed frames passed the configured quality gate"
    estimated = sum(item["status"] == CalibrationStatus.ESTIMATED.value for item in frames)
    if validated:
        return "PARTIAL", "only part of the processed frames passed the quality gate"
    if estimated:
        return "PARTIAL", "usable estimates exist but no frame reached validated status"
    return "BLOCKED", "no processed frame produced a usable calibration estimate"


def _csv_rows(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for frame in frames:
        rows.append(
            {
                "frame_id": frame["frame_id"],
                "timestamp_seconds": frame["timestamp_seconds"],
                "camera_segment_id": frame["camera_segment_id"],
                "status": frame["status"],
                "model_confidence": frame["confidence"]["model"],
                "evidence_confidence": frame["confidence"]["evidence"],
                "correspondence_confidence": frame["confidence"]["correspondence"],
                "geometric_confidence": frame["confidence"]["geometric"],
                "temporal_confidence": frame["confidence"]["temporal"],
                "projection_confidence": frame["confidence"]["projection"],
                "overall_confidence": frame["confidence"]["overall"],
                "failure_reason": frame["failure_reason"],
            }
        )
    return rows
