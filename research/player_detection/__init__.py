"""VE-002 isolated player-detection research layer."""

SCHEMA_VERSION = "matchiq.ve-002.player-detection.v1"

from .contracts import PlayerDetector, RawPlayerDetection
from .runner import PlayerDetectionConfig, PlayerDetectionRun, PlayerDetectionRunner

__all__ = [
    "PlayerDetectionConfig",
    "PlayerDetectionRun",
    "PlayerDetectionRunner",
    "PlayerDetector",
    "RawPlayerDetection",
    "SCHEMA_VERSION",
]
