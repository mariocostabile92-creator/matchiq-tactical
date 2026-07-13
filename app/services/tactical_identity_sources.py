import hashlib
import json
from typing import Any, Dict, List

from app.services import knowledge_intelligence_service


SOURCE_NODE_TYPES = (
    "coach_profile", "team_profile", "match", "coach_event", "voice_observation", "voice_match_theme",
    "historical_pattern", "weekly_briefing", "training_plan", "training_session", "video_frame", "video_report", "coach_report",
)


def _stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _allowed(node: Dict[str, Any]) -> bool:
    if node.get("node_type") == "historical_pattern":
        return node.get("validation_state") in {"established", "confirmed_by_staff", "resolved"} or node.get("reliability_level") in {"media", "alta"}
    if node.get("node_type") == "video_frame":
        return bool(node.get("match_id")) and (node.get("validation_state") in {"confirmed", "accepted", "confirmed_by_staff"} or node.get("reliability_level") == "alta")
    if node.get("node_type") in {"training_plan", "training_session"}:
        return node.get("validation_state") in {"accettata", "modificata", "completata", "confirmed_by_staff"}
    return True


def _matches_scope(node: Dict[str,Any],scope: Dict[str,Any]) -> bool:
    metadata=node.get("metadata_json") or {}
    if scope.get("team_profile_id") and node.get("team_profile_id") and int(node["team_profile_id"])!=int(scope["team_profile_id"]): return False
    competition=str(scope.get("competition") or "").strip().lower()
    if competition:
        available=" ".join(str(value or "") for value in (node.get("competition"),metadata.get("competition"),metadata.get("league"),node.get("search_text"))).lower()
        if competition not in available: return False
    formation=str(scope.get("formation") or "").strip().lower()
    if formation:
        available=" ".join(str(value or "") for value in (metadata.get("formation"),metadata.get("module"),node.get("summary"),node.get("search_text"))).lower()
        if formation not in available: return False
    return True


def collect(user_id: int, scope: Dict[str, Any]) -> Dict[str, Any]:
    knowledge_intelligence_service.sync(user_id, ["knowledge", "coach", "voice_coach", "pattern_intelligence", "weekly_briefing", "training_planner", "video_ai"], False)
    nodes=[]; seen=set()
    for node_type in SOURCE_NODE_TYPES:
        query={"question":{"text":""},"node_types":[node_type],"limit":100,"minimum_reliability":"bassa","team":scope.get("team"),"match_id":scope.get("match_id"),"season":scope.get("season"),"period":{"from":scope.get("period_start"),"to":scope.get("period_end")}}
        for node in knowledge_intelligence_service.memory_query(user_id,query).get("nodes") or []:
            if node["id"] in seen or not _allowed(node) or not _matches_scope(node,scope): continue
            if scope.get("source_type") and node.get("source_module") != scope["source_type"]: continue
            seen.add(node["id"]); nodes.append(node)
    matches={str(node.get("match_id") or node.get("source_id")) for node in nodes if node.get("node_type")=="match"}
    match_refs={str(node.get("match_id")) for node in nodes if node.get("match_id")}
    fingerprint=hashlib.sha256(_stable([{key:node.get(key) for key in ("id","source_fingerprint","validation_state","reliability_level","updated_at")} for node in nodes]).encode("utf-8")).hexdigest()
    return {"nodes":nodes,"matches":len(matches | match_refs),"sources":len(nodes),"source_fingerprint":fingerprint}
