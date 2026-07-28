from __future__ import annotations

from dataclasses import dataclass

from .line_detection import ImageSegment, all_intersections


@dataclass(frozen=True, slots=True)
class ImageKeypoint:
    keypoint_id: str
    point: tuple[float, float]
    kind: str
    support: float

    def as_dict(self) -> dict[str, object]:
        return {
            "keypoint_id": self.keypoint_id,
            "point": [round(value, 3) for value in self.point],
            "kind": self.kind,
            "support": round(self.support, 6),
        }


def detect_keypoints(
    segments: list[ImageSegment],
    image_size: tuple[int, int],
) -> list[ImageKeypoint]:
    points = all_intersections(segments, image_size)
    return [
        ImageKeypoint(
            keypoint_id=f"intersection_{index:03d}",
            point=point,
            kind="line_intersection",
            support=1.0,
        )
        for index, point in enumerate(points)
    ]
