import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.models.match_evidence import MatchEvidenceFinalizeRequest
from app.repositories import match_evidence_repository


MATCH_EVIDENCE_SCHEMA_VERSION = 1


def initialize_match_evidence() -> None:
    match_evidence_repository.initialize_match_evidence_schema()


def canonical_match_id(user_id: int, source_match_id: str) -> str:
    seed = f"matchiq:{user_id}:{source_match_id.strip()}".encode("utf-8")
    return f"match_{hashlib.sha256(seed).hexdigest()[:24]}"


def finalize(
    user_id: int,
    request: MatchEvidenceFinalizeRequest,
) -> Tuple[Dict[str, Any], bool]:
    payload = request.model_dump(mode="json")
    payload["schema_version"] = MATCH_EVIDENCE_SCHEMA_VERSION
    payload["metadata"]["schema_version"] = MATCH_EVIDENCE_SCHEMA_VERSION
    existing = match_evidence_repository.get_by_source(user_id, request.source_match_id)
    now = datetime.now(timezone.utc).isoformat()
    finalized_at = (
        request.finalized_at.astimezone(timezone.utc).isoformat()
        if request.finalized_at
        else now
    )
    canonical_id = (
        existing["canonical_match_id"]
        if existing
        else canonical_match_id(user_id, request.source_match_id)
    )
    created_at = existing["created_at"].isoformat() if existing and hasattr(existing["created_at"], "isoformat") else (
        existing["created_at"] if existing else now
    )
    item = match_evidence_repository.upsert(
        user_id=user_id,
        canonical_match_id=canonical_id,
        evidence=payload,
        created_at=created_at,
        finalized_at=finalized_at,
        updated_at=now,
    )
    from app.services.match_evidence_intelligence_sync import (
        sync_finalized_match_safely,
    )

    sync_finalized_match_safely(user_id,item)
    return item, existing is None


def get(user_id: int, canonical_id: str) -> Optional[Dict[str, Any]]:
    return match_evidence_repository.get_by_canonical_id(user_id, canonical_id)


def list_for_user(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    return match_evidence_repository.list_for_user(user_id, limit)
