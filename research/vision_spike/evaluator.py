from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import FrameResult
from .overlay import format_timestamp
from .utils import peak_rss_mb, require_cv2_numpy


@dataclass(slots=True)
class SampleFrame:
    result: FrameResult
    image: object
    reason: str


class EvaluationSampler:
    def __init__(self, expected_frames: int) -> None:
        self.expected_frames = max(1, expected_frames)
        self._samples: dict[str, SampleFrame] = {}
        self._previous_gray = None
        self._highest_motion = -1.0
        self._lowest_tactical = 2.0

    def observe(self, ordinal: int, image: object, result: FrameResult) -> None:
        cv2, _ = require_cv2_numpy()
        targets = {
            "start": 0,
            "center": max(0, self.expected_frames // 2),
            "end": max(0, self.expected_frames - 1),
        }
        for reason, target in targets.items():
            if reason not in self._samples or abs(ordinal - target) < abs(
                self._samples[reason].result.debug_metadata.get("ordinal", 0) - target
            ):
                result.debug_metadata["ordinal"] = ordinal
                self._samples[reason] = SampleFrame(result, image.copy(), reason)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if self._previous_gray is not None:
            motion = float(cv2.absdiff(gray, self._previous_gray).mean())
            if motion > self._highest_motion:
                self._highest_motion = motion
                self._samples["movement"] = SampleFrame(result, image.copy(), "highest sampled motion")
        self._previous_gray = gray
        if result.tactical_view_score < self._lowest_tactical:
            self._lowest_tactical = result.tactical_view_score
            self._samples["difficult"] = SampleFrame(result, image.copy(), "lowest tactical-view score")

    def save(self, directory: Path) -> list[dict[str, Any]]:
        cv2, _ = require_cv2_numpy()
        directory.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []
        ordered = ["start", "center", "end", "movement", "difficult"]
        for index, key in enumerate(ordered, start=1):
            sample = self._samples.get(key)
            if sample is None:
                continue
            path = directory / f"sample_{index}_{key}_{sample.result.frame_index}.jpg"
            cv2.imwrite(str(path), sample.image, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            rows.append(
                {
                    "path": str(path),
                    "timestamp_seconds": sample.result.timestamp_seconds,
                    "detections": len(sample.result.detections),
                    "tracks": len(sample.result.tracks),
                    "pitch_visible": sample.result.pitch_visible,
                    "tactical_view_score": sample.result.tactical_view_score,
                    "reason": sample.reason,
                }
            )
        return rows


class MetricsCollector:
    def __init__(self) -> None:
        self.processing_ms: list[float] = []
        self.person_counts: list[int] = []
        self.possible_ball_counts: list[int] = []
        self.track_counts: list[int] = []
        self.pitch_frames = 0
        self.outside_pitch_detections = 0
        self.total_detections = 0

    def observe(self, result: FrameResult, pitch_mask: object | None) -> None:
        self.processing_ms.append(result.processing_ms)
        self.person_counts.append(sum(1 for item in result.detections if item.class_name == "person"))
        self.possible_ball_counts.append(sum(1 for item in result.detections if item.class_name == "possible_ball"))
        self.track_counts.append(len(result.tracks))
        self.pitch_frames += int(result.pitch_visible)
        self.total_detections += len(result.detections)
        if pitch_mask is None:
            return
        height, width = pitch_mask.shape[:2]
        for detection in result.detections:
            x1, y1, x2, y2 = detection.bbox_xyxy
            center_x = max(0, min(width - 1, int((x1 + x2) / 2)))
            foot_y = max(0, min(height - 1, int(y2)))
            if pitch_mask[foot_y, center_x] == 0:
                self.outside_pitch_detections += 1

    def finalize(
        self,
        *,
        elapsed_seconds: float,
        tracker_metadata: dict[str, Any],
        team_metadata: dict[str, Any],
        device: str,
    ) -> dict[str, Any]:
        frame_count = len(self.processing_ms)
        average_ms = sum(self.processing_ms) / frame_count if frame_count else 0.0
        return {
            "processed_frames": frame_count,
            "elapsed_seconds": round(elapsed_seconds, 4),
            "processing_fps": round(frame_count / elapsed_seconds, 4) if elapsed_seconds > 0 else 0.0,
            "average_latency_ms": round(average_ms, 4),
            "average_people_detected": round(sum(self.person_counts) / frame_count, 4) if frame_count else 0.0,
            "possible_ball_detections": sum(self.possible_ball_counts),
            "tracks_total": tracker_metadata.get("tracks_created", 0),
            "average_track_age_frames": tracker_metadata.get("average_track_age_frames", 0.0),
            "tracks_lost": tracker_metadata.get("tracks_retired", 0),
            "frames_with_active_tracks_percent": round(100.0 * sum(count > 0 for count in self.track_counts) / frame_count, 2) if frame_count else 0.0,
            "pitch_visible_percent": round(100.0 * self.pitch_frames / frame_count, 2) if frame_count else 0.0,
            "detections_outside_pitch_percent": round(100.0 * self.outside_pitch_detections / self.total_detections, 2) if self.total_detections else 0.0,
            "peak_rss_mb": peak_rss_mb(),
            "device": device,
            "gpu_used": False,
            "tracker": tracker_metadata,
            "team_clustering": team_metadata,
            "accuracy_note": "No precision/recall: this run has no annotated ground truth.",
            "id_switch_note": "ID switches require manual review of the overlay.",
        }


def write_evaluation(path: Path, metrics: dict[str, Any], samples: list[dict[str, Any]]) -> None:
    lines = [
        "# MatchIQ Vision Spike V0 - Evaluation",
        "",
        "This report is a feasibility record, not a product capability claim.",
        "No precision or recall is reported because no ground-truth annotation is available.",
        "",
        "## Automatic metrics",
        "",
        f"- Processed frames: {metrics.get('processed_frames', 0)}",
        f"- Processing FPS: {metrics.get('processing_fps', 0)}",
        f"- Average latency: {metrics.get('average_latency_ms', 0)} ms/frame",
        f"- Average generic persons detected: {metrics.get('average_people_detected', 0)}",
        f"- Temporary tracks created: {metrics.get('tracks_total', 0)}",
        f"- Frames with active tracks: {metrics.get('frames_with_active_tracks_percent', 0)}%",
        f"- Pitch visible: {metrics.get('pitch_visible_percent', 0)}%",
        f"- Peak process RSS: {metrics.get('peak_rss_mb', 0)} MB",
        "",
        "## Manual review table",
        "",
        "| Timestamp | Players detected | Evident errors | Ball | Tracking | Pitch | Notes |",
        "|---|---:|---|---|---|---|---|",
    ]
    for sample in samples:
        lines.append(
            f"| {format_timestamp(sample['timestamp_seconds'])} | {sample['detections']} | REVIEW REQUIRED | "
            f"not evaluated | {sample['tracks']} active | {'yes' if sample['pitch_visible'] else 'no'} | {sample['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Decision gate",
            "",
            "PENDING_MANUAL_REVIEW",
            "",
            "The final GREEN/YELLOW/RED decision must be written only after inspecting overlay and sample frames.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
