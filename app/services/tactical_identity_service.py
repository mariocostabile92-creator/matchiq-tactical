import hashlib
import json
import uuid
from typing import Any, Dict, Optional

from app.repositories import knowledge_repository, pattern_intelligence_repository, tactical_identity_repository as repository
from app.repositories.tactical_identity_schema import initialize_schema
from app.services import tactical_identity_knowledge
from app.services.tactical_identity_engine import build
from app.services.tactical_identity_sources import collect


def initialize_tactical_identity() -> None:
    initialize_schema()


def _workspace(user_id: int):
    return knowledge_repository.get_or_create_workspace(user_id)


def _scope(payload: Dict[str,Any]) -> Dict[str,Any]:
    return {key:payload.get(key) for key in ("team_profile_id","coach_profile_id","season","period_start","period_end","competition","formation","source_type") if payload.get(key) is not None}


def _semantic_signature(dimensions) -> str:
    fields=("dimension_type","declared_value","observed_value","validated_value","alignment_state","confidence_level","trend_direction","validation_state")
    payload=sorted(
        ({key:item.get(key) for key in fields} for item in dimensions),
        key=lambda item:item.get("dimension_type") or "",
    )
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str).encode("utf-8")).hexdigest()


def run(user_id: int,payload: Dict[str,Any]) -> Dict[str,Any]:
    workspace=_workspace(user_id); wid=int(workspace["id"]); scope=_scope(payload)
    if scope.get("team_profile_id"):
        if not pattern_intelligence_repository.team_profile_belongs(wid,int(scope["team_profile_id"])): raise ValueError("Profilo squadra non valido")
    previous=repository.get_profile(wid,user_id,scope); token=str(uuid.uuid4())
    if not repository.acquire_lock(wid,user_id,scope,token): return {"generated":False,"status":"processing","message":"Aggiornamento identita gia in corso."}
    try:
        bundle=collect(user_id,scope)
        if previous and previous["source_fingerprint"]==bundle["source_fingerprint"] and not payload.get("force"):
            repository.release_unchanged(wid,user_id,previous["id"])
            return {"generated":False,"unchanged":True,"data":repository.full_profile(wid,user_id,previous)}
        old_dimensions={item["dimension_type"]:item for item in repository.list_dimensions(previous["id"])} if previous else {}
        result=build(bundle["nodes"],old_dimensions); semantic_changed=not previous or _semantic_signature(old_dimensions.values())!=_semantic_signature(result["dimensions"])
        version=(int(previous.get("identity_version") or 0)+1) if semantic_changed and previous else (1 if not previous else int(previous.get("identity_version") or 1))
        profile=repository.save_profile(wid,user_id,scope,{**result,"source_fingerprint":bundle["source_fingerprint"],"identity_version":version})
        repository.replace_dimensions(profile["id"],result["dimensions"]); complete=repository.full_profile(wid,user_id,profile)
        if semantic_changed: repository.add_version(profile["id"],version,complete,"Fonti o validazioni rilevanti aggiornate.","source_refresh",f"user:{user_id}")
        if semantic_changed: complete=repository.full_profile(wid,user_id,profile)
        tactical_identity_knowledge.publish(wid,user_id,profile,complete["dimensions"])
        return {"generated":semantic_changed,"unchanged":not semantic_changed,"evidence_refreshed":not semantic_changed,"data":complete}
    except Exception as exc:
        repository.release_error(wid,user_id,scope,str(exc)); raise


def current(user_id: int,filters: Dict[str,Any]) -> Optional[Dict[str,Any]]:
    workspace=_workspace(user_id); profile=repository.latest_profile(int(workspace["id"]),user_id,filters)
    return repository.full_profile(int(workspace["id"]),user_id,profile,filters) if profile else None


def status(user_id: int,filters: Dict[str,Any]) -> Dict[str,Any]:
    data=current(user_id,filters)
    return {"status":data.get("status") if data else "empty","last_updated":data.get("updated_at") if data else None,"identity_version":data.get("identity_version") if data else 0,"can_run":not data or data.get("status")!="processing","processing_error":data.get("processing_error") if data else None}


def dimension(user_id: int,dimension_id: int,page: int=1,page_size: int=20) -> Optional[Dict[str,Any]]:
    workspace=_workspace(user_id); wid=int(workspace["id"]); item=repository.get_dimension(wid,user_id,dimension_id)
    if not item: return None
    return {**item,"evidence":repository.list_evidence(wid,user_id,dimension_id,page,page_size),"feedback":repository.feedback_for_dimension(dimension_id)}


def validate(user_id: int,dimension_id: int,payload: Dict[str,Any]) -> Optional[Dict[str,Any]]:
    workspace=_workspace(user_id); wid=int(workspace["id"]); item=repository.save_feedback(wid,user_id,dimension_id,payload["action"],payload.get("note"),payload.get("declared_value"))
    if not item: return None
    profile=repository.get_profile_by_id(wid,user_id,item["identity_profile_id"]); complete=repository.full_profile(wid,user_id,profile); version=int(profile["identity_version"])+1
    profile=repository.save_profile(wid,user_id,profile["filters"],{**profile,"identity_version":version,"summary":profile["summary"],"source_fingerprint":profile["source_fingerprint"],"matches_analyzed":profile["matches_analyzed"],"sources_analyzed":profile["sources_analyzed"],"overall_confidence":profile["overall_confidence"]})
    repository.add_version(profile["id"],version,repository.full_profile(wid,user_id,profile),f"Validazione staff: {payload['action']}","staff_validation",f"user:{user_id}")
    tactical_identity_knowledge.publish(wid,user_id,profile,repository.list_dimensions(profile["id"]))
    return repository.get_dimension(wid,user_id,dimension_id)


def add_note(user_id: int,dimension_id: int,note: str) -> Optional[Dict[str,Any]]:
    return validate(user_id,dimension_id,{"action":"monitor","note":note})


def compare(user_id: int,filters: Dict[str,Any]) -> Dict[str,Any]:
    data=current(user_id,filters)
    if not data: return {"items":[],"message":"Non ci sono ancora partite sufficienti per costruire l'identita tattica."}
    return {"items":[{"id":item["id"],"label":item["label"],"declared":item.get("declared_value"),"observed":item.get("observed_value"),"validated":item.get("validated_value"),"alignment_state":item["alignment_state"],"confidence_level":item["confidence_level"]} for item in data["dimensions"]],"period":{"start":data.get("period_start"),"end":data.get("period_end")}}
