ALGORITHM_VERSION = "pattern-v1"

MIN_TOTAL_MATCHES = 3
CANDIDATE_MIN_MATCHES = 2
CANDIDATE_MIN_EVIDENCE = 3
ESTABLISHED_MIN_MATCHES = 3
ESTABLISHED_MIN_RATE = 0.50
ESTABLISHED_MIN_CONFIDENCE = 55
TREND_MIN_MATCHES = 4
TREND_CHANGE_THRESHOLD = 0.20

SOURCE_WEIGHTS = {
    "objective": 1.0,
    "staff_observation": 0.72,
    "ai_interpretation": 0.58,
    "derived": 0.45,
}

STAFF_STATUSES = {
    "candidate",
    "established",
    "monitoring",
    "confirmed_by_staff",
    "dismissed_by_staff",
    "resolved",
    "archived",
}

VISIBLE_WEEKLY_STATUSES = {"established", "confirmed_by_staff", "monitoring"}
