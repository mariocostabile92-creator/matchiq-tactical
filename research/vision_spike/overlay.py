from __future__ import annotations

from pathlib import Path

from .contracts import Detection, Track
from .utils import require_cv2_numpy


TEAM_COLORS = {
    "team_a": (40, 220, 40),
    "team_b": (255, 140, 30),
    "unknown": (40, 210, 255),
}


def format_timestamp(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def draw_overlay(
    frame: object,
    *,
    detections: list[Detection],
    tracks: list[Track],
    frame_index: int,
    timestamp_seconds: float,
    processing_fps: float,
    pitch_visible: bool,
    green_ratio: float,
) -> object:
    cv2, _ = require_cv2_numpy()
    canvas = frame.copy()
    tracked_ids = {track.track_id for track in tracks}
    for track in tracks:
        team = track.team_id or "unknown"
        color = TEAM_COLORS.get(team, TEAM_COLORS["unknown"])
        x1, y1, x2, y2 = [int(round(value)) for value in track.bbox_xyxy]
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        label = f"person T{track.track_id} {team} {track.confidence:.2f}"
        _draw_label(canvas, label, x1, y1, color)
    if not tracked_ids:
        for detection in detections:
            team = detection.metadata.get("team_id", "unknown")
            color = TEAM_COLORS.get(team, TEAM_COLORS["unknown"])
            x1, y1, x2, y2 = [int(round(value)) for value in detection.bbox_xyxy]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
            _draw_label(canvas, f"{detection.class_name} {detection.confidence:.2f}", x1, y1, color)
    header = (
        f"MatchIQ Vision Spike | {format_timestamp(timestamp_seconds)} | frame {frame_index} | "
        f"proc {processing_fps:.2f} FPS | pitch {'yes' if pitch_visible else 'no'} ({green_ratio:.2f})"
    )
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 42), (8, 15, 28), -1)
    cv2.putText(canvas, header, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (245, 248, 252), 2, cv2.LINE_AA)
    legend_x = max(10, canvas.shape[1] - 360)
    for offset, (team, color) in enumerate(TEAM_COLORS.items()):
        x = legend_x + (offset * 115)
        cv2.rectangle(canvas, (x, canvas.shape[0] - 28), (x + 16, canvas.shape[0] - 12), color, -1)
        cv2.putText(canvas, team, (x + 22, canvas.shape[0] - 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


def _draw_label(frame: object, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2, _ = require_cv2_numpy()
    (width, height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    top = max(42, y - height - 10)
    cv2.rectangle(frame, (x, top), (x + width + 8, top + height + 8), (8, 15, 28), -1)
    cv2.putText(frame, text, (x + 4, top + height + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


class VideoOverlayWriter:
    def __init__(self, path: Path, *, width: int, height: int, fps: float) -> None:
        cv2, _ = require_cv2_numpy()
        path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.path = path
        self._writer = cv2.VideoWriter(str(path), fourcc, max(0.1, fps), (width, height))
        if not self._writer.isOpened():
            self._writer.release()
            raise ValueError(f"cannot create overlay video: {path}")

    def write(self, frame: object) -> None:
        self._writer.write(frame)

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
