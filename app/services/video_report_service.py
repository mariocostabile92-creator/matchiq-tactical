from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List
from uuid import uuid4

from database import utc_now
from app.models.video_intelligence import VideoReportRequest
from app.repositories.video_intelligence_repository import load_project, save_project
from app.services.video_segmentation_service import phase_title


ACCEPTED_STATUSES = {"confirmed", "corrected"}


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
    return {
        "evidence_id": evidence.get("evidence_id"),
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
        "frame": deepcopy(evidence.get("representative_frame") or {}),
        "clip": deepcopy(evidence.get("clip_reference") or {}),
        "coach_link": {
            "event_id": evidence.get("linked_match_event_id"),
            "note_id": evidence.get("linked_note_id"),
            "type": evidence.get("link_type"),
        } if evidence.get("linked_match_event_id") or evidence.get("linked_note_id") else None,
    }


def generate_evidence_report(user_id: int, asset_id: int, data: VideoReportRequest) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    evidences = [item for item in (project.get("evidences") or []) if isinstance(item, dict)]
    accepted = [item for item in evidences if item.get("review_status") in ACCEPTED_STATUSES]
    if not accepted:
        raise ValueError("Conferma o correggi almeno un'evidenza prima di generare il report")
    accepted.sort(key=lambda item: int(item.get("representative_timestamp_ms") or 0))
    fingerprint = _fingerprint(project, accepted, data.include_pending_appendix)
    reports = project.get("reports") if isinstance(project.get("reports"), list) else []
    existing = next((item for item in reports if item.get("fingerprint") == fingerprint), None)
    if existing:
        return deepcopy(existing)

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
        "summary": {
            "accepted_evidences": len(accepted),
            "confirmed": len(accepted) - corrected,
            "corrected": corrected,
            "pending_appendix": len(pending),
            "rejected_excluded": sum(1 for item in evidences if item.get("review_status") == "rejected"),
        },
        "sections": sections,
        "pending_appendix": pending,
        "limitations": [
            "Il report descrive solo i momenti coperti dalle evidenze revisionate.",
            "Le interpretazioni restano supporto decisionale e richiedono verifica dello staff tecnico.",
        ],
    }
    reports.append(report)
    project["reports"] = reports[-20:]
    pipeline = project.get("pipeline") if isinstance(project.get("pipeline"), dict) else {}
    stages = pipeline.get("stages") if isinstance(pipeline.get("stages"), dict) else {}
    stages["report_generation"] = {"status": "completed", "progress": 100, "report_id": report["report_id"]}
    pipeline.update({"status": "completed", "stage": "report_generation", "progress": 100, "stages": stages})
    project["pipeline"] = pipeline
    saved = save_project(user_id, asset_id, project, status="completed", stage="report_generation", progress=100)
    if not saved:
        raise RuntimeError("Impossibile salvare il report tecnico")
    return deepcopy(report)
