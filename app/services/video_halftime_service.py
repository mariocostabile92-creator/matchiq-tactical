from __future__ import annotations

import os
from typing import Any, Dict

from database import utc_now
from app.models.video_intelligence import HalftimeAnalysisRequest
from app.repositories.video_intelligence_repository import load_project, save_project
from usage_guard import is_owner_user


HALFTIME_FLAG = "VIDEO_HALFTIME_BETA_ENABLED"
HALFTIME_USER_IDS = "VIDEO_HALFTIME_BETA_USER_IDS"
HALFTIME_EMAILS = "VIDEO_HALFTIME_BETA_EMAILS"
ACCEPTED_REVIEW_STATUSES = {"confirmed", "corrected"}


def _enabled(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _selected_values(name: str) -> set[str]:
    return {
        item.strip().lower()
        for item in str(os.getenv(name, "")).split(",")
        if item.strip()
    }


def halftime_access(user: Dict[str, Any]) -> Dict[str, Any]:
    globally_enabled = _enabled(os.getenv(HALFTIME_FLAG, "0"))
    user_id = str(user.get("id") or "").strip().lower()
    email = str(user.get("email") or "").strip().lower()
    selected = (
        user_id in _selected_values(HALFTIME_USER_IDS)
        or email in _selected_values(HALFTIME_EMAILS)
    )
    privileged = is_owner_user(user)
    available = globally_enabled and (privileged or selected)
    return {
        "available": available,
        "feature": "halftime_analysis_beta",
        "label": "Analisi intervallo beta",
        "experimental": True,
        "reason": "available" if available else "feature_not_enabled",
    }


def _confidence(evidence: Dict[str, Any]) -> float:
    value = float(evidence.get("confidence_score") or 0)
    return max(0.0, min(1.0, value / 100 if value > 1 else value))


def _priority(evidence: Dict[str, Any]) -> float:
    review_status = str(evidence.get("review_status") or "pending")
    frame = evidence.get("representative_frame") or {}
    tier_bonus = {
        "slide_ready": 0.15,
        "useful_hint": 0.06,
        "discard": -0.35,
    }.get(str(frame.get("tier") or ""), 0)
    review_bonus = 0.25 if review_status in ACCEPTED_REVIEW_STATUSES else 0
    return _confidence(evidence) + tier_bonus + review_bonus


def _timecode(timestamp_ms: int) -> str:
    seconds = max(0, int(timestamp_ms or 0) // 1000)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def generate_halftime_analysis(
    user: Dict[str, Any],
    asset_id: int,
    data: HalftimeAnalysisRequest,
) -> Dict[str, Any]:
    access = halftime_access(user)
    if not access["available"]:
        raise PermissionError("Analisi intervallo beta non abilitata per questo account")

    user_id = int(user["id"])
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    if str(project.get("period") or "") != "first_half":
        raise ValueError("Per il beta intervallo seleziona Primo tempo nel contesto dell'analisi")

    evidences = [
        item for item in (project.get("evidences") or [])
        if isinstance(item, dict) and str(item.get("review_status") or "pending") != "rejected"
    ]
    if not evidences:
        raise ValueError("Avvia prima Video Intelligence sul primo tempo")

    ranked = sorted(evidences, key=_priority, reverse=True)[: data.max_evidences]
    facts = []
    for item in ranked:
        timestamp_ms = int(item.get("representative_timestamp_ms") or 0)
        review_status = str(item.get("review_status") or "pending")
        facts.append({
            "evidence_id": item.get("evidence_id"),
            "timestamp_ms": timestamp_ms,
            "timecode": _timecode(timestamp_ms),
            "title": str(item.get("title") or "Evidenza video")[:160],
            "phase_type": str(item.get("phase_type") or "unclassified")[:80],
            "observation": str(item.get("observation") or "")[:420],
            "motivation": str(item.get("motivation") or "")[:260],
            "confidence_score": round(_confidence(item), 3),
            "review_status": review_status,
            "requires_staff_verification": review_status not in ACCEPTED_REVIEW_STATUSES,
            "representative_frame": item.get("representative_frame") or {},
            "clip_reference": item.get("clip_reference"),
        })

    pending_count = sum(1 for item in facts if item["requires_staff_verification"])
    result = {
        "analysis_id": f"halftime_{asset_id}_{len(project.get('halftime_runs') or []) + 1}",
        "project_id": project.get("project_id"),
        "video_asset_id": asset_id,
        "title": "Analisi intervallo sperimentale",
        "experimental": True,
        "evidence_policy": "Solo evidenze video del primo tempo; le proposte non confermate richiedono verifica dello staff.",
        "summary": f"{len(facts)} momenti prioritari disponibili; {pending_count} richiedono ancora verifica.",
        "facts": facts,
        "points_to_verify": [
            f"Verifica il momento {item['timecode']}: {item['title']}"
            for item in facts if item["requires_staff_verification"]
        ],
        "generated_at": utc_now(),
    }

    history = [item for item in (project.get("halftime_runs") or []) if isinstance(item, dict)]
    project["halftime_runs"] = (history + [result])[-10:]
    pipeline = project.get("pipeline") if isinstance(project.get("pipeline"), dict) else {}
    saved = save_project(
        user_id,
        asset_id,
        project,
        status=str(pipeline.get("status") or project.get("asset_status") or "review_ready"),
        stage=str(pipeline.get("stage") or "human_review"),
        progress=int(pipeline.get("progress") or 85),
    )
    if not saved:
        raise RuntimeError("Impossibile salvare l'analisi intervallo")
    return result
