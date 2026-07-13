from typing import Any, Dict

from app.services import knowledge_intelligence_service


def retrieve(user_id: int,query: Dict[str,Any]) -> Dict[str,Any]:
    payload={key:query.get(key) for key in ("team","question","period","themes","players","zones","source_types","node_types","source_id","node_id","match_id","season","validation_state","minimum_reliability","limit")}
    search_terms=list(query.get("themes") or query.get("players") or query.get("modules") or [""])[:3]
    payload["players"]=[]
    if payload.get("source_id") or payload.get("node_id"): payload["team"]=None
    node_types=list(payload.get("node_types") or [None]); combined=None; seen=set()
    for node_type in node_types:
      for search_term in search_terms:
        current=dict(payload); current["node_types"]=[node_type] if node_type else []; current["question"]={"text":str(search_term)[:200]}
        result=knowledge_intelligence_service.memory_query(user_id,current)
        if combined is None: combined={**result,"nodes":[],"results":[],"relations":[],"evidence":[],"provenance":[],"contradictions":[]}
        for key in ("nodes","results","evidence","provenance","contradictions"):
            for item in result.get(key) or []:
                identity=item.get("id") if isinstance(item,dict) else str(item)
                marker=(key,identity)
                if marker not in seen: seen.add(marker); combined[key].append(item)
        combined["relations"].extend(result.get("relations") or [])
        combined["limits"]=list(dict.fromkeys([*(combined.get("limits") or []),*(result.get("limits") or [])]))
    return combined or knowledge_intelligence_service.memory_query(user_id,{**payload,"question":{"text":""}})
