from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from research.tracking import SCHEMA_VERSION
from research.tracking.cli import main as tracking_main
from research.tracking.contracts import TrackingConfig
from research.tracking.runner import TrackingRunner
from research.tracking.sequence_loader import load_sequence


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detection(
    detection_id: str,
    bbox: tuple[int, int, int, int],
    *,
    confidence: float = 0.91,
    team: str = "TEAM_A",
) -> dict[str, object]:
    x1, y1, x2, y2 = bbox
    return {
        "detection_id": detection_id,
        "class_id": 1,
        "class_name": "person",
        "confidence": confidence,
        "bbox_xyxy": [x1, y1, x2, y2],
        "bbox_xywh": [x1, y1, x2 - x1, y2 - y1],
        "center_xy": [(x1 + x2) / 2, (y1 + y2) / 2],
        "foot_point_xy": [(x1 + x2) / 2, y2],
        "team_assignment": team,
        "team_confidence": 0.82,
        "dominant_color": {"bgr": [20, 30, 220]},
        "cluster_id": 0 if team == "TEAM_A" else 1,
        "roi_used": {"status": "used"},
    }


def _build_ve003_sequence(
    tmp_path: Path,
    *,
    frame_count: int = 6,
    missing_at: set[int] | None = None,
    segment_break_at: int | None = None,
) -> tuple[Path, list[Path]]:
    missing_at = missing_at or set()
    source_dir = tmp_path / "images"
    json_dir = tmp_path / "ve003" / "json"
    source_dir.mkdir(parents=True)
    json_dir.mkdir(parents=True)
    files: list[dict[str, object]] = []
    reports: list[Path] = []

    for index in range(frame_count):
        image = np.full((240, 420, 3), (55, 130, 55), dtype=np.uint8)
        first_box = (40 + index * 4, 55, 78 + index * 4, 175)
        second_box = (280 - index * 3, 62, 320 - index * 3, 182)
        cv2.rectangle(image, first_box[:2], first_box[2:], (25, 25, 220), -1)
        cv2.rectangle(image, second_box[:2], second_box[2:], (220, 70, 25), -1)
        image_path = source_dir / f"frame_{1000 + index:06d}_t{index * 200:06d}ms.jpg"
        assert cv2.imwrite(str(image_path), image)
        detections = []
        if index not in missing_at:
            detections = [
                _detection(f"a_{index}", first_box, team="TEAM_A"),
                _detection(f"b_{index}", second_box, team="TEAM_B"),
            ]

        report_path = json_dir / f"{index:04d}_frame.json"
        segment_id = "segment_002" if segment_break_at is not None and index >= segment_break_at else "segment_001"
        payload = {
            "schema_version": "matchiq.ve-003.team-assignment.v1",
            "source": {
                "file_name": image_path.name,
                "path": str(image_path),
                "width": 420,
                "height": 240,
                "frame_index": 1000 + index,
                "timestamp_seconds": index * 0.2,
                "segment_id": segment_id,
            },
            "detections": detections,
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        reports.append(report_path)
        files.append({
            "source_name": image_path.name,
            "status": "success",
            "json_report": str(report_path.relative_to(tmp_path / "ve003")).replace("\\", "/"),
        })

    manifest_path = tmp_path / "ve003" / "team_assignment_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "schema_version": "matchiq.ve-003.team-assignment.v1",
            "files": files,
        }, indent=2),
        encoding="utf-8",
    )
    return manifest_path, reports


def _config(output: Path, **overrides: object) -> TrackingConfig:
    values: dict[str, object] = {
        "output_dir": output,
        "fps": 5.0,
        "high_detection_threshold": 0.60,
        "low_detection_threshold": 0.20,
        "match_threshold": 0.10,
        "lost_buffer": 30,
        "minimum_confirmed_frames": 2,
        "maximum_detections": 20,
        "minimum_box_area": 64.0,
        "render_debug": True,
    }
    values.update(overrides)
    return TrackingConfig(**values)


def test_sequence_loader_uses_explicit_source_timing(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve003_sequence(tmp_path)

    frames, metadata = load_sequence(manifest_path, fps=5.0)

    assert len(frames) == 6
    assert frames[0].frame_index == 1000
    assert frames[2].timestamp_seconds == 0.4
    assert frames[0].timing_source == "source_metadata"
    assert metadata["uniform_timing_was_explicit"] is False


def test_runner_tracks_players_without_mutating_ve003(tmp_path: Path) -> None:
    manifest_path, reports = _build_ve003_sequence(tmp_path)
    before = {path: _sha256(path) for path in [manifest_path, *reports]}

    run = TrackingRunner().run(manifest_path, _config(tmp_path / "ve004b"))

    assert run.manifest["schema_version"] == SCHEMA_VERSION
    assert run.manifest["tracker"]["initialized_once"] is True
    assert run.manifest["limitations"]["detector_executed"] is False
    assert run.manifest["limitations"]["team_assignment_executed"] is False
    assert run.manifest["aggregate"]["tracks_total"] == 2
    assert run.manifest["aggregate"]["tracks_created"] == 2
    assert run.manifest["aggregate"]["tracks_confirmed"] == 2
    assert run.manifest["aggregate"]["tracks_terminated"] is None
    assert run.manifest["aggregate"]["tracks_terminated_status"] == (
        "not_exposed_by_tracker_package"
    )
    assert run.manifest["aggregate"]["predicted_observations"] == 0
    assert {item["track_id"] for item in run.manifest["tracks"]} == {"track_0001", "track_0002"}
    assert {item["dominant_team"] for item in run.manifest["tracks"]} == {"TEAM_A", "TEAM_B"}
    assert all(item["team_assignment_used_as_hard_gate"] is False for item in run.manifest["tracks"])
    assert before == {path: _sha256(path) for path in [manifest_path, *reports]}


def test_observations_keep_source_detection_and_real_foot_point(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve003_sequence(tmp_path)
    run = TrackingRunner().run(manifest_path, _config(tmp_path / "output", render_debug=False))

    observation = run.manifest["observations"][0]
    assert observation["source_detection_id"].startswith(("a_", "b_"))
    assert observation["observation_type"] == "detected"
    assert observation["association_score"] is None
    assert observation["association_score_status"] == "not_exposed_by_tracker_package"
    assert observation["foot_point_xy"][1] in {175.0, 182.0}


def test_gap_is_reported_without_fabricated_prediction(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve003_sequence(tmp_path, frame_count=7, missing_at={3})
    run = TrackingRunner().run(manifest_path, _config(tmp_path / "output", render_debug=False))

    assert run.manifest["aggregate"]["predicted_observations"] == 0
    assert any(track["gap_frames_total"] == 1 for track in run.manifest["tracks"])
    assert any(track["gap_count"] == 1 for track in run.manifest["tracks"])
    assert any(track["maximum_gap_processed_frames"] == 1 for track in run.manifest["tracks"])
    assert any(track["continuity"] < 1.0 for track in run.manifest["tracks"])
    assert any(track["occlusion_intervals"] for track in run.manifest["tracks"])


def test_segment_boundary_resets_tracker_without_reusing_public_id(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve003_sequence(tmp_path, frame_count=8, segment_break_at=4)
    run = TrackingRunner().run(manifest_path, _config(tmp_path / "output", render_debug=False))

    segment_one_ids = {
        item["track_id"] for item in run.manifest["observations"] if item["segment_id"] == "segment_001"
    }
    segment_two_ids = {
        item["track_id"] for item in run.manifest["observations"] if item["segment_id"] == "segment_002"
    }
    assert segment_one_ids
    assert segment_two_ids
    assert segment_one_ids.isdisjoint(segment_two_ids)
    assert run.manifest["aggregate"]["segments"] == 2


def test_thresholds_and_box_area_filter_inputs(tmp_path: Path) -> None:
    manifest_path, reports = _build_ve003_sequence(tmp_path, frame_count=4)
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    payload["detections"].append(_detection("low", (10, 10, 30, 60), confidence=0.10))
    payload["detections"].append(_detection("tiny", (10, 10, 12, 12), confidence=0.99))
    reports[0].write_text(json.dumps(payload, indent=2), encoding="utf-8")

    run = TrackingRunner().run(manifest_path, _config(tmp_path / "output", render_debug=False))

    first_frame = run.manifest["frames"][0]
    assert first_frame["detections_available"] == 4
    assert first_frame["detections_input"] == 2


def test_runner_writes_json_html_and_debug_images(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve003_sequence(tmp_path)
    output_dir = tmp_path / "output"

    run = TrackingRunner().run(manifest_path, _config(output_dir))

    assert run.manifest_path.exists()
    assert run.html_path.exists()
    assert "MatchIQ VE-004B" in run.html_path.read_text(encoding="utf-8")
    assert "Fragmented tracks" in run.html_path.read_text(encoding="utf-8")
    assert all("observed_team_changes" in track for track in run.manifest["tracks"])
    assert len(list((output_dir / "debug").glob("*.jpg"))) == 6
    saved = json.loads(run.manifest_path.read_text(encoding="utf-8"))
    assert saved["timing_ms"]["reporting_ms"] >= 0


def test_cli_runs_on_existing_ve003_manifest(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve003_sequence(tmp_path)
    output_dir = tmp_path / "cli-output"

    code = tracking_main([
        "--source", str(manifest_path),
        "--output", str(output_dir),
        "--fps", "5",
        "--minimum-confirmed-frames", "2",
    ])

    assert code == 0
    assert (output_dir / "tracking_manifest.json").exists()
    assert (output_dir / "tracking_report.html").exists()


def test_tracking_module_does_not_run_detector_team_assignment_or_openai() -> None:
    module_dir = Path(__file__).parents[1] / "research" / "tracking"
    source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in module_dir.rglob("*.py")
    )

    assert "rfdetr" not in source
    assert "openai" not in source
    assert "teamassignmentrunner" not in source
    assert "playerdetectionrunner" not in source
    assert ".detect(" not in source
