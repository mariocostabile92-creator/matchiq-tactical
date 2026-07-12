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
    workflow = meta.get("workflow_state") or meta.get("workflow") or row.get("status") or "ready"
    return {
        "id": row.get("id"),
        "kind": "video_session",
        "module": "Video Hub",
        "title": row.get("title") or row.get("file_name") or "Sessione Video",
        "status": str(workflow).replace("_", " ").title(),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at") or row.get("created_at")),
        "url": f"/video.html?session={row.get('id')}",
        "action": "Continua",
    }


def _report_item(row):
    return {
        "id": row.get("id"),
        "kind": "video_report",
        "module": "Video AI",
        "title": row.get("title") or "Report Video AI",
        "status": "Report pronto",
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("created_at")),
        "url": f"/video.html?report={row.get('id')}",
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
    activity = [_asset_item(row) for row in assets] + [_report_item(row) for row in reports]

    for row in scout_reports[:8]:
        activity.append({
            "id": row.get("id"), "kind": "scout_report", "module": "Scout",
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

    priorities = []
    if assets:
        latest_asset = _asset_item(max(assets, key=lambda row: _sort_key({"updated_at": row.get("updated_at"), "created_at": row.get("created_at")})))
        priorities.append({
            "type": "operational",
            "title": "Sessione Video pronta da continuare",
            "text": latest_asset["title"],
            "url": latest_asset["url"],
            "action": "Apri Video AI",
        })
    if reports:
        latest_report = _report_item(max(reports, key=lambda row: _sort_key({"created_at": row.get("created_at")})))
        priorities.append({
            "type": "confirmed",
            "title": "Ultimo report disponibile",
            "text": latest_report["title"],
            "url": latest_report["url"],
            "action": "Apri report",
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
        "continue_items": activity[:3],
        "activities": activity[:8],
        "ai_priorities": priorities[:3],
        "section_errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
