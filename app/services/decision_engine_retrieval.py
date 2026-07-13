from typing import Any, Dict, List

from app.repositories import knowledge_intelligence_search_repository as search_repository
from app.services.decision_engine_policy import clean_text
from app.services.decision_engine_registry import ACTION_URLS, SOURCE_TYPES


VALID_STATES = {"confirmed_by_staff", "generated", "accepted", "staff_source", "completed", "derived", "not_validated", "ai_candidate"}


def collect(workspace_id: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    seen = set()
    match_id = context.get("match_id")
    topic = context.get("focus") or context.get("tactical_topic")
    for node_type in SOURCE_TYPES:
        filters = {"node_type": node_type, "page": 1, "page_size": 8}
        if match_id and node_type in {"coach_event", "voice_observation", "video_frame", "video_report", "match", "coach_report"}:
            filters["match_id"] = str(match_id)
        if topic and node_type not in {"player", "tactical_identity_profile"}: filters["text"] = clean_text(topic, 100)
        for node in search_repository.search(workspace_id, filters)["items"]:
            if node["id"] in seen: continue
            if node.get("validation_state") not in VALID_STATES and node.get("reliability_level") == "bassa": continue
            node["action_url"] = ACTION_URLS.get(node_type, "/knowledge.html")
            node["title"] = clean_text(node.get("title"), 240)
            node["summary"] = clean_text(node.get("summary"), 1000)
            nodes.append(node); seen.add(node["id"])
    order = {"alta": 3, "media": 2, "bassa": 1}
    nodes.sort(key=lambda item: (order.get(item.get("reliability_level"), 0), bool(item.get("match_id") == str(match_id))), reverse=True)
    return nodes[:24]
