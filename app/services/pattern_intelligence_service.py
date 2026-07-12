from typing import Any, Dict, Optional

from app.models.pattern_intelligence import PatternListQuery, PatternRunRequest
from app.repositories import knowledge_repository, pattern_intelligence_repository
from app.services.pattern_intelligence_aggregator import collect_sources, fingerprint
from app.services.pattern_intelligence_config import ALGORITHM_VERSION, STAFF_STATUSES
from app.services.pattern_intelligence_engine import detect, impact
from app.services.knowledge_intelligence_sync import sync_module_safely


def initialize_pattern_intelligence() -> None:
    pattern_intelligence_repository.initialize_pattern_schema()


def run(user_id: int, request: PatternRunRequest) -> Dict[str, Any]:
    workspace=knowledge_repository.get_or_create_workspace(user_id)
    if request.team_profile_id and not pattern_intelligence_repository.team_profile_belongs(int(workspace["id"]),request.team_profile_id):
        raise ValueError("Profilo squadra non valido")
    bundle=collect_sources(user_id,request.local_matches,request.period_days)
    source_fingerprint=fingerprint(bundle)
    latest=pattern_intelligence_repository.latest_run(user_id)
    if latest and latest["source_fingerprint"]==source_fingerprint:
        return {"generated":False,"changed":False,"data":pattern_intelligence_repository.list_patterns(user_id,{"page":1,"page_size":50})}
    previous=pattern_intelligence_repository.prior_states(user_id)
    patterns=detect(bundle)
    record=pattern_intelligence_repository.create_run(user_id,int(workspace["id"]),request.team_profile_id,bundle["period_start"],bundle["period_end"],len(bundle["matches"]),bundle["source_types"],source_fingerprint,ALGORITHM_VERSION)
    pattern_intelligence_repository.save_patterns(record,patterns,previous)
    knowledge_repository.upsert_source_link(int(workspace["id"]),"pattern_intelligence_run",str(record["id"]),{"period_start":record["period_start"],"period_end":record["period_end"],"matches":record["matches_analyzed"],"fingerprint":source_fingerprint})
    data=pattern_intelligence_repository.list_patterns(user_id,{"page":1,"page_size":50})
    for item in data["items"]:
        knowledge_repository.upsert_source_link(int(workspace["id"]),"pattern_intelligence_pattern",str(item["id"]),{"run_id":record["id"],"topic":item["canonical_topic"],"status":item["status"],"confidence":item["confidence_level"]})
    sync_module_safely(user_id,"pattern_intelligence")
    return {"generated":True,"changed":bool(latest),"data":data}


def list_for_user(user_id: int, query: PatternListQuery) -> Dict[str, Any]:
    return pattern_intelligence_repository.list_patterns(user_id,query.model_dump(exclude_none=True))


def detail(user_id: int, pattern_id: int, page: int=1, page_size: int=20) -> Optional[Dict[str, Any]]:
    return pattern_intelligence_repository.get_pattern(user_id,pattern_id,page,page_size)


def set_status(user_id: int, pattern_id: int, status: str) -> Optional[Dict[str, Any]]:
    if status not in STAFF_STATUSES:
        raise ValueError("Stato pattern non valido")
    item=pattern_intelligence_repository.update_pattern(user_id,pattern_id,status=status)
    if item:
        workspace=knowledge_repository.get_or_create_workspace(user_id)
        knowledge_repository.upsert_source_link(int(workspace["id"]),"pattern_intelligence_pattern",str(pattern_id),{"run_id":item["run_id"],"topic":item["canonical_topic"],"status":item["status"],"confidence":item["confidence_level"]})
        sync_module_safely(user_id,"pattern_intelligence")
    return item


def add_note(user_id: int, pattern_id: int, note: str) -> Optional[Dict[str, Any]]:
    item=pattern_intelligence_repository.update_pattern(user_id,pattern_id,note=note.strip())
    if item: sync_module_safely(user_id,"pattern_intelligence")
    return item


def summary(user_id: int) -> Dict[str, Any]:
    return pattern_intelligence_repository.summary(user_id)


def post_match_impact(user_id: int, match: Dict[str, Any]) -> Dict[str, Any]:
    patterns=pattern_intelligence_repository.list_patterns(user_id,{"page":1,"page_size":50})["items"]
    return impact(patterns,match)
