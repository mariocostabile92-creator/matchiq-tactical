from __future__ import annotations

from pathlib import Path
from typing import Any


def render_debug_image(
    image: object,
    detections: list[dict[str, Any]],
    output_path: Path,
    *,
    backend: str,
) -> Path:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to render VE-002 debug images") from exc

    canvas = image.copy()
    for detection in detections:
        x1, y1, x2, y2 = (int(round(value)) for value in detection["bbox_xyxy"])
        foot_x, foot_y = (int(round(value)) for value in detection["foot_point_xy"])
        label = f"{detection['detection_id']} {detection['confidence']:.2f}"
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (40, 220, 90), 2)
        cv2.circle(canvas, (foot_x, foot_y), 4, (40, 80, 255), -1)
        label_y = max(18, y1 - 7)
        cv2.putText(
            canvas,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (8, 35, 18),
            1,
            cv2.LINE_AA,
        )
    cv2.putText(
        canvas,
        f"{backend} | person candidates: {len(detections)}",
        (14, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), canvas):
        raise OSError(f"unable to write debug image: {output_path}")
    return output_path
