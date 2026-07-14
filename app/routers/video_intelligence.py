from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models.video_intelligence import EvidenceCreateRequest, EvidenceReviewRequest, ProjectStateRequest, VideoPipelineRequest, VideoProjectCreate
from app.services.video_evidence_service import add_evidence, list_evidences, review_evidence
from app.services.video_intelligence_engine import (
    create_project,
    get_project,
    list_coach_matches,
    retry_project,
    run_pipeline,
    update_project_state,
)
from usage_guard import require_user


router = APIRouter(prefix="/api/video/intelligence", tags=["video-intelligence"])


@router.post("/projects")
def create_video_intelligence_project(data: VideoProjectCreate, user=Depends(require_user)):
    try:
        project = create_project(int(user["id"]), data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "project": project}


@router.get("/coach-matches")
def get_video_intelligence_coach_matches(user=Depends(require_user)):
    return {"ok": True, "matches": list_coach_matches(int(user["id"]))}


@router.get("/projects/{asset_id}")
def get_video_intelligence_project(asset_id: int, user=Depends(require_user)):
    project = get_project(int(user["id"]), asset_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto Video Intelligence non trovato")
    return {"ok": True, "project": project}


@router.post("/projects/{asset_id}/state")
def set_video_intelligence_project_state(asset_id: int, data: ProjectStateRequest, user=Depends(require_user)):
    try:
        project = update_project_state(int(user["id"]), asset_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "project": project}


@router.post("/projects/{asset_id}/retry")
def retry_video_intelligence_project(asset_id: int, user=Depends(require_user)):
    try:
        project = retry_project(int(user["id"]), asset_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "project": project}


@router.post("/projects/{asset_id}/pipeline")
def run_video_intelligence_pipeline(asset_id: int, data: VideoPipelineRequest, user=Depends(require_user)):
    try:
        project = run_pipeline(int(user["id"]), asset_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "project": project}


@router.post("/projects/{asset_id}/cancel")
def cancel_video_intelligence_project(asset_id: int, user=Depends(require_user)):
    data = ProjectStateRequest(status="cancelled", stage="cancelled")
    try:
        project = update_project_state(int(user["id"]), asset_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "project": project}


@router.get("/projects/{asset_id}/evidences")
def get_video_evidences(asset_id: int, include_rejected: bool = True, user=Depends(require_user)):
    try:
        items = list_evidences(int(user["id"]), asset_id, include_rejected=include_rejected)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "items": items, "count": len(items)}


@router.post("/projects/{asset_id}/evidences")
def create_video_evidence(asset_id: int, data: EvidenceCreateRequest, user=Depends(require_user)):
    try:
        evidence = add_evidence(int(user["id"]), asset_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "evidence": evidence}


@router.patch("/projects/{asset_id}/evidences/{evidence_id}/review")
def update_video_evidence_review(
    asset_id: int,
    evidence_id: str,
    data: EvidenceReviewRequest,
    user=Depends(require_user),
):
    try:
        evidence = review_evidence(int(user["id"]), asset_id, evidence_id, int(user["id"]), data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "evidence": evidence}
