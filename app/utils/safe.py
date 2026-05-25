"""
app/utils/safe.py

Utility sicure per conversioni, clamp e normalizzazione dati.
Usate da main.py, servizi e router.
"""


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value, min_value=0, max_value=100):
    try:
        return max(min_value, min(max_value, int(value)))
    except Exception:
        return min_value


def safe_percentage(value, default=0):
    return clamp(safe_float(value, default), 0, 100)


def normalize_score(score=None, home_goals=None, away_goals=None):
    if isinstance(score, str):
        parts = score.replace(" ", "").split("-")
        return {
            "home": safe_int(parts[0], 0) if len(parts) > 0 else 0,
            "away": safe_int(parts[1], 0) if len(parts) > 1 else 0,
        }

    if isinstance(score, dict):
        return {
            "home": safe_int(score.get("home", home_goals), 0),
            "away": safe_int(score.get("away", away_goals), 0),
        }

    return {
        "home": safe_int(home_goals, 0),
        "away": safe_int(away_goals, 0),
    }