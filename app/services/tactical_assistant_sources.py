from typing import Any, Dict, List

from app.services.tactical_assistant_policy import action_for, sanitize_source


def build(retrieval: Dict[str,Any]) -> List[Dict[str,Any]]:
    items=[]; seen=set()
    for node in retrieval.get("nodes") or []:
        if node.get("id") in seen: continue
        seen.add(node.get("id")); items.append({
          "knowledge_node_id":int(node["id"]),"source_type":str(node.get("source_type") or node.get("node_type")),"source_id":str(node.get("source_id") or ""),
          "title":sanitize_source(node.get("title")),"evidence_summary":sanitize_source(node.get("summary")),
          "reliability_level":node.get("reliability_level") or "bassa","objective_or_subjective":node.get("nature") or "dato_derivato",
          "relation_type":(node.get("relations") or [{}])[0].get("relation_type"),"action_url":action_for(node),
          "occurred_at":node.get("occurred_at"),"node_type":node.get("node_type"),"validation_state":node.get("validation_state"),
        })
    return items[:20]
