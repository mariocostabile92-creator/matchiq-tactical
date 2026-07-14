from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from database import utc_now
from app.models.video_intelligence import EvidenceLinkRequest
from app.repositories import voice_coach_repository
from app.repositories.video_intelligence_repository import load_project, save_project


MAX_LINK_DISTANCE_MS = 90_000


def _text(value: Any, limit: int = 400) -> str:
    return str(value or "").strip()[:limit]


def _event_timestamp(event: Dict[str, Any]) -> int:
    for key in ("timestamp_ms", "video_timestamp_ms", "elapsed_ms"):
        try:
            if event.get(key) is not None:
                return max(0, int(event[key]))
        except (TypeError, ValueError):
            pass
    try:
        return max(0, int(event.get("minute") or 0) * 60_000)
    except (TypeError, ValueError):
        return 0


def _safe_staff_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    safe = []
    for index, item in enumerate(events[:300]):
        if not isinstance(item, dict):
            continue
        event_id = _text(item.get("event_id") or item.get("id") or f"staff_{index + 1}", 120)
        safe.append({
            "id": event_id,
            "type": _text(item.get("type") or item.get("event_type") or "staff_event", 100),
            "label": _text(item.get("label") or item.get("title") or item.get("note") or "Evento Coach", 300),
            "timestamp_ms": _event_timestamp(item),
            "minute": item.get("minute"),
            "source": "coach_timeline",
        })
    return safe


def _voice_notes(user_id: int, match_id: str) -> List[Dict[str, Any]]:
    if not match_id:
        return []
    try:
        rows = voice_coach_repository.list_observations(user_id, match_id)
    except Exception:
        return []
    notes = []
    for row in rows[:300]:
        if row.get("status") == "cancelled":
            continue
        notes.append({
            "id": _text(row.get("client_id") or row.get("id"), 120),
            "type": "voice_note",
            "label": _text(row.get("normalized_summary") or row.get("original_text") or "Nota Voice Coach", 300),
            "timestamp_ms": _event_timestamp(row),
            "minute": row.get("minute"),
            "source": "voice_coach",
        })
    return notes


def suggest_coach_links(
    user_id: int,
    project: Dict[str, Any],
    evidences: List[Dict[str, Any]],
    staff_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    events = _safe_staff_events(staff_events)
    if str(project.get("analysis_mode") or "") == "coach":
        coach_match = (project.get("context") or {}).get("coach_match") or {}
        match_keys = {
            str(project.get("match_id") or ""),
            str(coach_match.get("id") or ""),
            str(coach_match.get("match_id") or ""),
        }
        seen_voice = set()
        for match_key in sorted(key for key in match_keys if key):
            for note in _voice_notes(user_id, match_key):
                marker = (note["source"], note["id"])
                if marker not in seen_voice:
                    seen_voice.add(marker)
                    events.append(note)
    for evidence in evidences:
        timestamp = int(evidence.get("representative_timestamp_ms") or 0)
        suggestions = []
        for event in events:
            distance = abs(timestamp - int(event.get("timestamp_ms") or 0))
            if distance <= MAX_LINK_DISTANCE_MS:
                suggestions.append({
                    **event,
                    "distance_ms": distance,
                    "link_type": "probable",
                    "reason": "Vicinanza temporale; richiede conferma dello staff.",
                })
        suggestions.sort(key=lambda item: (item["distance_ms"], item["source"], item["id"]))
        evidence["link_suggestions"] = suggestions[:5]
    return {"events": events, "evidences": evidences}


def set_evidence_link(
    user_id: int,
    asset_id: int,
    evidence_id: str,
    data: EvidenceLinkRequest,
) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = next((item for item in evidences if isinstance(item, dict) and item.get("evidence_id") == evidence_id), None)
    if not found:
        raise LookupError("Evidenza non trovata")

    event_id = _text(data.linked_match_event_id, 120)
    note_id = _text(data.linked_note_id, 120)
    if not event_id and not note_id:
        raise ValueError("Seleziona un evento o una nota da collegare")
    valid = {
        str(item.get("id"))
        for item in (project.get("coach_context") or {}).get("events", [])
        if isinstance(item, dict)
    }
    valid.update(
        str(item.get("id"))
        for item in found.get("link_suggestions", [])
        if isinstance(item, dict)
    )
    requested = event_id or note_id
    if requested not in valid:
        raise ValueError("Il collegamento non appartiene agli eventi Coach disponibili")

    found["linked_match_event_id"] = event_id or None
    found["linked_note_id"] = note_id or None
    found["link_type"] = "manual_confirmed"
    found["link_confirmed_by"] = int(user_id)
    found["link_confirmed_at"] = utc_now()
    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile salvare il collegamento Coach")
    return deepcopy(found)


def clear_evidence_link(user_id: int, asset_id: int, evidence_id: str) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = next((item for item in evidences if isinstance(item, dict) and item.get("evidence_id") == evidence_id), None)
    if not found:
        raise LookupError("Evidenza non trovata")
    for key in ("linked_match_event_id", "linked_note_id", "link_type", "link_confirmed_by", "link_confirmed_at"):
        found[key] = None
    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile rimuovere il collegamento Coach")
    return deepcopy(found)
