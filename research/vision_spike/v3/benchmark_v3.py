from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..benchmark import ClipSpec, aggregate_rows, default_clips
from ..config import VisionSpikeConfig
from ..pipeline import run_pipeline
from ..rfdetr_detector import RFDETRDetector
from ..utils import write_json
from . import CLASS_NAMES
from .football_detector import FootballRFDETRDetector
from .manifest import read_jsonl


def _class_summary(output: Path) -> dict[str, Any]:
    rows = read_jsonl(output / "detections.jsonl")
    counts = Counter(str(item.get("class_name", "unknown")) for item in rows)
    frame_ids = {int(item.get("frame_index", -1)) for item in rows}
    return {"detections_by_class": {name: counts.get(name, 0) for name in CLASS_NAMES}, "frames_with_detections": len(frame_ids)}


def run_detector(name: str, clips: tuple[ClipSpec, ...], output_root: Path, *, checkpoint: Path | None) -> list[dict[str, Any]]:
    rows = []
    for clip in clips:
        output = output_root / name / clip.name
        config = VisionSpikeConfig(
            input_video=clip.path, output_dir=output, detector_backend="rfdetr", confidence_threshold=0.25,
            iou_threshold=0.45, frame_stride=clip.frame_stride, max_seconds=30.0, device="auto",
            model_size="small", input_resolution=512, inference_mode="standard", half_precision=True,
            team_clustering_enabled=False, pitch_detection_enabled=True,
        )
        if checkpoint is None:
            detector = RFDETRDetector(confidence_threshold=0.25, input_resolution=512, device="auto", half_precision=True)
        else:
            detector = FootballRFDETRDetector(
                model_path=checkpoint, confidence_threshold=0.25, input_resolution=512,
                device="auto", half_precision=True,
            )
        result = run_pipeline(config, detector=detector)
        rows.append({"variant": name, "clip": clip.name, **result.metrics, **_class_summary(output)})
    return rows


def run_comparison(clip_root: Path, output_root: Path, checkpoint: Path) -> dict[str, Any]:
    clips = default_clips(clip_root)
    coco_rows = run_detector("rfdetr_small_coco", clips, output_root, checkpoint=None)
    football_rows = run_detector("rfdetr_small_football_v3", clips, output_root, checkpoint=checkpoint)
    payload = {
        "protocol": "same three clips, timestamps, stride, IoU tracker and standard 512 pipeline",
        "coco": aggregate_rows(coco_rows), "football_v3": aggregate_rows(football_rows),
        "runs": coco_rows + football_rows,
        "manual_metrics_required": ["coverage", "staff_public_false_positives"],
    }
    write_json(output_root / "v2_vs_v3.json", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark RF-DETR COCO against a V3 football checkpoint on the frozen V2 clips.")
    parser.add_argument("--clip-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_comparison(args.clip_root, args.output_root, args.checkpoint), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
