from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .contracts import Detection, Track


def bbox_iou(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    intersection_width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    intersection_height = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = intersection_width * intersection_height
    first_area = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    second_area = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = first_area + second_area - intersection
    return intersection / union if union > 0 else 0.0


class ObjectTracker(ABC):
    @abstractmethod
    def update(
        self,
        detections: list[Detection],
        *,
        frame_index: int,
        timestamp_seconds: float,
    ) -> list[Track]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(slots=True)
class _TrackState:
    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    class_name: str
    confidence: float
    age: int = 1
    hits: int = 1
    lost_count: int = 0
    team_id: str | None = None
    team_confidence: float | None = None


class IoUTracker(ObjectTracker):
    """Small deterministic tracker for short clips; IDs are not identities."""

    def __init__(self, *, iou_threshold: float = 0.25, max_lost: int = 8, min_hits: int = 2) -> None:
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost
        self.min_hits = min_hits
        self._next_id = 1
        self._active: dict[int, _TrackState] = {}
        self._created = 0
        self._retired = 0
        self._completed_ages: list[int] = []

    def update(
        self,
        detections: list[Detection],
        *,
        frame_index: int,
        timestamp_seconds: float,
    ) -> list[Track]:
        candidates: list[tuple[float, int, int]] = []
        for track_id, state in self._active.items():
            for detection_index, detection in enumerate(detections):
                if state.class_name != detection.class_name:
                    continue
                score = bbox_iou(state.bbox_xyxy, detection.bbox_xyxy)
                if score >= self.iou_threshold:
                    candidates.append((score, track_id, detection_index))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        used_tracks: set[int] = set()
        used_detections: set[int] = set()
        matched: dict[int, int] = {}
        for _, track_id, detection_index in candidates:
            if track_id in used_tracks or detection_index in used_detections:
                continue
            used_tracks.add(track_id)
            used_detections.add(detection_index)
            matched[track_id] = detection_index

        for track_id, state in list(self._active.items()):
            if track_id in matched:
                detection = detections[matched[track_id]]
                state.bbox_xyxy = detection.bbox_xyxy
                state.confidence = detection.confidence
                state.age += 1
                state.hits += 1
                state.lost_count = 0
                state.team_id = detection.metadata.get("team_id")
                state.team_confidence = detection.metadata.get("team_confidence")
            else:
                state.age += 1
                state.lost_count += 1
                if state.lost_count > self.max_lost:
                    self._completed_ages.append(state.age)
                    self._retired += 1
                    del self._active[track_id]

        for detection_index, detection in enumerate(detections):
            if detection_index in used_detections:
                continue
            track_id = self._next_id
            self._next_id += 1
            self._created += 1
            self._active[track_id] = _TrackState(
                track_id=track_id,
                bbox_xyxy=detection.bbox_xyxy,
                class_name=detection.class_name,
                confidence=detection.confidence,
                team_id=detection.metadata.get("team_id"),
                team_confidence=detection.metadata.get("team_confidence"),
            )
            matched[track_id] = detection_index

        visible: list[Track] = []
        for track_id, state in sorted(self._active.items()):
            if state.lost_count != 0 or state.hits < self.min_hits:
                continue
            visible.append(
                Track(
                    track_id=track_id,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    bbox_xyxy=state.bbox_xyxy,
                    class_name=state.class_name,
                    confidence=state.confidence,
                    track_age=state.age,
                    lost_count=state.lost_count,
                    team_id=state.team_id,
                    team_confidence=state.team_confidence,
                )
            )
        return visible

    def close(self) -> None:
        for state in self._active.values():
            self._completed_ages.append(state.age)
        self._active.clear()

    def metadata(self) -> dict[str, Any]:
        ages = self._completed_ages + [state.age for state in self._active.values()]
        return {
            "backend": "deterministic_iou",
            "iou_threshold": self.iou_threshold,
            "max_lost": self.max_lost,
            "min_hits": self.min_hits,
            "tracks_created": self._created,
            "tracks_retired": self._retired,
            "tracks_active": len(self._active),
            "average_track_age_frames": round(sum(ages) / len(ages), 3) if ages else 0.0,
            "identity_scope": "temporary_short_clip",
        }
