from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import SCHEMA_VERSION
from .clustering import cluster_team_samples
from .contracts import (
    TEAM_A,
    TEAM_B,
    UNKNOWN,
    ColorSample,
    TeamAssignmentConfig,
    TeamAssignmentRun,
)
from .features import ColorFeature, build_color_feature
from .renderer import render_team_debug_image
from .reports import write_html_report, write_json
from .roi import extract_torso_roi


@dataclass(slots=True)
class _PreparedDetection:
    sample_id: str
    image_index: int
    detection_index: int
    color: ColorFeature


@dataclass(slots=True)
class _PreparedImage:
    source_report_path: Path
    source_report: dict[str, Any]
    image: object
    detections: list[dict[str, Any]]
    extraction_ms: float


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    stem = Path(value).stem
    cleaned = "".join(character if character.isalnum() or character in "-_" else "_" for character in stem)
    return cleaned.strip("_") or "image"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_ve002(payload: dict[str, Any], *, path: Path) -> None:
    schema = str(payload.get("schema_version", ""))
    if not schema.startswith("matchiq.ve-002.player-detection."):
        raise ValueError(f"{path} is not a VE-002 player detection report")


class TeamAssignmentRunner:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.perf_counter,
        now: Callable[[], str] = _utc_now,
    ) -> None:
        self._clock = clock
        self._now = now

    def run_manifest(
        self,
        ve002_manifest_path: Path,
        config: TeamAssignmentConfig,
    ) -> TeamAssignmentRun:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV is required by VE-003") from exc

        started = self._clock()
        manifest_path = Path(ve002_manifest_path).resolve()
        source_manifest = _load_json(manifest_path)
        _require_ve002(source_manifest, path=manifest_path)
        output_dir = Path(config.output_dir)
        json_dir = output_dir / "json"
        debug_dir = output_dir / "debug"
        output_dir.mkdir(parents=True, exist_ok=True)

        prepared_images: list[_PreparedImage] = []
        prepared_detections: list[_PreparedDetection] = []
        errors: list[dict[str, str]] = []

        for file_index, file_entry in enumerate(source_manifest.get("files", []), start=1):
            if file_entry.get("status") != "success":
                continue
            json_report = Path(str(file_entry.get("json_report", "")))
            if not json_report.is_absolute():
                json_report = manifest_path.parent / json_report
            try:
                image_started = self._clock()
                source_report = _load_json(json_report)
                _require_ve002(source_report, path=json_report)
                source_path = Path(str(source_report["source"]["path"]))
                image = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
                if image is None:
                    raise ValueError(f"source image is unreadable: {source_path}")
                detections = copy.deepcopy(source_report.get("detections", []))
                prepared = _PreparedImage(
                    source_report_path=json_report.resolve(),
                    source_report=source_report,
                    image=image,
                    detections=detections,
                    extraction_ms=0.0,
                )
                prepared_images.append(prepared)
                prepared_image_index = len(prepared_images) - 1

                for detection_index, detection in enumerate(detections):
                    sample_id = f"{file_index:04d}:{detection.get('detection_id', detection_index)}"
                    torso = extract_torso_roi(
                        image,
                        detection.get("bbox_xyxy", []),
                        x_start=config.torso_x_start,
                        x_end=config.torso_x_end,
                        y_start=config.torso_y_start,
                        y_end=config.torso_y_end,
                    )
                    color = build_color_feature(
                        torso,
                        detection_confidence=float(detection.get("confidence", 0.0)),
                    )
                    prepared_detections.append(_PreparedDetection(
                        sample_id=sample_id,
                        image_index=prepared_image_index,
                        detection_index=detection_index,
                        color=color,
                    ))
                prepared.extraction_ms = (self._clock() - image_started) * 1000.0
            except Exception as exc:
                errors.append({
                    "source_name": str(file_entry.get("source_name", json_report.name)),
                    "message": str(exc),
                })

        valid_samples = [
            ColorSample(item.sample_id, item.color.vector, item.color.quality)
            for item in prepared_detections
            if item.color.vector is not None
        ]
        cluster_started = self._clock()
        assignments, clustering = cluster_team_samples(
            valid_samples,
            minimum_confidence=config.minimum_team_confidence,
            minimum_separation=config.minimum_cluster_separation,
        )
        clustering_ms = (self._clock() - cluster_started) * 1000.0

        for prepared in prepared_detections:
            detection = prepared_images[prepared.image_index].detections[prepared.detection_index]
            assignment = assignments.get(prepared.sample_id)
            if assignment is None:
                detection.update({
                    "team_assignment": UNKNOWN,
                    "team_confidence": 0.0,
                    "dominant_color": prepared.color.dominant_color,
                    "cluster_id": None,
                    "roi_used": prepared.color.roi_report,
                    "team_assignment_reason": prepared.color.reason or "roi_excluded",
                })
            else:
                detection.update({
                    "team_assignment": assignment.team_assignment,
                    "team_confidence": assignment.team_confidence,
                    "dominant_color": prepared.color.dominant_color,
                    "cluster_id": assignment.cluster_id,
                    "roi_used": prepared.color.roi_report,
                    "team_assignment_reason": assignment.reason,
                })

        files: list[dict[str, Any]] = []
        all_confidences: list[float] = []
        roi_excluded = 0
        total_players = 0
        rendering_ms = 0.0
        json_writing_ms = 0.0

        for index, prepared in enumerate(prepared_images, start=1):
            source_name = str(prepared.source_report["source"]["file_name"])
            output_stem = f"{index:04d}_{_safe_name(source_name)}"
            debug_path = debug_dir / f"{output_stem}_teams.jpg"
            output_json_path = json_dir / f"{output_stem}.json"

            render_started = self._clock()
            render_team_debug_image(prepared.image, prepared.detections, debug_path)
            rendering_ms += (self._clock() - render_started) * 1000.0

            counts = {
                team: sum(
                    1
                    for detection in prepared.detections
                    if detection.get("team_assignment") == team
                )
                for team in (TEAM_A, TEAM_B, UNKNOWN)
            }
            confidences = [
                float(detection.get("team_confidence", 0.0))
                for detection in prepared.detections
                if detection.get("team_assignment") != UNKNOWN
            ]
            excluded = sum(
                1
                for detection in prepared.detections
                if (detection.get("roi_used") or {}).get("status") != "used"
            )
            total_players += len(prepared.detections)
            roi_excluded += excluded
            all_confidences.extend(confidences)
            per_image = {
                "schema_version": SCHEMA_VERSION,
                "processed_at": self._now(),
                "source_ve002_report": str(prepared.source_report_path),
                "source": copy.deepcopy(prepared.source_report["source"]),
                "detector": copy.deepcopy(prepared.source_report.get("detector", {})),
                "configuration": {
                    "minimum_team_confidence": config.minimum_team_confidence,
                    "minimum_cluster_separation": config.minimum_cluster_separation,
                    "torso_roi_relative": [
                        config.torso_x_start,
                        config.torso_y_start,
                        config.torso_x_end,
                        config.torso_y_end,
                    ],
                },
                "clustering": copy.deepcopy(clustering),
                "player_count": len(prepared.detections),
                "team_summary": {
                    "TEAM_A": counts[TEAM_A],
                    "TEAM_B": counts[TEAM_B],
                    "UNKNOWN": counts[UNKNOWN],
                    "roi_excluded": excluded,
                    "average_team_confidence": round(
                        sum(confidences) / len(confidences),
                        6,
                    ) if confidences else 0.0,
                },
                "detections": prepared.detections,
                "timing_ms": {
                    "image_and_feature_extraction_ms": round(prepared.extraction_ms, 3),
                },
                "debug_image": str(debug_path.resolve()),
                "limitations": {
                    "team_labels_are_anonymous": True,
                    "goalkeeper_classification": False,
                    "referee_classification": False,
                    "tracking": False,
                    "identity": False,
                    "roles": False,
                    "tactical_interpretation": False,
                },
            }
            write_started = self._clock()
            write_json(per_image, output_json_path)
            json_writing_ms += (self._clock() - write_started) * 1000.0
            files.append({
                "source_name": source_name,
                "source_ve002_report": str(prepared.source_report_path),
                "status": "success",
                "player_count": len(prepared.detections),
                "team_a": counts[TEAM_A],
                "team_b": counts[TEAM_B],
                "unknown": counts[UNKNOWN],
                "roi_excluded": excluded,
                "average_team_confidence": per_image["team_summary"]["average_team_confidence"],
                "json_report": str(output_json_path.relative_to(output_dir)).replace("\\", "/"),
                "debug_image": str(debug_path.relative_to(output_dir)).replace("\\", "/"),
            })

        elapsed_ms = (self._clock() - started) * 1000.0
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run": {
                "processed_at": self._now(),
                "source_ve002_manifest": str(manifest_path),
                "output_dir": str(output_dir.resolve()),
                "status": "completed" if not errors else "completed_with_errors",
            },
            "configuration": {
                "minimum_team_confidence": config.minimum_team_confidence,
                "minimum_cluster_separation": config.minimum_cluster_separation,
                "torso_roi_relative": [
                    config.torso_x_start,
                    config.torso_y_start,
                    config.torso_x_end,
                    config.torso_y_end,
                ],
                "color_spaces": ["HSV", "LAB"],
                "clustering": "deterministic_kmeans_2",
            },
            "clustering": clustering,
            "aggregate": {
                "images_processed": len(prepared_images),
                "players_total": total_players,
                "team_a": sum(item["team_a"] for item in files),
                "team_b": sum(item["team_b"] for item in files),
                "unknown": sum(item["unknown"] for item in files),
                "roi_excluded": roi_excluded,
                "average_team_confidence": round(
                    sum(all_confidences) / len(all_confidences),
                    6,
                ) if all_confidences else 0.0,
                "average_ms_per_player": round(elapsed_ms / total_players, 3) if total_players else 0.0,
            },
            "timing_ms": {
                "clustering_ms": round(clustering_ms, 3),
                "rendering_ms": round(rendering_ms, 3),
                "json_writing_ms": round(json_writing_ms, 3),
                "total_ms": round(elapsed_ms, 3),
            },
            "files": files,
            "errors": errors,
            "limitations": {
                "consumes_ve002_only": True,
                "detector_executed": False,
                "team_labels_are_anonymous": True,
                "goalkeeper_classification": False,
                "referee_classification": False,
                "tracking": False,
                "identity": False,
                "roles": False,
                "tactical_interpretation": False,
            },
        }
        output_manifest_path = write_json(manifest, output_dir / "team_assignment_manifest.json")
        html_path = write_html_report(manifest, output_dir / "team_assignment_report.html")
        return TeamAssignmentRun(output_manifest_path, html_path, manifest)

