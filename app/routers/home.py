import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from database import (
    get_plan_limits,
    get_saved_matches,
    get_saved_players,
    get_scout_reports,
    get_usage_summary,
    get_video_assets,
    get_video_reports,
)
from usage_guard import get_optional_user, is_owner_user, normalize_plan


router = APIRouter(prefix="/api/home", tags=["home"])


def _metadata(value):
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _report_payload(row):
    return _metadata(row.get("payload"))


def _workflow_state(row, meta=None):
    meta = meta or _metadata(row.get("metadata"))
    raw = str(meta.get("workflow_state") or meta.get("workflow") or row.get("status") or "ready").lower().strip()
    if raw in {"queued", "pending", "processing", "uploading", "analyzing", "elaborazione", "in_progress"}:
        return "processing"
    if raw in {"failed", "error", "errore"}:
        return "failed"
    if raw in {"archived", "archiviata"} or str(meta.get("archive_state") or "").lower() == "archived":
        return "archived"
    return "ready"


def _iso(value):
    text = str(value or "").strip()
    return text or None


def _sort_key(item):
    raw = str(item.get("updated_at") or item.get("created_at") or "")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0


def _safe_call(name, callback, errors):
    try:
        return callback()
    except Exception:
        errors.append(name)
        return []


def _asset_item(row):
    meta = _metadata(row.get("metadata"))
    workflow = _workflow_state(row, meta)
    labels = {
        "processing": "In elaborazione",
        "failed": "Elaborazione non riuscita",
        "archived": "Archiviata",
        "ready": "Pronta",
    }
    return {
        "id": row.get("id"),
        "record_key": f"video_session:{row.get('id')}",
        "kind": "video_session",
        "module": "Libreria Video AI",
        "title": row.get("title") or row.get("file_name") or "Sessione Video",
        "status": labels[workflow],
        "workflow_state": workflow,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at") or row.get("created_at")),
        "url": f"/video.html?session={row.get('id')}",
        "action": "Controlla stato" if workflow == "processing" else "Continua",
    }


def _report_item(row):
    payload = _report_payload(row)
    asset_id = payload.get("video_asset_id")
    url = f"/video.html?session={asset_id}" if asset_id else "/video.html#archiveList"
    return {
        "id": row.get("id"),
        "record_key": f"video_report:{row.get('id')}",
        "kind": "video_report",
        "module": "Video AI",
        "title": row.get("title") or "Report Video AI",
        "status": "Report pronto",
        "video_asset_id": asset_id,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("created_at")),
        "url": url,
        "action": "Apri",
    }


@router.get("/summary")
def home_summary(user=Depends(get_optional_user)):
    if not user:
        return {
            "ok": True,
            "authenticated": False,
            "account": {"plan": "guest", "label": "Guest", "is_owner": False},
            "stats": {},
            "continue_items": [],
            "activities": [],
            "ai_priorities": [],
            "section_errors": [],
        }

    user_id = int(user["id"])
    errors = []
    assets = _safe_call("video_sessions", lambda: get_video_assets(user_id, limit=80), errors)
    reports = _safe_call("video_reports", lambda: get_video_reports(user_id, limit=80), errors)
    players = _safe_call("saved_players", lambda: get_saved_players(user_id), errors)
    scout_reports = _safe_call("scout_reports", lambda: get_scout_reports(user_id), errors)
    saved_matches = _safe_call("saved_matches", lambda: get_saved_matches(user_id), errors)
    usage = _safe_call("usage", lambda: get_usage_summary(user_id), errors)
    if not isinstance(usage, dict):
        usage = {}

    plan = "owner" if is_owner_user(user) else normalize_plan(user.get("plan") or "free")
    limits = get_plan_limits(plan)
    asset_items = [_asset_item(row) for row in assets]
    report_items = [_report_item(row) for row in reports]
    activity = asset_items + report_items

    for row in scout_reports[:8]:
        activity.append({
            "id": row.get("id"), "record_key": f"scout_report:{row.get('id')}",
            "kind": "scout_report", "module": "Scout",
            "title": row.get("title") or "Analisi Scout", "status": "Analisi salvata",
            "created_at": _iso(row.get("created_at")), "updated_at": _iso(row.get("created_at")),
            "url": "/scout.html", "action": "Apri Scout",
        })

    activity.sort(key=_sort_key, reverse=True)
    total_frames = sum(max(0, int(row.get("frames_analyzed") or 0)) for row in reports)
    archived = 0
    for row in assets:
        meta = _metadata(row.get("metadata"))
        if str(meta.get("archive_state") or "").lower() == "archived":
            archived += 1

    report_asset_ids = {str(item.get("video_asset_id")) for item in report_items if item.get("video_asset_id")}
    active_assets = [item for item in asset_items if item["workflow_state"] != "archived"]
    continue_items = sorted(active_assets, key=_sort_key, reverse=True)[:3]

    priorities = []
    processing_assets = [item for item in active_assets if item["workflow_state"] == "processing"]
    ready_without_report = [
        item for item in active_assets
        if item["workflow_state"] == "ready" and str(item["id"]) not in report_asset_ids
    ]
    if processing_assets:
        latest_asset = max(processing_assets, key=_sort_key)
        priorities.append({
            "type": "operational",
            "title": "Video in elaborazione",
            "text": latest_asset["title"],
            "url": latest_asset["url"],
            "action": "Controlla stato",
        })
    if ready_without_report:
        latest_asset = max(ready_without_report, key=_sort_key)
        priorities.append({
            "type": "operational",
            "title": "Sessione Video pronta: manca il report",
            "text": latest_asset["title"],
            "url": latest_asset["url"],
            "action": "Genera report",
        })

    return {
        "ok": True,
        "authenticated": True,
        "account": {
            "plan": plan,
            "label": "Owner" if plan == "owner" else plan.title(),
            "is_owner": plan == "owner",
            "limits": {
                "coach_enabled": True,
                "video_report_limit": limits.get("video_report_daily", 0),
                "video_archive_limit": limits.get("video_archive_limit", 0),
                "scout_enabled": bool(limits.get("advanced_scout") or limits.get("scout_daily")),
            },
        },
        "stats": {
            "video_sessions": len(assets),
            "video_reports": len(reports),
            "frames_saved": total_frames,
            "players_observed": len(players),
            "scout_reports": len(scout_reports),
            "saved_matches": len(saved_matches),
            "archived_items": archived,
            "usage_today": sum(int(value or 0) for value in usage.values() if isinstance(value, (int, float))),
        },
        "stats_available": {
            "video_sessions": "video_sessions" not in errors,
            "video_reports": "video_reports" not in errors,
            "frames_saved": "video_reports" not in errors,
            "players_observed": "saved_players" not in errors,
            "scout_reports": "scout_reports" not in errors,
            "saved_matches": "saved_matches" not in errors,
            "usage_today": "usage" not in errors,
        },
        "continue_items": continue_items,
        "activities": activity[:8],
        "ai_priorities": priorities[:3],
        "section_errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
