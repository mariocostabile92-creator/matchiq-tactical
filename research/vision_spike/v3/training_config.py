from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import CLASS_NAMES


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    source_path: Path
    values: dict[str, Any]

    @property
    def class_names(self) -> tuple[str, ...]:
        return tuple(str(item) for item in self.values["class_names"])

    @property
    def seed(self) -> int:
        return int(self.values["seed"])

    def resolved_dataset_path(self, override: Path | None = None) -> Path:
        if override is not None:
            return override.expanduser().resolve()
        raw = str(self.values["dataset_path"])
        if raw == "${MATCHIQ_V3_DATASET}":
            raw = os.getenv("MATCHIQ_V3_DATASET", "")
        if not raw:
            raise ValueError("dataset path missing; set MATCHIQ_V3_DATASET or pass --dataset")
        return Path(raw).expanduser().resolve()


REQUIRED_FIELDS = {
    "base_model", "class_names", "dataset_path", "train_split", "val_split", "test_split",
    "image_size", "batch_size", "gradient_accumulation", "learning_rate", "epochs", "warmup_epochs",
    "weight_decay", "augmentations", "seed", "device", "workers", "early_stopping",
    "checkpoint_directory", "mixed_precision", "evaluation_interval", "minimums",
}


def load_training_config(path: Path) -> TrainingConfig:
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"training config must be JSON-compatible YAML: {exc.msg}") from exc
    missing = REQUIRED_FIELDS - set(values)
    if missing:
        raise ValueError(f"training config missing fields: {', '.join(sorted(missing))}")
    if tuple(values["class_names"]) != CLASS_NAMES:
        raise ValueError(f"class_names must be exactly {CLASS_NAMES}")
    if int(values["image_size"]) < 256 or int(values["batch_size"]) < 1:
        raise ValueError("image_size and batch_size are invalid")
    if int(values["epochs"]) < 1 or float(values["learning_rate"]) <= 0:
        raise ValueError("epochs and learning_rate must be positive")
    augmentations = values["augmentations"]
    rotation = augmentations.get("Rotate", {})
    limit = rotation.get("limit", 0) if isinstance(rotation, dict) else 0
    if augmentations.get("VerticalFlip") or (isinstance(limit, (int, float)) and abs(limit) > 15):
        raise ValueError("unrealistic football augmentations are forbidden")
    return TrainingConfig(path.resolve(), values)
