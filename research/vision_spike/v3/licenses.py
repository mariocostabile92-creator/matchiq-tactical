from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DatasetSource:
    source_id: str
    name: str
    author: str
    origin: str
    license_name: str
    license_url: str
    modification_allowed: bool
    commercial_use_allowed: bool
    commercial_weight_training_allowed: bool
    redistribution_allowed: bool
    attribution_required: bool
    authorization_reference: str
    media_types: tuple[str, ...]
    annotation_quality: str
    classes: tuple[str, ...]
    image_count: int
    camera_types: tuple[str, ...]
    matchiq_relevance: str
    status: str
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetSource":
        tuple_fields = {"media_types", "classes", "camera_types"}
        normalized = {
            key: tuple(value) if key in tuple_fields else value
            for key, value in payload.items()
        }
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for field in ("media_types", "classes", "camera_types"):
            payload[field] = list(payload[field])
        return payload

    @property
    def approved_for_v3(self) -> bool:
        return all(
            (
                self.status == "approved",
                self.modification_allowed,
                self.commercial_use_allowed,
                self.commercial_weight_training_allowed,
                bool(self.authorization_reference.strip()),
                bool(self.license_name.strip()),
            )
        )


def load_source_registry(path: Path) -> list[DatasetSource]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("sources", payload if isinstance(payload, list) else [])
    if not isinstance(rows, list):
        raise ValueError("source registry must contain a 'sources' list")
    return [DatasetSource.from_dict(item) for item in rows]


def source_index(sources: list[DatasetSource]) -> dict[str, DatasetSource]:
    result: dict[str, DatasetSource] = {}
    for source in sources:
        if source.source_id in result:
            raise ValueError(f"duplicate dataset source_id: {source.source_id}")
        result[source.source_id] = source
    return result


def write_source_registry(path: Path, sources: list[DatasetSource]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": 1, "sources": [item.to_dict() for item in sources]}, indent=2),
        encoding="utf-8",
    )
