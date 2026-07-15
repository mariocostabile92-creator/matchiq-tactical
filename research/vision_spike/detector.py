from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from .contracts import Detection
from .utils import require_cv2_numpy


class VisionDetector(ABC):
    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def detect(self, frame: object, *, frame_index: int, timestamp_seconds: float) -> list[Detection]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        raise NotImplementedError


class OpenCvHogPersonDetector(VisionDetector):
    """Generic person detector. It does not infer football-specific roles."""

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.35,
        nms_threshold: float = 0.45,
        detector_width: int = 960,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.detector_width = detector_width
        self._hog = None

    def load(self) -> None:
        cv2, _ = require_cv2_numpy()
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self._hog = hog

    def detect(self, frame: object, *, frame_index: int, timestamp_seconds: float) -> list[Detection]:
        if self._hog is None:
            raise RuntimeError("detector is not loaded")
        cv2, _ = require_cv2_numpy()
        height, width = frame.shape[:2]
        scale = min(1.0, self.detector_width / float(width))
        working = frame
        if scale < 1.0:
            working = cv2.resize(frame, (int(width * scale), int(height * scale)))
        rects, weights = self._hog.detectMultiScale(
            working,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        boxes: list[list[int]] = []
        scores: list[float] = []
        for rect, raw_weight in zip(rects, weights):
            x, y, box_width, box_height = [int(value) for value in rect]
            raw = float(raw_weight)
            confidence = max(0.0, min(1.0, 1.0 - math.exp(-max(raw, 0.0))))
            if confidence < self.confidence_threshold:
                continue
            boxes.append([x, y, box_width, box_height])
            scores.append(confidence)
        if not boxes:
            return []
        kept = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_threshold, self.nms_threshold)
        indices = [int(item) for item in kept] if len(kept) else []
        inverse = 1.0 / scale
        detections: list[Detection] = []
        for sequence, index in enumerate(indices):
            x, y, box_width, box_height = boxes[index]
            x1 = max(0.0, x * inverse)
            y1 = max(0.0, y * inverse)
            x2 = min(float(width - 1), (x + box_width) * inverse)
            y2 = min(float(height - 1), (y + box_height) * inverse)
            detections.append(
                Detection(
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    class_id=0,
                    class_name="person",
                    confidence=round(scores[index], 6),
                    bbox_xyxy=(round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)),
                    source_model="opencv_hog_default_people",
                    detection_id=f"f{frame_index}-person-{sequence}",
                    metadata={"role": "unknown"},
                )
            )
        return detections

    def close(self) -> None:
        self._hog = None

    def metadata(self) -> dict[str, Any]:
        cv2, _ = require_cv2_numpy()
        return {
            "backend": "opencv_hog",
            "model": "OpenCV default people detector",
            "opencv_version": cv2.__version__,
            "device": "cpu",
            "classes": ["person"],
            "ball_supported": False,
            "roles_supported": False,
            "weights_downloaded": False,
        }


def build_detector(backend: str, **settings: Any) -> VisionDetector:
    if backend == "opencv_hog":
        return OpenCvHogPersonDetector(**settings)
    raise ValueError(f"detector backend is not available for CLI use: {backend}")
