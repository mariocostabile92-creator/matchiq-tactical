from datetime import date,timedelta
from typing import Any,Dict,Optional

from app.models.training_planner import TrainingPlanGenerateRequest
from app.repositories import knowledge_repository,training_planner_repository
from app.services.training_library import library_items
from app.services.training_planner_aggregator import collect,fingerprint
from app.services.training_planner_selector import build_week,select
from app.services.knowledge_intelligence_sync import sync_module_safely


PLAN_STATUSES={"bozza","proposta_ai","accettata","modificata","completata","archiviata","rifiutata"}
ACTIONS={"accept":"accettata","reject":"rifiutata","archive":"archiviata","complete":"completata","reopen":"bozza"}


def initialize_training_planner() -> None:
    training_planner_repository.initialize_training_schema(); training_planner_repository.seed_library(library_items())


def week_key(today: date=None) -> str:
    value=today or date.today(); return (value-timedelta(days=value.weekday())).isoformat()


def generate(user_id: int,request: TrainingPlanGenerateRequest) -> Dict[str,Any]:
    bundle=collect(user_id,request.local_context)
    settings={"players":request.players,"goalkeepers":request.goalkeepers,"session_duration":request.session_duration,"intensity":request.intensity.lower(),"category":request.category}
    request_data={**settings,"training_days":request.training_days}
    source_fingerprint=fingerprint(bundle,request_data); latest=training_planner_repository.latest_plan(user_id)
    if latest and latest["source_fingerprint"]==source_fingerprint and not request.force:
        return {"generated":False,"changed":False,"data":{"plan":latest,"sufficient":True}}
    if not bundle["priorities"]:
        return {"generated":False,"changed":False,"data":{"plan":None,"sufficient":False,"message":"Non ci sono ancora dati sufficienti per costruire un allenamento realmente personalizzato.","sources_count":bundle["sources_count"]}}
    proposals=select(bundle["priorities"],training_planner_repository.list_exercises(limit=50),settings)
    if not proposals:
        return {"generated":False,"changed":False,"data":{"plan":None,"sufficient":False,"message":"Le priorità sono reali, ma la libreria attuale non contiene ancora un'esercitazione sufficientemente coerente.","sources_count":bundle["sources_count"]}}
    plan_payload=build_week(proposals,request.training_days,settings)
    if latest and request.force: training_planner_repository.update_plan(user_id,latest["id"],status="archiviata",action="regenerated",note="Sostituito da una nuova proposta AI.")
    plan=training_planner_repository.save_plan(user_id,int(bundle["workspace"]["id"]),week_key(),request.training_days,bundle["priorities"],sum((item["sources"] for item in bundle["priorities"]),[]),plan_payload,source_fingerprint)
    knowledge_repository.upsert_source_link(int(bundle["workspace"]["id"]),"training_plan",str(plan["id"]),{"status":plan["status"],"week_key":plan["week_key"],"pattern_run_id":bundle.get("pattern_run_id"),"weekly_id":bundle.get("weekly_id"),"version":plan["version"]})
    sync_module_safely(user_id,"training_planner")
    return {"generated":True,"changed":bool(latest),"data":{"plan":plan,"sufficient":True}}


def current(user_id: int) -> Dict[str,Any]:
    plan=training_planner_repository.latest_plan(user_id); return {"plan":plan,"history":training_planner_repository.history(user_id,plan["id"]) if plan else []}


def get(user_id: int,plan_id: int) -> Optional[Dict[str,Any]]:
    plan=training_planner_repository.get_plan(user_id,plan_id)
    return {"plan":plan,"history":training_planner_repository.history(user_id,plan_id)} if plan else None


def modify(user_id: int,plan_id: int,current_plan: Dict[str,Any],note: Optional[str]) -> Optional[Dict[str,Any]]:
    item=training_planner_repository.update_plan(user_id,plan_id,current=current_plan,status="modificata",note=note,action="modified")
    if item: _link(user_id,item,"modified")
    if item: sync_module_safely(user_id,"training_planner")
    return item


def action(user_id: int,plan_id: int,action_name: str,note: Optional[str]) -> Optional[Dict[str,Any]]:
    if action_name=="duplicate":
        source=training_planner_repository.get_plan(user_id,plan_id)
        if not source: return None
        workspace=knowledge_repository.get_or_create_workspace(user_id)
        copy=training_planner_repository.save_plan(user_id,int(workspace["id"]),source["week_key"],source["training_days"],source["priorities"],source["sources"],source["current_plan"],source["source_fingerprint"]+f":copy:{source['id']}",status="bozza",version=1); _link(user_id,copy,"duplicated"); sync_module_safely(user_id,"training_planner"); return copy
    if action_name not in ACTIONS: raise ValueError("Azione piano non valida")
    item=training_planner_repository.update_plan(user_id,plan_id,status=ACTIONS[action_name],note=note,action=action_name)
    if item: _link(user_id,item,action_name)
    if item: sync_module_safely(user_id,"training_planner")
    return item


def mark_viewed(user_id: int,plan_id: int) -> Optional[Dict[str,Any]]:
    return training_planner_repository.mark_viewed(user_id,plan_id)


def _link(user_id: int,plan: Dict[str,Any],action_name: str) -> None:
    workspace=knowledge_repository.get_or_create_workspace(user_id); knowledge_repository.upsert_source_link(int(workspace["id"]),"training_plan",str(plan["id"]),{"status":plan["status"],"week_key":plan["week_key"],"version":plan["version"],"last_action":action_name})
