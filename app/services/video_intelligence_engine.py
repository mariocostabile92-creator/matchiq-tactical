from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Optional
from uuid import uuid4

from database import create_video_asset, get_saved_matches, get_video_asset, utc_now
from app.models.video_intelligence import AnalysisMode, EvidenceCreateRequest, ProjectStateRequest, VideoPipelineRequest, VideoProjectCreate
from app.repositories.video_intelligence_repository import load_project, save_project
from app.services.video_clip_service import build_clip_reference
from app.services.video_coach_link_service import suggest_coach_links
from app.services.video_evidence_service import build_evidence
from app.services.video_frame_ranking_service import build_candidate_pool, rank_segments
from app.services.video_segmentation_service import phase_title, segment_frames


ENGINE_VERSION = "1.0"
PROJECT_STATES = {
    "draft", "uploading", "queued", "processing", "review_ready",
    "completed", "failed", "cancelled",
}


def _clean(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def list_coach_matches(user_id: int) -> list[Dict[str, Any]]:
    matches = []
    for row in get_saved_matches(user_id):
        matches.append({
            "id": str(row.get("id") or row.get("match_id") or ""),
            "match_id": str(row.get("match_id") or ""),
            "home": _clean(row.get("home"), 120),
            "away": _clean(row.get("away"), 120),
            "competition": _clean(row.get("league"), 120),
            "created_at": row.get("created_at") or "",
        })
    return matches


def _coach_match_context(user_id: int, match_id: Optional[str]) -> Dict[str, Any]:
    wanted = _clean(match_id, 120)
    if not wanted:
        raise ValueError("Coach Mode richiede una partita collegata")
    for item in list_coach_matches(user_id):
        if wanted in {item.get("id"), item.get("match_id")}:
            return item
    raise LookupError("Partita Coach non trovata")


def create_project(user_id: int, data: VideoProjectCreate) -> Dict[str, Any]:
    coach_match = None
    if data.analysis_mode == AnalysisMode.COACH:
        coach_match = _coach_match_context(user_id, data.match_id)
    asset_id = data.video_asset_id
    if asset_id is not None and not get_video_asset(user_id, int(asset_id)):
        raise LookupError("Video non trovato")
    if asset_id is None:
        created = create_video_asset(
            user_id=user_id,
            title=_clean(data.title, 180) or "Nuovo progetto Video AI",
            club_name=_clean(data.observed_team, 160),
            source_type="session",
            status="draft",
            metadata={"created_from": "video_intelligence"},
        )
        asset_id = int(created["id"])

    now = utc_now()
    project = {
        "project_id": f"vip_{uuid4().hex}",
        "engine_version": ENGINE_VERSION,
        "analysis_mode": data.analysis_mode.value,
        "title": _clean(data.title, 180) or "Analisi Video MatchIQ",
        "observed_team": _clean(data.observed_team, 160),
        "opponent": _clean(data.opponent, 160),
        "video_type": _clean(data.video_type, 60) or "full_analysis",
        "period": _clean(data.period, 40) or "full_match",
        "perspective": _clean(data.perspective, 60) or "own_team",
        "notes": _clean(data.notes, 2000),
        "match_id": _clean(data.match_id, 120) or None,
        "context": {
            **(data.context if isinstance(data.context, dict) else {}),
            **({"coach_match": coach_match} if coach_match else {}),
        },
        "pipeline": {"status": "draft", "stage": "project", "progress": 0, "stages": {}},
        "evidences": [],
        "reports": [],
        "created_at": now,
        "updated_at": now,
    }
    saved = save_project(user_id, int(asset_id), project, status="draft", stage="project", progress=0)
    if not saved:
        raise RuntimeError("Impossibile salvare il progetto video")
    return saved


def get_project(user_id: int, asset_id: int) -> Optional[Dict[str, Any]]:
    return load_project(user_id, asset_id)


def update_project_state(user_id: int, asset_id: int, data: ProjectStateRequest) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    status = _clean(data.status, 40).lower()
    if status not in PROJECT_STATES:
        raise ValueError("Stato elaborazione non valido")
    progress = data.progress
    if progress is None:
        progress = int((project.get("pipeline") or {}).get("progress") or 0)
    progress = max(0, min(100, int(progress)))
    stage = _clean(data.stage, 60) or status
    pipeline = project.get("pipeline") if isinstance(project.get("pipeline"), dict) else {}
    pipeline.update({"status": status, "stage": stage, "progress": progress, "updated_at": utc_now()})
    if status == "failed":
        pipeline["error"] = {
            "code": _clean(data.error_code, 80) or "processing_failed",
            "message": _clean(data.error_message, 300) or "Elaborazione non completata. Il progetto resta salvato.",
        }
    elif status not in {"failed"}:
        pipeline.pop("error", None)
    project["pipeline"] = pipeline
    saved = save_project(
        user_id,
        asset_id,
        project,
        status=status,
        stage=stage,
        progress=progress,
        error=(pipeline.get("error") or {}).get("message", ""),
    )
    if not saved:
        raise RuntimeError("Impossibile aggiornare lo stato del progetto")
    return saved


def retry_project(user_id: int, asset_id: int) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    status = str((project.get("pipeline") or {}).get("status") or "")
    if status not in {"failed", "cancelled"}:
        raise ValueError("Il progetto non richiede un nuovo tentativo")
    return update_project_state(user_id, asset_id, ProjectStateRequest(status="queued", stage="queued", progress=0))


def run_pipeline(user_id: int, asset_id: int, data: VideoPipelineRequest) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    if not data.frame_times_ms:
        raise ValueError("Servono timestamp reali estratti dal video")

    pipeline = project.get("pipeline") if isinstance(project.get("pipeline"), dict) else {}
    request_key = _clean(data.idempotency_key, 160)
    if not request_key:
        raw_request = json.dumps({
            "duration_seconds": data.duration_seconds,
            "frame_times_ms": data.frame_times_ms,
            "frame_meta": data.frame_meta,
            "staff_events": data.staff_events,
        }, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        request_key = f"auto_{hashlib.sha256(raw_request).hexdigest()}"
    if request_key and pipeline.get("last_completed_key") == request_key:
        return project
    if pipeline.get("status") == "processing" and request_key and pipeline.get("active_key") == request_key:
        return project

    pipeline.update({"status": "processing", "stage": "validation", "progress": 5, "active_key": request_key, "error": None})
    pipeline["stages"] = {
        "validation": {"status": "completed", "progress": 100},
        "metadata": {"status": "completed", "progress": 100},
        "segmentation": {"status": "processing", "progress": 0},
    }
    project["pipeline"] = pipeline
    save_project(user_id, asset_id, project, status="processing", stage="segmentation", progress=20)

    duration_ms = max(0, int(float(data.duration_seconds or 0) * 1000))
    candidate_pool = build_candidate_pool(data.frame_times_ms, data.frame_meta)
    primary_pool = [
        item for item in candidate_pool
        if str(item.get("candidate_role") or "").lower() in {"primary", "selected", "verified"}
    ] or candidate_pool
    segments = rank_segments(
        segment_frames(
            [item["timestamp_ms"] for item in primary_pool],
            [item.get("frame_meta") or {} for item in primary_pool],
            duration_ms,
        ),
        candidate_pool=candidate_pool,
        duration_ms=duration_ms,
    )
    if not segments:
        update_project_state(
            user_id,
            asset_id,
            ProjectStateRequest(
                status="failed",
                stage="segmentation",
                progress=20,
                error_code="no_reliable_segments",
                error_message="Nessun segmento affidabile ricavato dai timestamp forniti.",
            ),
        )
        raise ValueError("Nessun segmento affidabile ricavato dai timestamp forniti")

    evidences = []
    for segment in segments:
        signals = segment.get("signals") or []
        observed = "Fotogramma reale disponibile al timestamp indicato."
        if signals:
            observed += " Segnali dichiarati dal selettore: " + ", ".join(signals[:5]) + "."
        interpretation = None if segment["phase_type"] == "unclassified" else phase_title(segment["phase_type"])
        evidence_data = EvidenceCreateRequest(
            phase_type=segment["phase_type"],
            start_timestamp_ms=segment["start_timestamp_ms"],
            end_timestamp_ms=segment["end_timestamp_ms"],
            representative_timestamp_ms=segment["representative_timestamp_ms"],
            representative_frame={
                "frame_index": segment["frame_index"],
                "timestamp_ms": segment["representative_timestamp_ms"],
                "selection_status": "suggested",
                "score": segment["frame_score"],
                "tier": segment["frame_tier"],
                "rank": segment["frame_rank"],
                "motivation": segment["frame_ranking_motivation"],
                "review_required": bool(segment.get("frame_review_required")),
            },
            title=phase_title(segment["phase_type"]),
            observation=observed,
            interpretation=interpretation,
            motivation=segment["motivation"],
            confidence_score=segment["confidence_score"],
            source_type=segment["source_type"],
        )
        evidence = build_evidence(project, asset_id, evidence_data)
        evidence["frame_candidates"] = deepcopy(segment.get("frame_candidates") or [])
        evidence["frame_selection_status"] = (
            "manual_review_required" if segment.get("frame_review_required") else "suggested"
        )
        evidence["clip_reference"] = build_clip_reference(
            asset_id,
            segment["start_timestamp_ms"],
            segment["end_timestamp_ms"],
            duration_ms,
        )
        evidences.append(evidence)

    linked = suggest_coach_links(user_id, project, evidences, data.staff_events)
    evidences = linked["evidences"]
    project["coach_context"] = {
        "match_id": project.get("match_id"),
        "events": linked["events"],
        "link_policy": "probable_until_staff_confirmation",
    }

    pipeline["stages"].update({
        "segmentation": {"status": "completed", "progress": 100, "segments": len(segments)},
        "candidate_detection": {"status": "completed", "progress": 100, "candidates": len(segments)},
        "classification": {"status": "completed", "progress": 100},
        "frame_ranking": {"status": "completed", "progress": 100, "ranked": len(segments)},
        "clip_windows": {"status": "completed", "progress": 100, "clips": len(evidences)},
        "evidence_generation": {"status": "completed", "progress": 100, "evidences": len(evidences)},
        "human_review": {"status": "pending", "progress": 0},
    })
    pipeline.update({
        "status": "review_ready",
        "stage": "human_review",
        "progress": 85,
        "last_completed_key": request_key,
        "active_key": None,
        "duration_ms": duration_ms,
    })
    project["segments"] = segments
    project["evidences"] = evidences
    project["pipeline"] = pipeline
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=85)
    if not saved:
        raise RuntimeError("Impossibile salvare i risultati dell'analisi")
    return saved
