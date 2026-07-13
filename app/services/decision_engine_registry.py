PHASES = ("pre_match", "live_match", "halftime", "post_match", "weekly")

DECISION_TYPES = {
    "pre_match": ("initial_shape", "pressing_height", "buildup", "width", "critical_side", "set_piece_plan"),
    "live_match": ("shape_adjustment", "pressing_adjustment", "side_protection", "aggression", "width_depth", "substitution", "score_management"),
    "halftime": ("priority_correction", "positive_maintenance", "department_monitoring", "shape_variation"),
    "post_match": ("decision_review", "pattern_followup", "training_followup"),
    "weekly": ("weekly_priority", "pattern_focus", "session_focus", "material_preparation"),
}

SOURCE_TYPES = (
    "coach_event", "voice_observation", "historical_pattern", "player", "tactical_identity_profile",
    "tactical_identity_dimension", "weekly_briefing", "training_plan", "video_frame", "video_report",
    "match", "coach_report", "staff_note",
)

ACTION_URLS = {
    "coach_event": "/coach.html", "voice_observation": "/coach.html", "historical_pattern": "/pattern-intelligence.html",
    "player": "/knowledge.html", "tactical_identity_profile": "/tactical-identity.html",
    "tactical_identity_dimension": "/tactical-identity.html", "weekly_briefing": "/weekly-briefing.html",
    "training_plan": "/training-planner.html", "video_frame": "/video.html", "video_report": "/video.html",
    "match": "/coach.html", "coach_report": "/coach.html", "staff_note": "/knowledge.html",
}
