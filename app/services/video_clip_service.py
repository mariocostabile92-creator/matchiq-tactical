from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from database import utc_now
from app.models.video_intelligence import EvidenceClipRequest
from app.repositories.video_intelligence_repository import load_project, save_project


MAX_EVIDENCE_CLIP_MS = 120_000
CLIP_QUALITY_CONFIG = {
    "default_pre_roll_ms": 4_000,
    "default_post_roll_ms": 4_000,
    "minimum_clip_ms": 4_000,
    "duplicate_overlap_ratio": 0.82,
    "duplicate_timestamp_ms": 1_200,
}


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


def build_suggested_clip_reference(
    asset_id: int,
    start_ms: int,
    end_ms: int,
    duration_ms: int = 0,
    pre_roll_ms: int = CLIP_QUALITY_CONFIG["default_pre_roll_ms"],
    post_roll_ms: int = CLIP_QUALITY_CONFIG["default_post_roll_ms"],
) -> Dict[str, Any]:
    source_start = max(0, int(start_ms))
    source_end = max(source_start + 1_000, int(end_ms))
    suggested_start = max(0, source_start - max(0, int(pre_roll_ms)))
    suggested_end = source_end + max(0, int(post_roll_ms))
    if duration_ms:
        suggested_end = min(int(duration_ms), suggested_end)
    if suggested_end - suggested_start < CLIP_QUALITY_CONFIG["minimum_clip_ms"]:
        suggested_end = suggested_start + CLIP_QUALITY_CONFIG["minimum_clip_ms"]
        if duration_ms and suggested_end > duration_ms:
            suggested_end = int(duration_ms)
            suggested_start = max(0, suggested_end - CLIP_QUALITY_CONFIG["minimum_clip_ms"])
    clip = build_clip_reference(asset_id, suggested_start, suggested_end, duration_ms)
    clip.update({
        "selection_status": "suggested",
        "suggested_start_timestamp_ms": clip["start_timestamp_ms"],
        "suggested_end_timestamp_ms": clip["end_timestamp_ms"],
        "source_segment_start_ms": source_start,
        "source_segment_end_ms": source_end,
        "pre_roll_ms": max(0, source_start - clip["start_timestamp_ms"]),
        "post_roll_ms": max(0, clip["end_timestamp_ms"] - source_end),
    })
    return clip


def _clip_overlap_ratio(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    left_clip = left.get("clip_reference") or {}
    right_clip = right.get("clip_reference") or {}
    left_start = int(left_clip.get("start_timestamp_ms") or left.get("start_timestamp_ms") or 0)
    left_end = int(left_clip.get("end_timestamp_ms") or left.get("end_timestamp_ms") or left_start)
    right_start = int(right_clip.get("start_timestamp_ms") or right.get("start_timestamp_ms") or 0)
    right_end = int(right_clip.get("end_timestamp_ms") or right.get("end_timestamp_ms") or right_start)
    overlap = max(0, min(left_end, right_end) - max(left_start, right_start))
    shortest = max(1, min(left_end - left_start, right_end - right_start))
    return overlap / shortest


def deduplicate_evidence_clips(evidences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    for evidence in sorted(evidences, key=lambda item: (
        int(item.get("representative_timestamp_ms") or 0), str(item.get("evidence_id") or "")
    )):
        duplicate = next((item for item in kept if (
            str(item.get("phase_type") or "") == str(evidence.get("phase_type") or "")
            and (
                abs(int(item.get("representative_timestamp_ms") or 0) - int(evidence.get("representative_timestamp_ms") or 0))
                <= CLIP_QUALITY_CONFIG["duplicate_timestamp_ms"]
                or _clip_overlap_ratio(item, evidence) >= CLIP_QUALITY_CONFIG["duplicate_overlap_ratio"]
            )
        )), None)
        if not duplicate:
            kept.append(evidence)
            continue
        current_score = float((evidence.get("representative_frame") or {}).get("score") or evidence.get("confidence_score") or 0)
        previous_score = float((duplicate.get("representative_frame") or {}).get("score") or duplicate.get("confidence_score") or 0)
        if current_score > previous_score:
            kept[kept.index(duplicate)] = evidence
    return kept


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
    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = None
    for evidence in evidences:
        if isinstance(evidence, dict) and evidence.get("evidence_id") == evidence_id:
            found = evidence
            break
    if not found:
        raise LookupError("Evidenza non trovata")

    current = found.get("clip_reference") if isinstance(found.get("clip_reference"), dict) else {}
    if data.reset_to_suggestion:
        start_ms = current.get("suggested_start_timestamp_ms")
        end_ms = current.get("suggested_end_timestamp_ms")
        if start_ms is None or end_ms is None:
            raise ValueError("Intervallo suggerito non disponibile")
        selection_status = "suggested"
    else:
        if data.start_timestamp_ms is None or data.end_timestamp_ms is None:
            raise ValueError("Indica inizio e fine della clip")
        start_ms = int(data.start_timestamp_ms)
        end_ms = int(data.end_timestamp_ms)
        selection_status = "staff_corrected"
    if end_ms <= start_ms:
        raise ValueError("La fine della clip deve essere successiva all'inizio")
    if duration_ms and start_ms >= duration_ms:
        raise ValueError("L'inizio della clip supera la durata del video")

    updated = build_clip_reference(
        asset_id,
        start_ms,
        end_ms,
        duration_ms,
    )
    updated.update({
        "selection_status": selection_status,
        "suggested_start_timestamp_ms": current.get("suggested_start_timestamp_ms", updated["start_timestamp_ms"]),
        "suggested_end_timestamp_ms": current.get("suggested_end_timestamp_ms", updated["end_timestamp_ms"]),
        "source_segment_start_ms": current.get("source_segment_start_ms"),
        "source_segment_end_ms": current.get("source_segment_end_ms"),
        "pre_roll_ms": current.get("pre_roll_ms", 0),
        "post_roll_ms": current.get("post_roll_ms", 0),
        "updated_at": utc_now(),
    })
    found["clip_reference"] = updated
    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile salvare la clip-evidenza")
    return deepcopy(found)
