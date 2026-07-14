from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from database import create_video_asset, get_video_asset, utc_now
from app.models.video_intelligence import AnalysisMode, VideoProjectCreate
from app.repositories.video_intelligence_repository import load_project, save_project


ENGINE_VERSION = "1.0"


def _clean(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def create_project(user_id: int, data: VideoProjectCreate) -> Dict[str, Any]:
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
        "context": data.context if isinstance(data.context, dict) else {},
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

