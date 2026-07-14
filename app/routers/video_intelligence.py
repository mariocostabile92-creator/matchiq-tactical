from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models.video_intelligence import VideoProjectCreate
from app.services.video_intelligence_engine import create_project, get_project, list_coach_matches
from usage_guard import require_user


router = APIRouter(prefix="/api/video/intelligence", tags=["video-intelligence"])


@router.post("/projects")
def create_video_intelligence_project(data: VideoProjectCreate, user=Depends(require_user)):
    try:
        project = create_project(int(user["id"]), data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "project": project}


@router.get("/coach-matches")
def get_video_intelligence_coach_matches(user=Depends(require_user)):
    return {"ok": True, "matches": list_coach_matches(int(user["id"]))}


@router.get("/projects/{asset_id}")
def get_video_intelligence_project(asset_id: int, user=Depends(require_user)):
    project = get_project(int(user["id"]), asset_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto Video Intelligence non trovato")
    return {"ok": True, "project": project}
