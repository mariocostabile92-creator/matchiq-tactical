from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from database import create_video_asset, get_saved_matches, get_video_asset, utc_now
from app.models.video_intelligence import AnalysisMode, VideoProjectCreate
from app.repositories.video_intelligence_repository import load_project, save_project


ENGINE_VERSION = "1.0"


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
