from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from research.pitch_calibration.adapters.matchiq_hybrid_adapter import (
    MatchIQHybridAdapter,
)
from research.pitch_calibration.cli import build_parser
from research.pitch_calibration.contracts import (
    AdapterResult,
    CalibrationConfig,
    CalibrationFrame,
    CalibrationStatus,
)
from research.pitch_calibration.correspondence_solver import (
    CalibrationHypothesis,
    SemanticCorrespondence,
    orientation_is_ambiguous,
)
from research.pitch_calibration.field_evidence import extract_field_evidence
from research.pitch_calibration.field_model import CanonicalPitchModel
from research.pitch_calibration.geometric_refinement import refine_homography
from research.pitch_calibration.homography_solver import (
    HomographyEstimate,
    estimate_homography,
    normalized_dlt,
    reprojection_errors,
)
from research.pitch_calibration.keypoint_detection import detect_keypoints
from research.pitch_calibration.line_detection import (
    ImageSegment,
    all_intersections,
    merge_collinear_segments,
    segment_intersection,
)
from research.pitch_calibration.projection import project_observations
from research.pitch_calibration.quality_gate import assess_calibration
from research.pitch_calibration.runner import PitchCalibrationRunner
from research.pitch_calibration.temporal_validation import (
    assess_temporal_pair,
    decay_confidence,
    histogram_distance,
    smooth_compatible_homographies,
    visual_histogram,
)


def _synthetic_pitch(width: int = 640, height: int = 360) -> np.ndarray:
    image = np.full((height, width, 3), (45, 125, 55), dtype=np.uint8)
    polygon = np.asarray([[60, 50], [580, 50], [625, 335], [15, 335]], np.int32)
    cv2.polylines(image, [polygon], True, (245, 245, 245), 5, cv2.LINE_AA)
    cv2.line(image, (320, 50), (320, 335), (245, 245, 245), 4, cv2.LINE_AA)
    cv2.circle(image, (320, 190), 48, (245, 245, 245), 4, cv2.LINE_AA)
    cv2.rectangle(image, (60, 120), (145, 270), (245, 245, 245), 4)
    cv2.rectangle(image, (495, 120), (580, 270), (245, 245, 245), 4)
    return image


def _estimate(score: float = 0.8) -> HomographyEstimate:
    matrix = np.eye(3, dtype=np.float64)
    return HomographyEstimate(
        matrix=matrix,
        inverse=matrix,
        inlier_mask=(True, True, True, True),
        inlier_ratio=1.0,
        reprojection_error_px=0.0,
        condition_number=1.0,
        spatial_spread=1.0,
    )


def _hypothesis(
    identifier: str,
    orientation: str,
    score: float,
) -> CalibrationHypothesis:
    return CalibrationHypothesis(
        hypothesis_id=identifier,
        region_id="full_pitch",
        orientation=orientation,
        correspondences=(),
        estimate=_estimate(),
        line_support=score,
        grass_support=score,
        plausibility=score,
        score=score,
    )


def _hybrid_result(status: CalibrationStatus = CalibrationStatus.ESTIMATED) -> AdapterResult:
    matrix = np.asarray(
        [[0.105, 0.0, 0.0], [0.0, 0.068, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    return AdapterResult(
        status=status,
        homography_image_to_pitch=matrix.tolist(),
        homography_pitch_to_image=np.linalg.inv(matrix).tolist(),
        camera_parameters=None,
        model_confidence=0.9,
        reprojection_error_px=0.5,
        coverage_score=0.8,
        calibration_origin="matchiq_classical_geometry",
        detected_field_elements=(
            {"kind": "line"},
            {"kind": "line"},
            {"kind": "line"},
            {"kind": "line"},
        ),
        evidence_confidence=0.8,
        correspondence_confidence=0.8,
        projection_confidence=0.8,
    )


def test_pitch_model_uses_canonical_dimensions() -> None:
    model = CanonicalPitchModel()
    assert (model.length, model.width) == (105.0, 68.0)


def test_pitch_model_rejects_non_positive_dimensions() -> None:
    with pytest.raises(ValueError):
        CanonicalPitchModel(0.0, 68.0)


def test_pitch_model_rejects_partial_physical_dimensions() -> None:
    with pytest.raises(ValueError):
        CanonicalPitchModel(physical_length=100.0)


def test_pitch_model_exposes_semantic_points() -> None:
    identifiers = {item.semantic_id for item in CanonicalPitchModel().points}
    assert {"center", "halfway_top", "left_penalty_spot"} <= identifiers


def test_pitch_model_exposes_semantic_lines() -> None:
    identifiers = {item.semantic_id for item in CanonicalPitchModel().segments}
    assert {"halfway_line", "left_penalty_outer", "touchline_top"} <= identifiers


def test_pitch_model_exposes_circle_and_arcs() -> None:
    model = CanonicalPitchModel()
    assert model.circles[0].semantic_id == "center_circle"
    assert {item.semantic_id for item in model.arcs} == {
        "left_penalty_arc",
        "right_penalty_arc",
    }


def test_pitch_model_exposes_goal_structures() -> None:
    assert len(CanonicalPitchModel().goal_structures) == 2


def test_pitch_model_normalized_round_trip() -> None:
    model = CanonicalPitchModel()
    assert model.canonical_from_normalized(model.normalized((52.5, 34.0))) == (52.5, 34.0)


def test_pitch_model_physical_coordinates_are_explicit() -> None:
    model = CanonicalPitchModel(physical_length=100.0, physical_width=64.0)
    assert model.physical_from_normalized((0.5, 0.5)) == (50.0, 32.0)


def test_pitch_model_does_not_invent_physical_dimensions() -> None:
    assert CanonicalPitchModel().physical_from_normalized((0.5, 0.5)) is None


def test_pitch_model_contains_respects_bounds() -> None:
    model = CanonicalPitchModel()
    assert model.contains((52.5, 34.0))
    assert not model.contains((-2.0, 34.0))


def test_pitch_model_render_is_nonempty() -> None:
    image = CanonicalPitchModel().render(scale=2.0)
    assert image.shape[0] > 100
    assert np.count_nonzero(image[:, :, 1] > image[:, :, 2]) > 0


def test_image_segment_geometry() -> None:
    segment = ImageSegment("a", (0.0, 0.0), (3.0, 4.0))
    assert segment.length == 5.0
    assert 53.0 < segment.angle < 54.0


def test_collinear_segments_are_merged() -> None:
    merged = merge_collinear_segments(
        [
            ImageSegment("a", (0.0, 10.0), (100.0, 10.0)),
            ImageSegment("b", (90.0, 11.0), (180.0, 11.0)),
        ]
    )
    assert len(merged) == 1
    assert merged[0].length > 170.0


def test_perpendicular_segments_intersect() -> None:
    first = ImageSegment("a", (0.0, 50.0), (100.0, 50.0))
    second = ImageSegment("b", (50.0, 0.0), (50.0, 100.0))
    assert segment_intersection(first, second) == pytest.approx((50.0, 50.0))


def test_parallel_segments_do_not_intersect() -> None:
    first = ImageSegment("a", (0.0, 10.0), (100.0, 10.0))
    second = ImageSegment("b", (0.0, 20.0), (100.0, 20.0))
    assert segment_intersection(first, second) is None


def test_all_intersections_filters_duplicates() -> None:
    segments = [
        ImageSegment("a", (0.0, 50.0), (100.0, 50.0)),
        ImageSegment("b", (50.0, 0.0), (50.0, 100.0)),
        ImageSegment("c", (51.0, 0.0), (51.0, 100.0)),
    ]
    assert len(all_intersections(segments, (100, 100))) == 1


def test_keypoints_are_created_from_line_intersections() -> None:
    segments = [
        ImageSegment("a", (0.0, 50.0), (100.0, 50.0)),
        ImageSegment("b", (50.0, 0.0), (50.0, 100.0)),
    ]
    keypoints = detect_keypoints(segments, (100, 100))
    assert keypoints[0].kind == "line_intersection"


def test_field_evidence_finds_grass_and_lines() -> None:
    evidence = extract_field_evidence(_synthetic_pitch())
    assert evidence.grass_ratio > 0.5
    assert evidence.line_ratio > 0.001
    assert len(evidence.segments) >= 3


def test_field_evidence_rejects_empty_image() -> None:
    with pytest.raises(ValueError):
        extract_field_evidence(np.asarray([], dtype=np.uint8))


def test_field_evidence_rejects_non_pitch_scene() -> None:
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    evidence = extract_field_evidence(image)
    assert "insufficient_grass_coverage" in evidence.rejection_reasons


def test_field_evidence_excludes_green_sky_component() -> None:
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    image[:70] = (220, 170, 40)
    image[110:220] = (45, 125, 45)
    cv2.line(image, (20, 180), (300, 180), (245, 245, 245), 3)

    evidence = extract_field_evidence(image)

    assert np.count_nonzero(evidence.grass_mask[:70]) == 0
    assert np.count_nonzero(evidence.grass_mask[110:220]) > 0


def test_normalized_dlt_identity() -> None:
    points = np.float64([[0, 0], [100, 0], [100, 60], [0, 60]])
    matrix = normalized_dlt(points, points)
    assert matrix == pytest.approx(np.eye(3), abs=1.0e-8)


def test_normalized_dlt_known_transform() -> None:
    source = np.float64([[10, 20], [210, 20], [210, 120], [10, 120]])
    target = np.float64([[0, 0], [105, 0], [105, 68], [0, 68]])
    matrix = normalized_dlt(source, target)
    assert reprojection_errors(matrix, source, target).max() < 1.0e-6


def test_normalized_dlt_rejects_collinear_points() -> None:
    points = np.float64([[0, 0], [1, 0], [2, 0], [3, 0]])
    with pytest.raises(ValueError):
        normalized_dlt(points, points)


def test_ransac_estimate_is_invertible() -> None:
    source = np.float64([[0, 0], [100, 0], [100, 60], [0, 60]])
    target = np.float64([[0, 0], [105, 0], [105, 68], [0, 68]])
    estimate = estimate_homography(source, target)
    assert estimate.matrix is not None
    assert estimate.inverse is not None


def test_ransac_rejects_an_outlier() -> None:
    source = np.float64([[0, 0], [100, 0], [100, 60], [0, 60], [50, 30]])
    target = np.float64([[0, 0], [105, 0], [105, 68], [0, 68], [999, 999]])
    estimate = estimate_homography(source, target, ransac_threshold_px=2.0)
    assert estimate.matrix is not None
    assert estimate.inlier_ratio < 1.0


def test_refinement_preserves_valid_homography() -> None:
    points = np.float64([[0, 0], [100, 0], [100, 60], [0, 60]])
    refined = refine_homography(np.eye(3), points, points, (True, True, True, True))
    assert refined == pytest.approx(np.eye(3))


def test_semantic_correspondence_serializes_provenance() -> None:
    item = SemanticCorrespondence(
        "c1",
        "line_a+line_b",
        (10.0, 20.0),
        "corner_top_left",
        (0.0, 0.0),
        0.8,
        "classical_line_family_intersection",
        None,
        0.7,
    )
    assert item.as_dict()["provenance"] == "classical_line_family_intersection"


def test_orientation_ambiguity_detects_close_mirror_hypotheses() -> None:
    values = [_hypothesis("a", "forward", 0.80), _hypothesis("b", "reversed", 0.77)]
    assert orientation_is_ambiguous(values)


def test_orientation_ambiguity_accepts_clear_margin() -> None:
    values = [_hypothesis("a", "forward", 0.90), _hypothesis("b", "reversed", 0.60)]
    assert not orientation_is_ambiguous(values)


def test_visual_histogram_distance_is_zero_for_same_image() -> None:
    histogram = visual_histogram(_synthetic_pitch())
    assert histogram_distance(histogram, histogram) == pytest.approx(0.0)


def test_temporal_pair_detects_visual_cut() -> None:
    first = visual_histogram(_synthetic_pitch())
    second = visual_histogram(np.full((360, 640, 3), (0, 0, 255), dtype=np.uint8))
    decision = assess_temporal_pair(np.eye(3), np.eye(3), first, second)
    assert decision.visual_jump
    assert not decision.compatible


def test_temporal_pair_accepts_identical_views() -> None:
    histogram = visual_histogram(_synthetic_pitch())
    decision = assess_temporal_pair(np.eye(3), np.eye(3), histogram, histogram)
    assert decision.compatible


def test_temporal_smoothing_normalizes_matrix() -> None:
    current = np.asarray([[2.0, 0, 0], [0, 2.0, 0], [0, 0, 2.0]])
    value = smooth_compatible_homographies(np.eye(3), current)
    assert value[2, 2] == pytest.approx(1.0)


def test_temporal_decay_reduces_confidence() -> None:
    assert decay_confidence(1.0, 2) == pytest.approx(0.78**2)


def test_config_rejects_invalid_keyframe_frequency(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        CalibrationConfig(output_dir=tmp_path, keyframe_frequency=0).validate()


def test_projection_rejects_ambiguous_calibration() -> None:
    records = project_observations(
        [{"foot_point_xy": [10, 20], "track_id": 1}],
        np.eye(3),
        canonical_pitch_length=105,
        canonical_pitch_width=68,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="AMBIGUOUS",
        calibration_confidence=0.9,
    )
    assert not records[0]["projection_valid"]


def test_projection_preserves_ve004_fields() -> None:
    records = project_observations(
        [
            {
                "foot_point_xy": [10, 20],
                "track_id": 7,
                "team_assignment": "TEAM_A",
                "timestamp_seconds": 1.2,
            }
        ],
        np.eye(3),
        canonical_pitch_length=105,
        canonical_pitch_width=68,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="ESTIMATED",
        calibration_confidence=0.9,
        calibration_id="cal_1",
        camera_segment_id="seg_1",
    )
    assert records[0]["track_id"] == 7
    assert records[0]["team_assignment"] == "TEAM_A"
    assert records[0]["calibration_id"] == "cal_1"


def test_hybrid_single_frame_does_not_claim_validation(tmp_path: Path) -> None:
    assessment = assess_calibration(
        _hybrid_result(),
        [{"foot_point_xy": [100.0, 100.0]}],
        CalibrationConfig(output_dir=tmp_path),
    )
    assert assessment.status is CalibrationStatus.ESTIMATED


def test_hybrid_ambiguous_result_stays_ambiguous(tmp_path: Path) -> None:
    result = _hybrid_result(CalibrationStatus.AMBIGUOUS)
    result = AdapterResult(
        **{
            field: getattr(result, field)
            for field in result.__dataclass_fields__
            if field not in {"ambiguity_flags"}
        },
        ambiguity_flags=("orientation_ambiguous",),
    )
    assessment = assess_calibration(result, (), CalibrationConfig(output_dir=tmp_path))
    assert assessment.status is CalibrationStatus.AMBIGUOUS


def test_hybrid_adapter_environment_is_local_and_original() -> None:
    environment = MatchIQHybridAdapter().inspect_environment()
    assert environment["ready"]
    assert environment["license_gate"]["external_gpl_code"] is False
    assert environment["weights"] is None


def test_hybrid_adapter_rejects_unreadable_image(tmp_path: Path) -> None:
    frame = CalibrationFrame(0, "f0", 0, 0.0, tmp_path / "missing.jpg")
    result = MatchIQHybridAdapter().calibrate(frame)
    assert result.status is CalibrationStatus.UNCALIBRATED
    assert result.failure_reason == "image_cannot_be_read"


def test_cli_accepts_matchiq_hybrid_adapter(tmp_path: Path) -> None:
    args = build_parser().parse_args(
        [
            "calibrate-image",
            "--source",
            str(tmp_path / "frame.jpg"),
            "--output",
            str(tmp_path / "out"),
            "--adapter",
            "matchiq-hybrid",
        ]
    )
    assert args.adapter == "matchiq-hybrid"


def test_runner_writes_ve005c_manifests_and_original_artifact(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.jpg"
    cv2.imwrite(str(image_path), _synthetic_pitch())

    class DeterministicHybrid:
        name = "matchiq-hybrid"
        version = "test"

        def inspect_environment(self) -> dict[str, object]:
            return {"ready": True, "device": "cpu"}

        def calibrate(self, frame: CalibrationFrame) -> AdapterResult:
            result = _hybrid_result()
            return AdapterResult(
                **{
                    field: getattr(result, field)
                    for field in result.__dataclass_fields__
                    if field != "artifact_images"
                },
                artifact_images={"line_mask": np.full((20, 20), 255, np.uint8)},
            )

    run = PitchCalibrationRunner(DeterministicHybrid()).run(
        image_path,
        CalibrationConfig(output_dir=tmp_path / "output"),
    )
    assert run.evidence_path and run.evidence_path.exists()
    assert run.correspondence_path and run.correspondence_path.exists()
    assert run.manifest["schema_version"] == "matchiq.ve-005c.pitch-calibration.v1"
    artifacts = run.manifest["frames"][0]["diagnostic_artifacts"]
    assert {"original", "line_mask"} <= artifacts.keys()
    assert json.loads(run.evidence_path.read_text(encoding="utf-8"))["frames"]
