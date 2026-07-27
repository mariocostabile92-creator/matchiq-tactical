from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RawPlayerDetection:
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    source_model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PlayerDetector(ABC):
    """Minimal adapter contract for an isolated player detector."""

    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def detect(self, image: object) -> list[RawPlayerDetection]:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        raise NotImplementedError

    def close(self) -> None:
        """Release optional model resources."""
