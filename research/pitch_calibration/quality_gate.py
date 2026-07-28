from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .contracts import AdapterResult, CalibrationConfig, CalibrationStatus
from .projection import as_homography, inside_pitch_ratio, project_point


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    status: CalibrationStatus
    evidence_confidence: float | None
    correspondence_confidence: float | None
    model_confidence: float | None
    geometric_confidence: float
    temporal_confidence: float | None
    projection_confidence: float | None
    overall_confidence: float
    flags: tuple[str, ...]
    metrics: dict[str, Any]


def assess_calibration(
    result: AdapterResult,
    observations: Iterable[dict[str, Any]],
    config: CalibrationConfig,
    *,
    previous_homography: Any | None = None,
) -> QualityAssessment:
    flags = list(result.ambiguity_flags)
    metrics: dict[str, Any] = {}
    if result.homography_image_to_pitch is None:
        flags.append("missing_homography")
        return QualityAssessment(
            status=CalibrationStatus.UNCALIBRATED,
            evidence_confidence=result.evidence_confidence,
            correspondence_confidence=result.correspondence_confidence,
            model_confidence=result.model_confidence,
            geometric_confidence=0.0,
            temporal_confidence=None,
            projection_confidence=result.projection_confidence,
            overall_confidence=0.0,
            flags=tuple(dict.fromkeys(flags)),
            metrics=metrics,
        )
    try:
        matrix = as_homography(result.homography_image_to_pitch)
    except ValueError as exc:
        flags.append(str(exc).replace(" ", "_"))
        return _rejected(result.model_confidence, flags, metrics)

    determinant = float(np.linalg.det(matrix))
    condition = float(np.linalg.cond(matrix))
    metrics.update(determinant=determinant, condition_number=condition)
    if abs(determinant) < 1.0e-12:
        flags.append("singular_homography")
    if not np.isfinite(condition) or condition > config.maximum_condition_number:
        flags.append("ill_conditioned_homography")
    if flags and any(flag in flags for flag in ("singular_homography", "ill_conditioned_homography")):
        return _rejected(result.model_confidence, flags, metrics)

    error = result.reprojection_error_px
    metrics["reprojection_error_px"] = error
    geometric_components = [1.0]
    if error is None:
        flags.append("reprojection_error_unavailable")
        geometric_components.append(0.45)
    else:
        geometric_components.append(max(0.0, 1.0 - error / config.maximum_reprojection_error_px))

    field_element_count = len(result.detected_field_elements)
    metrics["detected_field_element_count"] = field_element_count
    if field_element_count:
        geometric_components.append(min(1.0, field_element_count / 4.0))
    else:
        flags.append("field_elements_unavailable")
        geometric_components.append(0.45)

    coverage = result.coverage_score
    metrics["coverage_score"] = coverage
    if coverage is not None:
        geometric_components.append(max(0.0, min(1.0, coverage)))
        if coverage < 0.30:
            flags.append("insufficient_field_coverage")

    projected_points = []
    for observation in observations:
        point = observation.get("foot_point_xy")
        if isinstance(point, (list, tuple)) and len(point) == 2:
            projected = project_point(matrix, point)
            if projected is not None:
                projected_points.append(projected)
    ratio = inside_pitch_ratio(
        projected_points,
        config.canonical_pitch_length,
        config.canonical_pitch_width,
    )
    metrics["projected_player_inside_ratio"] = ratio
    if ratio is not None:
        geometric_components.append(ratio)
        if ratio < config.minimum_projected_player_inside_ratio:
            flags.append("players_project_outside_pitch")

    geometric_confidence = float(np.mean(geometric_components))
    temporal_confidence = _temporal_confidence(
        matrix,
        previous_homography,
        config.maximum_temporal_corner_jump,
        metrics,
        flags,
    )
    evidence = result.evidence_confidence
    correspondence = result.correspondence_confidence
    projection = result.projection_confidence
    metrics["evidence_confidence"] = evidence
    metrics["correspondence_confidence"] = correspondence
    metrics["projection_confidence"] = projection
    if evidence is not None and evidence < config.minimum_evidence_confidence:
        flags.append("evidence_confidence_below_threshold")
    if (
        correspondence is not None
        and correspondence < config.minimum_correspondence_confidence
    ):
        flags.append("correspondence_confidence_below_threshold")
    model = result.model_confidence
    available = [geometric_confidence]
    if evidence is not None:
        available.append(evidence)
    if correspondence is not None:
        available.append(correspondence)
    if model is not None:
        available.append(model)
    if temporal_confidence is not None:
        available.append(temporal_confidence)
    if projection is not None:
        available.append(projection)
    overall = float(np.mean(available))

    if result.status in (CalibrationStatus.REJECTED, CalibrationStatus.UNCALIBRATED):
        status = result.status
    elif (
        "orientation_ambiguous" in flags
        or "temporal_jump" in flags
        or "insufficient_field_coverage" in flags
    ):
        status = CalibrationStatus.AMBIGUOUS
    elif (
        result.calibration_origin == "matchiq_classical_geometry"
        and result.status is CalibrationStatus.ESTIMATED
        and temporal_confidence is None
    ):
        status = CalibrationStatus.ESTIMATED
    elif (
        model is not None
        and model >= config.minimum_model_confidence
        and geometric_confidence >= config.minimum_geometric_confidence
        and not any(
            flag
            for flag in flags
            if flag not in ("field_elements_unavailable", "reprojection_error_unavailable")
        )
    ):
        status = CalibrationStatus.VALIDATED
    elif geometric_confidence >= config.minimum_geometric_confidence:
        status = CalibrationStatus.ESTIMATED
    else:
        status = CalibrationStatus.REJECTED
    return QualityAssessment(
        status=status,
        evidence_confidence=evidence,
        correspondence_confidence=correspondence,
        model_confidence=model,
        geometric_confidence=geometric_confidence,
        temporal_confidence=temporal_confidence,
        projection_confidence=projection,
        overall_confidence=overall,
        flags=tuple(dict.fromkeys(flags)),
        metrics=metrics,
    )


def _temporal_confidence(
    matrix: np.ndarray,
    previous: Any | None,
    maximum_jump: float,
    metrics: dict[str, Any],
    flags: list[str],
) -> float | None:
    if previous is None:
        return None
    try:
        previous_matrix = as_homography(previous)
    except ValueError:
        flags.append("invalid_previous_homography")
        return None
    image_reference = np.float64(
        [[0.0, 0.0], [1920.0, 0.0], [1920.0, 1080.0], [0.0, 1080.0]]
    )
    current = _project_array(matrix, image_reference)
    before = _project_array(previous_matrix, image_reference)
    if current is None or before is None:
        return None
    diagonal = max(1.0, float(np.linalg.norm([105.0, 68.0])))
    jump = float(np.mean(np.linalg.norm(current - before, axis=1)) / diagonal)
    metrics["temporal_corner_jump"] = jump
    if jump > maximum_jump:
        flags.append("temporal_jump")
    return max(0.0, 1.0 - jump / max(maximum_jump, 1.0e-9))


def _project_array(matrix: np.ndarray, points: np.ndarray) -> np.ndarray | None:
    homogeneous = np.column_stack((points, np.ones(len(points))))
    values = (matrix @ homogeneous.T).T
    if np.any(np.abs(values[:, 2]) < 1.0e-12):
        return None
    result = values[:, :2] / values[:, 2:3]
    return result if np.isfinite(result).all() else None


def _rejected(
    model_confidence: float | None,
    flags: list[str],
    metrics: dict[str, Any],
) -> QualityAssessment:
    return QualityAssessment(
        status=CalibrationStatus.REJECTED,
        evidence_confidence=None,
        correspondence_confidence=None,
        model_confidence=model_confidence,
        geometric_confidence=0.0,
        temporal_confidence=None,
        projection_confidence=None,
        overall_confidence=0.0,
        flags=tuple(dict.fromkeys(flags)),
        metrics=metrics,
    )
