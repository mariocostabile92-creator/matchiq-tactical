import logging
from typing import Any, Dict

from app.models.pattern_intelligence import PatternRunRequest
from app.repositories import knowledge_repository
from app.services import pattern_intelligence_service
from app.services import weekly_priority_service
from app.services.intelligence_pipeline_log import log_pipeline_step
from app.services.knowledge_intelligence_sync import sync as sync_knowledge


logger = logging.getLogger(__name__)


def sync_finalized_match(user_id: int, evidence: Dict[str, Any]) -> Dict[str, Any]:
    workspace=knowledge_repository.get_or_create_workspace(user_id)
    workspace_id=int(workspace["id"])
    canonical_id=str(evidence["canonical_match_id"])
    log_pipeline_step(
        step="knowledge",
        status="START",
        user_id=user_id,
        canonical_match_id=canonical_id,
    )
    try:
        knowledge_repository.upsert_source_link(
            workspace_id,
            "match_evidence",
            canonical_id,
            {
                "canonical_match_id":canonical_id,
                "source_match_id":evidence.get("source_match_id"),
                "team_id":evidence.get("team_id"),
                "season_id":evidence.get("season_id"),
                "match_date":evidence.get("match_date"),
            },
        )
        knowledge=sync_knowledge(user_id,workspace_id,["coach"],False)
    except Exception:
        log_pipeline_step(
            step="knowledge",
            status="FAILED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            exc_info=True,
        )
        raise
    coach_status=(knowledge.get("modules") or {}).get("coach",{}).get("status")
    if coach_status in {"error","locked"}:
        log_pipeline_step(
            step="knowledge",
            status="FAILED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            detail={"module_status":coach_status},
        )
        log_pipeline_step(
            step="pattern",
            status="SKIPPED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            detail={"reason":"knowledge_unavailable"},
        )
        log_pipeline_step(
            step="weekly_priorities",
            status="SKIPPED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            detail={"reason":"knowledge_unavailable"},
        )
        log_pipeline_step(
            step="training_draft",
            status="SKIPPED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            detail={"reason":"knowledge_unavailable"},
        )
        return {
            "status":"partial",
            "knowledge":knowledge,
            "pattern":None,
            "priorities":None,
        }
    log_pipeline_step(
        step="knowledge",
        status="SUCCESS",
        user_id=user_id,
        canonical_match_id=canonical_id,
        detail={"module_status":coach_status or "ready"},
    )
    log_pipeline_step(
        step="pattern",
        status="START",
        user_id=user_id,
        canonical_match_id=canonical_id,
    )
    try:
        pattern=pattern_intelligence_service.run(
            user_id,
            PatternRunRequest(period_days=120,local_matches=[]),
        )
    except Exception:
        log_pipeline_step(
            step="pattern",
            status="FAILED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            exc_info=True,
        )
        raise
    log_pipeline_step(
        step="pattern",
        status="SUCCESS" if pattern.get("generated") else "SKIPPED",
        user_id=user_id,
        canonical_match_id=canonical_id,
        detail={"reason":"updated" if pattern.get("generated") else "unchanged"},
    )
    log_pipeline_step(
        step="weekly_priorities",
        status="START",
        user_id=user_id,
        canonical_match_id=canonical_id,
    )
    try:
        priorities=weekly_priority_service.sync_from_patterns(user_id)
    except Exception:
        log_pipeline_step(
            step="weekly_priorities",
            status="FAILED",
            user_id=user_id,
            canonical_match_id=canonical_id,
            exc_info=True,
        )
        raise
    log_pipeline_step(
        step="weekly_priorities",
        status="SUCCESS" if priorities.get("priorities") else "SKIPPED",
        user_id=user_id,
        canonical_match_id=canonical_id,
        detail={
            "count":len(priorities.get("priorities") or []),
            "reason":"updated" if priorities.get("priorities") else "no_consolidated_pattern",
        },
    )
    log_pipeline_step(
        step="training_draft",
        status="SKIPPED",
        user_id=user_id,
        canonical_match_id=canonical_id,
        detail={"reason":"awaiting_staff_confirmation"},
    )
    return {
        "status":"completed",
        "knowledge":knowledge,
        "pattern":pattern,
        "priorities":priorities,
    }


def sync_finalized_match_safely(user_id: int, evidence: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return sync_finalized_match(user_id,evidence)
    except Exception:
        logger.exception(
            "MatchEvidence intelligence sync failed",
            extra={"user_id":user_id,"canonical_match_id":evidence.get("canonical_match_id")},
        )
        return {
            "status":"error",
            "knowledge":None,
            "pattern":None,
            "priorities":None,
        }
