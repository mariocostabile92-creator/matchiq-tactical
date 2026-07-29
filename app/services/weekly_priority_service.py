import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.repositories import (
    knowledge_repository,
    pattern_intelligence_repository,
    weekly_priority_repository,
)


RANKING_VERSION = "weekly-priority-v1"
CONSOLIDATED_STATUSES = {"established", "confirmed_by_staff"}


def initialize_weekly_priorities() -> None:
    weekly_priority_repository.initialize_weekly_priority_schema()


def current_week_key(today: Optional[date] = None) -> str:
    value = today or date.today()
    return (value - timedelta(days=value.weekday())).isoformat()


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _parse_date(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _recency_score(last_seen_at: Any, now: Optional[datetime] = None) -> float:
    parsed = _parse_date(last_seen_at)
    if not parsed:
        return 0.0
    reference = now or datetime.now(timezone.utc)
    days = max(0, (reference - parsed.astimezone(timezone.utc)).days)
    if days <= 7:
        return 100.0
    if days <= 21:
        return 80.0
    if days <= 45:
        return 60.0
    if days <= 90:
        return 35.0
    return 15.0


def _impact_score(pattern: Dict[str, Any]) -> float:
    score = 45.0
    if pattern.get("polarity") == "negative":
        score += 25.0
    if pattern.get("severity") == "alta":
        score += 20.0
    if pattern.get("trend_direction") == "in aumento":
        score += 10.0
    elif pattern.get("trend_direction") == "in diminuzione":
        score -= 10.0
    return _clamp(score)


def rank_pattern(
    pattern: Dict[str, Any],
    staff_status: Optional[str] = None,
) -> Dict[str, Any]:
    frequency = _clamp(float(pattern.get("occurrence_rate") or 0) * 100)
    recency = _recency_score(pattern.get("last_seen_at"))
    confidence = _clamp(float(pattern.get("confidence_score") or 0))
    staff_values = {
        "CONFIRMED": 100.0,
        "MODIFIED": 80.0,
        "DISMISSED": 0.0,
    }
    staff = staff_values.get(
        str(staff_status or "").upper(),
        80.0 if pattern.get("status") == "confirmed_by_staff" else 45.0,
    )
    impact = _impact_score(pattern)
    ranking_score = round(
        frequency * 0.30
        + recency * 0.20
        + confidence * 0.25
        + staff * 0.15
        + impact * 0.10,
        2,
    )
    level = "HIGH" if ranking_score >= 72 else ("MEDIUM" if ranking_score >= 52 else "LOW")
    return {
        "ranking_score": ranking_score,
        "priority_level": level,
        "factors": {
            "frequency": round(frequency, 2),
            "recency": round(recency, 2),
            "confidence": round(confidence, 2),
            "staff_confirmation": round(staff, 2),
            "impact": round(impact, 2),
        },
    }


def _unique(values: Iterable[Any]) -> List[Any]:
    seen = set()
    output = []
    for value in values:
        key = str(value)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _references(
    evidence: List[Dict[str, Any]],
    pattern_ids: Iterable[int],
) -> Dict[str, Any]:
    voice = []
    video = []
    coach = []
    for entry in evidence:
        source_type = str(entry.get("source_type") or "").lower()
        source_id = str(entry.get("source_id") or "")
        if "voice" in source_type:
            voice.append(source_id)
        elif "video" in source_type or "frame" in source_type:
            video.append(source_id)
        elif "coach" in source_type or source_type.startswith("match_evidence_"):
            coach.append(source_id)
    return {
        "matches": _unique(str(item.get("match_id") or "") for item in evidence),
        "patterns": _unique(pattern_ids),
        "evidence": _unique(int(item["id"]) for item in evidence if item.get("id") is not None),
        "voice_coach": _unique(voice),
        "video_ai": _unique(video),
        "coach_notes": _unique(coach),
    }


def _priority_item(
    user_id: int,
    week_key: str,
    patterns: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:
    pattern = max(
        patterns,
        key=lambda item: (
            rank_pattern(item)["ranking_score"],
            float(item.get("confidence_score") or 0),
            int(item.get("id") or 0),
        ),
    )
    pattern_ids = sorted({int(item["id"]) for item in patterns})
    source_key = (
        f"{pattern.get('canonical_topic') or 'unknown'}|"
        f"{pattern.get('phase') or 'unknown'}"
    )
    priority_seed = f"{user_id}|{week_key}|{source_key}".encode("utf-8")
    priority_id = f"priority_{hashlib.sha256(priority_seed).hexdigest()[:24]}"
    existing = weekly_priority_repository.get_by_priority_id(user_id, priority_id)
    ranking = rank_pattern(pattern, (existing or {}).get("staff_status"))
    references = _references(evidence, pattern_ids)
    summary = (
        f"{len(references['matches'])} partite e "
        f"{len(references['evidence'])} evidenze sostengono questo tema."
    )
    reason = {
        "code": "CONSOLIDATED_PATTERN",
        "summary": summary,
        "factors": {
            **ranking["factors"],
            "matches_count": len(references["matches"]),
            "evidence_count": len(references["evidence"]),
            "trend": pattern.get("trend_direction") or "non determinabile",
            "ranking_version": RANKING_VERSION,
        },
    }
    fingerprint_payload = {
        "pattern_ids": pattern_ids,
        "topic": pattern.get("canonical_topic"),
        "phase": pattern.get("phase"),
        "ranking": ranking,
        "references": references,
    }
    source_fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "priority_id": priority_id,
        "source_key": source_key,
        "source_fingerprint": source_fingerprint,
        "canonical_match_ids": references["matches"],
        "pattern_ids": references["patterns"],
        "evidence_ids": references["evidence"],
        "topic": pattern.get("title") or pattern.get("canonical_topic") or "Tema tattico",
        "phase": pattern.get("phase") or "unknown",
        "priority_level": ranking["priority_level"],
        "confidence": float(pattern.get("confidence_score") or 0),
        "ranking_score": ranking["ranking_score"],
        "reason": reason,
        "references": references,
    }


def sync_from_patterns(user_id: int) -> Dict[str, Any]:
    workspace = knowledge_repository.get_or_create_workspace(user_id)
    week_key = current_week_key()
    latest = pattern_intelligence_repository.list_patterns(
        user_id,
        {"page": 1, "page_size": 50},
    )
    consolidated = [
        item
        for item in latest["items"]
        if item.get("status") in CONSOLIDATED_STATUSES
        and not item.get("contradictory")
    ]
    grouped: Dict[str, Dict[str, Any]] = {}
    for pattern in consolidated:
        source_key = (
            f"{pattern.get('canonical_topic') or 'unknown'}|"
            f"{pattern.get('phase') or 'unknown'}"
        )
        detail = pattern_intelligence_repository.get_pattern(
            user_id,
            int(pattern["id"]),
            1,
            100,
        )
        evidence = ((detail or {}).get("evidence") or {}).get("items") or []
        group = grouped.setdefault(source_key, {"patterns": [], "evidence": []})
        group["patterns"].append(pattern)
        group["evidence"].extend(evidence)

    saved = []
    for group in grouped.values():
        evidence_by_id = {
            int(item["id"]): item
            for item in group["evidence"]
            if item.get("id") is not None
        }
        item = _priority_item(
            user_id,
            week_key,
            group["patterns"],
            list(evidence_by_id.values()),
        )
        saved.append(
            weekly_priority_repository.upsert_generated(
                user_id=user_id,
                workspace_id=int(workspace["id"]),
                week_key=week_key,
                item=item,
            )
        )
    saved.sort(
        key=lambda item: (
            float(item.get("ranking_score") or 0),
            float(item.get("confidence") or 0),
            item.get("priority_id") or "",
        ),
        reverse=True,
    )
    return {
        "generated": bool(saved),
        "week_key": week_key,
        "priorities": saved,
    }


def list_current(user_id: int, include_dismissed: bool = False) -> List[Dict[str, Any]]:
    return weekly_priority_repository.list_latest(
        user_id,
        include_dismissed=include_dismissed,
        limit=20,
    )


def detail(user_id: int, priority_id: str) -> Optional[Dict[str, Any]]:
    return weekly_priority_repository.get_by_priority_id(user_id, priority_id)


def set_staff_status(
    user_id: int,
    priority_id: str,
    *,
    status: str,
    staff_reason: Optional[str],
    topic: Optional[str],
    phase: Optional[str],
    priority_level: Optional[str],
) -> Optional[Dict[str, Any]]:
    item = weekly_priority_repository.update_staff_status(
        user_id,
        priority_id,
        status=status,
        staff_reason=(staff_reason or "").strip() or None,
        topic=(topic or "").strip() or None,
        phase=(phase or "").strip() or None,
        priority_level=priority_level,
        staff_user_id=user_id,
    )
    if item and status == "CONFIRMED":
        from app.services.training_planner_service import sync_confirmed_priorities

        sync_confirmed_priorities(user_id)
    return item
