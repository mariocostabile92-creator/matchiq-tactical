from __future__ import annotations

import importlib.metadata
import time
from pathlib import Path
from typing import Any, Callable

from .contracts import Detection
from .detector import VisionDetector
from .inference_modes import letterbox_frame, restore_letterbox_box
from .utils import OptionalDependencyError, sha256_file


RFDETR_LICENSE = "Apache-2.0"
RFDETR_REPOSITORY = "https://github.com/roboflow/rf-detr"
RFDETR_WEIGHT_SOURCES = {
    "small": "https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth",
    "medium": "https://storage.googleapis.com/rfdetr/medium_coco/checkpoint_best_regular.pth",
}


class RFDETRDetector(VisionDetector):
    """Isolated COCO-person adapter for the RF-DETR feasibility benchmark."""

    def __init__(
        self,
        *,
        model_size: str = "small",
        model_path: Path | None = None,
        confidence_threshold: float = 0.3,
        input_resolution: int = 512,
        device: str = "auto",
        class_mapping: dict[str, str] | None = None,
        batch_size: int = 1,
        half_precision: bool = False,
        max_detections: int = 100,
        model_factory: Callable[..., Any] | None = None,
        inference_mode: str = "standard",
    ) -> None:
        if model_size not in {"small", "medium"}:
            raise ValueError(f"unsupported RF-DETR model size: {model_size}")
        if device not in {"auto", "cpu", "cuda"}:
            raise ValueError(f"unsupported RF-DETR device: {device}")
        if input_resolution < 320 or input_resolution % 32:
            raise ValueError("RF-DETR input_resolution must be at least 320 and divisible by 32")
        self.model_size = model_size
        self.model_path = Path(model_path) if model_path else None
        self.confidence_threshold = confidence_threshold
        self.input_resolution = input_resolution
        self.requested_device = device
        self.class_mapping = class_mapping or {"person": "person"}
        self.batch_size = batch_size
        self.half_precision_requested = half_precision
        self.max_detections = max_detections
        self._model_factory = model_factory
        self.inference_mode = inference_mode
        self._model: Any = None
        self._device = "unresolved"
        self._warnings: list[str] = []
        self._load_seconds = 0.0
        self._weights_sha256: str | None = None
        self._weights_size_bytes: int | None = None
        self._rfdetr_version = "unavailable"

    def _resolve_device(self, torch: Any) -> str:
        cuda_available = bool(torch.cuda.is_available())
        if self.requested_device == "cuda" and not cuda_available:
            self._warnings.append("CUDA requested but unavailable; RF-DETR CPU fallback used.")
            return "cpu"
        if self.requested_device == "auto":
            return "cuda" if cuda_available else "cpu"
        return self.requested_device

    def load(self) -> None:
        started = time.perf_counter()
        try:
            import torch
            from rfdetr import RFDETRMedium, RFDETRSmall
        except ImportError as exc:
            raise OptionalDependencyError(
                "RF-DETR dependencies are missing. Install research/vision_spike/requirements-rfdetr.txt "
                "inside a dedicated environment."
            ) from exc

        self._device = self._resolve_device(torch)
        try:
            self._rfdetr_version = importlib.metadata.version("rfdetr")
        except importlib.metadata.PackageNotFoundError:
            self._rfdetr_version = "unknown"

        factory = self._model_factory or (RFDETRSmall if self.model_size == "small" else RFDETRMedium)
        kwargs: dict[str, Any] = {
            "device": self._device,
            "resolution": self.input_resolution,
            "amp": bool(self.half_precision_requested and self._device == "cuda"),
        }
        if self.model_path is not None:
            if not self.model_path.is_file():
                raise FileNotFoundError(f"RF-DETR model weight not found: {self.model_path}")
            kwargs["pretrain_weights"] = str(self.model_path.resolve())
        self._model = factory(**kwargs)

        resolved_weight = self.model_path
        model_config = getattr(self._model, "model_config", None)
        if resolved_weight is None and model_config is not None:
            raw_path = getattr(model_config, "pretrain_weights", None)
            if raw_path:
                resolved_weight = Path(raw_path)
        if resolved_weight is not None and resolved_weight.is_file():
            self.model_path = resolved_weight.resolve()
            self._weights_sha256 = sha256_file(self.model_path)
            self._weights_size_bytes = self.model_path.stat().st_size
        self._load_seconds = time.perf_counter() - started

    def detect(self, frame: object, *, frame_index: int, timestamp_seconds: float) -> list[Detection]:
        if self._model is None:
            raise RuntimeError("RF-DETR detector is not loaded")
        original_height, original_width = frame.shape[:2]
        working, scale, offset_x, offset_y = letterbox_frame(frame, self.input_resolution)
        prediction = self._model.predict(
            working,
            threshold=self.confidence_threshold,
            shape=(self.input_resolution, self.input_resolution),
            include_source_image=False,
        )
        boxes = getattr(prediction, "xyxy", [])
        scores = getattr(prediction, "confidence", None)
        class_ids = getattr(prediction, "class_id", None)
        data = getattr(prediction, "data", {}) or {}
        class_names = data.get("class_name", [])
        candidates: list[tuple[float, int, str, tuple[float, float, float, float]]] = []
        for index, box in enumerate(boxes):
            score = float(scores[index]) if scores is not None else 0.0
            source_name = str(class_names[index]).strip().lower() if index < len(class_names) else "unknown"
            mapped_name = self.class_mapping.get(source_name)
            if mapped_name != "person":
                continue
            class_id = int(class_ids[index]) if class_ids is not None else -1
            coords = restore_letterbox_box(
                tuple(float(value) for value in box),
                scale=scale,
                offset_x=offset_x,
                offset_y=offset_y,
                original_width=original_width,
                original_height=original_height,
            )
            if coords[2] <= coords[0] or coords[3] <= coords[1]:
                continue
            candidates.append((score, class_id, source_name, coords))
        candidates.sort(key=lambda item: item[0], reverse=True)

        detections: list[Detection] = []
        for sequence, (score, class_id, source_name, coords) in enumerate(candidates[: self.max_detections]):
            detections.append(
                Detection(
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    class_id=class_id,
                    class_name="person",
                    confidence=round(score, 6),
                    bbox_xyxy=tuple(round(value, 2) for value in coords),
                    source_model=f"rfdetr-{self.model_size}-coco",
                    detection_id=f"f{frame_index}-rfdetr-person-{sequence}",
                    metadata={
                        "original_class": source_name,
                        "role": "unknown",
                        "generic_person_only": True,
                    },
                )
            )
        return detections

    def warmup(self) -> None:
        if self._model is None:
            raise RuntimeError("RF-DETR detector is not loaded")
        try:
            import numpy as np
        except ImportError as exc:
            raise OptionalDependencyError("NumPy is required for RF-DETR warmup") from exc
        sample = np.zeros((self.input_resolution, self.input_resolution, 3), dtype=np.uint8)
        self._model.predict(sample, threshold=0.99, include_source_image=False)

    def health_check(self) -> dict[str, Any]:
        return {
            "loaded": self._model is not None,
            "device": self._device,
            "weights_available": bool(self.model_path and self.model_path.is_file()),
            "warnings": list(self._warnings),
        }

    def close(self) -> None:
        self._model = None
        if self._device == "cuda":
            try:
                import torch

                torch.cuda.empty_cache()
            except (ImportError, RuntimeError):
                pass

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "rfdetr",
            "model": f"RF-DETR {self.model_size.title()} COCO",
            "model_size": self.model_size,
            "rfdetr_version": self._rfdetr_version,
            "repository": RFDETR_REPOSITORY,
            "code_license": RFDETR_LICENSE,
            "weights_license": RFDETR_LICENSE,
            "weights_source": RFDETR_WEIGHT_SOURCES[self.model_size],
            "weights_path": str(self.model_path) if self.model_path else None,
            "weights_sha256": self._weights_sha256,
            "weights_size_bytes": self._weights_size_bytes,
            "device": self._device,
            "requested_device": self.requested_device,
            "input_resolution": self.input_resolution,
            "inference_mode": self.inference_mode,
            "aspect_ratio_preserved": True,
            "batch_size": self.batch_size,
            "half_precision_requested": self.half_precision_requested,
            "half_precision_active": bool(self.half_precision_requested and self._device == "cuda"),
            "load_seconds": round(self._load_seconds, 4),
            "classes": ["person"],
            "ball_supported": False,
            "roles_supported": False,
            "football_specific_weights": "unavailable",
            "warnings": list(self._warnings),
        }
