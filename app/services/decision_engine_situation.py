from typing import Any, Dict, List

from app.services.decision_engine_policy import clean_text, sanitize_context


def build(payload: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    context = sanitize_context(payload.get("source_context") or {})
    parts = [payload["phase"].replace("_", " ")]
    if payload.get("minute") is not None: parts.append(f"minuto {payload['minute']}")
    if payload.get("score_state"): parts.append(f"punteggio {clean_text(payload['score_state'], 40)}")
    if context.get("team_name"): parts.append(str(context["team_name"]))
    if context.get("opponent"): parts.append(f"contro {context['opponent']}")
    if payload.get("prompt"): parts.append(clean_text(payload["prompt"], 300))
    topics=[]
    for source in sources:
        topic=source.get("tactical_topic")
        if topic and topic not in topics: topics.append(topic)
    if topics: parts.append("segnali: " + ", ".join(map(str,topics[:4])))
    return {"summary":". ".join(parts)[:1600],"context":context,"topics":topics[:8]}
