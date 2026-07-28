from __future__ import annotations

from pathlib import Path
from typing import Any


_TEAM_COLORS = {
    "TEAM_A": (40, 220, 80),
    "TEAM_B": (255, 130, 40),
    "UNKNOWN": (180, 180, 180),
}


def render_tracking_debug(
    image_path: Path,
    observations: list[dict[str, Any]],
    trajectories: dict[str, list[tuple[int, int]]],
    output_path: Path,
) -> Path:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to render VE-004B debug images") from exc

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read debug source image: {image_path}")

    for observation in observations:
        x1, y1, x2, y2 = (int(round(value)) for value in observation["bbox_xyxy"])
        team = str(observation.get("team_assignment", "UNKNOWN"))
        color = _TEAM_COLORS.get(team, _TEAM_COLORS["UNKNOWN"])
        track_id = str(observation["track_id"])
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        label = f"{track_id} {team}"
        cv2.putText(
            image,
            label,
            (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            color,
            2,
            cv2.LINE_AA,
        )

        points = trajectories.get(track_id, [])
        if len(points) >= 2:
            for start, end in zip(points[:-1], points[1:]):
                cv2.line(image, start, end, color, 1, cv2.LINE_AA)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), image):
        raise RuntimeError(f"cannot write debug image: {output_path}")
    return output_path
