from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from threading import RLock
from typing import Any, Dict, List
from uuid import uuid4

from database import utc_now
from app.models.video_intelligence import VideoReportRequest
from app.repositories.video_intelligence_repository import load_project, save_project
from app.services.video_intelligence_pdf_service import build_evidence_report_pdf, report_pdf_filename
from app.services.video_segmentation_service import phase_title


ACCEPTED_STATUSES = {"confirmed", "corrected"}
_REPORT_LOCK = RLock()


class ReportConflictError(ValueError):
    def __init__(self, code: str, message: str, review_counts: Dict[str, int]):
        super().__init__(message)
        self.code = code
        self.message = message
        self.review_counts = review_counts


def _review_counts(evidences: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "total": len(evidences),
        "confirmed": sum(1 for item in evidences if item.get("review_status") == "confirmed"),
        "corrected": sum(1 for item in evidences if item.get("review_status") == "corrected"),
        "pending": sum(1 for item in evidences if item.get("review_status") == "pending"),
        "rejected": sum(1 for item in evidences if item.get("review_status") == "rejected"),
    }


def _reports(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for item in (project.get("reports") or []) if isinstance(item, dict)]


def list_evidence_reports(user_id: int, asset_id: int) -> List[Dict[str, Any]]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    return deepcopy(_reports(project))


def get_evidence_report(user_id: int, asset_id: int, report_id: str) -> Dict[str, Any]:
    reports = list_evidence_reports(user_id, asset_id)
    report = next((item for item in reports if str(item.get("report_id")) == str(report_id)), None)
    if not report:
        raise LookupError("Report Video Intelligence non trovato")
    report["pdf_ready"] = str(report.get("status") or "ready") == "ready"
    report["pdf_filename"] = report_pdf_filename(report)
    return report


def _timecode(timestamp_ms: int) -> str:
    total = max(0, int(timestamp_ms)) // 1000
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def _fingerprint(project: Dict[str, Any], accepted: List[Dict[str, Any]], include_pending: bool) -> str:
    payload = {
        "project_id": project.get("project_id"),
        "engine_version": project.get("engine_version"),
        "include_pending": include_pending,
        "evidences": [
            {
                "id": item.get("evidence_id"),
                "status": item.get("review_status"),
                "phase": item.get("phase_type"),
                "timestamp": item.get("representative_timestamp_ms"),
                "title": item.get("title"),
                "observation": item.get("observation"),
                "interpretation": item.get("interpretation"),
                "correction": item.get("user_correction"),
            }
            for item in accepted
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _finding(evidence: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = int(evidence.get("representative_timestamp_ms") or 0)
    evidence_id = str(evidence.get("evidence_id") or "")
    video_id = int(evidence.get("video_id") or 0)
    frame = deepcopy(evidence.get("representative_frame") or {})
    clip = deepcopy(evidence.get("clip_reference") or {})
    return {
        "evidence_id": evidence_id,
        "title": evidence.get("title") or phase_title(str(evidence.get("phase_type") or "unclassified")),
        "phase_type": evidence.get("phase_type") or "unclassified",
        "timecode": _timecode(timestamp),
        "timestamp_ms": timestamp,
        "observation": evidence.get("observation") or "",
        "interpretation": evidence.get("interpretation"),
        "staff_correction": evidence.get("user_correction"),
        "review_status": evidence.get("review_status"),
        "confidence_score": evidence.get("confidence_score"),
        "confidence_label": evidence.get("confidence_label"),
        "frame": frame,
        "clip": clip,
        "traceability": {
            "trace_id": f"{video_id}:{evidence_id}:{timestamp}",
            "project_id": evidence.get("project_id"),
            "video_id": video_id,
            "evidence_id": evidence_id,
            "source_type": evidence.get("source_type"),
            "review_status": evidence.get("review_status"),
            "reviewed_by": evidence.get("reviewed_by"),
            "reviewed_at": evidence.get("reviewed_at"),
            "timestamp_ms": timestamp,
            "frame_index": frame.get("frame_index"),
            "frame_score": frame.get("score"),
            "clip_start_ms": clip.get("start_timestamp_ms"),
            "clip_end_ms": clip.get("end_timestamp_ms"),
        },
        "coach_link": {
            "event_id": evidence.get("linked_match_event_id"),
            "note_id": evidence.get("linked_note_id"),
            "type": evidence.get("link_type"),
        } if evidence.get("linked_match_event_id") or evidence.get("linked_note_id") else None,
    }


def generate_evidence_report_delivery(user_id: int, asset_id: int, data: VideoReportRequest) -> Dict[str, Any]:
    with _REPORT_LOCK:
        return _generate_evidence_report_delivery(user_id, asset_id, data)


def _generate_evidence_report_delivery(user_id: int, asset_id: int, data: VideoReportRequest) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    evidences = [item for item in (project.get("evidences") or []) if isinstance(item, dict)]
    reports = _reports(project)
    pipeline = project.get("pipeline") if isinstance(project.get("pipeline"), dict) else {}
    pipeline_status = str(pipeline.get("status") or "")
    if pipeline_status in {"queued", "processing"} and not reports:
        return {
            "status": "processing",
            "report": None,
            "report_id": None,
            "pdf_ready": False,
            "message": "L'analisi e ancora in corso. Il report sara disponibile al termine.",
        }

    accepted = [item for item in evidences if item.get("review_status") in ACCEPTED_STATUSES]
    if not accepted:
        if reports:
            existing = deepcopy(reports[-1])
            existing["pdf_ready"] = str(existing.get("status") or "ready") == "ready"
            existing["pdf_filename"] = report_pdf_filename(existing)
            return {
                "status": "already_exists",
                "report": existing,
                "report_id": existing.get("report_id"),
                "pdf_ready": existing["pdf_ready"],
                "idempotent_replay": True,
                "message": "Il report esiste gia ed e stato recuperato.",
            }
        raise ReportConflictError(
            "no_accepted_evidence",
            "Conferma o correggi almeno un'evidenza prima di generare il report",
            _review_counts(evidences),
        )
    accepted.sort(key=lambda item: int(item.get("representative_timestamp_ms") or 0))
    fingerprint = _fingerprint(project, accepted, data.include_pending_appendix)
    existing = next((item for item in reports if item.get("fingerprint") == fingerprint), None)
    if existing:
        existing = deepcopy(existing)
        existing["pdf_ready"] = str(existing.get("status") or "ready") == "ready"
        existing["pdf_filename"] = report_pdf_filename(existing)
        return {
            "status": "already_exists",
            "report": existing,
            "report_id": existing.get("report_id"),
            "pdf_ready": existing["pdf_ready"],
            "idempotent_replay": True,
            "message": "Il report esiste gia ed e stato recuperato.",
        }

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for evidence in accepted:
        grouped[str(evidence.get("phase_type") or "unclassified")].append(_finding(evidence))
    sections = [
        {
            "phase_type": phase,
            "title": phase_title(phase).replace("Possibile ", ""),
            "findings": findings,
        }
        for phase, findings in grouped.items()
    ]
    pending = [
        {
            "evidence_id": item.get("evidence_id"),
            "title": item.get("title"),
            "timecode": _timecode(int(item.get("representative_timestamp_ms") or 0)),
            "reason": "Evidenza ancora da verificare dallo staff.",
            "traceability": {
                "project_id": item.get("project_id"),
                "video_id": item.get("video_id"),
                "evidence_id": item.get("evidence_id"),
                "timestamp_ms": int(item.get("representative_timestamp_ms") or 0),
                "review_status": "pending",
            },
        }
        for item in evidences
        if data.include_pending_appendix and item.get("review_status") == "pending"
    ]
    corrected = sum(1 for item in accepted if item.get("review_status") == "corrected")
    report = {
        "report_id": f"vir_{uuid4().hex}",
        "fingerprint": fingerprint,
        "project_id": project.get("project_id"),
        "video_asset_id": int(asset_id),
        "analysis_mode": project.get("analysis_mode"),
        "title": str(data.title or project.get("title") or "Report tecnico Video AI")[:180],
        "generated_at": utc_now(),
        "status": "ready",
        "evidence_policy": "Solo evidenze confermate o corrette dallo staff alimentano le conclusioni.",
        "review_policy": {
            "accepted_statuses": sorted(ACCEPTED_STATUSES),
            "pending_destination": "appendix" if data.include_pending_appendix else "excluded",
            "rejected_destination": "excluded",
        },
        "summary": {
            "accepted_evidences": len(accepted),
            "confirmed": len(accepted) - corrected,
            "corrected": corrected,
            "pending_appendix": len(pending),
            "rejected_excluded": sum(1 for item in evidences if item.get("review_status") == "rejected"),
        },
        "sections": sections,
        "evidence_index": [
            {
                "evidence_id": item.get("evidence_id"),
                "timecode": _timecode(int(item.get("representative_timestamp_ms") or 0)),
                "phase_type": item.get("phase_type"),
                "review_status": item.get("review_status"),
                "source_type": item.get("source_type"),
            }
            for item in accepted
        ],
        "pending_appendix": pending,
        "limitations": [
            "Il report descrive solo i momenti coperti dalle evidenze revisionate.",
            "Le interpretazioni restano supporto decisionale e richiedono verifica dello staff tecnico.",
        ],
    }
    pdf_payload = build_evidence_report_pdf(report)
    report["pdf_ready"] = True
    report["pdf_filename"] = report_pdf_filename(report)
    report["pdf_size"] = len(pdf_payload)
    reports.append(report)
    project["reports"] = reports[-20:]
    stages = pipeline.get("stages") if isinstance(pipeline.get("stages"), dict) else {}
    stages["report_generation"] = {"status": "completed", "progress": 100, "report_id": report["report_id"]}
    pipeline.update({"status": "completed", "stage": "report_generation", "progress": 100, "stages": stages})
    project["pipeline"] = pipeline
    saved = save_project(user_id, asset_id, project, status="completed", stage="report_generation", progress=100)
    if not saved:
        raise RuntimeError("Impossibile salvare il report tecnico")
    return {
        "status": "created",
        "report": deepcopy(report),
        "report_id": report["report_id"],
        "pdf_ready": True,
        "idempotent_replay": False,
        "message": "Report tecnico generato.",
    }


def generate_evidence_report(user_id: int, asset_id: int, data: VideoReportRequest) -> Dict[str, Any]:
    delivery = generate_evidence_report_delivery(user_id, asset_id, data)
    if delivery.get("status") == "processing":
        raise ReportConflictError("report_processing", delivery.get("message") or "Report in preparazione", {})
    return deepcopy(delivery["report"])
