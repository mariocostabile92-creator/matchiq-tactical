from typing import Dict, FrozenSet


NODE_TYPES: Dict[str, dict] = {
    "match": {"owner": "coach", "source": "saved_match", "versioned": True, "on_delete": "invalidate"},
    "coach_session": {"owner": "coach", "source": "coach_session", "versioned": True, "on_delete": "invalidate"},
    "coach_event": {"owner": "coach", "source": "coach_event", "versioned": True, "on_delete": "invalidate"},
    "voice_observation": {"owner": "voice_coach", "source": "voice_observation", "versioned": True, "on_delete": "invalidate"},
    "voice_match_theme": {"owner": "voice_coach", "source": "voice_match_theme", "versioned": True, "on_delete": "invalidate"},
    "historical_pattern": {"owner": "pattern_intelligence", "source": "pattern", "versioned": True, "on_delete": "retain"},
    "evidence": {"owner": "pattern_intelligence", "source": "pattern_evidence", "versioned": False, "on_delete": "invalidate"},
    "weekly_briefing": {"owner": "weekly_briefing", "source": "weekly_briefing", "versioned": True, "on_delete": "invalidate"},
    "training_plan": {"owner": "training_planner", "source": "training_plan", "versioned": True, "on_delete": "retain"},
    "training_session": {"owner": "training_planner", "source": "training_session", "versioned": True, "on_delete": "invalidate"},
    "training_exercise": {"owner": "training_planner", "source": "training_exercise", "versioned": True, "on_delete": "invalidate"},
    "video_session": {"owner": "video_ai", "source": "video_asset", "versioned": True, "on_delete": "invalidate"},
    "video_frame": {"owner": "video_ai", "source": "video_frame", "versioned": True, "on_delete": "invalidate"},
    "video_clip": {"owner": "video_ai", "source": "video_clip", "versioned": True, "on_delete": "invalidate"},
    "video_report": {"owner": "video_ai", "source": "video_report", "versioned": True, "on_delete": "invalidate"},
    "coach_report": {"owner": "coach", "source": "coach_report", "versioned": True, "on_delete": "invalidate"},
    "player": {"owner": "knowledge", "source": "roster_player", "versioned": True, "on_delete": "invalidate"},
    "coach_profile": {"owner": "knowledge", "source": "coach_profile", "versioned": True, "on_delete": "invalidate"},
    "team_profile": {"owner": "knowledge", "source": "team_profile", "versioned": True, "on_delete": "invalidate"},
    "knowledge_source": {"owner": "knowledge", "source": "knowledge_source", "versioned": True, "on_delete": "invalidate"},
    "staff_note": {"owner": "knowledge", "source": "staff_note", "versioned": True, "on_delete": "retain"},
    "tag": {"owner": "knowledge", "source": "tag", "versioned": False, "on_delete": "invalidate"},
    "timeline_event": {"owner": "knowledge", "source": "timeline_event", "versioned": False, "on_delete": "invalidate"},
    "scout_report": {"owner": "scout", "source": "scout_report", "versioned": True, "on_delete": "invalidate"},
    "tactical_identity_profile": {"owner": "tactical_identity", "source": "tactical_identity_profile", "versioned": True, "on_delete": "retain"},
    "tactical_identity_dimension": {"owner": "tactical_identity", "source": "tactical_identity_dimension", "versioned": True, "on_delete": "retain"},
    "identity_change": {"owner": "tactical_identity", "source": "identity_change", "versioned": True, "on_delete": "retain"},
    "staff_validation": {"owner": "tactical_identity", "source": "staff_validation", "versioned": True, "on_delete": "retain"},
}

RELATION_TYPES: FrozenSet[str] = frozenset({
    "derives_from", "supported_by", "contradicts", "confirms", "weakens", "summarizes",
    "includes", "belongs_to", "occurred_in", "involves_player", "concerns_zone", "concerns_topic",
    "generated_from", "used_by", "produced", "followed_by", "preceded_by", "addressed_by",
    "selected_for", "modified_from", "validated_by_staff", "dismissed_by_staff", "resolved_by", "evolved_from", "observed_in", "related_to",
})

ALLOWED_RELATIONS = {
    "voice_observation": {"occurred_in", "involves_player", "concerns_zone", "concerns_topic", "supported_by", "related_to"},
    "voice_match_theme": {"includes", "occurred_in", "concerns_zone", "concerns_topic", "related_to"},
    "historical_pattern": {"supported_by", "contradicts", "concerns_zone", "concerns_topic", "addressed_by", "related_to"},
    "weekly_briefing": {"summarizes", "generated_from", "includes", "related_to"},
    "training_plan": {"generated_from", "addressed_by", "includes", "modified_from", "related_to"},
    "training_session": {"belongs_to", "includes", "selected_for", "followed_by", "preceded_by", "related_to"},
    "training_exercise": {"belongs_to", "selected_for", "concerns_topic", "related_to"},
    "video_frame": {"belongs_to", "confirms", "weakens", "concerns_topic", "related_to"},
    "video_clip": {"belongs_to", "confirms", "concerns_topic", "related_to"},
    "video_report": {"generated_from", "occurred_in", "summarizes", "related_to"},
    "coach_report": {"produced", "occurred_in", "summarizes", "related_to"},
    "evidence": {"occurred_in", "involves_player", "concerns_zone", "concerns_topic", "related_to"},
    "player": {"related_to"},
    "match": {"produced", "followed_by", "preceded_by", "includes", "related_to"},
    "scout_report": {"involves_player", "generated_from", "related_to"},
    "tactical_identity_profile": {"supported_by", "evolved_from", "belongs_to", "related_to"},
    "tactical_identity_dimension": {"belongs_to", "supported_by", "contradicts", "validated_by_staff", "observed_in", "evolved_from", "related_to"},
    "identity_change": {"belongs_to", "evolved_from", "supported_by", "related_to"},
    "staff_validation": {"belongs_to", "validated_by_staff", "related_to"},
}


def canonical_key(workspace_id: int, node_type: str, source_type: str, source_id: str) -> str:
    if node_type not in NODE_TYPES:
        raise ValueError("Tipo nodo Knowledge non supportato")
    return f"{workspace_id}:{node_type}:{source_type}:{source_id}"


def validate_relation(from_type: str, relation_type: str) -> None:
    if relation_type not in RELATION_TYPES:
        raise ValueError("Relazione Knowledge non supportata")
    allowed = ALLOWED_RELATIONS.get(from_type, {"related_to"})
    if relation_type not in allowed:
        raise ValueError(f"Relazione {relation_type} non consentita per {from_type}")
