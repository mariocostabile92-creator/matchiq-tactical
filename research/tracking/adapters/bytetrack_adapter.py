from __future__ import annotations

from importlib.metadata import version
from typing import Any

import numpy as np
import supervision as sv

from ..contracts import TrackedDetection, TrackingConfig, TrackingUpdate


def _foot_point(detection: dict[str, Any], bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    value = detection.get("foot_point_xy")
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return float(value[0]), float(value[1])
    x1, _, x2, y2 = bbox
    return (x1 + x2) / 2.0, y2


class ByteTrackAdapter:
    name = "roboflow-trackers-bytetrack"
    emits_predicted_observations = False

    def __init__(self, config: TrackingConfig) -> None:
        try:
            from trackers import ByteTrackTracker
        except ImportError as exc:
            raise RuntimeError(
                "VE-004B requires trackers==2.5.0.post0; install research/tracking/requirements.txt"
            ) from exc

        self.version = version("trackers")
        self._config = config
        self._tracker = ByteTrackTracker(
            lost_track_buffer=config.lost_buffer,
            frame_rate=config.fps,
            track_activation_threshold=config.high_detection_threshold,
            minimum_consecutive_frames=config.minimum_confirmed_frames,
            minimum_iou_threshold=config.match_threshold,
            high_conf_det_threshold=config.high_detection_threshold,
        )
        self._public_ids: dict[int, str] = {}
        self._next_public_id = 1

    def reset_segment(self) -> None:
        self._tracker.reset()
        self._public_ids.clear()

    def public_track_id(self, raw_tracker_id: int) -> str:
        track_id = self._public_ids.get(raw_tracker_id)
        if track_id is None:
            track_id = f"track_{self._next_public_id:04d}"
            self._next_public_id += 1
            self._public_ids[raw_tracker_id] = track_id
        return track_id

    def update(self, detections: list[dict[str, Any]]) -> TrackingUpdate:
        accepted: list[dict[str, Any]] = []
        for detection in detections:
            bbox = detection.get("bbox_xyxy")
            if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                continue
            values = tuple(float(value) for value in bbox[:4])
            area = max(0.0, values[2] - values[0]) * max(0.0, values[3] - values[1])
            confidence = float(detection.get("confidence", 0.0))
            if confidence < self._config.low_detection_threshold or area < self._config.minimum_box_area:
                continue
            normalized = dict(detection)
            normalized["_bbox"] = values
            accepted.append(normalized)

        accepted.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        accepted = accepted[:self._config.maximum_detections]
        if not accepted:
            empty = sv.Detections.empty()
            empty.tracker_id = np.array([], dtype=int)
            tracked = self._tracker.update(empty)
            return TrackingUpdate((), int(np.count_nonzero(tracked.tracker_id == -1)), 0)

        data = {
            "source_detection_id": np.asarray([
                str(item.get("detection_id", f"detection_{index:04d}"))
                for index, item in enumerate(accepted, start=1)
            ]),
            "team_assignment": np.asarray([str(item.get("team_assignment", "UNKNOWN")) for item in accepted]),
            "team_confidence": np.asarray([float(item.get("team_confidence", 0.0)) for item in accepted]),
            "dominant_color": np.asarray([item.get("dominant_color") for item in accepted], dtype=object),
            "cluster_id": np.asarray([item.get("cluster_id") for item in accepted], dtype=object),
            "roi_used": np.asarray([item.get("roi_used") for item in accepted], dtype=object),
            "foot_point_xy": np.asarray([
                item.get("foot_point_xy")
                for item in accepted
            ], dtype=object),
        }
        supervision_detections = sv.Detections(
            xyxy=np.asarray([item["_bbox"] for item in accepted], dtype=float),
            confidence=np.asarray([float(item.get("confidence", 0.0)) for item in accepted], dtype=float),
            class_id=np.zeros(len(accepted), dtype=int),
            data=data,
        )
        result = self._tracker.update(supervision_detections)
        tracked_items: list[TrackedDetection] = []
        tentative_count = 0
        for index, raw_tracker_id in enumerate(result.tracker_id.tolist()):
            if raw_tracker_id < 0:
                tentative_count += 1
                continue
            bbox = tuple(float(value) for value in result.xyxy[index].tolist())
            confidence = float(result.confidence[index]) if result.confidence is not None else 0.0
            tracked_items.append(TrackedDetection(
                raw_tracker_id=int(raw_tracker_id),
                source_detection_id=str(result.data["source_detection_id"][index]),
                bbox_xyxy=bbox,
                foot_point_xy=_foot_point(
                    {"foot_point_xy": result.data["foot_point_xy"][index]},
                    bbox,
                ),
                detection_confidence=confidence,
                association_stage=(
                    "high_confidence_input"
                    if confidence >= self._config.high_detection_threshold
                    else "low_confidence_input"
                ),
                team_assignment=str(result.data["team_assignment"][index]),
                team_confidence=float(result.data["team_confidence"][index]),
                dominant_color=result.data["dominant_color"][index],
                cluster_id=(
                    int(result.data["cluster_id"][index])
                    if result.data["cluster_id"][index] is not None
                    else None
                ),
                roi_used=result.data["roi_used"][index],
            ))
        return TrackingUpdate(tuple(tracked_items), tentative_count, len(accepted))
