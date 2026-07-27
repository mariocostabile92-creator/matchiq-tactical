from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from . import SCHEMA_VERSION
from .adapters import build_player_detector
from .contracts import PlayerDetector
from .geometry import describe_bbox
from .renderer import render_debug_image
from .reports import write_html_report, write_json


@dataclass(frozen=True, slots=True)
class PlayerDetectionConfig:
    output_dir: Path
    backend: str = "opencv_hog"
    confidence_threshold: float = 0.35
    nms_threshold: float = 0.45
    detector_width: int = 960
    model_path: Path | None = None
    device: str = "auto"


@dataclass(frozen=True, slots=True)
class PlayerDetectionRun:
    manifest_path: Path
    html_path: Path
    manifest: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(path: Path) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_" else "_" for character in path.stem)
    return cleaned.strip("_") or "image"


def _confidence_distribution(values: list[float]) -> dict[str, int]:
    buckets = {
        "0.00-0.24": 0,
        "0.25-0.49": 0,
        "0.50-0.74": 0,
        "0.75-1.00": 0,
    }
    for value in values:
        if value < 0.25:
            buckets["0.00-0.24"] += 1
        elif value < 0.50:
            buckets["0.25-0.49"] += 1
        elif value < 0.75:
            buckets["0.50-0.74"] += 1
        else:
            buckets["0.75-1.00"] += 1
    return buckets


class PlayerDetectionRunner:
    def __init__(
        self,
        *,
        detector: PlayerDetector | None = None,
        detector_factory: Callable[..., PlayerDetector] = build_player_detector,
        clock: Callable[[], float] = time.perf_counter,
        now: Callable[[], str] = _utc_now,
    ) -> None:
        self._detector = detector
        self._detector_factory = detector_factory
        self._clock = clock
        self._now = now

    def run(
        self,
        image_paths: Iterable[Path],
        config: PlayerDetectionConfig,
        *,
        source_mode: str,
    ) -> PlayerDetectionRun:
        paths = [Path(path) for path in image_paths]
        if not paths:
            raise ValueError("no input images found")
        output_dir = Path(config.output_dir)
        json_dir = output_dir / "json"
        debug_dir = output_dir / "debug"
        output_dir.mkdir(parents=True, exist_ok=True)
        started = self._clock()
        detector = self._detector or self._detector_factory(
            backend=config.backend,
            confidence_threshold=config.confidence_threshold,
            nms_threshold=config.nms_threshold,
            detector_width=config.detector_width,
            model_path=config.model_path,
            device=config.device,
        )
        load_started = self._clock()
        detector.load()
        model_load_ms = (self._clock() - load_started) * 1000.0
        detector_metadata = detector.metadata()

        files: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        confidences: list[float] = []
        detection_counts: list[int] = []
        successful_inference_ms: list[float] = []
        timing_totals = {
            "image_load_ms": 0.0,
            "inference_ms": 0.0,
            "postprocessing_ms": 0.0,
            "rendering_ms": 0.0,
        }
        try:
            for index, source_path in enumerate(paths, start=1):
                item = self._process_image(
                    source_path,
                    index=index,
                    json_dir=json_dir,
                    debug_dir=debug_dir,
                    detector=detector,
                    detector_metadata=detector_metadata,
                )
                files.append(item)
                for key in timing_totals:
                    timing_totals[key] += float(item.get("timing_ms", {}).get(key, 0.0))
                if item["status"] == "success":
                    detection_counts.append(item["detection_count"])
                    successful_inference_ms.append(item["inference_ms"])
                    confidences.extend(item["confidences"])
                else:
                    errors.append({
                        "source_name": item["source_name"],
                        "message": item["error"],
                    })
            detector_metadata = detector.metadata()
        finally:
            detector.close()

        total_ms = (self._clock() - started) * 1000.0
        successful = len(detection_counts)
        detections_total = sum(detection_counts)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run": {
                "processed_at": self._now(),
                "source_mode": source_mode,
                "output_dir": str(output_dir.resolve()),
                "status": "completed" if not errors else "completed_with_errors",
            },
            "configuration": {
                "backend": config.backend,
                "confidence_threshold": config.confidence_threshold,
                "nms_threshold": config.nms_threshold,
                "detector_width": config.detector_width,
                "model_path": str(config.model_path.resolve()) if config.model_path else None,
                "device": config.device,
            },
            "detector": detector_metadata,
            "aggregate": {
                "images_processed": len(paths),
                "images_successful": successful,
                "images_failed": len(paths) - successful,
                "detections_total": detections_total,
                "raw_detections_total": sum(
                    int(item.get("raw_detection_count", 0))
                    for item in files
                    if item["status"] == "success"
                ),
                "detections_average": round(detections_total / successful, 3) if successful else 0.0,
                "detections_min": min(detection_counts) if detection_counts else 0,
                "detections_max": max(detection_counts) if detection_counts else 0,
                "confidence_distribution": _confidence_distribution(confidences),
            },
            "timing_ms": {
                "model_load_ms": round(model_load_ms, 3),
                **{key: round(value, 3) for key, value in timing_totals.items()},
                "average_inference_ms": round(
                    sum(successful_inference_ms) / len(successful_inference_ms), 3
                ) if successful_inference_ms else 0.0,
                "total_ms": round(total_ms, 3),
            },
            "files": [
                {key: value for key, value in item.items() if key not in {"confidences", "timing_ms"}}
                for item in files
            ],
            "errors": errors,
            "limitations": {
                "generic_person_detector": True,
                "football_specific_model": False,
                "tracking": False,
                "team_classification": False,
                "player_identity": False,
                "ball_detection": False,
                "field_calibration": False,
                "tactical_interpretation": False,
            },
        }
        manifest_path = write_json(manifest, output_dir / "player_detection_manifest.json")
        html_path = write_html_report(manifest, output_dir / "player_detection_report.html")
        return PlayerDetectionRun(
            manifest_path=manifest_path,
            html_path=html_path,
            manifest=manifest,
        )

    def _process_image(
        self,
        source_path: Path,
        *,
        index: int,
        json_dir: Path,
        debug_dir: Path,
        detector: PlayerDetector,
        detector_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV is required by VE-002") from exc

        image_started = self._clock()
        source_name = source_path.name
        output_stem = f"{index:04d}_{_safe_name(source_path)}"
        json_path = json_dir / f"{output_stem}.json"
        debug_path = debug_dir / f"{output_stem}_annotated.jpg"
        timing = {
            "image_load_ms": 0.0,
            "inference_ms": 0.0,
            "postprocessing_ms": 0.0,
            "rendering_ms": 0.0,
            "total_ms": 0.0,
        }
        try:
            load_started = self._clock()
            image = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
            timing["image_load_ms"] = (self._clock() - load_started) * 1000.0
            if image is None:
                raise ValueError("image is unreadable or corrupt")
            height, width = image.shape[:2]

            inference_started = self._clock()
            raw_detections = detector.detect(image)
            timing["inference_ms"] = (self._clock() - inference_started) * 1000.0
            current_detector_metadata = detector.metadata()
            inference_stats = current_detector_metadata.get("last_inference", {})

            post_started = self._clock()
            detections: list[dict[str, Any]] = []
            for sequence, raw in enumerate(raw_detections, start=1):
                geometry = describe_bbox(raw.bbox_xyxy, width=width, height=height)
                if geometry["bbox_xywh"][2] <= 0 or geometry["bbox_xywh"][3] <= 0:
                    continue
                detections.append({
                    "detection_id": f"player_{sequence:03d}",
                    "class_id": raw.class_id,
                    "class_name": raw.class_name,
                    "candidate_type": "player_candidate",
                    "confidence": round(float(raw.confidence), 6),
                    "source_model": raw.source_model,
                    "original_class": raw.metadata.get("original_class", raw.class_name),
                    "source_metadata": dict(raw.metadata),
                    **geometry,
                })
            timing["postprocessing_ms"] = (self._clock() - post_started) * 1000.0

            render_started = self._clock()
            render_debug_image(
                image,
                detections,
                debug_path,
                backend=str(current_detector_metadata.get("backend", "unknown")),
            )
            timing["rendering_ms"] = (self._clock() - render_started) * 1000.0
            timing["total_ms"] = (self._clock() - image_started) * 1000.0
            payload = {
                "schema_version": SCHEMA_VERSION,
                "source": {
                    "file_name": source_name,
                    "path": str(source_path.resolve()),
                    "width": width,
                    "height": height,
                },
                "detector": current_detector_metadata,
                "postprocessing": {
                    "raw_detection_count": int(
                        inference_stats.get("raw_detection_count", len(raw_detections))
                    ),
                    "backend_output_count": int(
                        inference_stats.get("backend_output_count", len(raw_detections))
                    ),
                    "kept_detection_count": len(detections),
                    "invalid_boxes_removed": int(
                        inference_stats.get("invalid_boxes_removed", 0)
                    ),
                    "warnings": list(current_detector_metadata.get("warnings", [])),
                },
                "detection_count": len(detections),
                "detections": detections,
                "timing_ms": {key: round(value, 3) for key, value in timing.items()},
                "debug_image": str(debug_path.relative_to(json_dir.parent)).replace("\\", "/"),
            }
            write_json(payload, json_path)
            return {
                "source_name": source_name,
                "source_path": str(source_path.resolve()),
                "status": "success",
                "detection_count": len(detections),
                "raw_detection_count": int(
                    inference_stats.get("raw_detection_count", len(raw_detections))
                ),
                "confidences": [item["confidence"] for item in detections],
                "average_confidence": round(
                    sum(item["confidence"] for item in detections) / len(detections), 6
                ) if detections else 0.0,
                "inference_ms": round(timing["inference_ms"], 3),
                "json_report": str(json_path.relative_to(json_dir.parent)).replace("\\", "/"),
                "debug_image": str(debug_path.relative_to(debug_dir.parent)).replace("\\", "/"),
                "timing_ms": timing,
                "error": None,
            }
        except (OSError, RuntimeError, ValueError) as exc:
            timing["total_ms"] = (self._clock() - image_started) * 1000.0
            error_payload = {
                "schema_version": SCHEMA_VERSION,
                "source": {
                    "file_name": source_name,
                    "path": str(source_path.resolve()),
                },
                "detector": detector_metadata,
                "status": "failed",
                "detection_count": 0,
                "detections": [],
                "timing_ms": {key: round(value, 3) for key, value in timing.items()},
                "error": str(exc),
                "debug_image": None,
            }
            write_json(error_payload, json_path)
            return {
                "source_name": source_name,
                "source_path": str(source_path.resolve()),
                "status": "failed",
                "detection_count": 0,
                "raw_detection_count": 0,
                "confidences": [],
                "average_confidence": 0.0,
                "inference_ms": round(timing["inference_ms"], 3),
                "json_report": str(json_path.relative_to(json_dir.parent)).replace("\\", "/"),
                "debug_image": None,
                "timing_ms": timing,
                "error": str(exc),
            }
