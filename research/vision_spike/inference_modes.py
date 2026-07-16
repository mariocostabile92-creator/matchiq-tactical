from __future__ import annotations

from dataclasses import replace
from typing import Any

from .contracts import Detection
from .detector import VisionDetector
from .tracker import bbox_iou
from .utils import require_cv2_numpy


def letterbox_frame(frame: object, target_size: int) -> tuple[object, float, int, int]:
    cv2, np = require_cv2_numpy()
    height, width = frame.shape[:2]
    scale = min(target_size / float(width), target_size / float(height))
    resized_width = max(1, int(round(width * scale)))
    resized_height = max(1, int(round(height * scale)))
    resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((target_size, target_size, 3), dtype=frame.dtype)
    offset_x = (target_size - resized_width) // 2
    offset_y = (target_size - resized_height) // 2
    canvas[offset_y : offset_y + resized_height, offset_x : offset_x + resized_width] = resized
    return canvas, scale, offset_x, offset_y


def restore_letterbox_box(
    box: tuple[float, float, float, float],
    *,
    scale: float,
    offset_x: int,
    offset_y: int,
    original_width: int,
    original_height: int,
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = box
    return (
        max(0.0, min(float(original_width - 1), (x1 - offset_x) / scale)),
        max(0.0, min(float(original_height - 1), (y1 - offset_y) / scale)),
        max(0.0, min(float(original_width - 1), (x2 - offset_x) / scale)),
        max(0.0, min(float(original_height - 1), (y2 - offset_y) / scale)),
    )


def tile_origins(length: int, tile_size: int, overlap: float) -> list[int]:
    if length <= tile_size:
        return [0]
    step = max(1, int(round(tile_size * (1.0 - overlap))))
    values = list(range(0, max(1, length - tile_size + 1), step))
    last = length - tile_size
    if values[-1] != last:
        values.append(last)
    return sorted(set(values))


def deduplicate_detections(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    kept: list[Detection] = []
    for candidate in sorted(detections, key=lambda item: item.confidence, reverse=True):
        duplicate = any(
            existing.class_name == candidate.class_name
            and bbox_iou(existing.bbox_xyxy, candidate.bbox_xyxy) >= iou_threshold
            for existing in kept
        )
        if not duplicate:
            kept.append(candidate)
    return kept


class TiledInferenceDetector(VisionDetector):
    def __init__(
        self,
        detector: VisionDetector,
        *,
        tile_size: int = 960,
        overlap: float = 0.2,
        nms_iou_threshold: float = 0.45,
        max_detections: int = 100,
    ) -> None:
        self.detector = detector
        self.tile_size = tile_size
        self.overlap = overlap
        self.nms_iou_threshold = nms_iou_threshold
        self.max_detections = max_detections
        self.raw_detections = 0
        self.duplicates_removed = 0

    def load(self) -> None:
        self.detector.load()

    def detect(self, frame: object, *, frame_index: int, timestamp_seconds: float) -> list[Detection]:
        height, width = frame.shape[:2]
        all_detections: list[Detection] = []
        tile_index = 0
        for y in tile_origins(height, self.tile_size, self.overlap):
            for x in tile_origins(width, self.tile_size, self.overlap):
                tile = frame[y : min(height, y + self.tile_size), x : min(width, x + self.tile_size)]
                local = self.detector.detect(tile, frame_index=frame_index, timestamp_seconds=timestamp_seconds)
                for detection in local:
                    x1, y1, x2, y2 = detection.bbox_xyxy
                    metadata = dict(detection.metadata)
                    metadata.update({"tile_index": tile_index, "tile_origin": [x, y]})
                    all_detections.append(
                        replace(
                            detection,
                            bbox_xyxy=(x1 + x, y1 + y, x2 + x, y2 + y),
                            detection_id=f"{detection.detection_id}-tile{tile_index}",
                            metadata=metadata,
                        )
                    )
                tile_index += 1
        merged = deduplicate_detections(all_detections, self.nms_iou_threshold)
        self.raw_detections += len(all_detections)
        self.duplicates_removed += max(0, len(all_detections) - len(merged))
        for index, detection in enumerate(merged):
            detection.detection_id = f"f{frame_index}-rfdetr-tiled-person-{index}"
        return merged[: self.max_detections]

    def warmup(self) -> None:
        warmup = getattr(self.detector, "warmup", None)
        if warmup:
            warmup()

    def health_check(self) -> dict[str, Any]:
        health_check = getattr(self.detector, "health_check", None)
        data = health_check() if health_check else {"loaded": True}
        return {**data, "inference_mode": "tiled"}

    def close(self) -> None:
        self.detector.close()

    def metadata(self) -> dict[str, Any]:
        return {
            **self.detector.metadata(),
            "inference_mode": "tiled",
            "tile_size": self.tile_size,
            "tile_overlap": self.overlap,
            "global_nms_iou_threshold": self.nms_iou_threshold,
            "raw_tile_detections": self.raw_detections,
            "duplicates_removed": self.duplicates_removed,
        }
