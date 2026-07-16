from __future__ import annotations

import argparse
import json
import shutil
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .benchmark import ClipSpec, default_clips
from .utils import require_cv2_numpy, write_json


VARIANTS = (
    "baseline_opencv",
    "rfdetr_small_standard",
    "rfdetr_small_highres",
    "rfdetr_small_tiled",
)
REVIEW_TIMESTAMPS = (7.0, 12.0, 15.0, 22.0, 29.0)


@dataclass(slots=True)
class ManualObservation:
    variant: str
    clip: str
    timestamp_seconds: float
    scene_type: str
    people_clearly_visible: int
    correct_detections: int
    people_missed: int
    false_positives: int
    duplicate_boxes: int
    staff_or_crowd_detections: int
    pitch_visible: bool
    tactical_utility: str
    notes: str = ""

    @property
    def manual_exploratory_coverage(self) -> float | None:
        if self.people_clearly_visible <= 0:
            return None
        return self.correct_detections / self.people_clearly_visible

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        coverage = self.manual_exploratory_coverage
        payload["manual_exploratory_coverage"] = round(coverage, 4) if coverage is not None else None
        return payload


def load_observations(path: Path) -> list[ManualObservation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("observations", payload) if isinstance(payload, dict) else payload
    observations = []
    for row in rows:
        clean = {key: value for key, value in row.items() if key != "manual_exploratory_coverage"}
        observations.append(ManualObservation(**clean))
    return observations


def write_review_template(path: Path, clips: tuple[ClipSpec, ...]) -> None:
    observations = []
    for clip in clips:
        for timestamp in REVIEW_TIMESTAMPS:
            for variant in VARIANTS:
                observations.append(
                    ManualObservation(
                        variant=variant,
                        clip=clip.name,
                        timestamp_seconds=timestamp,
                        scene_type="wide_tactical" if timestamp in {12.0, 15.0, 22.0} else "close_or_nontactical",
                        people_clearly_visible=0,
                        correct_detections=0,
                        people_missed=0,
                        false_positives=0,
                        duplicate_boxes=0,
                        staff_or_crowd_detections=0,
                        pitch_visible=False,
                        tactical_utility="pending",
                    ).to_dict()
                )
    write_json(
        path,
        {
            "metric_name": "manual exploratory coverage",
            "warning": "Exploratory manual review only; this is not precision or recall.",
            "observations": observations,
        },
    )


def summarize_manual_review(observations: list[ManualObservation], comparison_metrics: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    variants = comparison_metrics.get("variants", {})
    for variant in VARIANTS:
        wide = [
            item
            for item in observations
            if item.variant == variant
            and item.scene_type == "wide_tactical"
            and item.manual_exploratory_coverage is not None
        ]
        coverages = [float(item.manual_exploratory_coverage) for item in wide]
        median_coverage = statistics.median(coverages) if coverages else None
        tracking = float(variants.get(variant, {}).get("frames_with_active_tracks_percent", 0.0))
        false_positives = sum(item.false_positives for item in wide)
        duplicates = sum(item.duplicate_boxes for item in wide)
        gate = decision_gate(median_coverage, tracking, licensing_ok=True)
        result[variant] = {
            "wide_tactical_frames_reviewed": len(wide),
            "median_manual_exploratory_coverage": round(median_coverage, 4) if median_coverage is not None else None,
            "frames_with_active_tracks_percent": tracking,
            "manual_false_positives": false_positives,
            "manual_duplicate_boxes": duplicates,
            "decision_gate": gate,
        }
    return result


def decision_gate(median_coverage: float | None, tracking_percent: float, *, licensing_ok: bool) -> str:
    if not licensing_ok:
        return "RED"
    if median_coverage is None:
        return "PENDING_MANUAL_REVIEW"
    coverage_percent = median_coverage * 100.0
    if coverage_percent >= 70.0 and tracking_percent >= 70.0:
        return "GREEN"
    if coverage_percent >= 40.0:
        return "YELLOW"
    return "RED"


def _read_frame(video_path: Path, timestamp_seconds: float) -> object:
    cv2, _ = require_cv2_numpy()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open comparison clip: {video_path}")
    try:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            raise ValueError(f"cannot read {video_path} at {timestamp_seconds}s")
        return frame
    finally:
        capture.release()


def _closest_frame_payload(run_dir: Path, timestamp_seconds: float) -> dict[str, Any] | None:
    frames_path = run_dir / "frames.json"
    if not frames_path.is_file():
        return None
    frames = json.loads(frames_path.read_text(encoding="utf-8"))
    if not frames:
        return None
    return min(frames, key=lambda item: abs(float(item.get("timestamp_seconds", 0.0)) - timestamp_seconds))


def _draw_payload(frame: object, payload: dict[str, Any] | None, title: str) -> object:
    cv2, _ = require_cv2_numpy()
    output = frame.copy()
    if payload:
        for detection in payload.get("detections", []):
            x1, y1, x2, y2 = (int(round(value)) for value in detection.get("bbox_xyxy", (0, 0, 0, 0)))
            confidence = float(detection.get("confidence", 0.0))
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 240, 160), 2)
            cv2.putText(output, f"person {confidence:.2f}", (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(output, (0, 0), (output.shape[1], 42), (4, 13, 29), -1)
    cv2.putText(output, title, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
    return output


def create_contact_sheet(
    *,
    clip: ClipSpec,
    timestamp_seconds: float,
    output_root: Path,
    destination: Path,
) -> None:
    cv2, np = require_cv2_numpy()
    original = _read_frame(clip.path, timestamp_seconds)
    height, width = original.shape[:2]
    panels = [_draw_payload(original, None, "ORIGINALE")]
    for variant in VARIANTS:
        payload = _closest_frame_payload(output_root / variant / clip.name, timestamp_seconds)
        panels.append(_draw_payload(original, payload, variant.upper()))
    panel_width = 640
    panel_height = int(round(panel_width * height / width))
    panels = [cv2.resize(panel, (panel_width, panel_height), interpolation=cv2.INTER_AREA) for panel in panels]
    sheet = np.hstack(panels)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])


def build_visual_comparison(output_root: Path, clips: tuple[ClipSpec, ...]) -> list[str]:
    contact_dir = output_root / "comparison" / "contact_sheets"
    overlay_dir = output_root / "comparison" / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for clip in clips:
        for timestamp in REVIEW_TIMESTAMPS:
            destination = contact_dir / f"{clip.name}_{int(timestamp):02d}s.jpg"
            create_contact_sheet(clip=clip, timestamp_seconds=timestamp, output_root=output_root, destination=destination)
            created.append(str(destination))
        for variant in VARIANTS:
            source = output_root / variant / clip.name / "overlay.mp4"
            if source.is_file():
                shutil.copy2(source, overlay_dir / f"{variant}_{clip.name}.mp4")
    write_json(output_root / "comparison" / "contact_sheets.json", {"files": created})
    return created


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build visual comparison and manual exploratory coverage outputs.")
    parser.add_argument("--clip-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--review", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    clips = default_clips(args.clip_root)
    build_visual_comparison(args.output_root, clips)
    review_path = args.review or args.output_root / "comparison" / "manual_review.json"
    if not review_path.exists():
        write_review_template(review_path, clips)
    comparison_path = args.output_root / "comparison" / "detector_comparison.json"
    if comparison_path.is_file() and args.review:
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        summary = summarize_manual_review(load_observations(review_path), comparison)
        write_json(args.output_root / "comparison" / "manual_coverage_summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
