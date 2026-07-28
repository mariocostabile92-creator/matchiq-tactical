from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import SCHEMA_VERSION
from .adapters import ByteTrackAdapter
from .contracts import TrackerAdapter, TrackingConfig, TrackingRun
from .renderer import render_tracking_debug
from .reports import write_html_report, write_json
from .sequence_loader import load_sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_point(point: tuple[float, float]) -> list[float]:
    return [round(point[0], 3), round(point[1], 3)]


def _serializable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, tuple):
        return [_serializable(item) for item in value]
    if isinstance(value, list):
        return [_serializable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serializable(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _build_track_summaries(
    observations: list[dict[str, Any]],
    *,
    final_sequence_index: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[str(observation["track_id"])].append(observation)

    summaries: list[dict[str, Any]] = []
    for track_id in sorted(grouped):
        items = sorted(grouped[track_id], key=lambda item: item["sequence_index"])
        gaps: list[dict[str, Any]] = []
        for previous, current in zip(items[:-1], items[1:]):
            missing = current["sequence_index"] - previous["sequence_index"] - 1
            if missing > 0:
                gaps.append({
                    "after_sequence_index": previous["sequence_index"],
                    "before_sequence_index": current["sequence_index"],
                    "missing_processed_frames": missing,
                    "start_timestamp_seconds": previous["timestamp_seconds"],
                    "end_timestamp_seconds": current["timestamp_seconds"],
                })

        teams = Counter(
            item["team_assignment"]
            for item in items
            if item["team_assignment"] in {"TEAM_A", "TEAM_B"}
        )
        known_team_count = sum(teams.values())
        dominant_team = teams.most_common(1)[0][0] if teams else "UNKNOWN"
        dominant_share = teams[dominant_team] / known_team_count if known_team_count else 0.0
        detection_confidences = [item["detection_confidence"] for item in items]
        team_confidences = [
            item["team_confidence"]
            for item in items
            if item["team_assignment"] != "UNKNOWN"
        ]
        velocities: list[tuple[float, float]] = []
        for previous, current in zip(items[:-1], items[1:]):
            delta = current["sequence_index"] - previous["sequence_index"]
            if delta <= 0:
                continue
            velocities.append((
                (current["foot_point_xy"][0] - previous["foot_point_xy"][0]) / delta,
                (current["foot_point_xy"][1] - previous["foot_point_xy"][1]) / delta,
            ))
        average_velocity = (
            [
                round(sum(item[0] for item in velocities) / len(velocities), 4),
                round(sum(item[1] for item in velocities) / len(velocities), 4),
            ]
            if velocities
            else [0.0, 0.0]
        )
        observed_span = items[-1]["sequence_index"] - items[0]["sequence_index"] + 1
        coverage = len(items) / observed_span if observed_span else 0.0
        average_detection_confidence = sum(detection_confidences) / len(detection_confidences)
        preliminary_quality = max(0.0, min(1.0, average_detection_confidence * coverage))
        warning_reasons: list[str] = []
        if known_team_count >= 3 and dominant_share < 0.60:
            warning_reasons.append("inconsistent_team_diagnostic")
        if any(math.hypot(*velocity) > 250.0 for velocity in velocities):
            warning_reasons.append("large_image_space_displacement")
        known_team_sequence = [
            item["team_assignment"]
            for item in items
            if item["team_assignment"] in {"TEAM_A", "TEAM_B"}
        ]
        observed_team_changes = sum(
            previous != current
            for previous, current in zip(
                known_team_sequence[:-1],
                known_team_sequence[1:],
            )
        )
        observed_at_sequence_end = items[-1]["sequence_index"] == final_sequence_index

        summaries.append({
            "track_id": track_id,
            "segment_id": items[0]["segment_id"],
            "start_sequence_index": items[0]["sequence_index"],
            "end_sequence_index": items[-1]["sequence_index"],
            "start_frame_index": items[0]["frame_index"],
            "end_frame_index": items[-1]["frame_index"],
            "start_timestamp_seconds": items[0]["timestamp_seconds"],
            "end_timestamp_seconds": items[-1]["timestamp_seconds"],
            "age_processed_frames": observed_span,
            "detected_frames": len(items),
            "predicted_frames": 0,
            "gap_count": len(gaps),
            "gap_frames_total": sum(gap["missing_processed_frames"] for gap in gaps),
            "maximum_gap_processed_frames": max(
                (gap["missing_processed_frames"] for gap in gaps),
                default=0,
            ),
            "occlusion_intervals": gaps,
            "termination_reason": (
                "end_of_sequence"
                if observed_at_sequence_end
                else "not_observed_at_sequence_end"
            ),
            "final_state": (
                "active_at_sequence_end"
                if observed_at_sequence_end
                else "not_observed_at_sequence_end"
            ),
            "continuity": round(coverage, 6),
            "average_detection_confidence": round(average_detection_confidence, 6),
            "preliminary_track_quality": round(preliminary_quality, 6),
            "track_quality_definition": "mean_detection_confidence_x_observation_coverage",
            "id_switch_warning": bool(warning_reasons),
            "id_switch_warning_reasons": warning_reasons,
            "trajectory_image_space": [
                {
                    "sequence_index": item["sequence_index"],
                    "frame_index": item["frame_index"],
                    "timestamp_seconds": item["timestamp_seconds"],
                    "foot_point_xy": item["foot_point_xy"],
                }
                for item in items
            ],
            "average_velocity_pixels_per_processed_frame": average_velocity,
            "team_distribution": {
                "TEAM_A": teams.get("TEAM_A", 0),
                "TEAM_B": teams.get("TEAM_B", 0),
                "UNKNOWN": sum(1 for item in items if item["team_assignment"] == "UNKNOWN"),
            },
            "dominant_team": dominant_team,
            "dominant_team_share": round(dominant_share, 6),
            "observed_team_changes": observed_team_changes,
            "average_team_confidence": round(
                sum(team_confidences) / len(team_confidences),
                6,
            ) if team_confidences else 0.0,
            "team_assignment_used_as_hard_gate": False,
        })
    return summaries


class TrackingRunner:
    def __init__(
        self,
        *,
        adapter_factory: Callable[[TrackingConfig], TrackerAdapter] = ByteTrackAdapter,
        clock: Callable[[], float] = time.perf_counter,
        now: Callable[[], str] = _utc_now,
    ) -> None:
        self._adapter_factory = adapter_factory
        self._clock = clock
        self._now = now

    def run(self, source: Path, config: TrackingConfig) -> TrackingRun:
        config.validate()
        started = self._clock()
        load_started = self._clock()
        frames, source_metadata = load_sequence(Path(source), fps=config.fps)
        loading_ms = (self._clock() - load_started) * 1000.0

        output_dir = Path(config.output_dir)
        debug_dir = output_dir / "debug"
        output_dir.mkdir(parents=True, exist_ok=True)
        adapter = self._adapter_factory(config)
        observations: list[dict[str, Any]] = []
        frame_reports: list[dict[str, Any]] = []
        trajectories: dict[str, list[tuple[int, int]]] = defaultdict(list)
        last_seen: dict[str, int] = {}
        current_segment: str | None = None
        tracking_ms = 0.0
        rendering_ms = 0.0
        tentative_total = 0
        accepted_total = 0

        for frame in frames:
            if frame.segment_id != current_segment:
                if current_segment is not None:
                    adapter.reset_segment()
                current_segment = frame.segment_id

            update_started = self._clock()
            update = adapter.update(list(frame.detections))
            tracking_ms += (self._clock() - update_started) * 1000.0
            tentative_total += update.tentative_count
            accepted_total += update.input_count
            frame_observations: list[dict[str, Any]] = []

            for tracked in update.tracked:
                public_track_id = (
                    adapter.public_track_id(tracked.raw_tracker_id)
                    if hasattr(adapter, "public_track_id")
                    else f"track_{tracked.raw_tracker_id + 1:04d}"
                )
                missing = max(0, frame.sequence_index - last_seen.get(public_track_id, frame.sequence_index) - 1)
                observation = {
                    "track_id": public_track_id,
                    "raw_tracker_id": tracked.raw_tracker_id,
                    "segment_id": frame.segment_id,
                    "sequence_index": frame.sequence_index,
                    "frame_index": frame.frame_index,
                    "timestamp_seconds": round(frame.timestamp_seconds, 6),
                    "observation_type": "detected",
                    "track_state": "confirmed",
                    "source_detection_id": tracked.source_detection_id,
                    "bbox_xyxy": [round(value, 3) for value in tracked.bbox_xyxy],
                    "foot_point_xy": _round_point(tracked.foot_point_xy),
                    "detection_confidence": round(tracked.detection_confidence, 6),
                    "association_stage": tracked.association_stage,
                    "association_score": None,
                    "association_score_status": "not_exposed_by_tracker_package",
                    "gap_since_previous_observation": missing,
                    "team_assignment": tracked.team_assignment,
                    "team_confidence": round(tracked.team_confidence, 6),
                    "dominant_color": _serializable(tracked.dominant_color),
                    "cluster_id": tracked.cluster_id,
                    "roi_used": _serializable(tracked.roi_used),
                    "team_assignment_role": "diagnostic_only",
                }
                observations.append(observation)
                frame_observations.append(observation)
                last_seen[public_track_id] = frame.sequence_index
                trajectories[public_track_id].append((
                    int(round(tracked.foot_point_xy[0])),
                    int(round(tracked.foot_point_xy[1])),
                ))

            debug_path: Path | None = None
            if config.render_debug:
                render_started = self._clock()
                debug_path = render_tracking_debug(
                    frame.image_path,
                    frame_observations,
                    trajectories,
                    debug_dir / f"{frame.sequence_index:05d}_tracking.jpg",
                )
                rendering_ms += (self._clock() - render_started) * 1000.0
            frame_reports.append({
                "sequence_index": frame.sequence_index,
                "frame_index": frame.frame_index,
                "timestamp_seconds": round(frame.timestamp_seconds, 6),
                "segment_id": frame.segment_id,
                "timing_source": frame.timing_source,
                "source_image": str(frame.image_path),
                "source_ve003_report": str(frame.source_report_path),
                "detections_available": len(frame.detections),
                "detections_input": update.input_count,
                "tracks_confirmed": len(frame_observations),
                "tentative_count": update.tentative_count,
                "debug_image": (
                    str(debug_path.relative_to(output_dir)).replace("\\", "/")
                    if debug_path
                    else None
                ),
            })

        tracks = _build_track_summaries(
            observations,
            final_sequence_index=frames[-1].sequence_index,
        )
        gap_lengths = [
            interval["missing_processed_frames"]
            for track in tracks
            for interval in track["occlusion_intervals"]
        ]
        detector_confidences = [
            observation["detection_confidence"]
            for observation in observations
        ]
        short_tracks = [
            track for track in tracks if track["detected_frames"] <= 2
        ]
        fragmented_tracks = [
            track for track in tracks if track["gap_count"] > 0
        ]
        reporting_started = self._clock()
        elapsed_ms = (self._clock() - started) * 1000.0
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run": {
                "processed_at": self._now(),
                "status": "completed",
                "output_dir": str(output_dir.resolve()),
            },
            "source": source_metadata,
            "tracker": {
                "name": adapter.name,
                "package_version": adapter.version,
                "initialized_once": True,
                "segment_reset_method": "tracker.reset",
                "emits_predicted_observations": adapter.emits_predicted_observations,
            },
            "configuration": {
                "fps": config.fps,
                "high_detection_threshold": config.high_detection_threshold,
                "low_detection_threshold": config.low_detection_threshold,
                "match_threshold_iou": config.match_threshold,
                "lost_buffer": config.lost_buffer,
                "minimum_confirmed_frames": config.minimum_confirmed_frames,
                "maximum_detections": config.maximum_detections,
                "minimum_box_area": config.minimum_box_area,
                "render_debug": config.render_debug,
            },
            "aggregate": {
                "frames_processed": len(frames),
                "detections_available": sum(len(frame.detections) for frame in frames),
                "detections_accepted": accepted_total,
                "tracks_total": len(tracks),
                "tracks_created": len(tracks),
                "tracks_confirmed": len(tracks),
                "tracks_terminated": None,
                "tracks_terminated_status": "not_exposed_by_tracker_package",
                "tracks_not_observed_at_sequence_end": sum(
                    track["final_state"] == "not_observed_at_sequence_end"
                    for track in tracks
                ),
                "short_tracks_max_2_detections": len(short_tracks),
                "fragmented_tracks": len(fragmented_tracks),
                "average_track_age_processed_frames": round(
                    sum(track["age_processed_frames"] for track in tracks) / len(tracks),
                    6,
                ) if tracks else 0.0,
                "average_gap_processed_frames": round(
                    sum(gap_lengths) / len(gap_lengths),
                    6,
                ) if gap_lengths else 0.0,
                "maximum_gap_processed_frames": max(gap_lengths, default=0),
                "detected_observations": len(observations),
                "predicted_observations": 0,
                "tentative_observations": tentative_total,
                "observed_team_changes": sum(
                    track["observed_team_changes"] for track in tracks
                ),
                "id_switch_heuristic_warnings": sum(
                    bool(track["id_switch_warning"]) for track in tracks
                ),
                "average_detector_confidence": round(
                    sum(detector_confidences) / len(detector_confidences),
                    6,
                ) if detector_confidences else 0.0,
                "average_preliminary_track_quality": round(
                    sum(track["preliminary_track_quality"] for track in tracks) / len(tracks),
                    6,
                ) if tracks else 0.0,
                "segments": len({frame.segment_id for frame in frames}),
                "average_tracks_per_frame": round(len(observations) / len(frames), 6),
            },
            "timing_ms": {
                "loading_ms": round(loading_ms, 3),
                "tracking_ms": round(tracking_ms, 3),
                "rendering_ms": round(rendering_ms, 3),
                "reporting_ms": 0.0,
                "total_ms": round(elapsed_ms, 3),
                "average_tracking_ms_per_frame": round(tracking_ms / len(frames), 3),
            },
            "frames": frame_reports,
            "observations": observations,
            "tracks": tracks,
            "limitations": {
                "consumes_existing_ve002_ve003_outputs": True,
                "detector_executed": False,
                "team_assignment_executed": False,
                "predicted_rows_available": False,
                "association_scores_available": False,
                "ground_truth_identity_available": False,
                "id_switch_metric_is_heuristic": True,
                "image_space_only": True,
                "field_calibration": False,
                "tracking_is_not_tactical_interpretation": True,
            },
        }
        manifest_path = write_json(manifest, output_dir / "tracking_manifest.json")
        html_path = write_html_report(manifest, output_dir / "tracking_report.html")
        reporting_ms = (self._clock() - reporting_started) * 1000.0
        manifest["timing_ms"]["reporting_ms"] = round(reporting_ms, 3)
        manifest["timing_ms"]["total_ms"] = round((self._clock() - started) * 1000.0, 3)
        write_json(manifest, manifest_path)
        return TrackingRun(manifest_path, html_path, manifest)
