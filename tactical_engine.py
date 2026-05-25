def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def calculate_team_momentum(stats: dict):
    momentum = (
        safe_int(stats.get("shots")) * 2
        + safe_int(stats.get("shots_on_target")) * 5
        + safe_int(stats.get("dangerous_attacks")) * 0.7
        + safe_float(stats.get("xg")) * 12
        + safe_int(stats.get("corners")) * 2
    )

    return round(momentum, 2)


def calculate_pressure_score(stats: dict):
    pressure = (
        safe_int(stats.get("shots_on_target")) * 10
        + safe_int(stats.get("shots")) * 5
        + safe_int(stats.get("corners")) * 4
        + safe_int(stats.get("dangerous_attacks")) * 1.2
        + safe_float(stats.get("possession")) * 0.4
    )

    return round(clamp(pressure), 1)


def calculate_danger_score(stats: dict):
    danger = (
        safe_float(stats.get("xg")) * 35
        + safe_int(stats.get("shots_on_target")) * 8
        + safe_int(stats.get("shots")) * 3
        + safe_int(stats.get("corners")) * 3
    )

    return round(clamp(danger), 1)


def calculate_transition_risk(stats: dict):
    lost_balls = safe_int(stats.get("lost_balls"))
    fouls = safe_int(stats.get("fouls"))
    yellow_cards = safe_int(stats.get("yellow_cards"))
    possession = safe_float(stats.get("possession"))

    risk = (
        lost_balls * 3
        + fouls * 2
        + yellow_cards * 6
        + max(50 - possession, 0) * 0.5
    )

    return round(clamp(risk), 1)


def calculate_fatigue_risk(stats: dict):
    fouls = safe_int(stats.get("fouls"))
    yellow_cards = safe_int(stats.get("yellow_cards"))
    possession = safe_float(stats.get("possession"))

    fatigue = (
        fouls * 3
        + yellow_cards * 5
        + max(50 - possession, 0) * 0.7
    )

    return round(clamp(fatigue), 1)


def calculate_match_tempo(home_stats: dict, away_stats: dict):
    total_shots = safe_int(home_stats.get("shots")) + safe_int(away_stats.get("shots"))
    total_danger = safe_int(home_stats.get("dangerous_attacks")) + safe_int(away_stats.get("dangerous_attacks"))
    total_fouls = safe_int(home_stats.get("fouls")) + safe_int(away_stats.get("fouls"))

    tempo_value = total_shots * 4 + total_danger * 1.5 - total_fouls
    tempo_value = round(clamp(tempo_value), 1)

    if tempo_value >= 70:
        label = "ALTO"
    elif tempo_value >= 40:
        label = "MEDIO"
    else:
        label = "BASSO"

    return {
        "value": tempo_value,
        "label": label
    }


def get_dominant_team(home_score, away_score, home_name, away_name):
    if home_score > away_score:
        return home_name

    if away_score > home_score:
        return away_name

    return "Equilibrio"


def generate_tactical_insights(
    home_name,
    away_name,
    home_stats,
    away_stats,
    home_pressure,
    away_pressure,
    home_danger,
    away_danger,
    home_transition,
    away_transition,
    tempo
):
    insights = []

    if home_pressure > away_pressure + 20:
        insights.append(f"{home_name} sta esercitando una pressione offensiva superiore.")

    if away_pressure > home_pressure + 20:
        insights.append(f"{away_name} sta imponendo maggiore pressione offensiva.")

    if home_danger > away_danger + 20:
        insights.append(f"{home_name} sta creando occasioni più pericolose negli ultimi metri.")

    if away_danger > home_danger + 20:
        insights.append(f"{away_name} appare più pericolosa in zona offensiva.")

    if home_transition >= 65:
        insights.append(f"{home_name} mostra vulnerabilità nelle transizioni difensive.")

    if away_transition >= 65:
        insights.append(f"{away_name} soffre le transizioni dopo perdita palla.")

    if safe_float(home_stats.get("possession")) >= 60:
        insights.append(f"{home_name} controlla il possesso e gestisce il ritmo della gara.")

    if safe_float(away_stats.get("possession")) >= 60:
        insights.append(f"{away_name} controlla maggiormente il possesso palla.")

    if safe_int(home_stats.get("corners")) >= 5:
        insights.append(f"{home_name} sta creando pressione laterale e situazioni da palla inattiva.")

    if safe_int(away_stats.get("corners")) >= 5:
        insights.append(f"{away_name} spinge molto sulle corsie laterali.")

    if tempo["label"] == "ALTO":
        insights.append("Il ritmo partita è alto, con continui ribaltamenti di fronte.")

    if tempo["label"] == "BASSO":
        insights.append("La partita ha un ritmo basso e poche accelerazioni offensive.")

    if not insights:
        insights.append("La partita è tatticamente equilibrata: nessuna squadra sta creando un vantaggio netto nei dati disponibili.")

    return insights


def analyze_match_tactical(match_data: dict):
    home = match_data.get("home", "Home")
    away = match_data.get("away", "Away")

    home_stats = match_data.get("team_stats", {}).get("home", {})
    away_stats = match_data.get("team_stats", {}).get("away", {})

    home_momentum = calculate_team_momentum(home_stats)
    away_momentum = calculate_team_momentum(away_stats)

    home_pressure = calculate_pressure_score(home_stats)
    away_pressure = calculate_pressure_score(away_stats)

    home_danger = calculate_danger_score(home_stats)
    away_danger = calculate_danger_score(away_stats)

    home_transition = calculate_transition_risk(home_stats)
    away_transition = calculate_transition_risk(away_stats)

    home_fatigue = calculate_fatigue_risk(home_stats)
    away_fatigue = calculate_fatigue_risk(away_stats)

    tempo = calculate_match_tempo(home_stats, away_stats)

    dominant_team = get_dominant_team(
        home_momentum,
        away_momentum,
        home,
        away
    )

    tactical_insights = generate_tactical_insights(
        home,
        away,
        home_stats,
        away_stats,
        home_pressure,
        away_pressure,
        home_danger,
        away_danger,
        home_transition,
        away_transition,
        tempo
    )

    total_momentum = home_momentum + away_momentum

    if total_momentum > 0:
        home_win_momentum = round((home_momentum / total_momentum) * 100, 1)
        away_win_momentum = round((away_momentum / total_momentum) * 100, 1)
    else:
        home_win_momentum = 50
        away_win_momentum = 50

    if abs(home_danger - away_danger) >= 30:
        match_risk_level = "ALTO"
    elif abs(home_danger - away_danger) >= 15:
        match_risk_level = "MEDIO"
    else:
        match_risk_level = "BASSO"

    return {
        "match": f"{home} vs {away}",
        "minute": match_data.get("minute"),

        "dominant_team": dominant_team,

        "home_momentum": home_momentum,
        "away_momentum": away_momentum,

        "home_pressure": home_pressure,
        "away_pressure": away_pressure,

        "home_danger_score": home_danger,
        "away_danger_score": away_danger,

        "home_transition_risk": home_transition,
        "away_transition_risk": away_transition,

        "home_fatigue_risk": home_fatigue,
        "away_fatigue_risk": away_fatigue,

        "home_win_momentum": home_win_momentum,
        "away_win_momentum": away_win_momentum,

        "match_tempo": tempo,
        "match_risk_level": match_risk_level,

        "tactical_insights": tactical_insights
    }