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
        if item.get("status") in {"CONFIRMED", "MODIFIED"}
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
        "level": team.get("level"),
        "average_age": team.get("average_age"),
        "player_count": team.get("player_count") or len(roster),
        "goalkeeper_count": team.get("goalkeeper_count")
        or len(
            [
                player
                for player in roster
                if str(player.get("role") or "").lower() in {"portiere", "gk"}
            ]
        ),
        "training_days": team.get("training_days") or [],
        "training_duration": team.get("training_duration"),
        "match_day": team.get("match_day"),
        "pitch_type": team.get("pitch_type"),
        "pitch_dimensions": team.get("pitch_dimensions"),
        "available_materials": team.get("available_materials") or [],
        "playing_principles": team.get("playing_principles") or [],
        "preferred_formation": team.get("preferred_formation"),
        "average_intensity": team.get("average_intensity"),
        "season_objectives": team.get("season_objectives") or [],
    }
    return {
        "workspace": workspace,
        "priorities": priorities,
        "team_profile": team,
        "constraints": constraints,
        "sources_count": sum(len(item["sources"]) for item in priorities),
    }


def source_fingerprint(
    bundle: Dict[str, Any],
    settings: Dict[str, Any],
) -> str:
    stable = {
        "contract": "weekly-priority-session-composer-v2",
        "priorities": [
            {
                "priority_id": item["priority_id"],
                "topic": item["topic"],
                "title": item["title"],
                "phase": item["phase"],
                "priority_level": item["priority_level"],
                "confidence": item["confidence"],
                "references": item["references"],
            }
            for item in bundle["priorities"]
        ],
        "team_profile": {
            key: (bundle.get("team_profile") or {}).get(key)
            for key in (
                "category",
                "level",
                "average_age",
                "player_count",
                "goalkeeper_count",
                "training_days",
                "training_duration",
                "match_day",
                "pitch_type",
                "pitch_dimensions",
                "available_materials",
                "playing_principles",
                "preferred_formation",
                "average_intensity",
                "season_objectives",
            )
        },
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
        "session_duration": int(constraints.get("training_duration") or 90),
        "intensity": constraints.get("average_intensity") or "media",
        "category": constraints.get("category") or "Dilettanti",
    }
