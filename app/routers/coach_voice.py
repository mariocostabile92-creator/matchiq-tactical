import logging
import time

from fastapi import APIRouter, HTTPException

from app.services.voice_coach_schemas import (
    VoiceCoachInterpretRequest,
    VoiceCoachInterpretResponse,
)
from app.services.voice_coach_service import interpret_voice_coach_command


router = APIRouter(prefix="/api/coach/voice", tags=["coach-voice"])
logger = logging.getLogger("matchiq.coach.voice")


@router.post("/interpret", response_model=VoiceCoachInterpretResponse)
def interpret_voice_command(payload: VoiceCoachInterpretRequest):
    started = time.perf_counter()
    try:
        result = interpret_voice_coach_command(payload)
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
