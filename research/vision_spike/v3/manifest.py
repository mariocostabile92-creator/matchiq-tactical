from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class FrameRecord:
    frame_id: str
    file_name: str
    video_id: str
    source_id: str
    source_file_name: str
    source_sha256: str
    frame_sha256: str
    timestamp_seconds: float
    frame_index: int
    width: int
    height: int
    source_fps: float
    camera_type: str
    quality: str
    lighting: str
    authorization_origin: str
    split: str
    blur_score: float
    mean_luma: float
    green_ratio: float
    tactical_view_score: float
    is_negative: bool = False
    match_id: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FrameRecord":
        fields = cls.__dataclass_fields__
        return cls(**{key: payload[key] for key in fields if key in payload})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path.name}:{line_number}: {exc.msg}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"invalid JSONL row at {path.name}:{line_number}: object required")
            rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def append_unique_records(path: Path, records: Iterable[FrameRecord]) -> int:
    existing = read_jsonl(path)
    seen = {str(item.get("frame_id", "")) for item in existing}
    added = 0
    for record in records:
        if record.frame_id in seen:
            continue
        existing.append(record.to_dict())
        seen.add(record.frame_id)
        added += 1
    write_jsonl(path, existing)
    return added
