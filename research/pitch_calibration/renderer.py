from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from .projection import as_homography, invert_homography, project_point


TEAM_COLORS = {
    "TEAM_A": (0, 220, 120),
    "TEAM_B": (255, 150, 30),
    "UNKNOWN": (160, 160, 160),
}


def render_diagnostic(
    image_path: Path,
    output_path: Path,
    *,
    homography_image_to_pitch: Any | None,
    observations: Iterable[dict[str, Any]],
    detected_field_elements: Iterable[dict[str, Any]] = (),
    status: str,
    confidence: float,
    flags: Iterable[str],
    pitch_length: float,
    pitch_width: float,
) -> Path:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"cannot read image: {image_path}")
    canvas = image.copy()
    if homography_image_to_pitch is not None:
        _draw_pitch_reprojection(
            canvas,
            homography_image_to_pitch,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
        )
    _draw_detected_field_elements(canvas, detected_field_elements)
    for observation in observations:
        point = observation.get("foot_point_xy")
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            continue
        color = TEAM_COLORS.get(str(observation.get("team_assignment")), TEAM_COLORS["UNKNOWN"])
        cv2.circle(canvas, (round(point[0]), round(point[1])), 5, color, -1, cv2.LINE_AA)
        label = str(observation.get("track_id") or observation.get("source_detection_id") or "")
        if label:
            cv2.putText(
                canvas,
                label,
                (round(point[0]) + 7, round(point[1]) - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                color,
                1,
                cv2.LINE_AA,
            )
    overlay = f"{status} | confidence {confidence:.2f}"
    cv2.rectangle(canvas, (10, 10), (min(canvas.shape[1] - 10, 520), 70), (5, 16, 32), -1)
    cv2.putText(canvas, overlay, (22, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.64, (255, 255, 255), 2)
    flag_text = ", ".join(flags) or "no quality flags"
    cv2.putText(
        canvas,
        flag_text[:90],
        (22, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (190, 220, 245),
        1,
        cv2.LINE_AA,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), canvas):
        raise RuntimeError(f"cannot write diagnostic image: {output_path}")
    return output_path


def _draw_detected_field_elements(
    image: np.ndarray,
    elements: Iterable[dict[str, Any]],
) -> None:
    for element in elements:
        points = element.get("points") or element.get("polyline")
        if not isinstance(points, list) or len(points) < 2:
            continue
        array = np.asarray(points, dtype=np.float32)
        if array.ndim != 2 or array.shape[1] != 2 or not np.isfinite(array).all():
            continue
        cv2.polylines(
            image,
            [np.rint(array).astype(np.int32)],
            False,
            (255, 90, 210),
            2,
            cv2.LINE_AA,
        )


def render_minimap(
    output_path: Path,
    projected: Iterable[dict[str, Any]],
    *,
    pitch_length: float,
    pitch_width: float,
) -> Path:
    width, height, margin = 840, 544, 30
    canvas = np.full((height + 2 * margin, width + 2 * margin, 3), (24, 92, 55), np.uint8)
    white = (235, 245, 238)
    cv2.rectangle(canvas, (margin, margin), (margin + width, margin + height), white, 2)
    cv2.line(
        canvas,
        (margin + width // 2, margin),
        (margin + width // 2, margin + height),
        white,
        2,
    )
    cv2.circle(canvas, (margin + width // 2, margin + height // 2), 65, white, 2)
    for item in projected:
        normalized = item.get("canonical_normalized")
        if not isinstance(normalized, list) or len(normalized) != 2:
            continue
        x = margin + round(normalized[0] * width)
        y = margin + round(normalized[1] * height)
        color = TEAM_COLORS.get(str(item.get("team_assignment")), TEAM_COLORS["UNKNOWN"])
        cv2.circle(canvas, (x, y), 7, color, -1, cv2.LINE_AA)
        label = str(item.get("track_id") or "")
        if label:
            cv2.putText(canvas, label, (x + 8, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, white, 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), canvas):
        raise RuntimeError(f"cannot write minimap: {output_path}")
    return output_path


def _draw_pitch_reprojection(
    image: np.ndarray,
    image_to_pitch: Any,
    *,
    pitch_length: float,
    pitch_width: float,
) -> None:
    try:
        pitch_to_image = invert_homography(image_to_pitch)
    except ValueError:
        return
    lines = [
        ((0.0, 0.0), (pitch_length, 0.0)),
        ((pitch_length, 0.0), (pitch_length, pitch_width)),
        ((pitch_length, pitch_width), (0.0, pitch_width)),
        ((0.0, pitch_width), (0.0, 0.0)),
        ((pitch_length / 2, 0.0), (pitch_length / 2, pitch_width)),
    ]
    for start, end in lines:
        p1 = project_point(pitch_to_image, start)
        p2 = project_point(pitch_to_image, end)
        if p1 is None or p2 is None:
            continue
        cv2.line(
            image,
            (round(p1[0]), round(p1[1])),
            (round(p2[0]), round(p2[1])),
            (30, 230, 255),
            2,
            cv2.LINE_AA,
        )
