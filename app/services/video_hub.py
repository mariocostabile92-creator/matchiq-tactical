from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from database import (
    create_video_asset,
    get_video_asset,
    get_video_assets,
    update_video_asset_status,
    utc_now,
)


SESSION_TYPES = {
    "official_match": "Partita ufficiale",
    "friendly_match": "Amichevole",
    "training": "Allenamento",
    "exercise": "Esercitazione",
    "opponent_analysis": "Analisi avversario",
    "individual_analysis": "Analisi individuale",
    "goalkeeper": "Portieri",
    "youth": "Settore giovanile",
    "other": "Altro",
}

SESSION_STATES = {"draft", "uploading", "importing", "processing", "ready", "failed", "archived"}
ARCHIVE_STATES = {"active", "archived"}


def _clean_text(value: Any, limit: int = 240) -> str:
    return str(value or "").strip()[:limit]


def _clean_float(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _clean_tags(value: Any, limit: int = 12) -> List[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").replace(";", ",").split(",")
    tags: List[str] = []
    for raw in raw_items:
        tag = _clean_text(raw, 40).strip("# ")
        if tag and tag.lower() not in {item.lower() for item in tags}:
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags


def _metadata(row: Optional[dict]) -> Dict[str, Any]:
    metadata = (row or {}).get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def _pick_session_type(value: Any) -> str:
    value = _clean_text(value, 80)
    return value if value in SESSION_TYPES else "official_match"


def _pick_status(value: Any) -> str:
    value = _clean_text(value, 40).lower()
    if value == "error":
        return "failed"
    if value == "queued":
        return "processing"
    return value if value in SESSION_STATES else "ready"


def _pick_archive_state(value: Any) -> str:
    value = _clean_text(value, 40).lower()
    return value if value in ARCHIVE_STATES else "active"


def normalize_session_payload(data: dict) -> Dict[str, Any]:
    data = data or {}
    session_type = _pick_session_type(data.get("session_type") or data.get("type"))
    home_team = _clean_text(data.get("home_team") or data.get("team"), 120)
    away_team = _clean_text(data.get("away_team") or data.get("opponent"), 120)
    return {
        "session_type": session_type,
        "season": _clean_text(data.get("season"), 40),
        "session_date": _clean_text(data.get("session_date") or data.get("date"), 40),
        "team": _clean_text(data.get("team") or home_team, 120),
        "home_team": home_team,
        "away_team": away_team,
        "opponent": _clean_text(data.get("opponent") or away_team, 120),
        "competition": _clean_text(data.get("competition"), 120),
        "category": _clean_text(data.get("category"), 80),
        "result": _clean_text(data.get("result"), 40),
        "field": _clean_text(data.get("field") or data.get("field_name"), 120),
        "duration_seconds": _clean_float(data.get("duration_seconds")),
        "source_provider": _clean_text(data.get("source_provider") or data.get("provider"), 80) or "matchiq",
        "external_id": _clean_text(data.get("external_id"), 180),
        "original_name": _clean_text(data.get("original_name"), 220),
        "storage_key": _clean_text(data.get("storage_key"), 260),
        "format": _clean_text(data.get("format"), 40),
        "mime_type": _clean_text(data.get("mime_type"), 120),
        "thumbnail": _clean_text(data.get("thumbnail"), 500),
        "notes": _clean_text(data.get("notes"), 2000),
        "tags": _clean_tags(data.get("tags")),
        "archive_state": _pick_archive_state(data.get("archive_state")),
    }


def public_video_session(row: dict) -> Dict[str, Any]:
    metadata = _metadata(row)
    job = metadata.get("job") if isinstance(metadata.get("job"), dict) else {}
    status = _pick_status(row.get("status") or job.get("status") or metadata.get("status"))
    archive_state = _pick_archive_state(metadata.get("archive_state"))
    return {
        "id": row.get("id"),
        "owner_id": row.get("user_id"),
        "title": row.get("title") or row.get("file_name") or "Sessione video MatchIQ",
        "type": _pick_session_type(metadata.get("session_type") or metadata.get("type")),
        "type_label": SESSION_TYPES.get(_pick_session_type(metadata.get("session_type") or metadata.get("type")), "Partita ufficiale"),
        "season": metadata.get("season") or "",
        "date": metadata.get("session_date") or metadata.get("date") or "",
        "team": metadata.get("team") or metadata.get("home_team") or "",
        "home_team": metadata.get("home_team") or "",
        "away_team": metadata.get("away_team") or "",
        "opponent": metadata.get("opponent") or metadata.get("away_team") or "",
        "competition": metadata.get("competition") or "",
        "category": row.get("category") or metadata.get("category") or "",
        "result": metadata.get("result") or "",
        "field": metadata.get("field") or metadata.get("field_name") or "",
        "duration_seconds": _clean_float(metadata.get("duration_seconds")),
        "source_type": row.get("source_type") or "session",
        "source_provider": metadata.get("source_provider") or metadata.get("provider") or metadata.get("storage") or "matchiq",
        "source_url": row.get("source_url") or "",
        "external_id": metadata.get("external_id") or "",
        "original_name": metadata.get("original_name") or row.get("file_name") or "",
        "storage_key": metadata.get("storage_key") or "",
        "format": metadata.get("format") or "",
        "mime_type": row.get("mime_type") or metadata.get("mime_type") or "",
        "size_bytes": int(row.get("size_bytes") or 0),
        "thumbnail": metadata.get("thumbnail") or "",
        "status": status,
        "progress": max(0, min(100, int(job.get("progress") if job.get("progress") is not None else (100 if status == "ready" else 0)))),
        "notes": metadata.get("notes") or "",
        "tags": metadata.get("tags") if isinstance(metadata.get("tags"), list) else [],
        "created_at": row.get("created_at") or "",
        "updated_at": row.get("updated_at") or "",
        "last_used_at": metadata.get("last_used_at") or "",
        "rights_confirmed": bool(row.get("rights_confirmed")),
        "archive_state": archive_state,
        "is_archived": archive_state == "archived" or status == "archived",
        "error": job.get("error") or metadata.get("error") or "",
        "metadata": metadata,
    }


def create_video_session(user_id: int, data: dict) -> Dict[str, Any]:
    session = normalize_session_payload(data)
    now = utc_now()
    metadata = {
        **session,
        "hub_version": 1,
        "created_from": "video_hub",
        "job": {"status": "draft", "stage": "draft", "progress": 0, "updated_at": now},
    }
    result = create_video_asset(
        user_id=user_id,
        title=_clean_text(data.get("title"), 180) or "Nuova sessione video",
        club_name=_clean_text(data.get("club_name") or data.get("team"), 160),
        category=session.get("category") or "",
        source_type=_clean_text(data.get("source_type"), 40) or "session",
        source_url=_clean_text(data.get("source_url"), 1000),
        file_name=session.get("original_name") or "",
        mime_type=session.get("mime_type") or "",
        size_bytes=int(data.get("size_bytes") or 0),
        rights_confirmed=bool(data.get("rights_confirmed", False)),
        status="draft",
        metadata=metadata,
    )
    return public_video_session(get_video_asset(user_id, result["id"]))


def patch_video_session(user_id: int, asset_id: int, data: dict) -> Optional[Dict[str, Any]]:
    asset = get_video_asset(user_id, asset_id)
    if not asset:
        return None
    metadata = _metadata(asset)
    patch = normalize_session_payload({**metadata, **(data or {})})
    metadata.update({key: value for key, value in patch.items() if value not in ("", [], 0.0)})
    metadata["updated_from"] = "video_hub"
    metadata["updated_at"] = utc_now()
    status = _pick_status((data or {}).get("status") or asset.get("status") or metadata.get("status"))
    updated = update_video_asset_status(
        user_id=user_id,
        asset_id=asset_id,
        status=status,
        progress=(data or {}).get("progress"),
        stage=status,
        error=_clean_text((data or {}).get("error"), 500),
        metadata_patch=metadata,
    )
    return public_video_session(updated) if updated else None


def archive_video_session(user_id: int, asset_id: int, archived: bool = True) -> Optional[Dict[str, Any]]:
    asset = get_video_asset(user_id, asset_id)
    if not asset:
        return None
    metadata = _metadata(asset)
    metadata["archive_state"] = "archived" if archived else "active"
    metadata["archived_at" if archived else "restored_at"] = utc_now()
    status = "archived" if archived else _pick_status(metadata.get("job", {}).get("status") if isinstance(metadata.get("job"), dict) else "ready")
    updated = update_video_asset_status(
        user_id=user_id,
        asset_id=asset_id,
        status=status,
        progress=100 if not archived else None,
        stage=status,
        metadata_patch=metadata,
    )
    return public_video_session(updated) if updated else None


def touch_video_session(user_id: int, asset_id: int) -> Optional[Dict[str, Any]]:
    asset = get_video_asset(user_id, asset_id)
    if not asset:
        return None
    public = public_video_session(asset)
    updated = update_video_asset_status(
        user_id=user_id,
        asset_id=asset_id,
        status=public.get("status") or "ready",
        progress=public.get("progress", 100),
        stage=public.get("status") or "ready",
        metadata_patch={"last_used_at": utc_now()},
    )
    return public_video_session(updated) if updated else None


def list_video_sessions(user_id: int, filters: dict) -> Dict[str, Any]:
    limit = max(1, min(100, int(filters.get("limit") or 40)))
    offset = max(0, int(filters.get("offset") or 0))
    search = _clean_text(filters.get("search"), 160).lower()
    type_filter = _clean_text(filters.get("type"), 80)
    status_filter = _clean_text(filters.get("status"), 40).lower()
    provider_filter = _clean_text(filters.get("provider"), 80).lower()
    archive_filter = _clean_text(filters.get("archive_state") or "active", 40).lower()

    rows = get_video_assets(user_id, limit=500)
    sessions = [public_video_session(row) for row in rows]

    def matches(session: dict) -> bool:
        if archive_filter != "all" and session.get("archive_state") != archive_filter:
            return False
        if type_filter and type_filter != "all" and session.get("type") != type_filter:
            return False
        if status_filter and status_filter != "all" and session.get("status") != status_filter:
            return False
        if provider_filter and provider_filter != "all" and str(session.get("source_provider") or "").lower() != provider_filter:
            return False
        if search:
            haystack = " ".join(str(session.get(key) or "") for key in (
                "title", "team", "home_team", "away_team", "opponent", "competition", "season", "notes", "category", "result"
            ))
            haystack = f"{haystack} {' '.join(session.get('tags') or [])}".lower()
            if search not in haystack:
                return False
        return True

    filtered = [session for session in sessions if matches(session)]
    return {
        "items": filtered[offset:offset + limit],
        "count": len(filtered),
        "total": len(sessions),
        "limit": limit,
        "offset": offset,
        "session_types": [{"id": key, "label": value} for key, value in SESSION_TYPES.items()],
        "states": sorted(SESSION_STATES),
    }
