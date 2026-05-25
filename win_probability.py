"""
win_probability.py
AI Win Probability Engine - MatchIQ Tactical
"""

import math


def clamp(value, min_value=0, max_value=100):
    return max(min_value, min(max_value, value))


def normalize_probs(home, draw, away):
    total = home + draw + away

    if total <= 0:
        return {
            "home": 33,
            "draw": 34,
            "away": 33
        }

    return {
        "home": round((home / total) * 100, 1),
        "draw": round((draw / total) * 100, 1),
        "away": round((away / total) * 100, 1)
    }


def generate_win_probability(match_data):
    """
    Genera probabilità live AI
    """

    home_score = match_data.get("goals", {}).get("home", 0)
    away_score = match_data.get("goals", {}).get("away", 0)

    minute = match_data.get("minute", 0)

    tactical = match_data.get("tactical_analysis", {})

    home_pressure = tactical.get("home_pressure", 0)
    away_pressure = tactical.get("away_pressure", 0)

    home_danger = tactical.get("home_danger", 0)
    away_danger = tactical.get("away_danger", 0)

    home_momentum = tactical.get("home_win_momentum", 50)
    away_momentum = tactical.get("away_win_momentum", 50)

    # BASE
    home_prob = 33
    draw_prob = 34
    away_prob = 33

    # SCORE IMPACT
    score_diff = home_score - away_score

    home_prob += score_diff * 12
    away_prob -= score_diff * 12

    # PRESSURE
    home_prob += home_pressure * 0.4
    away_prob += away_pressure * 0.4

    # DANGER
    home_prob += home_danger * 0.6
    away_prob += away_danger * 0.6

    # MOMENTUM
    home_prob += (home_momentum - 50) * 0.5
    away_prob += (away_momentum - 50) * 0.5

    # LATE GAME EFFECT
    if minute > 70:

        if score_diff > 0:
            home_prob += 10
            draw_prob -= 5
            away_prob -= 5

        elif score_diff < 0:
            away_prob += 10
            draw_prob -= 5
            home_prob -= 5

    # DRAW LOGIC
    if abs(score_diff) == 0:
        draw_prob += 10

    # CLAMP
    home_prob = clamp(home_prob)
    draw_prob = clamp(draw_prob)
    away_prob = clamp(away_prob)

    normalized = normalize_probs(
        home_prob,
        draw_prob,
        away_prob
    )

    dominant = max(normalized, key=normalized.get)

    return {
        "home_win": normalized["home"],
        "draw": normalized["draw"],
        "away_win": normalized["away"],
        "dominant_outcome": dominant,
        "generated_minute": minute
    }