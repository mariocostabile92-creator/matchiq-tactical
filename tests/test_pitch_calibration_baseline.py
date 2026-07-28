from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from research.pitch_calibration.adapters.base import ExternalCalibrationError
from research.pitch_calibration.adapters.tvcalib_adapter import TVCalibAdapter
from research.pitch_calibration.cli import build_parser, main
from research.pitch_calibration.contracts import (
    SCHEMA_VERSION,
    AdapterResult,
    CalibrationConfig,
    CalibrationStatus,
    DimensionsType,
)
from research.pitch_calibration.projection import (
    as_homography,
    canonical_normalized,
    inside_pitch_ratio,
    invert_homography,
    project_observations,
    project_point,
)
from research.pitch_calibration.quality_gate import assess_calibration
from research.pitch_calibration.runner import PitchCalibrationRunner
from research.pitch_calibration.sequence_loader import load_source


IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


class StubAdapter:
    name = "stub"
    version = "test-only"

    def __init__(self, result: AdapterResult | None = None) -> None:
        self.result = result or _adapter_result()

    def inspect_environment(self) -> dict[str, object]:
        return {"ready": True, "adapter": self.name, "blocking_reasons": []}

    def calibrate(self, frame: object) -> AdapterResult:
        return self.result


def _adapter_result(
    *,
    matrix: list[list[float]] | None = None,
    status: CalibrationStatus = CalibrationStatus.ESTIMATED,
    model_confidence: float | None = 0.9,
    error: float | None = 2.0,
    flags: tuple[str, ...] = (),
) -> AdapterResult:
    value = IDENTITY if matrix is None else matrix
    return AdapterResult(
        status=status,
        homography_image_to_pitch=value,
        homography_pitch_to_image=value,
        camera_parameters=None,
        model_confidence=model_confidence,
        reprojection_error_px=error,
        ambiguity_flags=flags,
    )


def _write_image(path: Path, *, width: int = 120, height: int = 80) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((height, width, 3), 80, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)
    return path


def _write_ve004_manifest(path: Path, images: list[Path]) -> Path:
    payload = {
        "schema_version": "matchiq.ve-004b.tracking-manifest.v1",
        "frames": [
            {
                "sequence_index": index,
                "frame_index": index * 10,
                "timestamp_seconds": index * 0.5,
                "source_image": str(image),
            }
            for index, image in enumerate(images)
        ],
        "observations": [
            {
                "sequence_index": index,
                "track_id": f"track_{index}",
                "timestamp_seconds": index * 0.5,
                "foot_point_xy": [10.0 + index, 20.0],
                "team_assignment": "TEAM_A",
                "observation_type": "detected",
            }
            for index in range(len(images))
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_schema_version_is_explicit() -> None:
    assert SCHEMA_VERSION == "matchiq.ve-005b.pitch-calibration.v1"


def test_config_rejects_partial_physical_dimensions(tmp_path: Path) -> None:
    config = CalibrationConfig(output_dir=tmp_path, physical_pitch_length=100.0)
    with pytest.raises(ValueError, match="both known"):
        config.validate()


def test_config_rejects_invalid_sampling(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="sample_interval"):
        CalibrationConfig(output_dir=tmp_path, sample_interval_seconds=0).validate()


def test_config_dimension_semantics(tmp_path: Path) -> None:
    canonical = CalibrationConfig(output_dir=tmp_path)
    physical = CalibrationConfig(
        output_dir=tmp_path,
        physical_pitch_length=101.0,
        physical_pitch_width=65.0,
    )
    assert canonical.dimensions_type is DimensionsType.CANONICAL
    assert physical.dimensions_type is DimensionsType.PHYSICAL


def test_as_homography_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError, match="3x3"):
        as_homography([[1.0, 0.0], [0.0, 1.0]])


def test_as_homography_rejects_non_finite_values() -> None:
    matrix = [[1.0, 0.0, 0.0], [0.0, float("nan"), 0.0], [0.0, 0.0, 1.0]]
    with pytest.raises(ValueError, match="non-finite"):
        as_homography(matrix)


def test_invert_homography_rejects_singular_matrix() -> None:
    singular = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    with pytest.raises(ValueError, match="singular"):
        invert_homography(singular)


def test_project_point_identity() -> None:
    assert project_point(IDENTITY, [12.5, 8.0]) == pytest.approx((12.5, 8.0))


def test_project_point_rejects_invalid_point() -> None:
    assert project_point(IDENTITY, [1.0]) is None


def test_canonical_normalized_coordinates() -> None:
    assert canonical_normalized((52.5, 34.0), 105.0, 68.0) == (0.5, 0.5)


def test_inside_pitch_ratio() -> None:
    ratio = inside_pitch_ratio([(1.0, 1.0), (50.0, 20.0), (200.0, 20.0)], 105.0, 68.0)
    assert ratio == pytest.approx(2 / 3)


def test_project_observations_keeps_coordinate_semantics() -> None:
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [52.5, 34.0]}],
        IDENTITY,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="VALIDATED",
        calibration_confidence=0.8,
    )
    assert projected[0]["canonical_normalized"] == [0.5, 0.5]
    assert projected[0]["pitch_position_normalized"] == [0.5, 0.5]
    assert projected[0]["foot_point_pixel"] == [52.5, 34.0]
    assert projected[0]["physical_meters"] is None


def test_project_observations_can_emit_known_physical_dimensions() -> None:
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [52.5, 34.0]}],
        IDENTITY,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=100.0,
        physical_pitch_width=64.0,
        calibration_status="VALIDATED",
        calibration_confidence=0.8,
    )
    assert projected[0]["physical_meters"] == [50.0, 32.0]


def test_project_observations_known_perspective_mapping() -> None:
    matrix = [[0.5, 0.0, 2.0], [0.0, 0.25, 3.0], [0.0, 0.0, 1.0]]
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [100.0, 80.0]}],
        matrix,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="VALIDATED",
        calibration_confidence=0.9,
    )
    assert projected[0]["pitch_position_canonical_meters"] == [52.0, 23.0]
    assert projected[0]["projection_valid"] is True


def test_project_observations_rejects_point_outside_valid_region() -> None:
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [90.0, 70.0]}],
        IDENTITY,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="VALIDATED",
        calibration_confidence=0.9,
        valid_image_region={"bbox_xyxy": [0.0, 0.0, 50.0, 50.0]},
    )
    assert projected[0]["projection_valid"] is False
    assert projected[0]["exclusion_reason"] == "foot_point_outside_valid_image_region"


def test_project_observations_rejects_low_calibration_confidence() -> None:
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [20.0, 20.0]}],
        IDENTITY,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="ESTIMATED",
        calibration_confidence=0.3,
        minimum_calibration_confidence=0.45,
    )
    assert projected[0]["projection_valid"] is False
    assert projected[0]["exclusion_reason"] == "calibration_confidence_below_threshold"


def test_project_observations_rejected_status_is_auditable() -> None:
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [20.0, 20.0]}],
        IDENTITY,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="REJECTED",
        calibration_confidence=0.0,
    )
    assert projected[0]["projection_valid"] is False
    assert projected[0]["exclusion_reason"] == "calibration_status_rejected"


def test_project_observations_rejects_position_far_outside_pitch() -> None:
    projected = project_observations(
        [{"track_id": "p1", "foot_point_xy": [500.0, 500.0]}],
        IDENTITY,
        canonical_pitch_length=105.0,
        canonical_pitch_width=68.0,
        physical_pitch_length=None,
        physical_pitch_width=None,
        calibration_status="VALIDATED",
        calibration_confidence=0.9,
    )
    assert projected[0]["projection_valid"] is False
    assert projected[0]["exclusion_reason"] == "projected_position_too_far_outside_pitch"


def test_quality_gate_uncalibrated_without_homography(tmp_path: Path) -> None:
    result = AdapterResult(
        status=CalibrationStatus.UNCALIBRATED,
        homography_image_to_pitch=None,
        homography_pitch_to_image=None,
        camera_parameters=None,
        model_confidence=None,
        reprojection_error_px=None,
    )
    assessment = assess_calibration(result, [], CalibrationConfig(output_dir=tmp_path))
    assert assessment.status is CalibrationStatus.UNCALIBRATED
    assert "missing_homography" in assessment.flags


def test_quality_gate_rejects_singular_homography(tmp_path: Path) -> None:
    singular = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    result = _adapter_result(matrix=singular)
    assessment = assess_calibration(result, [], CalibrationConfig(output_dir=tmp_path))
    assert assessment.status is CalibrationStatus.REJECTED
    assert "singular_homography" in assessment.flags


def test_quality_gate_validates_strong_result(tmp_path: Path) -> None:
    observations = [{"foot_point_xy": [30.0, 20.0]}]
    assessment = assess_calibration(
        _adapter_result(),
        observations,
        CalibrationConfig(output_dir=tmp_path),
    )
    assert assessment.status is CalibrationStatus.VALIDATED


def test_quality_gate_marks_orientation_ambiguity(tmp_path: Path) -> None:
    assessment = assess_calibration(
        _adapter_result(flags=("orientation_ambiguous",)),
        [],
        CalibrationConfig(output_dir=tmp_path),
    )
    assert assessment.status is CalibrationStatus.AMBIGUOUS


def test_quality_gate_detects_temporal_jump(tmp_path: Path) -> None:
    shifted = [[1.0, 0.0, 100.0], [0.0, 1.0, 100.0], [0.0, 0.0, 1.0]]
    assessment = assess_calibration(
        _adapter_result(matrix=shifted),
        [],
        CalibrationConfig(output_dir=tmp_path),
        previous_homography=IDENTITY,
    )
    assert assessment.status is CalibrationStatus.AMBIGUOUS
    assert "temporal_jump" in assessment.flags


def test_load_single_image(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "frame.jpg")
    frames, metadata = load_source(image, sample_interval_seconds=2.0)
    assert len(frames) == 1
    assert metadata["kind"] == "image"


def test_load_image_directory_is_sorted_and_limited(tmp_path: Path) -> None:
    _write_image(tmp_path / "b.jpg")
    _write_image(tmp_path / "a.jpg")
    frames, metadata = load_source(
        tmp_path,
        sample_interval_seconds=2.0,
        maximum_frames=1,
    )
    assert frames[0].image_path.name == "a.jpg"
    assert metadata["frames"] == 1


def test_load_source_rejects_unknown_suffix(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_source(source, sample_interval_seconds=2.0)


def test_load_ve004_manifest_preserves_observations(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "frame.jpg")
    manifest = _write_ve004_manifest(tmp_path / "tracking_manifest.json", [image])
    frames, metadata = load_source(manifest, sample_interval_seconds=2.0)
    assert metadata["kind"] == "ve004_manifest"
    assert frames[0].observations[0]["track_id"] == "track_0"


def test_load_manifest_rejects_unknown_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": "unknown"}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported manifest"):
        load_source(manifest, sample_interval_seconds=2.0)


def test_cli_help_is_available(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    assert "VE-005B" in capsys.readouterr().out


def test_cli_missing_input_returns_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [
            "calibrate-image",
            "--input",
            str(tmp_path / "missing.jpg"),
            "--output",
            str(tmp_path / "output"),
        ]
    )
    assert code == 2
    assert "source does not exist" in capsys.readouterr().err


def test_tvcalib_environment_is_blocked_without_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MATCHIQ_TVCALIB_COMMAND", raising=False)
    environment = TVCalibAdapter().inspect_environment()
    assert environment["ready"] is False
    assert environment["license_gate"]["checkpoint"].startswith("UNVERIFIED")


def test_tvcalib_adapter_rejects_invalid_json(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "frame.jpg")
    frames, _ = load_source(image, sample_interval_seconds=2.0)
    adapter = TVCalibAdapter(
        command=[
            "python",
            "-c",
            "print('not-json')",
        ],
        timeout_seconds=5,
    )
    with pytest.raises(ExternalCalibrationError, match="valid JSON"):
        adapter.calibrate(frames[0])


def test_runner_writes_blocked_outputs_for_unconfigured_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MATCHIQ_TVCALIB_COMMAND", raising=False)
    image = _write_image(tmp_path / "frame.jpg")
    output = tmp_path / "output"
    run = PitchCalibrationRunner(TVCalibAdapter()).run(
        image,
        CalibrationConfig(output_dir=output),
    )
    assert run.manifest["aggregate"]["status_distribution"] == {"UNCALIBRATED": 1}
    benchmark = json.loads(run.benchmark_path.read_text(encoding="utf-8"))
    assert benchmark["research_status"] == "BLOCKED"
    assert run.html_path.exists()


def test_runner_projects_detected_observations_and_writes_reports(tmp_path: Path) -> None:
    images = [_write_image(tmp_path / f"frame_{index}.jpg") for index in range(2)]
    manifest = _write_ve004_manifest(tmp_path / "tracking_manifest.json", images)
    output = tmp_path / "output"
    run = PitchCalibrationRunner(StubAdapter()).run(
        manifest,
        CalibrationConfig(output_dir=output),
    )
    assert run.manifest["aggregate"]["frames_processed"] == 2
    assert run.manifest["aggregate"]["projected_observations"] == 2
    assert (output / "calibration_frames.csv").exists()
    assert (output / "diagnostics" / "frame_000001_calibration.jpg").exists()
    report = run.html_path.read_text(encoding="utf-8")
    assert "MatchIQ VE-005B TVCalib Baseline" in report
    assert "No measured accuracy is claimed" in report
    assert run.manifest["configuration"]["quality_thresholds"][
        "minimum_projection_confidence"
    ] == 0.45


def test_runner_creates_output_directory_and_versioned_contract(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "frame.jpg")
    output = tmp_path / "nested" / "output"
    run = PitchCalibrationRunner(StubAdapter()).run(
        image,
        CalibrationConfig(output_dir=output),
    )
    frame = run.manifest["frames"][0]
    assert output.is_dir()
    assert frame["schema_version"] == SCHEMA_VERSION
    assert frame["calibration_id"].startswith("cal_")
    assert frame["source_id"].startswith("src_")
    assert frame["image_to_pitch_matrix"] == IDENTITY


def test_runner_core_results_are_deterministic(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "frame.jpg")
    first = PitchCalibrationRunner(StubAdapter()).run(
        image,
        CalibrationConfig(output_dir=tmp_path / "first", render_debug=False),
    )
    second = PitchCalibrationRunner(StubAdapter()).run(
        image,
        CalibrationConfig(output_dir=tmp_path / "second", render_debug=False),
    )
    first_frame = first.manifest["frames"][0]
    second_frame = second.manifest["frames"][0]
    for key in (
        "calibration_id",
        "source_id",
        "status",
        "image_to_pitch_matrix",
        "confidence",
        "quality_flags",
        "projected_observations",
    ):
        assert first_frame[key] == second_frame[key]


def test_runner_starts_new_camera_segment_on_temporal_jump(tmp_path: Path) -> None:
    images = [_write_image(tmp_path / f"frame_{index}.jpg") for index in range(2)]
    manifest = _write_ve004_manifest(tmp_path / "tracking_manifest.json", images)

    class JumpAdapter(StubAdapter):
        calls = 0

        def calibrate(self, frame: object) -> AdapterResult:
            self.calls += 1
            if self.calls == 1:
                return _adapter_result()
            return _adapter_result(
                matrix=[[1.0, 0.0, 100.0], [0.0, 1.0, 100.0], [0.0, 0.0, 1.0]]
            )

    run = PitchCalibrationRunner(JumpAdapter()).run(
        manifest,
        CalibrationConfig(output_dir=tmp_path / "output"),
    )
    assert run.manifest["aggregate"]["camera_segments"] == 2
    assert run.manifest["frames"][1]["camera_segment_id"] == "camera_segment_002"


def test_runner_preserves_manifest_camera_segment(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "frame.jpg")
    manifest = _write_ve004_manifest(tmp_path / "tracking_manifest.json", [image])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["frames"][0]["camera_segment_id"] = "camera_main"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    run = PitchCalibrationRunner(StubAdapter()).run(
        manifest,
        CalibrationConfig(output_dir=tmp_path / "output"),
    )
    assert run.manifest["frames"][0]["camera_segment_id"] == "camera_main"
    assert run.manifest["aggregate"]["camera_segments"] == 1


def test_research_module_does_not_import_production_app() -> None:
    root = Path(__file__).parents[1] / "research" / "pitch_calibration"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    assert "from main import" not in source
    assert "from app." not in source
