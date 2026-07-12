import uuid
from collections import defaultdict
from typing import Any, Dict, List

from app.repositories import knowledge_intelligence_repository as repository
from app.services.knowledge_intelligence_adapters import ADAPTERS


MODULE_SOURCE_TYPES={
  "knowledge":{"coach_profile","team_profile","roster_player"},"coach":{"saved_match","coach_session","coach_event","coach_report"},
  "voice_coach":{"voice_observation","voice_match_theme"},"pattern_intelligence":{"pattern","pattern_evidence"},
  "weekly_briefing":{"weekly_briefing"},"training_planner":{"training_plan","training_session","training_exercise"},
  "video_ai":{"video_asset","video_frame","video_clip","video_report"},"scout":{"scout_report"},
}


def _key(node: Dict[str,Any]) -> tuple:
    return node["node_type"],node["source_type"],str(node["source_id"])


def _resolve_edges(workspace_id: int,edge_specs: List[Dict[str,Any]]) -> int:
    nodes=repository.list_nodes(workspace_id); by_key={_key(node):node for node in nodes}; by_match={str(node.get("match_id")):node for node in nodes if node["node_type"]=="match" and node.get("match_id")}; by_topic=defaultdict(list)
    for node in nodes:
        if node["node_type"]=="historical_pattern" and node.get("tactical_topic"): by_topic[node["tactical_topic"]].append(node)
    total=0
    for spec in edge_specs:
        source=by_key.get(tuple(spec["from"])); target=None
        if spec.get("to"): target=by_key.get(tuple(spec["to"]))
        elif spec.get("to_match"): target=by_match.get(str(spec["to_match"]))
        elif spec.get("to_pattern_topic"): target=(by_topic.get(spec["to_pattern_topic"]) or [None])[0]
        if not source or not target or source["id"]==target["id"]: continue
        try:
            repository.upsert_edge(workspace_id,source,target,spec["relation"],source["source_type"],source["source_id"],spec.get("explanation") or "",spec.get("confidence") or "media",spec.get("validation") or "derived",spec.get("metadata") or {})
            total+=1
        except ValueError:
            continue
    return total


def sync(user_id: int,workspace_id: int,modules: List[str]=None,force: bool=False) -> Dict[str,Any]:
    selected=modules or list(ADAPTERS); invalid=[name for name in selected if name not in ADAPTERS]
    if invalid: raise ValueError("Modulo Knowledge non supportato: "+", ".join(invalid))
    result={"modules":{},"nodes":0,"edges":0,"versions":0,"invalidated":0,"partial":False}; all_edges=[]
    for module in selected:
        token=str(uuid.uuid4()); current=repository.get_sync_state(workspace_id,module)
        if current and current.get("status")=="running" and current.get("lock_token"):
            result["modules"][module]={"status":"locked","indexed":0}; result["partial"]=True; continue
        repository.set_sync_state(workspace_id,user_id,module,"running",lock_token=token)
        try:
            bundle=ADAPTERS[module](user_id,workspace_id); source_fp=repository.fingerprint({"nodes":bundle["nodes"],"edges":bundle["edges"]})
            if current and current.get("source_fingerprint")==source_fp and not force:
                repository.set_sync_state(workspace_id,user_id,module,"completed",source_fp,metadata={"unchanged":True,"indexed":0}); result["modules"][module]={"status":"unchanged","indexed":0}; continue
            before={node["canonical_key"]:node["current_version"] for node in repository.list_nodes(workspace_id,False)}; seen=defaultdict(list)
            for item in bundle["nodes"]:
                node=repository.upsert_node(workspace_id,user_id,item.pop("node_type"),module,item.pop("source_type"),str(item.pop("source_id")),item)
                seen[node["source_type"]].append(node["source_id"]); result["nodes"]+=1
                if int(node["current_version"])>int(before.get(node["canonical_key"],0) or 0) and node["canonical_key"] in before: result["versions"]+=1
            invalidated=sum(repository.deactivate_missing(workspace_id,source_type,seen.get(source_type,[])) for source_type in MODULE_SOURCE_TYPES[module])
            result["invalidated"]+=invalidated; all_edges.extend(bundle["edges"]); repository.set_sync_state(workspace_id,user_id,module,"completed",source_fp,metadata={"indexed":len(bundle["nodes"]),"invalidated":invalidated}); result["modules"][module]={"status":"completed","indexed":len(bundle["nodes"]),"invalidated":invalidated}
        except Exception as exc:
            repository.set_sync_state(workspace_id,user_id,module,"error",error=str(exc),metadata={"retry_available":True}); result["modules"][module]={"status":"error","error":"Fonte non aggiornata. Riprova la sincronizzazione."}; result["partial"]=True
    result["edges"]=_resolve_edges(workspace_id,all_edges)
    return result


def rebuild(user_id: int,workspace_id: int) -> Dict[str,Any]:
    return sync(user_id,workspace_id,force=True)


def sync_module_safely(user_id: int,module: str) -> None:
    try:
        from app.repositories import knowledge_repository
        workspace=knowledge_repository.get_or_create_workspace(user_id)
        sync(user_id,int(workspace["id"]),[module],False)
    except Exception:
        # Knowledge is an auxiliary index: source writes must always remain authoritative.
        return
