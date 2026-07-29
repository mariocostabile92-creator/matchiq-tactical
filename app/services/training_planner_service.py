from datetime import date, timedelta
from typing import Any, Dict, Optional

from app.models.training_planner import TrainingDraftPayload, TrainingPlanGenerateRequest
from app.repositories import knowledge_repository, training_planner_repository
from app.services.knowledge_intelligence_sync import sync_module_safely
from app.services.training_library import library_items
from app.services.training_planner_selector import select
from app.services.training_priority_adapter import (
    collect_confirmed,
    default_settings,
    source_fingerprint,
)
from app.services.training_session_composer import compose_session


PLAN_STATUSES = {
    "bozza",
    "proposta_ai",
    "accettata",
    "modificata",
    "completata",
    "archiviata",
    "rifiutata",
}
ACTIONS = {
    "accept": "accettata",
    "reject": "rifiutata",
    "archive": "archiviata",
    "complete": "completata",
    "reopen": "bozza",
}


def initialize_training_planner() -> None:
    training_planner_repository.initialize_training_schema()
    training_planner_repository.seed_library(library_items())


def week_key(today: Optional[date] = None) -> str:
    value = today or date.today()
    return (value - timedelta(days=value.weekday())).isoformat()


def generate(user_id: int, request: TrainingPlanGenerateRequest) -> Dict[str, Any]:
    bundle = collect_confirmed(user_id)
    settings = {
        "players": request.players,
        "goalkeepers": request.goalkeepers,
        "session_duration": request.session_duration,
        "intensity": request.intensity.lower(),
        "category": request.category,
        "training_days": request.training_days,
    }
    fingerprint = source_fingerprint(bundle, settings)
    existing = training_planner_repository.get_by_fingerprint(user_id, fingerprint)
    if existing:
        return {
            "generated": False,
            "changed": False,
            "data": {"plan": existing, "sufficient": True},
        }

    latest = training_planner_repository.latest_plan(user_id)
    if not bundle["priorities"]:
        return {
            "generated": False,
            "changed": False,
            "data": {
                "plan": None,
                "sufficient": False,
                "message": (
                    "Conferma almeno una priorita della settimana per ricevere "
                    "una bozza di allenamento."
                ),
                "sources_count": 0,
            },
        }

    proposals = select(
        bundle["priorities"],
        training_planner_repository.list_exercises(limit=50),
        settings,
    )
    if not proposals:
        return {
            "generated": False,
            "changed": False,
            "data": {
                "plan": None,
                "sufficient": False,
                "message": (
                    "Le priorita sono confermate, ma la libreria non contiene "
                    "ancora esercitazioni coerenti."
                ),
                "sources_count": bundle["sources_count"],
            },
        }

    plan_payload = TrainingDraftPayload(
        **compose_session(
            proposals,
            settings,
            bundle.get("team_profile") or {},
            request.training_days,
        )
    ).model_dump()
    if latest and request.force:
        training_planner_repository.update_plan(
            user_id,
            latest["id"],
            status="archiviata",
            action="regenerated",
            note="Sostituito da una nuova bozza basata sulle priorita confermate.",
        )
    sources = sum((item["sources"] for item in bundle["priorities"]), [])
    plan = training_planner_repository.save_plan(
        user_id,
        int(bundle["workspace"]["id"]),
        week_key(),
        request.training_days,
        bundle["priorities"],
        sources,
        plan_payload,
        fingerprint,
    )
    knowledge_repository.upsert_source_link(
        int(bundle["workspace"]["id"]),
        "training_plan",
        str(plan["id"]),
        {
            "status": plan["status"],
            "week_key": plan["week_key"],
            "priority_ids": [
                item["priority_id"] for item in bundle["priorities"]
            ],
            "version": plan["version"],
        },
    )
    sync_module_safely(user_id, "training_planner")
    return {
        "generated": True,
        "changed": bool(latest),
        "data": {"plan": plan, "sufficient": True},
    }


def sync_confirmed_priorities(user_id: int) -> Dict[str, Any]:
    bundle = collect_confirmed(user_id)
    if not bundle["priorities"]:
        return {
            "generated": False,
            "changed": False,
            "data": {"plan": None, "sufficient": False},
        }
    training_days = (bundle.get("constraints") or {}).get("training_days") or [
        "Da programmare"
    ]
    request = TrainingPlanGenerateRequest(
        training_days=training_days,
        force=training_planner_repository.latest_plan(user_id) is not None,
        **default_settings(bundle),
    )
    return generate(user_id, request)


def current(user_id: int) -> Dict[str, Any]:
    sync_confirmed_priorities(user_id)
    plan = training_planner_repository.latest_plan(user_id)
    return {
        "plan": plan,
        "history": (
            training_planner_repository.history(user_id, plan["id"])
            if plan
            else []
        ),
    }


def get(user_id: int, plan_id: int) -> Optional[Dict[str, Any]]:
    plan = training_planner_repository.get_plan(user_id, plan_id)
    return (
        {
            "plan": plan,
            "history": training_planner_repository.history(user_id, plan_id),
        }
        if plan
        else None
    )


def modify(
    user_id: int,
    plan_id: int,
    current_plan: Dict[str, Any],
    note: Optional[str],
) -> Optional[Dict[str, Any]]:
    item = training_planner_repository.update_plan(
        user_id,
        plan_id,
        current=current_plan,
        status="modificata",
        note=note,
        action="modified",
    )
    if item:
        _link(user_id, item, "modified")
        sync_module_safely(user_id, "training_planner")
    return item


def action(
    user_id: int,
    plan_id: int,
    action_name: str,
    note: Optional[str],
) -> Optional[Dict[str, Any]]:
    if action_name == "duplicate":
        source = training_planner_repository.get_plan(user_id, plan_id)
        if not source:
            return None
        workspace = knowledge_repository.get_or_create_workspace(user_id)
        copy = training_planner_repository.save_plan(
            user_id,
            int(workspace["id"]),
            source["week_key"],
            source["training_days"],
            source["priorities"],
            source["sources"],
            source["current_plan"],
            source["source_fingerprint"] + f":copy:{source['id']}",
            status="bozza",
            version=1,
        )
        _link(user_id, copy, "duplicated")
        sync_module_safely(user_id, "training_planner")
        return copy
    if action_name not in ACTIONS:
        raise ValueError("Azione piano non valida")
    item = training_planner_repository.update_plan(
        user_id,
        plan_id,
        status=ACTIONS[action_name],
        note=note,
        action=action_name,
    )
    if item:
        _link(user_id, item, action_name)
        sync_module_safely(user_id, "training_planner")
    return item


def mark_viewed(user_id: int, plan_id: int) -> Optional[Dict[str, Any]]:
    return training_planner_repository.mark_viewed(user_id, plan_id)


def _link(user_id: int, plan: Dict[str, Any], action_name: str) -> None:
    workspace = knowledge_repository.get_or_create_workspace(user_id)
    knowledge_repository.upsert_source_link(
        int(workspace["id"]),
        "training_plan",
        str(plan["id"]),
        {
            "status": plan["status"],
            "week_key": plan["week_key"],
            "version": plan["version"],
            "last_action": action_name,
        },
    )
