from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .utils import require_cv2_numpy


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    path: str
    duration_seconds: float
    fps: float
    width: int
    height: int
    frame_count: int


@dataclass(slots=True)
class VideoFrame:
    frame_index: int
    timestamp_seconds: float
    image: object


class LocalVideoReader:
    def __init__(
        self,
        path: Path,
        *,
        frame_stride: int = 1,
        start_seconds: float = 0.0,
        max_seconds: float | None = None,
        max_frames: int | None = None,
    ) -> None:
        if frame_stride < 1:
            raise ValueError("frame_stride must be at least 1")
        self.path = Path(path)
        self.frame_stride = frame_stride
        self.start_seconds = max(0.0, float(start_seconds))
        self.max_seconds = max_seconds
        self.max_frames = max_frames
        self._capture = None
        self._metadata: VideoMetadata | None = None

    def open(self) -> VideoMetadata:
        if not self.path.exists():
            raise ValueError(f"video not found: {self.path}")
        cv2, _ = require_cv2_numpy()
        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            capture.release()
            raise ValueError(f"video cannot be opened: {self.path}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or width <= 0 or height <= 0:
            capture.release()
            raise ValueError("video metadata is invalid or codec is unsupported")
        duration = frame_count / fps if frame_count > 0 else 0.0
        if self.start_seconds >= duration and duration > 0:
            capture.release()
            raise ValueError("start_seconds is outside the video duration")
        capture.set(cv2.CAP_PROP_POS_MSEC, self.start_seconds * 1000.0)
        self._capture = capture
        self._metadata = VideoMetadata(
            path=str(self.path.resolve()),
            duration_seconds=duration,
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
        )
        return self._metadata

    @property
    def metadata(self) -> VideoMetadata:
        if self._metadata is None:
            raise RuntimeError("video reader is not open")
        return self._metadata

    def frames(self) -> Iterator[VideoFrame]:
        if self._capture is None:
            self.open()
        cv2, _ = require_cv2_numpy()
        capture = self._capture
        assert capture is not None
        fps = self.metadata.fps
        start_frame = int(round(self.start_seconds * fps))
        source_index = max(start_frame, int(capture.get(cv2.CAP_PROP_POS_FRAMES)))
        yielded = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            timestamp = source_index / fps
            elapsed = timestamp - self.start_seconds
            if self.max_seconds is not None and elapsed > self.max_seconds + (0.5 / fps):
                break
            relative_index = source_index - start_frame
            if relative_index % self.frame_stride == 0:
                yield VideoFrame(source_index, round(timestamp, 6), frame)
                yielded += 1
                if self.max_frames is not None and yielded >= self.max_frames:
                    break
            source_index += 1

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "LocalVideoReader":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
