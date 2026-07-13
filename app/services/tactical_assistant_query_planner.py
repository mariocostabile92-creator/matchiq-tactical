import re
from datetime import date, timedelta
from typing import Any, Dict

from app.services.tactical_assistant_intents import SOURCE_BY_INTENT, detect_intent, detect_themes


MODULE_RE=re.compile(r"\b(\d-\d-\d(?:-\d)?|\d-\d-\d-\d)\b")
PLAYER_RE=re.compile(r"(?:su|di|riguardano|parlami di)\s+([A-ZÀ-Ý][\wÀ-ÿ'-]{2,}(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]{2,})?)")


def _period(text: str) -> Dict[str,str]:
    today=date.today(); clean=text.lower()
    if "ultime tre partite" in clean: return {"recent_matches":"3"}
    if "ultima partita" in clean: return {"recent_matches":"1"}
    if "ultimo mese" in clean: return {"from":(today-timedelta(days=30)).isoformat(),"to":today.isoformat()}
    if "ultimi 60 giorni" in clean: return {"from":(today-timedelta(days=60)).isoformat(),"to":today.isoformat()}
    return {}


def _needs_clarification(text: str,intent: str,themes,players,context: Dict[str,Any]) -> str:
    clean=text.lower().strip()
    if clean in {"come stiamo andando","come stiamo andando?","dimmi di piu","parlami della squadra"}:
        return "Vuoi confrontare risultati, pressing, costruzione, pattern o rendimento individuale?"
    if clean.startswith("parlami di ") and players:
        return "Vuoi analizzare osservazioni dello staff, eventi, profilo rosa o pattern collegati?"
    if intent=="context_comparison" and "meglio" in clean and not MODULE_RE.search(clean):
        return "Quali moduli o contesti vuoi confrontare?"
    return ""


def plan(question: str,conversation_context: Dict[str,Any],request_context: Dict[str,Any]) -> Dict[str,Any]:
    text=" ".join(question.strip().split()); intent=detect_intent(text); themes=detect_themes(text)
    player_match=PLAYER_RE.search(text); players=[player_match.group(1)] if player_match else []
    modules=MODULE_RE.findall(text); period=_period(text)
    if not themes and len(text.split())<8: themes=list(conversation_context.get("themes") or [])[:2]
    if not players and any(word in text.lower() for word in ("lui","giocatore","e nelle")): players=list(conversation_context.get("players") or [])[:2]
    scope={**(conversation_context or {}),**(request_context or {})}; clarification=_needs_clarification(text,intent,themes,players,scope)
    node_types=SOURCE_BY_INTENT.get(intent,[]); source_id=None; node_id=None
    for key,node_type in (("pattern_id","historical_pattern"),("briefing_id","weekly_briefing"),("training_plan_id","training_plan"),("video_id","video_session"),("identity_dimension_id","tactical_identity_dimension"),("identity_profile_id","tactical_identity_profile"),("decision_case_id","decision_case"),("decision_option_id","decision_option")):
        if request_context.get(key): source_id=str(request_context[key]); node_types=[node_type]; break
    if request_context.get("knowledge_node_id"):
        try: node_id=int(request_context["knowledge_node_id"])
        except (TypeError,ValueError): node_id=None
    return {
      "intent":intent,"question":{"text":text[:200]},"period":period,"season":scope.get("season"),"team":scope.get("team"),
      "match_id":scope.get("match_id"),"players":players,"modules":modules,"themes":themes,"zones":[],
      "source_types":[],"node_types":node_types,"source_id":source_id,"node_id":node_id,"minimum_reliability":"bassa","limit":20,
      "comparison_type":"descriptive" if intent in {"context_comparison","temporal_comparison"} else None,
      "needs_clarification":bool(clarification),"clarification_question":clarification,
    }
