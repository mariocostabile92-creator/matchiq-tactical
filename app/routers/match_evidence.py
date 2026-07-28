import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.match_evidence import (
    MatchEvidenceFinalizeRequest,
    MatchEvidenceFinalizeResponse,
    MatchEvidenceListResponse,
    MatchEvidenceResponse,
)
from app.services import match_evidence_service
from usage_guard import require_user


router = APIRouter(prefix="/api/match-evidence", tags=["match-evidence"])


@router.put("/finalize", response_model=MatchEvidenceFinalizeResponse)
def finalize_match_evidence(
    payload: MatchEvidenceFinalizeRequest,
    user=Depends(require_user),
):
    if len(json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)) > 1_500_000:
        raise HTTPException(status_code=413, detail="Partita Coach troppo grande")
    item, created = match_evidence_service.finalize(int(user["id"]), payload)
    return MatchEvidenceFinalizeResponse(created=created, data=MatchEvidenceResponse(**item))


@router.get("", response_model=MatchEvidenceListResponse)
def list_match_evidence(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_user),
):
    items = match_evidence_service.list_for_user(int(user["id"]), limit)
    return MatchEvidenceListResponse(
        data=[MatchEvidenceResponse(**item) for item in items]
    )


@router.get("/{canonical_match_id}", response_model=MatchEvidenceResponse)
def get_match_evidence(
    canonical_match_id: str,
    user=Depends(require_user),
):
    item = match_evidence_service.get(int(user["id"]), canonical_match_id)
    if not item:
        raise HTTPException(status_code=404, detail="Partita canonica non trovata")
    return MatchEvidenceResponse(**item)
