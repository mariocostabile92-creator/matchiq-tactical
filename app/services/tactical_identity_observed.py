from collections import Counter, defaultdict
from typing import Any, Dict
from app.services.tactical_identity_registry import DIMENSIONS, dimension_for_topic


WEIGHTS={"alta":1.0,"media":0.7,"bassa":0.4}
NATURE_FACTOR={"oggettiva":1.0,"osservazione_staff":0.9,"decisione_staff":0.9,"pattern_confermato":0.85,"dato_derivato":0.55,"interpretazione_ai":0.5,"suggerimento":0.25}


def _dimensions(node: Dict[str,Any]):
    topic=str(node.get("tactical_topic") or "").lower(); found=dimension_for_topic(topic)
    if node.get("node_type")=="match":
        formation=str((node.get("metadata_json") or {}).get("formation") or "")
        if formation: found.append("structure.primary_formation")
    return list(dict.fromkeys(found))


def extract(nodes: list) -> Dict[str, Dict[str,Any]]:
    groups=defaultdict(list)
    for node in nodes:
        if node.get("node_type") in {"weekly_briefing","coach_profile","team_profile"}: continue
        for dimension in _dimensions(node): groups[dimension].append(node)
    result={}
    for dimension,items in groups.items():
        matches={str(item.get("match_id")) for item in items if item.get("match_id")}; source_classes={item.get("source_module") for item in items}
        weighted=sum(WEIGHTS.get(item.get("reliability_level"),0.4)*NATURE_FACTOR.get(item.get("nature"),0.5) for item in items)
        contradictions=[item for item in items if item.get("polarity")=="contradictory" or item.get("validation_state") in {"contested_by_staff","dismissed_by_staff"}]
        values=Counter(str(item.get("title") or DIMENSIONS[dimension]["label"]) for item in items)
        result[dimension]={"items":items,"matches":len(matches),"source_classes":len(source_classes),"weighted":round(weighted,2),"contradictions":contradictions,"distribution":dict(values.most_common(5)),"value":f"{DIMENSIONS[dimension]['label']} osservata in {len(matches)} partite con {len(items)} evidenze" if matches else f"{DIMENSIONS[dimension]['label']} sostenuta da {len(items)} evidenze"}
    return result


def evidence_payload(node: Dict[str,Any]) -> Dict[str,Any]:
    metadata=node.get("metadata_json") or {}
    return {"knowledge_node_id":node["id"],"source_type":node["source_module"],"source_id":node["source_id"],"match_id":node.get("match_id"),"player_id":node.get("player_id"),"topic":node.get("tactical_topic"),"zone":node.get("zone"),"phase":metadata.get("phase"),"evidence_summary":str(node.get("summary") or node.get("title") or "")[:2000],"evidence_nature":node.get("nature") or "dato_derivato","reliability_level":node.get("reliability_level") or "bassa","evidence_weight":round(WEIGHTS.get(node.get("reliability_level"),0.4)*NATURE_FACTOR.get(node.get("nature"),0.5),2),"occurred_at":node.get("occurred_at")}
