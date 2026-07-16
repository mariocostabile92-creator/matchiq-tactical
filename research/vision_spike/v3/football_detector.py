from __future__ import annotations

from pathlib import Path
from typing import Any

from ..contracts import Detection
from ..inference_modes import letterbox_frame, restore_letterbox_box
from ..rfdetr_detector import RFDETRDetector
from . import CATEGORY_IDS, CLASS_NAMES


class FootballRFDETRDetector(RFDETRDetector):
    """RF-DETR adapter for an approved four-class V3 football checkpoint."""

    def __init__(self, *, model_path: Path, **settings: Any) -> None:
        super().__init__(model_size="small", model_path=model_path, class_mapping={}, **settings)

    def detect(self, frame: object, *, frame_index: int, timestamp_seconds: float) -> list[Detection]:
        if self._model is None:
            raise RuntimeError("RF-DETR football detector is not loaded")
        original_height, original_width = frame.shape[:2]
        working, scale, offset_x, offset_y = letterbox_frame(frame, self.input_resolution)
        prediction = self._model.predict(
            working, threshold=self.confidence_threshold,
            shape=(self.input_resolution, self.input_resolution), include_source_image=False,
        )
        boxes = getattr(prediction, "xyxy", [])
        scores = getattr(prediction, "confidence", None)
        data = getattr(prediction, "data", {}) or {}
        class_names = data.get("class_name", [])
        class_ids = getattr(prediction, "class_id", None)
        rows = []
        for index, box in enumerate(boxes):
            source_name = str(class_names[index]).strip().lower() if index < len(class_names) else "unknown"
            raw_id = int(class_ids[index]) if class_ids is not None else -1
            class_name = source_name if source_name in CLASS_NAMES else (CLASS_NAMES[raw_id] if 0 <= raw_id < len(CLASS_NAMES) else "")
            if class_name not in CLASS_NAMES:
                continue
            coords = restore_letterbox_box(
                tuple(float(value) for value in box), scale=scale, offset_x=offset_x, offset_y=offset_y,
                original_width=original_width, original_height=original_height,
            )
            if coords[2] <= coords[0] or coords[3] <= coords[1]:
                continue
            score = float(scores[index]) if scores is not None else 0.0
            rows.append((score, class_name, coords))
        rows.sort(reverse=True, key=lambda item: item[0])
        return [
            Detection(
                frame_index=frame_index, timestamp_seconds=timestamp_seconds,
                class_id=CATEGORY_IDS[name], class_name=name, confidence=round(score, 6),
                bbox_xyxy=tuple(round(value, 2) for value in box),
                source_model="rfdetr-small-football-v3", detection_id=f"f{frame_index}-v3-{name}-{sequence}",
                metadata={"football_specific": True},
            )
            for sequence, (score, name, box) in enumerate(rows[: self.max_detections])
        ]

    def metadata(self) -> dict[str, Any]:
        metadata = super().metadata()
        metadata.update(
            model="RF-DETR Small Football V3", classes=list(CLASS_NAMES), ball_supported=True,
            roles_supported=True, football_specific_weights="local-approved-checkpoint",
        )
        return metadata
