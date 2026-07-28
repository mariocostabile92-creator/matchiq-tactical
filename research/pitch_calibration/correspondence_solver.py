from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
from math import hypot

import cv2
import numpy as np

from .field_evidence import FieldEvidence
from .field_model import CanonicalPitchModel
from .geometric_refinement import refine_homography
from .homography_solver import (
    HomographyEstimate,
    estimate_homography,
    reprojection_errors,
)
from .line_detection import ImageSegment, segment_intersection


@dataclass(frozen=True, slots=True)
class SemanticCorrespondence:
    correspondence_id: str
    image_element: str
    image_point: tuple[float, float]
    canonical_element: str
    canonical_point: tuple[float, float]
    confidence: float
    provenance: str
    ambiguity: str | None
    geometric_support: float
    exclusion_reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "correspondence_id": self.correspondence_id,
            "image_element": self.image_element,
            "image_point": [round(value, 3) for value in self.image_point],
            "canonical_element": self.canonical_element,
            "canonical_point": [round(value, 4) for value in self.canonical_point],
            "confidence": round(self.confidence, 6),
            "provenance": self.provenance,
            "ambiguity": self.ambiguity,
            "geometric_support": round(self.geometric_support, 6),
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass(frozen=True, slots=True)
class CalibrationHypothesis:
    hypothesis_id: str
    region_id: str
    orientation: str
    correspondences: tuple[SemanticCorrespondence, ...]
    estimate: HomographyEstimate
    line_support: float
    grass_support: float
    plausibility: float
    score: float

    def as_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "region_id": self.region_id,
            "orientation": self.orientation,
            "score": round(self.score, 6),
            "line_support": round(self.line_support, 6),
            "grass_support": round(self.grass_support, 6),
            "plausibility": round(self.plausibility, 6),
            "inlier_ratio": round(self.estimate.inlier_ratio, 6),
            "reprojection_error_px": self.estimate.reprojection_error_px,
            "condition_number": self.estimate.condition_number,
            "spatial_spread": round(self.estimate.spatial_spread, 6),
            "failure_reason": self.estimate.failure_reason,
            "correspondences": [item.as_dict() for item in self.correspondences],
        }


def solve_correspondences(
    evidence: FieldEvidence,
    model: CanonicalPitchModel,
    image_shape: tuple[int, int, int],
    *,
    seed: int = 7,
    maximum_hypotheses: int = 24,
) -> list[CalibrationHypothesis]:
    height, width = image_shape[:2]
    quadrilaterals = _candidate_quadrilaterals(evidence.segments[:16], width, height)
    regions = _canonical_regions(model)
    hypotheses: list[CalibrationHypothesis] = []
    counter = 0
    for image_quad, line_ids, geometric_support in quadrilaterals:
        for region_id, canonical_quad in regions:
            for orientation, target in _orientations(canonical_quad):
                correspondences = tuple(
                    SemanticCorrespondence(
                        correspondence_id=f"corr_{counter:05d}_{index}",
                        image_element=f"{line_ids[index // 2]}+{line_ids[2 + index % 2]}",
                        image_point=(float(image_quad[index][0]), float(image_quad[index][1])),
                        canonical_element=f"{region_id}_corner_{index}",
                        canonical_point=(float(target[index][0]), float(target[index][1])),
                        confidence=geometric_support,
                        provenance="classical_line_family_intersection",
                        ambiguity="left_right_orientation" if orientation != "forward" else None,
                        geometric_support=geometric_support,
                    )
                    for index in range(4)
                )
                estimate = estimate_homography(
                    np.asarray(image_quad, dtype=np.float64),
                    np.asarray(target, dtype=np.float64),
                    seed=seed,
                )
                if estimate.matrix is None or estimate.inverse is None:
                    counter += 1
                    continue
                estimate = _refine_estimate(
                    estimate,
                    np.asarray(image_quad, dtype=np.float64),
                    np.asarray(target, dtype=np.float64),
                )
                line_support = _model_line_support(
                    estimate.inverse,
                    model,
                    evidence.line_mask,
                )
                grass_support = _projected_pitch_grass_support(
                    estimate.inverse,
                    model,
                    evidence.grass_mask,
                )
                plausibility = _projection_plausibility(
                    estimate.inverse,
                    model,
                    width,
                    height,
                )
                score = float(
                    0.43 * line_support
                    + 0.22 * grass_support
                    + 0.20 * plausibility
                    + 0.15 * geometric_support
                )
                hypotheses.append(
                    CalibrationHypothesis(
                        hypothesis_id=f"hyp_{counter:05d}",
                        region_id=region_id,
                        orientation=orientation,
                        correspondences=correspondences,
                        estimate=estimate,
                        line_support=line_support,
                        grass_support=grass_support,
                        plausibility=plausibility,
                        score=score,
                    )
                )
                counter += 1
    return sorted(hypotheses, key=lambda item: item.score, reverse=True)[:maximum_hypotheses]


def _refine_estimate(
    estimate: HomographyEstimate,
    image_points: np.ndarray,
    pitch_points: np.ndarray,
) -> HomographyEstimate:
    assert estimate.matrix is not None
    refined = refine_homography(
        estimate.matrix,
        image_points,
        pitch_points,
        estimate.inlier_mask,
    )
    try:
        inverse = np.linalg.inv(refined)
    except np.linalg.LinAlgError:
        return estimate
    errors = reprojection_errors(refined, image_points, pitch_points)
    inliers = np.asarray(estimate.inlier_mask, dtype=bool)
    used_errors = errors[inliers] if len(inliers) and np.any(inliers) else errors
    return replace(
        estimate,
        matrix=refined,
        inverse=inverse,
        reprojection_error_px=float(np.mean(used_errors)),
        condition_number=float(np.linalg.cond(refined)),
    )


def orientation_is_ambiguous(
    hypotheses: list[CalibrationHypothesis],
    *,
    score_margin: float = 0.055,
) -> bool:
    if len(hypotheses) < 2:
        return False
    best = hypotheses[0]
    for candidate in hypotheses[1:]:
        if candidate.orientation != best.orientation and best.score - candidate.score < score_margin:
            return True
    return False


def _candidate_quadrilaterals(
    segments: list[ImageSegment],
    width: int,
    height: int,
) -> list[tuple[np.ndarray, tuple[str, str, str, str], float]]:
    if len(segments) < 4:
        return []
    features = np.asarray(
        [[np.cos(np.deg2rad(2 * item.angle)), np.sin(np.deg2rad(2 * item.angle))] for item in segments],
        dtype=np.float32,
    )
    cv2.setRNGSeed(7)
    _, labels, _ = cv2.kmeans(
        features,
        2,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0e-4),
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    families = [
        [segment for segment, label in zip(segments, labels.reshape(-1), strict=True) if label == family]
        for family in (0, 1)
    ]
    if min(map(len, families)) < 2:
        return []
    result: list[tuple[np.ndarray, tuple[str, str, str, str], float]] = []
    diagonal = hypot(width, height)
    for pair_a in combinations(families[0][:6], 2):
        if _pair_separation(pair_a) < diagonal * 0.05:
            continue
        for pair_b in combinations(families[1][:6], 2):
            if _pair_separation(pair_b) < diagonal * 0.05:
                continue
            points = (
                segment_intersection(pair_a[0], pair_b[0]),
                segment_intersection(pair_a[1], pair_b[0]),
                segment_intersection(pair_a[1], pair_b[1]),
                segment_intersection(pair_a[0], pair_b[1]),
            )
            if any(point is None for point in points):
                continue
            quad = np.asarray(points, dtype=np.float64)
            if not np.isfinite(quad).all() or abs(cv2.contourArea(quad.astype(np.float32))) < width * height * 0.008:
                continue
            margin_x, margin_y = width * 0.25, height * 0.25
            if np.any(quad[:, 0] < -margin_x) or np.any(quad[:, 0] > width + margin_x):
                continue
            if np.any(quad[:, 1] < -margin_y) or np.any(quad[:, 1] > height + margin_y):
                continue
            support = min(
                1.0,
                sum(item.length for item in (*pair_a, *pair_b)) / (4.0 * diagonal),
            )
            result.append(
                (
                    quad,
                    (
                        pair_a[0].segment_id,
                        pair_a[1].segment_id,
                        pair_b[0].segment_id,
                        pair_b[1].segment_id,
                    ),
                    support,
                )
            )
    return sorted(result, key=lambda item: item[2], reverse=True)[:12]


def _canonical_regions(model: CanonicalPitchModel) -> list[tuple[str, np.ndarray]]:
    l, w = model.length, model.width
    return [
        ("full_pitch", np.float64([[0, 0], [l, 0], [l, w], [0, w]])),
        ("left_half", np.float64([[0, 0], [l / 2, 0], [l / 2, w], [0, w]])),
        ("right_half", np.float64([[l / 2, 0], [l, 0], [l, w], [l / 2, w]])),
        ("left_penalty_band", np.float64([[0, 13.84], [16.5, 13.84], [16.5, 54.16], [0, 54.16]])),
        ("right_penalty_band", np.float64([[88.5, 13.84], [l, 13.84], [l, 54.16], [88.5, 54.16]])),
    ]


def _orientations(quad: np.ndarray) -> list[tuple[str, np.ndarray]]:
    return [
        ("forward", quad),
        ("reversed", quad[[1, 0, 3, 2]]),
    ]


def _pair_separation(pair: tuple[ImageSegment, ImageSegment]) -> float:
    first_mid = np.mean(np.asarray((pair[0].start, pair[0].end)), axis=0)
    second_mid = np.mean(np.asarray((pair[1].start, pair[1].end)), axis=0)
    return float(np.linalg.norm(first_mid - second_mid))


def _model_line_support(
    pitch_to_image: np.ndarray,
    model: CanonicalPitchModel,
    line_mask: np.ndarray,
) -> float:
    height, width = line_mask.shape[:2]
    canvas = np.zeros_like(line_mask)
    for segment in model.segments:
        source = np.asarray([segment.start_meters, segment.end_meters], dtype=np.float32)
        points = cv2.perspectiveTransform(source.reshape(-1, 1, 2), pitch_to_image).reshape(-1, 2)
        if not np.isfinite(points).all():
            continue
        start, end = [tuple(int(round(value)) for value in point) for point in points]
        cv2.line(canvas, start, end, 255, 5, cv2.LINE_AA)
    support_pixels = np.count_nonzero(canvas)
    if support_pixels == 0:
        return 0.0
    overlap = np.count_nonzero((canvas > 0) & (cv2.dilate(line_mask, np.ones((7, 7), np.uint8)) > 0))
    visible = np.count_nonzero((canvas > 0) & _image_bounds_mask(width, height))
    return float(overlap / max(1, visible))


def _projected_pitch_grass_support(
    pitch_to_image: np.ndarray,
    model: CanonicalPitchModel,
    grass_mask: np.ndarray,
) -> float:
    corners = np.float32([[0, 0], [model.length, 0], [model.length, model.width], [0, model.width]])
    projected = cv2.perspectiveTransform(corners.reshape(-1, 1, 2), pitch_to_image).reshape(-1, 2)
    if not np.isfinite(projected).all():
        return 0.0
    polygon_mask = np.zeros_like(grass_mask)
    cv2.fillConvexPoly(polygon_mask, np.round(projected).astype(np.int32), 255)
    area = np.count_nonzero(polygon_mask)
    if area == 0:
        return 0.0
    return float(np.count_nonzero((polygon_mask > 0) & (grass_mask > 0)) / area)


def _projection_plausibility(
    pitch_to_image: np.ndarray,
    model: CanonicalPitchModel,
    width: int,
    height: int,
) -> float:
    corners = np.float32([[0, 0], [model.length, 0], [model.length, model.width], [0, model.width]])
    projected = cv2.perspectiveTransform(corners.reshape(-1, 1, 2), pitch_to_image).reshape(-1, 2)
    if not np.isfinite(projected).all():
        return 0.0
    area = abs(cv2.contourArea(projected.astype(np.float32)))
    area_ratio = area / max(1.0, width * height)
    convex = bool(cv2.isContourConvex(projected.astype(np.float32)))
    bounded = float(
        np.mean(
            (projected[:, 0] >= -0.5 * width)
            & (projected[:, 0] <= 1.5 * width)
            & (projected[:, 1] >= -0.5 * height)
            & (projected[:, 1] <= 1.5 * height)
        )
    )
    return float(0.45 * min(1.0, area_ratio / 0.25) + 0.35 * bounded + 0.20 * convex)


def _image_bounds_mask(width: int, height: int) -> np.ndarray:
    return np.ones((height, width), dtype=bool)
