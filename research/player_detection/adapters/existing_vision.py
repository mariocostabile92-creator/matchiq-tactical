from __future__ import annotations

from pathlib import Path
from typing import Any

from research.vision_spike.detector import VisionDetector, build_detector

from ..contracts import PlayerDetector, RawPlayerDetection


class ExistingVisionDetectorAdapter(PlayerDetector):
    """Adapts the existing isolated Vision Spike detector without duplicating it."""

    def __init__(
        self,
        *,
        backend: str = "opencv_hog",
        confidence_threshold: float = 0.35,
        nms_threshold: float = 0.45,
        detector_width: int = 960,
        model_path: Path | None = None,
        device: str = "auto",
    ) -> None:
        self.backend = "opencv_hog" if backend == "hog" else backend
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.detector_width = detector_width
        self.model_path = Path(model_path) if model_path else None
        self.device = device
        self._detector: VisionDetector | None = None
        self._last_inference: dict[str, Any] = {
            "raw_detection_count": 0,
            "backend_output_count": 0,
            "person_detection_count": 0,
            "kept_detection_count": 0,
            "dropped_non_person": 0,
        }

    def load(self) -> None:
        if self._detector is not None:
            return
        if self.backend == "rfdetr":
            if self.model_path is None:
                raise RuntimeError(
                    "RF-DETR requires --model-path pointing to local weights; "
                    "VE-002 never downloads model weights automatically."
                )
            if not self.model_path.is_file():
                raise FileNotFoundError(f"RF-DETR local weights not found: {self.model_path}")
            settings: dict[str, Any] = {
                "confidence_threshold": self.confidence_threshold,
                "model_path": self.model_path,
                "device": self.device,
            }
        elif self.backend == "opencv_hog":
            settings = {
                "confidence_threshold": self.confidence_threshold,
                "nms_threshold": self.nms_threshold,
                "detector_width": self.detector_width,
            }
        else:
            raise ValueError(f"unsupported player detector backend: {self.backend}")
        detector = build_detector(self.backend, **settings)
        detector.load()
        self._detector = detector

    def detect(self, image: object) -> list[RawPlayerDetection]:
        if self._detector is None:
            raise RuntimeError("player detector is not loaded")
        detections = self._detector.detect(image, frame_index=0, timestamp_seconds=0.0)
        people = [item for item in detections if item.class_name.lower() == "person"]
        people.sort(
            key=lambda item: (
                -float(item.confidence),
                tuple(float(value) for value in item.bbox_xyxy),
                int(item.class_id),
            )
        )
        detector_metadata = self._detector.metadata()
        detector_stats = detector_metadata.get("last_inference", {})
        self._last_inference = {
            "raw_detection_count": int(
                detector_stats.get("raw_detection_count", len(detections))
            ),
            "backend_output_count": len(detections),
            "person_detection_count": int(
                detector_stats.get("person_detection_count", len(people))
            ),
            "kept_detection_count": len(people),
            "dropped_non_person": len(detections) - len(people),
            "invalid_boxes_removed": int(
                detector_stats.get("invalid_boxes_removed", 0)
            ),
            "limited_by_max_detections": int(
                detector_stats.get("limited_by_max_detections", 0)
            ),
        }
        return [
            RawPlayerDetection(
                class_id=item.class_id,
                class_name=item.class_name,
                confidence=item.confidence,
                bbox_xyxy=item.bbox_xyxy,
                source_model=item.source_model,
                metadata=dict(item.metadata),
            )
            for item in people
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = self._detector.metadata() if self._detector else {
            "backend": self.backend,
            "loaded": False,
        }
        return {
            **metadata,
            "adapter": "research.player_detection.ExistingVisionDetectorAdapter",
            "purpose": "generic person/player candidate detection",
            "confidence_threshold": self.confidence_threshold,
            "nms_threshold": self.nms_threshold if self.backend == "opencv_hog" else None,
            "model_version": metadata.get("rfdetr_version")
            or metadata.get("opencv_version")
            or "unknown",
            "last_inference": dict(self._last_inference),
            "identity_supported": False,
            "team_supported": False,
            "tracking_supported": False,
            "automatic_downloads": False,
        }

    def close(self) -> None:
        if self._detector is not None:
            self._detector.close()
            self._detector = None


def build_player_detector(
    *,
    backend: str,
    confidence_threshold: float,
    nms_threshold: float,
    detector_width: int,
    model_path: Path | None,
    device: str,
) -> PlayerDetector:
    return ExistingVisionDetectorAdapter(
        backend=backend,
        confidence_threshold=confidence_threshold,
        nms_threshold=nms_threshold,
        detector_width=detector_width,
        model_path=model_path,
        device=device,
    )
