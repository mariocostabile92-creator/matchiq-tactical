from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ..rfdetr_detector import RFDETRDetector
from ..utils import require_cv2_numpy
from . import CLASS_NAMES
from .coco import load_coco
from .football_detector import FootballRFDETRDetector
from .metrics import coco_to_xyxy, evaluate_by_scene, evaluate_detection_metrics
from .paths import DatasetPaths
from .validate_dataset import resolve_image_path


def _truth_rows(coco: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    categories = {int(item["id"]): str(item["name"]) for item in coco["categories"]}
    image_metadata = {int(item["id"]): item.get("metadata", {}) for item in coco["images"]}
    rows = []
    for item in coco["annotations"]:
        box = coco_to_xyxy(item["bbox"])
        rows.append({
            "image_id": int(item["image_id"]), "class_name": categories[int(item["category_id"])],
            "bbox_xyxy": box, "area": float(item.get("area", item["bbox"][2] * item["bbox"][3])),
            "ignore": bool(item.get("ignore", False)),
        })
    return rows, image_metadata


def run_test_evaluation(
    dataset_root: Path, *, mode: str, checkpoint: Path | None, confidence: float = 0.25, device: str = "auto"
) -> dict[str, Any]:
    paths = DatasetPaths.from_root(dataset_root)
    coco = load_coco(paths.cache / "rfdetr_dataset" / "test" / "_annotations.coco.json")
    if mode == "football":
        if checkpoint is None:
            raise ValueError("football evaluation requires --checkpoint")
        detector = FootballRFDETRDetector(model_path=checkpoint, confidence_threshold=confidence, input_resolution=512, device=device)
    else:
        detector = RFDETRDetector(confidence_threshold=confidence, input_resolution=512, device=device)
    detector.load()
    cv2, _ = require_cv2_numpy()
    predictions: list[dict[str, Any]] = []
    latencies = []
    try:
        for image in coco["images"]:
            path = resolve_image_path(paths, image) or (paths.cache / "rfdetr_dataset" / "test" / Path(image["file_name"]).name)
            frame = cv2.imread(str(path))
            if frame is None:
                raise ValueError(f"unreadable test image: {path.name}")
            started = time.perf_counter()
            detections = detector.detect(frame, frame_index=int(image["id"]), timestamp_seconds=0.0)
            latencies.append((time.perf_counter() - started) * 1000)
            for detection in detections:
                name = detection.class_name
                if mode == "coco" and name == "person":
                    name = "player"
                x1, y1, x2, y2 = detection.bbox_xyxy
                predictions.append({
                    "image_id": int(image["id"]), "class_name": name, "bbox_xyxy": detection.bbox_xyxy,
                    "area": (x2 - x1) * (y2 - y1), "score": detection.confidence,
                })
    finally:
        detector.close()
    truth, metadata = _truth_rows(coco)
    metrics = evaluate_detection_metrics(truth, predictions, class_names=CLASS_NAMES)
    metrics.update(
        mode=mode, images=len(coco["images"]), predictions=len(predictions),
        average_latency_ms=round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        fps=round(1000.0 / (sum(latencies) / len(latencies)), 3) if latencies and sum(latencies) else 0.0,
        scene_metrics=evaluate_by_scene(truth, predictions, metadata),
        staff_public_false_positives=sum(
            values.get("false_positive", 0)
            for key, scene in evaluate_by_scene(truth, predictions, metadata).items()
            if key == "staff_public_visible:true"
            for values in scene["per_class"].values()
        ),
    )
    destination = paths.reports / f"{mode}_test_metrics.json"
    destination.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate COCO baseline or football V3 RF-DETR on the frozen test split.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--mode", choices=("coco", "football"), required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_test_evaluation(args.dataset, mode=args.mode, checkpoint=args.checkpoint, confidence=args.confidence, device=args.device), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
