from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import TEAM_A, TEAM_B


TEAM_COLORS = {
    TEAM_A: (42, 84, 240),
    TEAM_B: (235, 170, 35),
    "UNKNOWN": (145, 145, 145),
}


def render_team_debug_image(
    image: object,
    detections: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required by VE-003") from exc

    canvas = image.copy()
    for detection in detections:
        team = str(detection.get("team_assignment", "UNKNOWN"))
        color = TEAM_COLORS.get(team, TEAM_COLORS["UNKNOWN"])
        x1, y1, x2, y2 = (int(round(float(value))) for value in detection["bbox_xyxy"])
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)

        roi = detection.get("roi_used") or {}
        roi_bbox = roi.get("bbox_xyxy")
        if roi_bbox:
            rx1, ry1, rx2, ry2 = (int(value) for value in roi_bbox)
            cv2.rectangle(canvas, (rx1, ry1), (rx2, ry2), (45, 220, 245), 1)

        confidence = float(detection.get("team_confidence", 0.0))
        label = f"{team} {confidence:.2f}"
        (text_width, text_height), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            1,
        )
        top = max(0, y1 - text_height - 10)
        cv2.rectangle(canvas, (x1, top), (x1 + text_width + 8, y1), color, -1)
        cv2.putText(
            canvas,
            label,
            (x1 + 4, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    counts = {
        team: sum(1 for detection in detections if detection.get("team_assignment") == team)
        for team in (TEAM_A, TEAM_B, "UNKNOWN")
    }
    summary = f"VE-003  A:{counts[TEAM_A]}  B:{counts[TEAM_B]}  UNKNOWN:{counts['UNKNOWN']}"
    cv2.rectangle(canvas, (8, 8), (455, 42), (7, 15, 31), -1)
    cv2.putText(
        canvas,
        summary,
        (18, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), canvas):
        raise OSError(f"could not write debug image: {output_path}")
    return output_path

