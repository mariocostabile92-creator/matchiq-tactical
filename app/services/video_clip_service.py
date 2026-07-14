from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from database import utc_now
from app.models.video_intelligence import EvidenceClipRequest
from app.repositories.video_intelligence_repository import load_project, save_project


MAX_EVIDENCE_CLIP_MS = 120_000


def build_clip_reference(asset_id: int, start_ms: int, end_ms: int, duration_ms: int = 0) -> Dict[str, Any]:
    start_ms = max(0, int(start_ms))
    end_ms = max(start_ms + 1000, int(end_ms))
    if duration_ms:
        end_ms = min(int(duration_ms), end_ms)
    if end_ms - start_ms > MAX_EVIDENCE_CLIP_MS:
        end_ms = start_ms + MAX_EVIDENCE_CLIP_MS
    return {
        "type": "source_window",
        "video_asset_id": int(asset_id),
        "start_timestamp_ms": start_ms,
        "end_timestamp_ms": end_ms,
        "duration_ms": max(0, end_ms - start_ms),
        "stream_url": f"/api/video/library/{int(asset_id)}/stream",
        "generated_file": False,
        "playback_mode": "seek_and_stop",
    }


def update_evidence_clip(
    user_id: int,
    asset_id: int,
    evidence_id: str,
    data: EvidenceClipRequest,
) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    duration_ms = int((project.get("pipeline") or {}).get("duration_ms") or 0)
    if data.end_timestamp_ms <= data.start_timestamp_ms:
        raise ValueError("La fine della clip deve essere successiva all'inizio")
    if duration_ms and data.start_timestamp_ms >= duration_ms:
        raise ValueError("L'inizio della clip supera la durata del video")

    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = None
    for evidence in evidences:
        if isinstance(evidence, dict) and evidence.get("evidence_id") == evidence_id:
            found = evidence
            break
    if not found:
        raise LookupError("Evidenza non trovata")

    found["clip_reference"] = build_clip_reference(
        asset_id,
        data.start_timestamp_ms,
        data.end_timestamp_ms,
        duration_ms,
    )
    found["clip_reference"]["selection_status"] = "staff_corrected"
    found["clip_reference"]["updated_at"] = utc_now()
    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile salvare la clip-evidenza")
    return deepcopy(found)
