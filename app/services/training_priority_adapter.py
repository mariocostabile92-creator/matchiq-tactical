import hashlib
import json
from typing import Any, Dict, Iterable, List

from app.repositories import (
    knowledge_repository,
    pattern_intelligence_repository,
    weekly_priority_repository,
)


TOPIC_FALLBACKS = {
    "transition_defense": "negative_transition",
    "lost_ball": "negative_transition",
    "transition_attack": "positive_transition",
    "left_flank": "right_flank",
    "individual_difficulty": "duels",
    "positive_behavior": "recovery",
    "rest_defense": "negative_transition",
}


def _unique(values: Iterable[Any]) -> List[Any]:
    seen = set()
    output = []
    for value in values:
        key = str(value)
        if key and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _pattern_topic(user_id: int, pattern_ids: List[int], phase: str) -> str:
    for pattern_id in pattern_ids:
        pattern = pattern_intelligence_repository.get_pattern(
            user_id,
            int(pattern_id),
            1,
            1,
        )
        canonical = str((pattern or {}).get("canonical_topic") or "").strip()
        if canonical:
            return TOPIC_FALLBACKS.get(canonical, canonical)
    fallback = str(phase or "general").strip()
    return TOPIC_FALLBACKS.get(fallback, fallback)


def _source(module: str, source_id: Any, label: str) -> Dict[str, Any]:
    return {
        "module": module,
        "source_id": str(source_id),
        "label": label,
        "count": 1,
        "kind": "structured_reference",
    }


def _sources(priority: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources = [
        _source("MatchEvidence", value, "Partita canonica")
        for value in priority.get("canonical_match_ids") or []
    ]
    sources.extend(
        _source("Pattern Intelligence", value, "Pattern consolidato")
        for value in priority.get("pattern_ids") or []
    )
    sources.extend(
        _source("Evidence", value, "Evidenza verificabile")
        for value in priority.get("evidence_ids") or []
    )
    return sources


def collect_confirmed(user_id: int) -> Dict[str, Any]:
    workspace = knowledge_repository.get_or_create_workspace(user_id)
    knowledge_id = int(workspace["id"])
    team = knowledge_repository.get_profile(
        "knowledge_team_profiles",
        knowledge_id,
        knowledge_repository.TEAM_COLUMNS,
    )
    roster = knowledge_repository.list_roster(knowledge_id)
    confirmed = [
        item
        for item in weekly_priority_repository.list_latest(
            user_id,
            include_dismissed=True,
            limit=20,
        )
        if item.get("status") == "CONFIRMED"
    ]
    priorities = []
    for item in confirmed:
        references = {
            "canonical_match_ids": _unique(item.get("canonical_match_ids") or []),
            "pattern_ids": _unique(item.get("pattern_ids") or []),
            "evidence_ids": _unique(item.get("evidence_ids") or []),
        }
        priorities.append(
            {
                "priority_id": item["priority_id"],
                "topic": _pattern_topic(
                    user_id,
                    references["pattern_ids"],
                    item.get("phase") or "",
                ),
                "title": item["topic"],
                "reason": (item.get("reason") or {}).get("summary")
                or "Priorita confermata dallo staff.",
                "level": str(item.get("priority_level") or "MEDIUM").lower(),
                "priority_level": item.get("priority_level") or "MEDIUM",
                "confidence": float(item.get("confidence") or 0),
                "phase": item.get("phase") or "unknown",
                "sources": _sources(item),
                "references": references,
            }
        )
    priorities.sort(
        key=lambda item: (
            {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(item["priority_level"], 0),
            item["confidence"],
            item["priority_id"],
        ),
        reverse=True,
    )
    constraints = {
        "category": team.get("category"),
        "player_count": team.get("player_count") or len(roster),
        "goalkeeper_count": team.get("goalkeeper_count")
        or len(
            [
                player
                for player in roster
                if str(player.get("role") or "").lower() in {"portiere", "gk"}
            ]
        ),
    }
    return {
        "workspace": workspace,
        "priorities": priorities,
        "constraints": constraints,
        "sources_count": sum(len(item["sources"]) for item in priorities),
    }


def source_fingerprint(
    bundle: Dict[str, Any],
    settings: Dict[str, Any],
) -> str:
    stable = {
        "contract": "weekly-priority-training-draft-v1",
        "priorities": [
            {
                "priority_id": item["priority_id"],
                "topic": item["topic"],
                "references": item["references"],
            }
            for item in bundle["priorities"]
        ],
        "settings": settings,
    }
    raw = json.dumps(
        stable,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def default_settings(bundle: Dict[str, Any]) -> Dict[str, Any]:
    constraints = bundle.get("constraints") or {}
    return {
        "players": max(6, int(constraints.get("player_count") or 18)),
        "goalkeepers": max(0, int(constraints.get("goalkeeper_count") or 2)),
        "session_duration": 90,
        "intensity": "media",
        "category": constraints.get("category") or "Dilettanti",
    }
