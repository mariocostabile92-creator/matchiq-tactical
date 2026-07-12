import json

from fastapi import APIRouter, Depends, HTTPException

from app.models.weekly_briefing import WeeklyBriefingEnvelope, WeeklyBriefingGenerateRequest
from app.repositories import weekly_briefing_repository
from app.services import weekly_briefing_service
from usage_guard import require_user


router = APIRouter(prefix="/api/weekly-briefing", tags=["weekly-briefing"])


@router.post("/generate", response_model=WeeklyBriefingEnvelope)
def generate_weekly_briefing(payload: WeeklyBriefingGenerateRequest, user=Depends(require_user)):
    if len(json.dumps(payload.local_sources, ensure_ascii=False, default=str)) > 600_000:
        raise HTTPException(status_code=413, detail="Fotografia locale troppo grande")
    result = weekly_briefing_service.generate(int(user["id"]), payload)
    return WeeklyBriefingEnvelope(**result)


@router.get("/current", response_model=WeeklyBriefingEnvelope)
def current_weekly_briefing(user=Depends(require_user)):
    briefing = weekly_briefing_repository.get_latest(int(user["id"]))
    return WeeklyBriefingEnvelope(briefing=briefing)


@router.post("/{briefing_id}/read", response_model=WeeklyBriefingEnvelope)
def mark_weekly_briefing_read(briefing_id: int, user=Depends(require_user)):
    briefing = weekly_briefing_repository.mark_read(int(user["id"]), briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Weekly AI Briefing non trovato")
    return WeeklyBriefingEnvelope(briefing=briefing)
