"""
live_flow_engine.py
MatchIQ Tactical - Real Live Match Flow Engine
Versione 3.0

Genera:
- match status
- chaos index
- momentum swing
- fatigue progression
- goal shock
- pressure spike
- control level
"""

from datetime import datetime


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, int(value)))


def safe_get(data, *keys, default=0):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def calculate_goal_shock(match_data):
    score = match_data.get("score", {})
    home_goals = int(score.get("home", 0))
    away_goals = int(score.get("away", 0))

    diff = home_goals - away_goals

    if diff > 0:
        return {
            "leader": "HOME",
            "trailing": "AWAY",
            "shock_level": clamp(abs(diff) * 18),
            "message": "La squadra di casa ha un vantaggio psicologico."
        }

    if diff < 0:
        return {
            "leader": "AWAY",
            "trailing": "HOME",
            "shock_level": clamp(abs(diff) * 18),
            "message": "La squadra ospite ha un vantaggio psicologico."
        }

    return {
        "leader": "BALANCED",
        "trailing": "BALANCED",
        "shock_level": 0,
        "message": "Match in equilibrio psicologico."
    }


def calculate_fatigue(minute, pressure, danger):
    base = 18 + minute * 0.65
    intensity_bonus = (pressure * 0.18) + (danger * 0.22)

    if minute >= 70:
        base += 10

    if minute >= 82:
        base += 12

    return clamp(base + intensity_bonus)


def calculate_momentum_score(pressure, danger, xthreat, fatigue, goal_bonus=0):
    value = (
        pressure * 0.38 +
        danger * 0.34 +
        xthreat * 0.18 -
        fatigue * 0.10 +
        goal_bonus
    )

    return clamp(value)


def get_match_status(home_momentum, away_momentum, chaos_index):
    diff = abs(home_momentum - away_momentum)

    if chaos_index >= 80:
        return "CHAOTIC"

    if diff >= 30:
        return "DOMINATING"

    if home_momentum >= 75 or away_momentum >= 75:
        return "HIGH PRESSURE"

    if diff <= 10:
        return "BALANCED"

    return "TACTICAL"


def generate_live_flow(match_data, pressure_data, xg_data=None):
    xg_data = xg_data or {}

    minute = int(match_data.get("minute", 0))

    home_pressure = safe_get(pressure_data, "home", "pressure", default=0)
    away_pressure = safe_get(pressure_data, "away", "pressure", default=0)

    home_danger = safe_get(pressure_data, "home", "danger", default=0)
    away_danger = safe_get(pressure_data, "away", "danger", default=0)

    home_xthreat = float(xg_data.get("home_xthreat", 50))
    away_xthreat = float(xg_data.get("away_xthreat", 50))

    goal_shock = calculate_goal_shock(match_data)

    home_goal_bonus = 0
    away_goal_bonus = 0

    if goal_shock["leader"] == "HOME":
        home_goal_bonus = goal_shock["shock_level"] * 0.35
        away_goal_bonus = -goal_shock["shock_level"] * 0.18

    if goal_shock["leader"] == "AWAY":
        away_goal_bonus = goal_shock["shock_level"] * 0.35
        home_goal_bonus = -goal_shock["shock_level"] * 0.18

    home_fatigue = calculate_fatigue(
        minute,
        home_pressure,
        home_danger
    )

    away_fatigue = calculate_fatigue(
        minute,
        away_pressure,
        away_danger
    )

    home_momentum = calculate_momentum_score(
        home_pressure,
        home_danger,
        home_xthreat,
        home_fatigue,
        home_goal_bonus
    )

    away_momentum = calculate_momentum_score(
        away_pressure,
        away_danger,
        away_xthreat,
        away_fatigue,
        away_goal_bonus
    )

    chaos_index = clamp(
        abs(home_danger - away_danger) * 0.25 +
        max(home_pressure, away_pressure) * 0.35 +
        max(home_xthreat, away_xthreat) * 0.25 +
        minute * 0.15
    )

    if home_momentum > away_momentum + 12:
        momentum_shift = "HOME"
    elif away_momentum > home_momentum + 12:
        momentum_shift = "AWAY"
    else:
        momentum_shift = "BALANCED"

    pressure_spike = max(home_pressure, away_pressure) >= 85
    danger_spike = max(home_danger, away_danger) >= 85

    match_status = get_match_status(
        home_momentum,
        away_momentum,
        chaos_index
    )

    control_level = clamp(
        100 - chaos_index + abs(home_momentum - away_momentum) * 0.4
    )

    if control_level >= 70:
        control_label = "CONTROLLED"
    elif control_level >= 45:
        control_label = "OPEN"
    else:
        control_label = "UNSTABLE"

    if chaos_index >= 75:
        story = "La partita è entrata in una fase caotica con transizioni rapide."
    elif momentum_shift == "HOME":
        story = "La squadra di casa sta prendendo il controllo del flusso partita."
    elif momentum_shift == "AWAY":
        story = "La squadra ospite sta spostando l'inerzia dalla propria parte."
    else:
        story = "Il match resta equilibrato ma con segnali tattici in evoluzione."

    return {
        "generated_at": str(datetime.now()),
        "minute": minute,
        "match_status": match_status,
        "control_label": control_label,
        "control_level": control_level,
        "chaos_index": chaos_index,
        "momentum_shift": momentum_shift,
        "pressure_spike": pressure_spike,
        "danger_spike": danger_spike,
        "goal_shock": goal_shock,
        "home": {
            "momentum": home_momentum,
            "fatigue": home_fatigue,
            "flow": "AGGRESSIVE" if home_momentum >= 70 else "STABLE"
        },
        "away": {
            "momentum": away_momentum,
            "fatigue": away_fatigue,
            "flow": "AGGRESSIVE" if away_momentum >= 70 else "STABLE"
        },
        "story": story
    }