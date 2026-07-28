from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


TEAM_A = "TEAM_A"
TEAM_B = "TEAM_B"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class TeamAssignmentConfig:
    output_dir: Path
    minimum_team_confidence: float = 0.20
    minimum_cluster_separation: float = 0.18
    torso_x_start: float = 0.20
    torso_x_end: float = 0.80
    torso_y_start: float = 0.18
    torso_y_end: float = 0.58


@dataclass(frozen=True, slots=True)
class ColorSample:
    sample_id: str
    feature: tuple[float, ...]
    quality: float


@dataclass(frozen=True, slots=True)
class ClusterAssignment:
    team_assignment: str
    team_confidence: float
    cluster_id: int | None
    reason: str


@dataclass(frozen=True, slots=True)
class TeamAssignmentRun:
    manifest_path: Path
    html_path: Path
    manifest: dict[str, Any]
