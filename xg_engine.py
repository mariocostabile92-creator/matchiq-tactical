import random


def generate_xg_analysis(match_data, tactical_data=None):

    minute = match_data.get("minute", 0)

    home_pressure = 50
    away_pressure = 50

    if tactical_data:
        home_pressure = tactical_data.get("home_pressure", 50)
        away_pressure = tactical_data.get("away_pressure", 50)

    # -------------------------
    # HOME xG
    # -------------------------

    home_xg = round(
        (home_pressure / 100) * random.uniform(0.8, 2.8),
        2
    )

    # -------------------------
    # AWAY xG
    # -------------------------

    away_xg = round(
        (away_pressure / 100) * random.uniform(0.8, 2.8),
        2
    )

    # -------------------------
    # BIG CHANCES
    # -------------------------

    home_big = max(0, int(home_xg * random.uniform(1, 3)))
    away_big = max(0, int(away_xg * random.uniform(1, 3)))

    # -------------------------
    # SHOT QUALITY
    # -------------------------

    home_quality = round(
        min(100, home_xg * 35),
        1
    )

    away_quality = round(
        min(100, away_xg * 35),
        1
    )

    # -------------------------
    # XTHREAT
    # -------------------------

    home_xthreat = round(
        home_pressure * random.uniform(0.6, 1.4),
        1
    )

    away_xthreat = round(
        away_pressure * random.uniform(0.6, 1.4),
        1
    )

    # -------------------------
    # DOMINANCE
    # -------------------------

    if home_xg > away_xg:
        dominance = "HOME"
    elif away_xg > home_xg:
        dominance = "AWAY"
    else:
        dominance = "BALANCED"

    return {
        "minute": minute,

        "home_xg": home_xg,
        "away_xg": away_xg,

        "home_big_chances": home_big,
        "away_big_chances": away_big,

        "home_shot_quality": home_quality,
        "away_shot_quality": away_quality,

        "home_xthreat": home_xthreat,
        "away_xthreat": away_xthreat,

        "dominance": dominance
    }