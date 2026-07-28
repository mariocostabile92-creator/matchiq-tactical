import logging
from typing import Any, Dict

from app.models.pattern_intelligence import PatternRunRequest
from app.repositories import knowledge_repository
from app.services import pattern_intelligence_service
from app.services import weekly_priority_service
from app.services.knowledge_intelligence_sync import sync as sync_knowledge


logger = logging.getLogger(__name__)


def sync_finalized_match(user_id: int, evidence: Dict[str, Any]) -> Dict[str, Any]:
    workspace=knowledge_repository.get_or_create_workspace(user_id)
    workspace_id=int(workspace["id"])
    canonical_id=str(evidence["canonical_match_id"])
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
    coach_status=(knowledge.get("modules") or {}).get("coach",{}).get("status")
    if coach_status in {"error","locked"}:
        return {
            "status":"partial",
            "knowledge":knowledge,
            "pattern":None,
            "priorities":None,
        }
    pattern=pattern_intelligence_service.run(
        user_id,
        PatternRunRequest(period_days=120,local_matches=[]),
    )
    priorities=weekly_priority_service.sync_from_patterns(user_id)
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
