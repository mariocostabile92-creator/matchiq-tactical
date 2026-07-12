import logging
import time

from fastapi import APIRouter, Depends, HTTPException

from app.services.voice_coach_schemas import (
    VoiceCoachInterpretRequest,
    VoiceCoachInterpretResponse,
    VoiceCoachPlayer,
)
from app.services.voice_coach_service import interpret_voice_coach_command
from app.models.voice_coach_intelligence import VoiceObservationCreate, VoiceThemeStatusUpdate
from app.services.voice_coach_intelligence_service import (
    cancel_observation,
    delete_match_intelligence,
    enrich_interpretation,
    knowledge_players,
    match_intelligence,
    save_observation,
    update_theme_status,
)
from usage_guard import get_optional_user, require_user


router = APIRouter(prefix="/api/coach/voice", tags=["coach-voice"])
logger = logging.getLogger("matchiq.coach.voice")


@router.post("/interpret", response_model=VoiceCoachInterpretResponse)
def interpret_voice_command(payload: VoiceCoachInterpretRequest, user=Depends(get_optional_user)):
    started = time.perf_counter()
    try:
        if isinstance(user, dict) and user.get("id"):
            existing_ids = {str(player.id) for player in [*payload.context.lineup, *payload.context.bench]}
            for item in knowledge_players(int(user["id"])):
                if str(item["id"]) not in existing_ids:
                    payload.context.lineup.append(VoiceCoachPlayer(**item))
        result = enrich_interpretation(interpret_voice_coach_command(payload), payload)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "coach_voice_interpret intent=%s confidence=%.2f confirm=%s elapsed_ms=%s source=%s",
            result.intent,
            result.confidence,
            result.requires_confirmation,
            elapsed_ms,
            payload.source,
        )
        return result
    except Exception as exc:
        logger.warning("coach_voice_interpret_failed error=%s", exc)
        raise HTTPException(
            status_code=422,
            detail="Non ho capito il comando. Prova con una frase piu breve.",
        ) from exc


@router.post("/observations")
def persist_voice_observation(payload: VoiceObservationCreate, user=Depends(require_user)):
    return {"ok": True, **save_observation(int(user["id"]), payload)}


@router.get("/matches/{match_key}")
def load_voice_match_intelligence(match_key: str, user=Depends(require_user)):
    return {"ok": True, **match_intelligence(int(user["id"]), match_key)}


@router.delete("/matches/{match_key}")
def remove_voice_match_intelligence(match_key: str, user=Depends(require_user)):
    return {"ok": True, "deleted": delete_match_intelligence(int(user["id"]), match_key)}


@router.delete("/observations/{client_id}")
def remove_voice_observation(client_id: str, user=Depends(require_user)):
    result = cancel_observation(int(user["id"]), client_id)
    if not result:
        raise HTTPException(status_code=404, detail="Osservazione Voice Coach non trovata")
    return {"ok": True, "observation": result}


@router.patch("/matches/{match_key}/themes/{theme_id}")
def change_voice_theme_status(match_key: str, theme_id: int, payload: VoiceThemeStatusUpdate, user=Depends(require_user)):
    result = update_theme_status(int(user["id"]), match_key, theme_id, payload.status)
    if not result:
        raise HTTPException(status_code=404, detail="Tema Voice Coach non trovato")
    return {"ok": True, "theme": result}
