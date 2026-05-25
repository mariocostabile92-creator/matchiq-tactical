"""
event_engine.py

MatchIQ Tactical - Event Engine
Trasforma statistiche live grezze in segnali tattici intelligenti.

Obiettivo:
- pressione offensiva
- rischio goal
- momentum live
- ritmo partita
- vulnerabilità difensive
- alert tattici
- match personality
"""


def safe_number(value, default=0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace("%", "").strip()

        return float(value)

    except Exception:
        return default


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def get_level(value):
    value = safe_number(value)

    if value >= 75:
        return "ALTO"

    if value >= 50:
        return "MEDIO"

    return "BASSO"


def calculate_pressure_score(stats: dict):
    shots = safe_number(stats.get("shots"))
    shots_on_target = safe_number(stats.get("shots_on_target"))
    corners = safe_number(stats.get("corners"))
    dangerous_attacks = safe_number(stats.get("dangerous_attacks"))
    possession = safe_number(stats.get("possession"))

    score = (
        shots * 4
        + shots_on_target * 9
        + corners * 5
        + dangerous_attacks * 1.4
        + possession * 0.25
    )

    return round(clamp(score), 1)


def calculate_danger_index(stats: dict):
    shots = safe_number(stats.get("shots"))
    shots_on_target = safe_number(stats.get("shots_on_target"))
    xg = safe_number(stats.get("xg"))
    corners = safe_number(stats.get("corners"))

    score = (
        xg * 38
        + shots_on_target * 11
        + shots * 3
        + corners * 4
    )

    return round(clamp(score), 1)


def calculate_transition_risk(stats: dict):
    lost_balls = safe_number(stats.get("lost_balls"))
    fouls = safe_number(stats.get("fouls"))
    yellow_cards = safe_number(stats.get("yellow_cards"))
    possession = safe_number(stats.get("possession"))

    score = (
        lost_balls * 3.5
        + fouls * 2.5
        + yellow_cards * 7
        + max(50 - possession, 0) * 0.6
    )

    return round(clamp(score), 1)


def calculate_aggression_score(stats: dict):
    fouls = safe_number(stats.get("fouls"))
    yellow_cards = safe_number(stats.get("yellow_cards"))
    red_cards = safe_number(stats.get("red_cards"))
    corners = safe_number(stats.get("corners"))
    shots = safe_number(stats.get("shots"))

    score = (
        fouls * 3
        + yellow_cards * 10
        + red_cards * 25
        + corners * 3
        + shots * 2
    )

    return round(clamp(score), 1)


def calculate_fatigue_signal(stats: dict, minute: int):
    fouls = safe_number(stats.get("fouls"))
    lost_balls = safe_number(stats.get("lost_balls"))
    possession = safe_number(stats.get("possession"))

    minute_factor = safe_number(minute) * 0.35

    score = (
        minute_factor
        + fouls * 2
        + lost_balls * 2.2
        + max(45 - possession, 0) * 0.7
    )

    return round(clamp(score), 1)


def calculate_goal_probability(danger, pressure, tempo, minute):
    danger = safe_number(danger)
    pressure = safe_number(pressure)
    tempo = safe_number(tempo)
    minute = safe_number(minute)

    score = (
        danger * 0.45
        + pressure * 0.30
        + tempo * 0.15
        + min(minute, 90) * 0.10
    )

    return round(clamp(score), 1)


def calculate_tempo_index(home_stats: dict, away_stats: dict):
    total_shots = safe_number(home_stats.get("shots")) + safe_number(away_stats.get("shots"))
    total_corners = safe_number(home_stats.get("corners")) + safe_number(away_stats.get("corners"))
    total_dangerous = safe_number(home_stats.get("dangerous_attacks")) + safe_number(away_stats.get("dangerous_attacks"))
    total_fouls = safe_number(home_stats.get("fouls")) + safe_number(away_stats.get("fouls"))

    score = (
        total_shots * 4
        + total_corners * 3
        + total_dangerous * 1.2
        - total_fouls * 0.8
    )

    return round(clamp(score), 1)


def detect_match_personality(tempo, total_danger, total_aggression):
    tempo = safe_number(tempo)
    total_danger = safe_number(total_danger)
    total_aggression = safe_number(total_aggression)

    if tempo >= 75 and total_danger >= 70:
        return "Match aperto e ad alta intensità"

    if total_aggression >= 75:
        return "Match aggressivo e fisico"

    if total_danger >= 75:
        return "Match con alto potenziale offensivo"

    if tempo <= 35 and total_danger <= 35:
        return "Partita bloccata e tattica"

    if tempo >= 55:
        return "Match dinamico con buon ritmo"

    return "Match equilibrato"


def generate_alerts(
    team_name,
    pressure,
    danger,
    transition,
    aggression,
    fatigue,
    goal_probability
):
    alerts = []

    if pressure >= 75:
        alerts.append({
            "type": "PRESSURE",
            "level": "HIGH",
            "message": f"{team_name} sta aumentando fortemente la pressione offensiva."
        })

    if danger >= 70:
        alerts.append({
            "type": "DANGER",
            "level": "HIGH",
            "message": f"{team_name} sta creando occasioni pericolose con continuità."
        })

    if transition >= 70:
        alerts.append({
            "type": "TRANSITION_RISK",
            "level": "HIGH",
            "message": f"{team_name} è vulnerabile nelle transizioni difensive."
        })

    if aggression >= 75:
        alerts.append({
            "type": "AGGRESSION",
            "level": "MEDIUM",
            "message": f"{team_name} mostra un livello alto di aggressività e rischio disciplinare."
        })

    if fatigue >= 75:
        alerts.append({
            "type": "FATIGUE",
            "level": "MEDIUM",
            "message": f"{team_name} mostra segnali di calo fisico e perdita di lucidità."
        })

    if goal_probability >= 72:
        alerts.append({
            "type": "GOAL_PROBABILITY",
            "level": "HIGH",
            "message": f"Possibile fase favorevole al goal per {team_name}."
        })

    return alerts


def generate_tactical_events(match_data: dict):
    home = match_data.get("home", "Home")
    away = match_data.get("away", "Away")
    minute = match_data.get("minute") or 0

    team_stats = match_data.get("team_stats", {})
    home_stats = team_stats.get("home", {})
    away_stats = team_stats.get("away", {})

    tempo = calculate_tempo_index(home_stats, away_stats)

    home_pressure = calculate_pressure_score(home_stats)
    away_pressure = calculate_pressure_score(away_stats)

    home_danger = calculate_danger_index(home_stats)
    away_danger = calculate_danger_index(away_stats)

    home_transition = calculate_transition_risk(home_stats)
    away_transition = calculate_transition_risk(away_stats)

    home_aggression = calculate_aggression_score(home_stats)
    away_aggression = calculate_aggression_score(away_stats)

    home_fatigue = calculate_fatigue_signal(home_stats, minute)
    away_fatigue = calculate_fatigue_signal(away_stats, minute)

    home_goal_probability = calculate_goal_probability(
        home_danger,
        home_pressure,
        tempo,
        minute
    )

    away_goal_probability = calculate_goal_probability(
        away_danger,
        away_pressure,
        tempo,
        minute
    )

    total_danger = (home_danger + away_danger) / 2
    total_aggression = (home_aggression + away_aggression) / 2

    match_personality = detect_match_personality(
        tempo,
        total_danger,
        total_aggression
    )

    home_alerts = generate_alerts(
        home,
        home_pressure,
        home_danger,
        home_transition,
        home_aggression,
        home_fatigue,
        home_goal_probability
    )

    away_alerts = generate_alerts(
        away,
        away_pressure,
        away_danger,
        away_transition,
        away_aggression,
        away_fatigue,
        away_goal_probability
    )

    all_alerts = home_alerts + away_alerts

    if home_pressure > away_pressure + 20:
        momentum_team = home
    elif away_pressure > home_pressure + 20:
        momentum_team = away
    else:
        momentum_team = "Equilibrio"

    return {
        "match": f"{home} vs {away}",
        "minute": minute,

        "tempo_index": tempo,
        "tempo_level": get_level(tempo),

        "match_personality": match_personality,
        "momentum_team": momentum_team,

        "home": {
            "team": home,
            "pressure_score": home_pressure,
            "pressure_level": get_level(home_pressure),
            "danger_index": home_danger,
            "danger_level": get_level(home_danger),
            "transition_risk": home_transition,
            "transition_level": get_level(home_transition),
            "aggression_score": home_aggression,
            "aggression_level": get_level(home_aggression),
            "fatigue_signal": home_fatigue,
            "fatigue_level": get_level(home_fatigue),
            "goal_probability": home_goal_probability,
            "goal_probability_level": get_level(home_goal_probability),
            "alerts": home_alerts
        },

        "away": {
            "team": away,
            "pressure_score": away_pressure,
            "pressure_level": get_level(away_pressure),
            "danger_index": away_danger,
            "danger_level": get_level(away_danger),
            "transition_risk": away_transition,
            "transition_level": get_level(away_transition),
            "aggression_score": away_aggression,
            "aggression_level": get_level(away_aggression),
            "fatigue_signal": away_fatigue,
            "fatigue_level": get_level(away_fatigue),
            "goal_probability": away_goal_probability,
            "goal_probability_level": get_level(away_goal_probability),
            "alerts": away_alerts
        },

        "alerts": all_alerts
    }