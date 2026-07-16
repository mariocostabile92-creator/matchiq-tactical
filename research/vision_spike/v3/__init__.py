"""Isolated football-specific dataset and fine-tuning research tools."""

from __future__ import annotations

DATASET_VERSION = "matchiq-football-detection-v3.0"
CLASS_NAMES = ("player", "goalkeeper", "referee", "ball")
CATEGORY_IDS = {name: index + 1 for index, name in enumerate(CLASS_NAMES)}
TRAINING_STATUS_NOT_READY = "DATASET_NOT_READY"

__all__ = [
    "CATEGORY_IDS",
    "CLASS_NAMES",
    "DATASET_VERSION",
    "TRAINING_STATUS_NOT_READY",
]
