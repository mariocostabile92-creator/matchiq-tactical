import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel

from usage_guard import get_optional_user
from database import track_api_usage

logger = logging.getLogger("matchiq")

router = APIRouter()

ALLOWED_COACH_FEATURES = {
    "coach",
    "coach_report",
    "coach_pdf",
    "coach_whatsapp",
    "coach_pagelle",
    "coach_history",
    "coach_storico",
}


class CoachTrackPayload(BaseModel):
    feature: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/api/coach/track")
def track_coach_action(
    payload: CoachTrackPayload = Body(...),
    user=Depends(get_optional_user)
):
    feature = str(payload.feature or "").strip().lower()

    if feature not in ALLOWED_COACH_FEATURES:
        raise HTTPException(status_code=400, detail="Feature Coach non valida")

    user_id = None

    if isinstance(user, dict):
        user_id = user.get("id")

    try:
        track_api_usage(
            user_id=user_id,
            endpoint="/api/coach/track",
            feature=feature
        )

        return {
            "ok": True,
            "tracked": True,
            "feature": feature
        }

    except Exception as e:
        logger.exception("[COACH TRACKING] Errore tracking feature=%s", feature)
        return {
            "ok": False,
            "tracked": False,
            "feature": feature,
            "message": str(e)
        }