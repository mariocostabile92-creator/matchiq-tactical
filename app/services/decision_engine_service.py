import hashlib
import json
import time
from typing import Any, Dict, Optional

from app.repositories import decision_engine_repository as repository, knowledge_intelligence_repository, knowledge_repository, pattern_intelligence_repository
from app.repositories.decision_engine_schema import initialize_schema
from app.services import decision_engine_knowledge
from app.services.decision_engine_eligibility import evaluate as evaluate_eligibility
from app.services.decision_engine_options import generate
from app.services.decision_engine_policy import sanitize_context, validate_staff_action
from app.services.decision_engine_retrieval import collect
from app.services.decision_engine_situation import build


def initialize_decision_engine() -> None: initialize_schema()


def _scope(user_id: int):
    workspace=knowledge_repository.get_or_create_workspace(user_id); return int(workspace["id"])


def _fingerprint(user_id: int,payload: Dict[str,Any],context: Dict[str,Any]) -> str:
    data={"user":user_id,"phase":payload["phase"],"team":payload.get("team_profile_id"),"match":payload.get("match_id"),"minute":payload.get("minute"),"score":payload.get("score_state"),"prompt":payload.get("prompt"),"context":context}
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,default=str).encode("utf-8")).hexdigest()


def evaluate(user_id: int,payload: Dict[str,Any]) -> Dict[str,Any]:
    started=time.perf_counter(); wid=_scope(user_id)
    if payload.get("team_profile_id") and not pattern_intelligence_repository.team_profile_belongs(wid,int(payload["team_profile_id"])): raise ValueError("Profilo squadra non valido")
    context=sanitize_context(payload.get("source_context") or {}); context.update({key:payload.get(key) for key in ("match_id","minute","score_state") if payload.get(key) is not None})
    fp=_fingerprint(user_id,payload,context); existing=repository.get_case_by_fingerprint(wid,user_id,fp)
    if existing and not payload.get("force"): return full_case(user_id,existing["id"],unchanged=True)
    if existing and payload.get("force"): fp=hashlib.sha256(f"{fp}:{time.time_ns()}".encode("utf-8")).hexdigest()
    sources=collect(wid,{**context,"match_id":payload.get("match_id")}); situation=build({**payload,"source_context":context},sources); eligibility=evaluate_eligibility(payload["phase"],context,sources); options=generate(payload["phase"],situation,eligibility,sources)
    case=repository.create_case(wid,user_id,{**payload,"source_context":context,"situation_summary":situation["summary"],"status":"ready" if options else "insufficient_evidence","evidence_state":eligibility["state"],"source_fingerprint":fp,"limitations":eligibility["limitations"]})
    repository.replace_options(case["id"],options,sources); complete=full_case(user_id,case["id"]); decision_engine_knowledge.publish_case(wid,user_id,case,complete["options"])
    repository.telemetry(wid,user_id,case["id"],"evaluate",int((time.perf_counter()-started)*1000),len(sources),len(options),{"engine":"deterministic-v1","evidence_state":eligibility["state"]})
    return complete


def full_case(user_id: int,case_id: int,unchanged: bool=False) -> Optional[Dict[str,Any]]:
    wid=_scope(user_id); case=repository.get_case(wid,user_id,case_id)
    if not case: return None
    return {**case,"options":repository.list_options(wid,user_id,case_id),"staff_decisions":repository.list_staff_decisions(wid,user_id,case_id),"outcomes":repository.outcomes(wid,user_id,case_id),"unchanged":unchanged}


def cases(user_id: int,page: int,page_size: int,phase: Optional[str]=None): return repository.list_cases(_scope(user_id),user_id,page,page_size,phase)


def options(user_id: int,case_id: int): return repository.list_options(_scope(user_id),user_id,case_id)


def staff_decision(user_id: int,case_id: int,payload: Dict[str,Any]):
    validate_staff_action(payload); wid=_scope(user_id); decision=repository.add_staff_decision(wid,user_id,case_id,payload)
    if not decision: return None
    case_node=knowledge_intelligence_repository.get_node_by_key(wid,f"{wid}:decision_case:decision_case:{case_id}")
    option_node=knowledge_intelligence_repository.get_node_by_key(wid,f"{wid}:decision_option:decision_option:{decision['option_id']}") if decision.get("option_id") else None
    if case_node: decision_engine_knowledge.publish_staff(wid,user_id,case_node,decision,option_node)
    repository.telemetry(wid,user_id,case_id,"staff_decision",metadata={"action":payload["action"]}); return decision


def note(user_id: int,case_id: int,note_text: str): return staff_decision(user_id,case_id,{"action":"save_later","note":note_text,"executed_manually":False})


def add_outcome(user_id: int,case_id: int,decision_id: int,payload: Dict[str,Any]):
    wid=_scope(user_id); outcome=repository.add_outcome(wid,user_id,case_id,decision_id,payload)
    if not outcome: return None
    decision_node=knowledge_intelligence_repository.get_node_by_key(wid,f"{wid}:staff_decision:staff_decision:{decision_id}")
    if decision_node: decision_engine_knowledge.publish_outcome(wid,user_id,decision_node,outcome)
    return outcome


def outcomes(user_id: int,case_id: int): return repository.outcomes(_scope(user_id),user_id,case_id)


def status(user_id: int) -> Dict[str,Any]:
    data=repository.list_cases(_scope(user_id),user_id,1,5); return {"status":"ready","engine_version":"deterministic-v1","recent_cases":data["items"],"rules":{"automatic_execution":False,"max_primary_options":2,"max_conservative_options":1}}
