from __future__ import annotations

from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ..contracts import AdapterResult, CalibrationFrame, CalibrationStatus
from ..correspondence_solver import orientation_is_ambiguous, solve_correspondences
from ..field_evidence import EvidenceConfig, extract_field_evidence
from ..field_model import CanonicalPitchModel


class MatchIQHybridAdapter:
    name = "matchiq-hybrid"
    version = "ve-005c.1"

    def __init__(
        self,
        *,
        pitch_length: float = 105.0,
        pitch_width: float = 68.0,
        physical_length: float | None = None,
        physical_width: float | None = None,
        camera_profile: str = "fixed",
        seed: int = 7,
        minimum_hypothesis_score: float = 0.34,
        minimum_line_support: float = 0.05,
    ) -> None:
        self.model = CanonicalPitchModel(
            pitch_length,
            pitch_width,
            physical_length,
            physical_width,
        )
        self.evidence_config = EvidenceConfig(camera_profile=camera_profile)
        self.seed = int(seed)
        self.minimum_hypothesis_score = float(minimum_hypothesis_score)
        self.minimum_line_support = float(minimum_line_support)

    def inspect_environment(self) -> dict[str, Any]:
        return {
            "ready": True,
            "adapter": self.name,
            "adapter_version": self.version,
            "runtime": "classical-opencv-cpu",
            "device": "cpu",
            "dependencies": {
                "numpy": _package_record("numpy"),
                "opencv-python": _package_record("opencv-python"),
            },
            "weights": None,
            "license_gate": {
                "code": "MatchIQ original implementation",
                "weights": "not applicable",
                "external_gpl_code": False,
            },
            "blocking_reasons": [],
            "experimental_thresholds": {
                "minimum_hypothesis_score": self.minimum_hypothesis_score,
                "minimum_line_support": self.minimum_line_support,
                "evidence": asdict(self.evidence_config),
            },
        }

    def calibrate(self, frame: CalibrationFrame) -> AdapterResult:
        image = cv2.imread(str(frame.image_path))
        if image is None:
            return _uncalibrated("image_cannot_be_read")
        evidence = extract_field_evidence(image, self.evidence_config)
        artifacts = {
            "grass_mask": evidence.grass_mask,
            "line_mask": evidence.line_mask,
            "segments": _render_segments(image, evidence.segments),
            "keypoints": _render_keypoints(image, evidence.keypoints),
        }
        hypotheses = solve_correspondences(
            evidence,
            self.model,
            image.shape,
            seed=self.seed,
        )
        diagnostics: dict[str, Any] = {
            "evidence": evidence.summary(),
            "hypotheses": [item.as_dict() for item in hypotheses],
            "selected_hypothesis": hypotheses[0].hypothesis_id if hypotheses else None,
            "thresholds": {
                "minimum_hypothesis_score": self.minimum_hypothesis_score,
                "minimum_line_support": self.minimum_line_support,
            },
        }
        field_elements = tuple(
            {
                "element_id": item.segment_id,
                "kind": "line_segment",
                "start": list(item.start),
                "end": list(item.end),
                "polyline": [list(item.start), list(item.end)],
                "support": item.support,
            }
            for item in evidence.segments
        )
        if evidence.rejection_reasons or not hypotheses:
            reason = (
                ",".join(evidence.rejection_reasons)
                if evidence.rejection_reasons
                else "no_semantic_hypothesis"
            )
            return AdapterResult(
                status=CalibrationStatus.UNCALIBRATED,
                homography_image_to_pitch=None,
                homography_pitch_to_image=None,
                camera_parameters=None,
                model_confidence=None,
                reprojection_error_px=None,
                coverage_score=evidence.grass_ratio,
                valid_image_region=evidence.valid_region,
                calibration_origin="matchiq_classical_geometry",
                detected_field_elements=field_elements,
                failure_reason=reason,
                diagnostics=diagnostics,
                evidence_confidence=evidence.confidence,
                correspondence_confidence=0.0,
                artifact_images=artifacts,
            )
        best = hypotheses[0]
        ambiguous = orientation_is_ambiguous(hypotheses)
        correspondence_confidence = float(
            np.mean([item.confidence for item in best.correspondences])
        )
        rejected = tuple(
            {
                **correspondence.as_dict(),
                "exclusion_reason": "lower_scoring_hypothesis",
                "hypothesis_id": hypothesis.hypothesis_id,
            }
            for hypothesis in hypotheses[1:4]
            for correspondence in hypothesis.correspondences
        )
        accepted = tuple(item.as_dict() for item in best.correspondences)
        diagnostics["ambiguity_margin"] = (
            round(best.score - hypotheses[1].score, 6) if len(hypotheses) > 1 else None
        )
        if (
            best.score < self.minimum_hypothesis_score
            or best.line_support < self.minimum_line_support
        ):
            return AdapterResult(
                status=CalibrationStatus.REJECTED,
                homography_image_to_pitch=None,
                homography_pitch_to_image=None,
                camera_parameters=None,
                model_confidence=best.score,
                reprojection_error_px=best.estimate.reprojection_error_px,
                coverage_score=evidence.grass_ratio,
                valid_image_region=evidence.valid_region,
                calibration_origin="matchiq_classical_geometry",
                detected_field_elements=field_elements,
                failure_reason="hypothesis_below_quality_threshold",
                diagnostics=diagnostics,
                evidence_confidence=evidence.confidence,
                correspondence_confidence=correspondence_confidence,
                accepted_correspondences=accepted,
                rejected_correspondences=rejected,
                artifact_images=artifacts,
            )
        matrix = best.estimate.matrix
        inverse = best.estimate.inverse
        assert matrix is not None and inverse is not None
        flags = ("orientation_ambiguous",) if ambiguous else ()
        status = CalibrationStatus.AMBIGUOUS if ambiguous else CalibrationStatus.ESTIMATED
        artifacts["correspondences"] = _render_correspondences(image, accepted, rejected)
        return AdapterResult(
            status=status,
            homography_image_to_pitch=matrix.tolist(),
            homography_pitch_to_image=inverse.tolist(),
            camera_parameters=None,
            model_confidence=best.score,
            reprojection_error_px=best.estimate.reprojection_error_px,
            coverage_score=evidence.grass_ratio,
            valid_image_region=evidence.valid_region,
            calibration_origin="matchiq_classical_geometry",
            detected_field_elements=field_elements,
            ambiguity_flags=flags,
            diagnostics=diagnostics,
            evidence_confidence=evidence.confidence,
            correspondence_confidence=correspondence_confidence,
            projection_confidence=min(best.grass_support, best.plausibility),
            accepted_correspondences=accepted,
            rejected_correspondences=rejected,
            artifact_images=artifacts,
        )


def _uncalibrated(reason: str) -> AdapterResult:
    return AdapterResult(
        status=CalibrationStatus.UNCALIBRATED,
        homography_image_to_pitch=None,
        homography_pitch_to_image=None,
        camera_parameters=None,
        model_confidence=None,
        reprojection_error_px=None,
        calibration_origin="matchiq_classical_geometry",
        failure_reason=reason,
    )


def _render_segments(image: np.ndarray, segments: list[Any]) -> np.ndarray:
    canvas = image.copy()
    for segment in segments:
        cv2.line(
            canvas,
            tuple(int(round(value)) for value in segment.start),
            tuple(int(round(value)) for value in segment.end),
            (0, 220, 255),
            2,
            cv2.LINE_AA,
        )
    return canvas


def _render_keypoints(image: np.ndarray, keypoints: list[Any]) -> np.ndarray:
    canvas = image.copy()
    for keypoint in keypoints:
        cv2.circle(
            canvas,
            tuple(int(round(value)) for value in keypoint.point),
            5,
            (255, 80, 0),
            -1,
            cv2.LINE_AA,
        )
    return canvas


def _render_correspondences(
    image: np.ndarray,
    accepted: tuple[dict[str, Any], ...],
    rejected: tuple[dict[str, Any], ...],
) -> np.ndarray:
    canvas = image.copy()
    for item in rejected:
        point = item.get("image_point")
        if isinstance(point, list) and len(point) == 2:
            cv2.circle(canvas, tuple(int(round(value)) for value in point), 4, (0, 0, 220), 1)
    for item in accepted:
        point = item.get("image_point")
        if isinstance(point, list) and len(point) == 2:
            cv2.circle(canvas, tuple(int(round(value)) for value in point), 6, (0, 220, 0), -1)
    return canvas


def _package_record(package_name: str) -> dict[str, str | None]:
    try:
        package_metadata = metadata(package_name)
        return {
            "version": version(package_name),
            "license": package_metadata.get("License"),
            "homepage": package_metadata.get("Home-page"),
        }
    except PackageNotFoundError:
        return {"version": None, "license": None, "homepage": None}
