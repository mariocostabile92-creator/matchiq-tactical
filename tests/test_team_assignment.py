from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from research.team_assignment import SCHEMA_VERSION
from research.team_assignment.cli import main as team_assignment_main
from research.team_assignment.clustering import cluster_team_samples
from research.team_assignment.contracts import (
    TEAM_A,
    TEAM_B,
    UNKNOWN,
    ColorSample,
    TeamAssignmentConfig,
)
from research.team_assignment.features import build_color_feature
from research.team_assignment.roi import extract_torso_roi
from research.team_assignment.runner import TeamAssignmentRunner


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paint_player(
    image: np.ndarray,
    bbox: tuple[int, int, int, int],
    torso_color: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = bbox
    cv2.rectangle(image, (x1, y1), (x2, y2), (220, 200, 180), -1)
    width = x2 - x1
    height = y2 - y1
    torso_x1 = int(round(x1 + width * 0.16))
    torso_x2 = int(round(x1 + width * 0.84))
    torso_y1 = int(round(y1 + height * 0.14))
    torso_y2 = int(round(y1 + height * 0.62))
    cv2.rectangle(image, (torso_x1, torso_y1), (torso_x2, torso_y2), torso_color, -1)
    cv2.rectangle(
        image,
        (x1, int(round(y1 + height * 0.63))),
        (x2, y2),
        (25, 25, 25),
        -1,
    )


def _ve002_detection(sequence: int, bbox: tuple[int, int, int, int]) -> dict[str, object]:
    x1, y1, x2, y2 = bbox
    return {
        "detection_id": f"player_{sequence:03d}",
        "class_id": 1,
        "class_name": "person",
        "candidate_type": "player_candidate",
        "confidence": 0.91,
        "source_model": "test-ve002",
        "bbox_xyxy": [float(x1), float(y1), float(x2), float(y2)],
        "bbox_xywh": [float(x1), float(y1), float(x2 - x1), float(y2 - y1)],
        "center_xy": [float((x1 + x2) / 2), float((y1 + y2) / 2)],
        "foot_point_xy": [float((x1 + x2) / 2), float(y2)],
    }


def _build_ve002_fixture(tmp_path: Path) -> tuple[Path, list[Path]]:
    source_dir = tmp_path / "source"
    json_dir = tmp_path / "ve002" / "json"
    source_dir.mkdir(parents=True)
    json_dir.mkdir(parents=True)
    report_paths: list[Path] = []
    files: list[dict[str, object]] = []

    layouts = [
        [
            ((30, 30, 70, 130), (20, 20, 220)),
            ((95, 35, 135, 135), (25, 25, 225)),
            ((180, 32, 220, 132), (220, 65, 25)),
            ((245, 38, 285, 138), (225, 70, 25)),
        ],
        [
            ((45, 28, 85, 128), (25, 25, 215)),
            ((115, 34, 155, 134), (20, 20, 230)),
            ((195, 30, 235, 130), (215, 60, 20)),
            ((260, 36, 300, 136), (230, 75, 30)),
        ],
    ]
    for image_index, layout in enumerate(layouts, start=1):
        image = np.full((170, 340, 3), (55, 135, 55), dtype=np.uint8)
        detections: list[dict[str, object]] = []
        for detection_index, (bbox, color) in enumerate(layout, start=1):
            _paint_player(image, bbox, color)
            detections.append(_ve002_detection(detection_index, bbox))
        source_path = source_dir / f"frame_{image_index}.jpg"
        assert cv2.imwrite(str(source_path), image)

        report_path = json_dir / f"{image_index:04d}_frame.json"
        payload = {
            "schema_version": "matchiq.ve-002.player-detection.v1",
            "source": {
                "file_name": source_path.name,
                "path": str(source_path),
                "width": 340,
                "height": 170,
            },
            "detector": {"backend": "fixture", "team_supported": False},
            "detection_count": len(detections),
            "detections": detections,
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        report_paths.append(report_path)
        files.append({
            "source_name": source_path.name,
            "source_path": str(source_path),
            "status": "success",
            "detection_count": len(detections),
            "json_report": str(report_path.relative_to(tmp_path / "ve002")).replace("\\", "/"),
        })

    manifest_path = tmp_path / "ve002" / "player_detection_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "schema_version": "matchiq.ve-002.player-detection.v1",
            "run": {"status": "completed"},
            "files": files,
        }, indent=2),
        encoding="utf-8",
    )
    return manifest_path, report_paths


def test_torso_roi_excludes_head_shorts_and_feet() -> None:
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    roi = extract_torso_roi(image, [50, 10, 150, 90])

    assert roi.status == "used"
    assert roi.bbox_xyxy == (70, 24, 130, 56)
    assert roi.image.shape[:2] == (32, 60)


def test_torso_roi_rejects_tiny_detection() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    roi = extract_torso_roi(image, [10, 10, 15, 20])

    assert roi.status == "excluded"
    assert roi.reason == "detection_too_small"


def test_color_feature_uses_hsv_lab_and_ignores_grass() -> None:
    image = np.full((120, 100, 3), (45, 145, 45), dtype=np.uint8)
    _paint_player(image, (30, 10, 70, 110), (20, 20, 230))
    roi = extract_torso_roi(image, [30, 10, 70, 110])
    feature = build_color_feature(roi, detection_confidence=0.9)

    assert feature.vector is not None
    assert len(feature.vector) == 25
    assert feature.dominant_color is not None
    assert feature.roi_report["status"] == "used"
    assert feature.quality > 0.5


def test_deterministic_clustering_is_stable_across_input_order() -> None:
    red = (0.20,) * 20 + (0.90, 0.02, 0.03, 0.02, 0.01)
    blue = (0.75,) * 20 + (0.02, 0.85, 0.02, 0.03, 0.01)
    samples = [
        ColorSample("a1", red, 0.95),
        ColorSample("a2", tuple(value + 0.01 for value in red), 0.92),
        ColorSample("b1", blue, 0.94),
        ColorSample("b2", tuple(value - 0.01 for value in blue), 0.91),
    ]
    first, first_meta = cluster_team_samples(
        samples,
        minimum_confidence=0.2,
        minimum_separation=0.1,
    )
    second, second_meta = cluster_team_samples(
        reversed(samples),
        minimum_confidence=0.2,
        minimum_separation=0.1,
    )

    assert first == second
    assert first_meta["centers"] == second_meta["centers"]
    assert {assignment.team_assignment for assignment in first.values()} == {TEAM_A, TEAM_B}


def test_ambiguous_clusters_return_unknown() -> None:
    samples = [
        ColorSample("p1", (0.50,) * 25, 0.9),
        ColorSample("p2", (0.501,) * 25, 0.9),
        ColorSample("p3", (0.502,) * 25, 0.9),
    ]
    assignments, metadata = cluster_team_samples(
        samples,
        minimum_confidence=0.35,
        minimum_separation=0.18,
    )

    assert metadata["status"] == "unreliable"
    assert all(item.team_assignment == UNKNOWN for item in assignments.values())


def test_runner_consumes_ve002_without_mutating_it(tmp_path: Path) -> None:
    manifest_path, source_reports = _build_ve002_fixture(tmp_path)
    hashes_before = {path: _sha256(path) for path in [manifest_path, *source_reports]}
    output_dir = tmp_path / "ve003"

    run = TeamAssignmentRunner().run_manifest(
        manifest_path,
        TeamAssignmentConfig(
            output_dir=output_dir,
            minimum_team_confidence=0.20,
            minimum_cluster_separation=0.10,
        ),
    )

    assert run.manifest["schema_version"] == SCHEMA_VERSION
    assert run.manifest["limitations"]["detector_executed"] is False
    assert run.manifest["aggregate"]["players_total"] == 8
    assert run.manifest["aggregate"]["team_a"] == 4
    assert run.manifest["aggregate"]["team_b"] == 4
    assert run.manifest["aggregate"]["unknown"] == 0
    assert run.manifest_path.exists()
    assert run.html_path.exists()
    assert "<table>" in run.html_path.read_text(encoding="utf-8")
    assert all((output_dir / item["debug_image"]).exists() for item in run.manifest["files"])
    assert hashes_before == {path: _sha256(path) for path in [manifest_path, *source_reports]}

    first_output = json.loads((output_dir / run.manifest["files"][0]["json_report"]).read_text())
    for detection in first_output["detections"]:
        assert detection["team_assignment"] in {TEAM_A, TEAM_B, UNKNOWN}
        assert isinstance(detection["team_confidence"], float)
        assert "dominant_color" in detection
        assert "cluster_id" in detection
        assert "roi_used" in detection


def test_cli_generates_json_html_and_debug_images(tmp_path: Path) -> None:
    manifest_path, _ = _build_ve002_fixture(tmp_path)
    output_dir = tmp_path / "cli-output"

    exit_code = team_assignment_main([
        "--manifest",
        str(manifest_path),
        "--output",
        str(output_dir),
        "--minimum-confidence",
        "0.20",
        "--minimum-separation",
        "0.10",
    ])

    assert exit_code == 0
    assert (output_dir / "team_assignment_manifest.json").exists()
    assert (output_dir / "team_assignment_report.html").exists()
    assert len(list((output_dir / "debug").glob("*.jpg"))) == 2


def test_team_assignment_module_does_not_import_detector_or_openai() -> None:
    module_dir = Path(__file__).parents[1] / "research" / "team_assignment"
    source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in module_dir.glob("*.py")
    )

    assert "build_player_detector" not in source
    assert "rfdetr_detector" not in source
    assert "openai" not in source
    assert ".detect(" not in source

