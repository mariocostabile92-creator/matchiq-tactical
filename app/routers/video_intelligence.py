from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response

from app.models.video_intelligence import EvidenceClipRequest, EvidenceCreateRequest, EvidenceFrameRequest, EvidenceLinkRequest, EvidenceReviewRequest, HalftimeAnalysisRequest, ProjectStateRequest, VideoPipelineRequest, VideoProjectCreate, VideoReportRequest
from app.services.video_clip_service import update_evidence_clip
from app.services.video_coach_link_service import clear_evidence_link, set_evidence_link
from app.services.video_evidence_service import add_evidence, list_evidences, review_evidence
from app.services.video_frame_ranking_service import replace_evidence_frame
from app.services.video_halftime_service import generate_halftime_analysis, halftime_access
from app.services.video_intelligence_engine import (
    create_project,
    get_project,
    list_coach_matches,
    retry_project,
    run_pipeline,
    update_project_state,
)
from app.services.video_intelligence_pdf_service import build_evidence_report_pdf, report_pdf_filename
from app.services.video_report_service import (
    ReportConflictError,
    generate_evidence_report_delivery,
    get_evidence_report,
    list_evidence_reports,
)
from usage_guard import require_user


router = APIRouter(prefix="/api/video/intelligence", tags=["video-intelligence"])


@router.get("/halftime/config")
def get_halftime_analysis_config(user=Depends(require_user)):
    return {"ok": True, **halftime_access(user)}


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


@router.post("/projects/{asset_id}/evidences/{evidence_id}/frame")
def set_video_evidence_frame(
    asset_id: int,
    evidence_id: str,
    data: EvidenceFrameRequest,
    user=Depends(require_user),
):
    try:
        evidence = replace_evidence_frame(int(user["id"]), asset_id, evidence_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "evidence": evidence}


@router.post("/projects/{asset_id}/evidences/{evidence_id}/clip")
def set_video_evidence_clip(
    asset_id: int,
    evidence_id: str,
    data: EvidenceClipRequest,
    user=Depends(require_user),
):
    try:
        evidence = update_evidence_clip(int(user["id"]), asset_id, evidence_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "evidence": evidence}


@router.post("/projects/{asset_id}/evidences/{evidence_id}/link")
def link_video_evidence_to_coach(
    asset_id: int,
    evidence_id: str,
    data: EvidenceLinkRequest,
    user=Depends(require_user),
):
    try:
        evidence = set_evidence_link(int(user["id"]), asset_id, evidence_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "evidence": evidence}


@router.delete("/projects/{asset_id}/evidences/{evidence_id}/link")
def unlink_video_evidence_from_coach(asset_id: int, evidence_id: str, user=Depends(require_user)):
    try:
        evidence = clear_evidence_link(int(user["id"]), asset_id, evidence_id)
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


@router.post("/projects/{asset_id}/reports")
def generate_video_intelligence_report(asset_id: int, data: VideoReportRequest, user=Depends(require_user)):
    try:
        delivery = generate_evidence_report_delivery(int(user["id"]), asset_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReportConflictError as exc:
        raise HTTPException(status_code=409, detail={
            "code": exc.code,
            "status": "not_ready",
            "message": exc.message,
            "pdf_ready": False,
            "review_counts": exc.review_counts,
        }) from exc
    if delivery.get("status") == "processing":
        return JSONResponse(status_code=202, content={"ok": True, **delivery})
    return {"ok": True, **delivery}


@router.get("/projects/{asset_id}/reports")
def get_video_intelligence_reports(asset_id: int, user=Depends(require_user)):
    try:
        reports = list_evidence_reports(int(user["id"]), asset_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = []
    for report in reports:
        item = dict(report)
        item["pdf_ready"] = str(item.get("status") or "ready") == "ready"
        item["pdf_filename"] = report_pdf_filename(item)
        items.append(item)
    return {"ok": True, "status": "ready" if items else "empty", "items": items, "count": len(items)}


@router.get("/projects/{asset_id}/reports/{report_id}")
def get_video_intelligence_report(asset_id: int, report_id: str, user=Depends(require_user)):
    try:
        report = get_evidence_report(int(user["id"]), asset_id, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "status": "ready", "report": report, "pdf_ready": bool(report.get("pdf_ready"))}


@router.get("/projects/{asset_id}/reports/{report_id}/pdf")
def download_video_intelligence_report_pdf(asset_id: int, report_id: str, user=Depends(require_user)):
    try:
        report = get_evidence_report(int(user["id"]), asset_id, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if str(report.get("status") or "ready") != "ready":
        raise HTTPException(status_code=409, detail={
            "code": "pdf_not_ready",
            "status": str(report.get("status") or "processing"),
            "message": "Il PDF e ancora in preparazione.",
            "pdf_ready": False,
            "report_id": report_id,
        })
    payload = build_evidence_report_pdf(report)
    filename = report_pdf_filename(report)
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/projects/{asset_id}/halftime")
def generate_video_halftime_analysis(
    asset_id: int,
    data: HalftimeAnalysisRequest,
    user=Depends(require_user),
):
    try:
        analysis = generate_halftime_analysis(user, asset_id, data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "analysis": analysis}
