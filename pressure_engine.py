"""
pressure_engine.py
MatchIQ Tactical - Pressure Engine V1

Genera:
- pressure zones
- heatmap values
- attack flow
- goal probability
- fatigue impact
- transition risk
- dominance score

Tutto usando dati già disponibili da match_data/team_stats,
senza aumentare il consumo API.
"""

from datetime import datetime


def clamp(value, minimum=0, maximum=100):
    try:
        value = float(value)
    except Exception:
        value = 0

    return max(minimum, min(maximum, value))


def get_stats(match_data, side):
    return match_data.get("team_stats", {}).get(side, {}) or {}


def calc_pressure(stats):
    possession = clamp(stats.get("possession", 0))
    shots = clamp(stats.get("shots", 0), 0, 30)
    shots_on_target = clamp(stats.get("shots_on_target", 0), 0, 20)
    corners = clamp(stats.get("corners", 0), 0, 20)

    score = (
        possession * 0.32
        + shots * 3.2
        + shots_on_target * 7.5
        + corners * 4.5
    )

    return round(clamp(score), 1)


def calc_danger(stats):
    shots = clamp(stats.get("shots", 0), 0, 30)
    shots_on_target = clamp(stats.get("shots_on_target", 0), 0, 20)
    dangerous_attacks = clamp(stats.get("dangerous_attacks", 0), 0, 100)
    xg = clamp(stats.get("xg", 0), 0, 5)
    corners = clamp(stats.get("corners", 0), 0, 20)

    score = (
        dangerous_attacks * 0.35
        + shots * 2.8
        + shots_on_target * 8.5
        + corners * 3.8
        + xg * 16
    )

    return round(clamp(score), 1)


def calc_transition_risk(stats):
    lost_balls = clamp(stats.get("lost_balls", 0), 0, 40)
    fouls = clamp(stats.get("fouls", 0), 0, 30)
    offsides = clamp(stats.get("offsides", 0), 0, 10)

    score = lost_balls * 2.5 + fouls * 1.8 + offsides * 2.2

    return round(clamp(score), 1)


def calc_fatigue(minute, pressure):
    minute = clamp(minute, 0, 120)

    score = minute * 0.55 + pressure * 0.22

    return round(clamp(score), 1)


def calc_goal_probability(pressure, danger, opponent_transition_risk, fatigue):
    score = (
        pressure * 0.26
        + danger * 0.42
        + opponent_transition_risk * 0.20
        + fatigue * 0.12
    )

    return round(clamp(score), 1)


def detect_attack_flow(pressure, danger):
    intensity = pressure * 0.45 + danger * 0.55

    if intensity >= 75:
        return "HIGH_ATTACK_WAVE"

    if intensity >= 55:
        return "ACTIVE_PRESSURE"

    if intensity >= 35:
        return "CONTROLLED_POSSESSION"

    return "LOW_THREAT"


def build_heatmap_zones(pressure, danger, side):
    """
    6 zone:
    - left flank
    - central attack
    - right flank
    - half-space left
    - box pressure
    - transition zone
    """

    base = pressure * 0.45 + danger * 0.55

    if side == "home":
        return {
            "left_flank": round(clamp(base * 0.72), 1),
            "central_attack": round(clamp(base * 0.88), 1),
            "right_flank": round(clamp(base * 0.76), 1),
            "half_space": round(clamp(base * 0.82), 1),
            "box_pressure": round(clamp(base * 1.05), 1),
            "transition_zone": round(clamp(pressure * 0.65), 1)
        }

    return {
        "left_flank": round(clamp(base * 0.75), 1),
        "central_attack": round(clamp(base * 0.90), 1),
        "right_flank": round(clamp(base * 0.70), 1),
        "half_space": round(clamp(base * 0.80), 1),
        "box_pressure": round(clamp(base * 1.02), 1),
        "transition_zone": round(clamp(pressure * 0.62), 1)
    }


def dominance_label(score):
    if score >= 70:
        return "Dominanza forte"

    if score >= 55:
        return "Dominanza moderata"

    if score >= 45:
        return "Equilibrio dinamico"

    return "Fase difensiva"


def pressure_alerts(home_name, away_name, home, away):
    alerts = []

    if home["goal_probability"] >= 75:
        alerts.append({
            "level": "HIGH",
            "team": home_name,
            "title": "Goal probability alta",
            "message": f"{home_name} sta entrando in una fase offensiva molto pericolosa."
        })

    if away["goal_probability"] >= 75:
        alerts.append({
            "level": "HIGH",
            "team": away_name,
            "title": "Goal probability alta",
            "message": f"{away_name} sta entrando in una fase offensiva molto pericolosa."
        })

    if home["attack_flow"] == "HIGH_ATTACK_WAVE":
        alerts.append({
            "level": "MEDIUM",
            "team": home_name,
            "title": "Attack wave rilevata",
            "message": f"{home_name} sta generando una sequenza offensiva importante."
        })

    if away["attack_flow"] == "HIGH_ATTACK_WAVE":
        alerts.append({
            "level": "MEDIUM",
            "team": away_name,
            "title": "Attack wave rilevata",
            "message": f"{away_name} sta generando una sequenza offensiva importante."
        })

    return alerts


def analyze_pressure(match_data):
    home_stats = get_stats(match_data, "home")
    away_stats = get_stats(match_data, "away")

    minute = match_data.get("minute") or 0

    home_name = match_data.get("home", "Home")
    away_name = match_data.get("away", "Away")

    home_pressure = calc_pressure(home_stats)
    away_pressure = calc_pressure(away_stats)

    home_danger = calc_danger(home_stats)
    away_danger = calc_danger(away_stats)

    home_transition_risk = calc_transition_risk(home_stats)
    away_transition_risk = calc_transition_risk(away_stats)

    home_fatigue = calc_fatigue(minute, home_pressure)
    away_fatigue = calc_fatigue(minute, away_pressure)

    home_goal_probability = calc_goal_probability(
        home_pressure,
        home_danger,
        away_transition_risk,
        away_fatigue
    )

    away_goal_probability = calc_goal_probability(
        away_pressure,
        away_danger,
        home_transition_risk,
        home_fatigue
    )

    home = {
        "team": home_name,
        "pressure": home_pressure,
        "danger": home_danger,
        "transition_risk": home_transition_risk,
        "fatigue": home_fatigue,
        "goal_probability": home_goal_probability,
        "attack_flow": detect_attack_flow(home_pressure, home_danger),
        "heatmap_zones": build_heatmap_zones(home_pressure, home_danger, "home")
    }

    away = {
        "team": away_name,
        "pressure": away_pressure,
        "danger": away_danger,
        "transition_risk": away_transition_risk,
        "fatigue": away_fatigue,
        "goal_probability": away_goal_probability,
        "attack_flow": detect_attack_flow(away_pressure, away_danger),
        "heatmap_zones": build_heatmap_zones(away_pressure, away_danger, "away")
    }

    dominance_score = round(
        clamp(
            50
            + (home_pressure - away_pressure) * 0.25
            + (home_danger - away_danger) * 0.25
        ),
        1
    )

    if dominance_score > 55:
        dominant_team = home_name
    elif dominance_score < 45:
        dominant_team = away_name
    else:
        dominant_team = "Equilibrio"

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "minute": minute,
        "dominance_score": dominance_score,
        "dominance_label": dominance_label(dominance_score),
        "dominant_team": dominant_team,
        "home": home,
        "away": away,
        "alerts": pressure_alerts(home_name, away_name, home, away)
    }