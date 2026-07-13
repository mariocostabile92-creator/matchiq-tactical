from typing import Any, Dict, List


def update(previous: Dict[str,Any],query: Dict[str,Any],sources: List[Dict[str,Any]]) -> Dict[str,Any]:
    context=dict(previous or {})
    for key in ("team","season","match_id","intent","comparison_type"):
        if query.get(key): context[key]=query[key]
    for key in ("themes","players","modules","zones"):
        if query.get(key): context[key]=query[key][:5]
    context["last_source_ids"]=[item["knowledge_node_id"] for item in sources[:8]]
    context["last_source_types"]=list(dict.fromkeys(item["source_type"] for item in sources[:8]))
    return context


def recent_context(messages: List[Dict[str,Any]],stored: Dict[str,Any]) -> Dict[str,Any]:
    context=dict(stored or {})
    for message in reversed(messages[-6:]):
        query=message.get("structured_query_json") or {}
        for key in ("team","season","match_id","intent","comparison_type"):
            if query.get(key) and not context.get(key): context[key]=query[key]
        for key in ("themes","players","modules","zones"):
            if query.get(key) and not context.get(key): context[key]=query[key]
    return context
