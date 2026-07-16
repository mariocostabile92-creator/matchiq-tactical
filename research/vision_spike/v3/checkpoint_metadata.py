from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checkpoint_metadata(path: Path, *, checkpoint: Path, values: dict[str, Any]) -> dict[str, Any]:
    payload = dict(values)
    payload.update(
        checkpoint_file=checkpoint.name,
        checkpoint_sha256=sha256_path(checkpoint),
        checkpoint_bytes=checkpoint.stat().st_size,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
