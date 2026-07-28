from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .contracts import SequenceFrame


_FRAME_PATTERN = re.compile(r"(?:frame|f)[_-]?(\d+)", re.IGNORECASE)
_TIME_PATTERN = re.compile(r"(?:time|t)[_-]?(\d+)(?:ms)?", re.IGNORECASE)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _require_ve003(payload: dict[str, Any], path: Path) -> None:
    schema = str(payload.get("schema_version", ""))
    if not schema.startswith("matchiq.ve-003.team-assignment."):
        raise ValueError(f"{path} is not a VE-003 team assignment report")


def _resolve_report_paths(source: Path) -> tuple[list[Path], Path | None]:
    source = source.resolve()
    if source.is_dir():
        paths = sorted(
            path
            for path in source.rglob("*.json")
            if path.name != "team_assignment_manifest.json"
        )
        return paths, None

    payload = _load_json(source)
    _require_ve003(payload, source)
    if "files" not in payload:
        return [source], None

    paths: list[Path] = []
    for entry in payload.get("files", []):
        if entry.get("status") != "success":
            continue
        report = Path(str(entry.get("json_report", "")))
        if not report.is_absolute():
            report = source.parent / report
        paths.append(report.resolve())
    return paths, source


def _parse_filename_timing(path: Path) -> tuple[int | None, float | None]:
    frame_match = _FRAME_PATTERN.search(path.stem)
    time_match = _TIME_PATTERN.search(path.stem)
    frame_index = int(frame_match.group(1)) if frame_match else None
    timestamp = int(time_match.group(1)) / 1000.0 if time_match else None
    return frame_index, timestamp


def load_sequence(source: Path, *, fps: float) -> tuple[list[SequenceFrame], dict[str, Any]]:
    if fps <= 0:
        raise ValueError("fps must be positive")
    report_paths, aggregate_manifest = _resolve_report_paths(Path(source))
    if not report_paths:
        raise ValueError("no VE-003 per-frame reports found")

    frames: list[SequenceFrame] = []
    timing_modes: set[str] = set()
    for sequence_index, report_path in enumerate(report_paths):
        payload = _load_json(report_path)
        _require_ve003(payload, report_path)
        if "files" in payload:
            raise ValueError("nested VE-003 aggregate manifests are not supported")

        source_meta = payload.get("source")
        if not isinstance(source_meta, dict):
            raise ValueError(f"{report_path} has no source metadata")
        image_path = Path(str(source_meta.get("path", "")))
        if not image_path.is_absolute():
            image_path = report_path.parent / image_path
        image_path = image_path.resolve()
        if not image_path.exists():
            raise ValueError(f"source image does not exist: {image_path}")

        filename_frame, filename_time = _parse_filename_timing(image_path)
        if source_meta.get("frame_index") is not None:
            frame_index = int(source_meta["frame_index"])
            timing_source = "source_metadata"
        elif filename_frame is not None:
            frame_index = filename_frame
            timing_source = "filename"
        else:
            frame_index = sequence_index
            timing_source = "explicit_uniform_fps"

        if source_meta.get("timestamp_seconds") is not None:
            timestamp = float(source_meta["timestamp_seconds"])
            timing_source = "source_metadata"
        elif source_meta.get("timestamp_ms") is not None:
            timestamp = float(source_meta["timestamp_ms"]) / 1000.0
            timing_source = "source_metadata"
        elif filename_time is not None:
            timestamp = filename_time
            timing_source = "filename"
        else:
            timestamp = sequence_index / fps
            if timing_source != "source_metadata":
                timing_source = "explicit_uniform_fps"

        segment_id = str(source_meta.get("segment_id", "segment_001"))
        detections = payload.get("detections", [])
        if not isinstance(detections, list):
            raise ValueError(f"{report_path} detections must be an array")
        frames.append(SequenceFrame(
            sequence_index=sequence_index,
            frame_index=frame_index,
            timestamp_seconds=timestamp,
            segment_id=segment_id,
            image_path=image_path,
            source_report_path=report_path.resolve(),
            source=dict(source_meta),
            detections=tuple(dict(item) for item in detections if isinstance(item, dict)),
            timing_source=timing_source,
        ))
        timing_modes.add(timing_source)

    return frames, {
        "source": str(Path(source).resolve()),
        "source_aggregate_manifest": str(aggregate_manifest) if aggregate_manifest else None,
        "frames": len(frames),
        "fps": fps,
        "timing_modes": sorted(timing_modes),
        "uniform_timing_was_explicit": "explicit_uniform_fps" in timing_modes,
    }
