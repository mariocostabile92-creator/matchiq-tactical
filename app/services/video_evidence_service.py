from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List
from uuid import uuid4

from database import utc_now
from app.models.video_intelligence import (
    ConfidenceLabel,
    EvidenceCreateRequest,
    EvidenceReviewRequest,
    ReviewStatus,
    VideoEvidence,
)
from app.repositories.video_intelligence_repository import load_project, save_project


def confidence_label(score: float) -> str:
    score = max(0.0, min(1.0, float(score or 0)))
    if score >= 0.75:
        return ConfidenceLabel.HIGH.value
    if score >= 0.45:
        return ConfidenceLabel.MEDIUM.value
    return ConfidenceLabel.LOW.value


def _validate_timestamps(start_ms: int, end_ms: int, representative_ms: int) -> tuple[int, int, int]:
    start_ms = max(0, int(start_ms))
    end_ms = max(start_ms, int(end_ms))
    representative_ms = max(start_ms, min(end_ms, int(representative_ms)))
    return start_ms, end_ms, representative_ms


def build_evidence(project: Dict[str, Any], asset_id: int, data: EvidenceCreateRequest) -> Dict[str, Any]:
    start_ms, end_ms, representative_ms = _validate_timestamps(
        data.start_timestamp_ms,
        data.end_timestamp_ms,
        data.representative_timestamp_ms,
    )
    score = max(0.0, min(1.0, float(data.confidence_score or 0)))
    evidence = VideoEvidence(
        evidence_id=f"ev_{uuid4().hex}",
        project_id=str(project.get("project_id") or ""),
        video_id=int(asset_id),
        analysis_mode=str(project.get("analysis_mode") or "analysis"),
        phase_type=str(data.phase_type or "unclassified")[:120],
        event_type=str(data.event_type or "")[:120] or None,
        team_context=str(data.team_context or "")[:120] or None,
        start_timestamp_ms=start_ms,
        end_timestamp_ms=end_ms,
        representative_timestamp_ms=representative_ms,
        representative_frame=deepcopy(data.representative_frame or {}),
        title=str(data.title or "Evidenza video")[:180],
        observation=str(data.observation or "")[:1200],
        interpretation=str(data.interpretation or "")[:1200] or None,
        motivation=str(data.motivation or "")[:800],
        confidence_score=score,
        confidence_label=confidence_label(score),
        source_type=str(data.source_type or "staff_manual")[:80],
        created_at=utc_now(),
    )
    return evidence.model_dump() if hasattr(evidence, "model_dump") else evidence.dict()


def add_evidence(user_id: int, asset_id: int, data: EvidenceCreateRequest) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    evidence = build_evidence(project, asset_id, data)
    evidences.append(evidence)
    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile salvare l'evidenza")
    return evidence


def list_evidences(user_id: int, asset_id: int, include_rejected: bool = True) -> List[Dict[str, Any]]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    items = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    return [item for item in items if isinstance(item, dict) and (include_rejected or item.get("review_status") != "rejected")]


def review_evidence(
    user_id: int,
    asset_id: int,
    evidence_id: str,
    reviewer_id: int,
    data: EvidenceReviewRequest,
) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = None
    for evidence in evidences:
        if isinstance(evidence, dict) and evidence.get("evidence_id") == evidence_id:
            found = evidence
            break
    if not found:
        raise LookupError("Evidenza non trovata")

    found["review_status"] = data.status.value
    found["reviewed_by"] = int(reviewer_id)
    found["reviewed_at"] = utc_now()
    for key in ("title", "observation", "interpretation", "phase_type"):
        value = getattr(data, key)
        if value is not None:
            found[key] = str(value).strip()[:1200]
    if data.status == ReviewStatus.CORRECTED:
        found["user_correction"] = str(data.user_correction or "Correzione dello staff").strip()[:1200]
    elif data.user_correction is not None:
        found["user_correction"] = str(data.user_correction).strip()[:1200]

    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile salvare la revisione")
    return deepcopy(found)
