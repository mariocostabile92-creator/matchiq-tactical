import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException

from app.repositories import tactical_assistant_repository as repository
from usage_guard import get_effective_plan


INJECTION_MARKERS=("ignore previous","ignora le istruzioni","system prompt","developer message","esegui codice","reveal secret","api key")
ACTION_WHITELIST={"historical_pattern":"/pattern-intelligence.html","weekly_briefing":"/weekly-briefing.html","training_plan":"/training-planner.html","training_session":"/training-planner.html","video_session":"/video.html","video_frame":"/video.html","video_report":"/video.html","match":"/coach.html","coach_report":"/coach.html","player":"/knowledge.html","voice_observation":"/knowledge.html","tactical_identity_profile":"/tactical-identity.html","tactical_identity_dimension":"/tactical-identity.html"}


def validate_question(text: str) -> str:
    clean=" ".join(str(text or "").split())
    if len(clean)<2 or len(clean)>1200: raise HTTPException(status_code=422,detail="La domanda deve contenere da 2 a 1200 caratteri.")
    return clean


def sanitize_source(value: Any) -> str:
    text=re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]"," ",str(value or ""))
    for marker in INJECTION_MARKERS: text=re.sub(re.escape(marker),"[contenuto non attendibile]",text,flags=re.IGNORECASE)
    return html.escape(text[:2000],quote=False)


def enforce_rate(user: Dict[str,Any]) -> None:
    if get_effective_plan(user)=="owner": return
    since=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    if repository.recent_request_count(int(user["id"]),since)>=30:
        raise HTTPException(status_code=429,detail="Troppe richieste ravvicinate. Riprova tra poco.")


def action_for(node: Dict[str,Any]) -> str:
    node_type=node.get("node_type"); base=ACTION_WHITELIST.get(node_type,"/knowledge.html"); source_id=str(node.get("source_id") or "")
    if node_type=="historical_pattern" and source_id: return f"{base}?pattern={source_id}"
    if node_type=="video_session" and source_id: return f"{base}?session={source_id}"
    return f"{base}?knowledge_node={int(node['id'])}"
