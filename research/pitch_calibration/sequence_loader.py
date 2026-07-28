from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import cv2

from .contracts import CalibrationFrame


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm"}


def load_source(
    source: Path,
    *,
    sample_interval_seconds: float,
    maximum_frames: int | None = None,
    extracted_frames_dir: Path | None = None,
) -> tuple[list[CalibrationFrame], dict[str, Any]]:
    source = Path(source).resolve()
    if not source.exists():
        raise ValueError(f"source does not exist: {source}")
    if source.is_dir():
        return _load_image_directory(source, maximum_frames)
    if source.suffix.lower() in IMAGE_SUFFIXES:
        return [_frame_from_image(source, 0)], _source_meta("image", source, 1)
    if source.suffix.lower() in VIDEO_SUFFIXES:
        if extracted_frames_dir is None:
            raise ValueError("extracted_frames_dir is required for video input")
        frames = _sample_video(
            source,
            extracted_frames_dir,
            sample_interval_seconds=sample_interval_seconds,
            maximum_frames=maximum_frames,
        )
        return frames, _source_meta("video", source, len(frames))
    if source.suffix.lower() == ".json":
        return _load_manifest(source, maximum_frames)
    raise ValueError(f"unsupported source type: {source.suffix}")


def _source_meta(kind: str, source: Path, frames: int) -> dict[str, Any]:
    return {"kind": kind, "path": str(source), "frames": frames}


def _frame_from_image(
    image_path: Path,
    sequence_index: int,
    *,
    frame_index: int | None = None,
    timestamp_seconds: float | None = None,
    source_manifest: Path | None = None,
    source: dict[str, Any] | None = None,
    observations: Iterable[dict[str, Any]] = (),
) -> CalibrationFrame:
    return CalibrationFrame(
        sequence_index=sequence_index,
        frame_id=f"frame_{sequence_index + 1:06d}",
        frame_index=sequence_index if frame_index is None else frame_index,
        timestamp_seconds=float(sequence_index if timestamp_seconds is None else timestamp_seconds),
        image_path=image_path.resolve(),
        source_manifest=source_manifest.resolve() if source_manifest else None,
        source=dict(source or {}),
        observations=tuple(dict(item) for item in observations),
    )


def _load_image_directory(
    directory: Path,
    maximum_frames: int | None,
) -> tuple[list[CalibrationFrame], dict[str, Any]]:
    paths = sorted(path for path in directory.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    if maximum_frames is not None:
        paths = paths[:maximum_frames]
    if not paths:
        raise ValueError(f"no supported images found in {directory}")
    frames = [_frame_from_image(path, index) for index, path in enumerate(paths)]
    return frames, _source_meta("image_directory", directory, len(frames))


def _sample_video(
    video_path: Path,
    output_dir: Path,
    *,
    sample_interval_seconds: float,
    maximum_frames: int | None,
) -> list[CalibrationFrame]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open video: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or total <= 0:
        capture.release()
        raise ValueError("video metadata is invalid")
    step = max(1, round(sample_interval_seconds * fps))
    output_dir.mkdir(parents=True, exist_ok=True)
    frames: list[CalibrationFrame] = []
    source_index = 0
    try:
        while source_index < total:
            if maximum_frames is not None and len(frames) >= maximum_frames:
                break
            capture.set(cv2.CAP_PROP_POS_FRAMES, source_index)
            ok, image = capture.read()
            if not ok:
                break
            target = output_dir / f"frame_{source_index:08d}.jpg"
            if not cv2.imwrite(str(target), image):
                raise RuntimeError(f"cannot write sampled frame: {target}")
            frames.append(
                _frame_from_image(
                    target,
                    len(frames),
                    frame_index=source_index,
                    timestamp_seconds=source_index / fps,
                    source={"video_path": str(video_path), "fps": fps},
                )
            )
            source_index += step
    finally:
        capture.release()
    if not frames:
        raise ValueError("video sampling produced no frames")
    return frames


def _load_manifest(
    manifest_path: Path,
    maximum_frames: int | None,
) -> tuple[list[CalibrationFrame], dict[str, Any]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must contain a JSON object")
    schema = str(payload.get("schema_version", ""))
    if schema.startswith("matchiq.ve-004"):
        frames = _load_ve004_manifest(payload, manifest_path)
        kind = "ve004_manifest"
    elif schema.startswith("matchiq.ve-003"):
        frames = _load_ve003_manifest(payload, manifest_path)
        kind = "ve003_manifest"
    else:
        raise ValueError(f"unsupported manifest schema: {schema or 'missing'}")
    if maximum_frames is not None:
        frames = frames[:maximum_frames]
    if not frames:
        raise ValueError("manifest contains no usable frames")
    return frames, {
        "kind": kind,
        "path": str(manifest_path),
        "schema_version": schema,
        "frames": len(frames),
    }


def _load_ve004_manifest(
    payload: dict[str, Any],
    manifest_path: Path,
) -> list[CalibrationFrame]:
    observations_by_sequence: dict[int, list[dict[str, Any]]] = {}
    for item in payload.get("observations", []):
        if not isinstance(item, dict):
            continue
        observations_by_sequence.setdefault(int(item.get("sequence_index", -1)), []).append(item)
    frames: list[CalibrationFrame] = []
    for sequence_index, item in enumerate(payload.get("frames", [])):
        if not isinstance(item, dict):
            continue
        image_path = _resolve_path(item.get("source_image"), manifest_path.parent)
        if image_path is None or not image_path.exists():
            continue
        frame_sequence_index = int(item.get("sequence_index", sequence_index))
        frames.append(
            _frame_from_image(
                image_path,
                frame_sequence_index,
                frame_index=int(item.get("frame_index", frame_sequence_index)),
                timestamp_seconds=float(item.get("timestamp_seconds", frame_sequence_index)),
                source_manifest=manifest_path,
                source=item,
                observations=observations_by_sequence.get(frame_sequence_index, ()),
            )
        )
    return frames


def _load_ve003_manifest(
    payload: dict[str, Any],
    manifest_path: Path,
) -> list[CalibrationFrame]:
    if "files" not in payload:
        source = payload.get("source") or {}
        image_path = _resolve_path(source.get("path"), manifest_path.parent)
        if image_path is None or not image_path.exists():
            return []
        return [
            _frame_from_image(
                image_path,
                0,
                frame_index=int(source.get("frame_index", 0)),
                timestamp_seconds=float(source.get("timestamp_seconds", 0.0)),
                source_manifest=manifest_path,
                source=source,
                observations=payload.get("detections", ()),
            )
        ]
    frames: list[CalibrationFrame] = []
    for sequence_index, entry in enumerate(payload.get("files", [])):
        if not isinstance(entry, dict) or entry.get("status") != "success":
            continue
        report_path = _resolve_path(entry.get("json_report"), manifest_path.parent)
        if report_path is None or not report_path.exists():
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        source = report.get("source") or {}
        image_path = _resolve_path(source.get("path"), report_path.parent)
        if image_path is None or not image_path.exists():
            continue
        frames.append(
            _frame_from_image(
                image_path,
                sequence_index,
                frame_index=int(source.get("frame_index", sequence_index)),
                timestamp_seconds=float(source.get("timestamp_seconds", sequence_index)),
                source_manifest=manifest_path,
                source=source,
                observations=report.get("detections", ()),
            )
        )
    return frames


def _resolve_path(value: Any, parent: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = parent / path
    return path.resolve()
