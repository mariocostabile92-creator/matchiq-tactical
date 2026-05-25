"""
alert_engine.py

MatchIQ Tactical - Live Tactical Alert System

Genera alert live intelligenti usando:
- Event Engine
- Tactical Engine
- Goal Probability
- Pressure
- Danger
- Transition Risk
- Fatigue
- Momentum
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


def build_alert(alert_type, level, title, message, team=None, value=None):
    return {
        "type": alert_type,
        "level": level,
        "title": title,
        "message": message,
        "team": team,
        "value": value
    }


def get_priority(level):
    priorities = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    return priorities.get(level, 0)


def generate_team_alerts(team_data: dict):
    alerts = []

    team = team_data.get("team", "Team")

    pressure = safe_number(team_data.get("pressure_score"))
    danger = safe_number(team_data.get("danger_index"))
    transition = safe_number(team_data.get("transition_risk"))
    aggression = safe_number(team_data.get("aggression_score"))
    fatigue = safe_number(team_data.get("fatigue_signal"))
    goal_probability = safe_number(team_data.get("goal_probability"))

    if pressure >= 85:
        alerts.append(build_alert(
            "PRESSURE",
            "CRITICAL",
            "Pressione altissima",
            f"{team} sta schiacciando l'avversario con pressione offensiva molto alta.",
            team,
            pressure
        ))

    elif pressure >= 70:
        alerts.append(build_alert(
            "PRESSURE",
            "HIGH",
            "Pressione offensiva elevata",
            f"{team} sta aumentando il volume offensivo.",
            team,
            pressure
        ))

    if danger >= 85:
        alerts.append(build_alert(
            "DANGER",
            "CRITICAL",
            "Pericolo goal imminente",
            f"{team} sta producendo occasioni molto pericolose.",
            team,
            danger
        ))

    elif danger >= 70:
        alerts.append(build_alert(
            "DANGER",
            "HIGH",
            "Danger zone attiva",
            f"{team} è entrata in una fase offensiva pericolosa.",
            team,
            danger
        ))

    if goal_probability >= 80:
        alerts.append(build_alert(
            "GOAL_PROBABILITY",
            "CRITICAL",
            "Goal probability rising",
            f"La probabilità di goal per {team} è molto alta in questa fase.",
            team,
            goal_probability
        ))

    elif goal_probability >= 65:
        alerts.append(build_alert(
            "GOAL_PROBABILITY",
            "HIGH",
            "Possibile fase da goal",
            f"{team} sta entrando in una fase favorevole al goal.",
            team,
            goal_probability
        ))

    if transition >= 80:
        alerts.append(build_alert(
            "TRANSITION_RISK",
            "CRITICAL",
            "Transizioni difensive vulnerabili",
            f"{team} è molto esposta dopo perdita palla.",
            team,
            transition
        ))

    elif transition >= 65:
        alerts.append(build_alert(
            "TRANSITION_RISK",
            "HIGH",
            "Rischio transizione",
            f"{team} mostra vulnerabilità nelle transizioni difensive.",
            team,
            transition
        ))

    if fatigue >= 80:
        alerts.append(build_alert(
            "FATIGUE",
            "HIGH",
            "Calo fisico evidente",
            f"{team} mostra segnali di stanchezza e perdita di lucidità.",
            team,
            fatigue
        ))

    elif fatigue >= 65:
        alerts.append(build_alert(
            "FATIGUE",
            "MEDIUM",
            "Possibile calo intensità",
            f"{team} potrebbe iniziare a perdere intensità.",
            team,
            fatigue
        ))

    if aggression >= 85:
        alerts.append(build_alert(
            "AGGRESSION",
            "HIGH",
            "Rischio disciplinare",
            f"{team} sta giocando con aggressività elevata e rischio cartellini.",
            team,
            aggression
        ))

    elif aggression >= 70:
        alerts.append(build_alert(
            "AGGRESSION",
            "MEDIUM",
            "Aggressività alta",
            f"{team} sta aumentando il livello fisico del match.",
            team,
            aggression
        ))

    return alerts


def generate_momentum_alerts(event_analysis: dict):
    alerts = []

    momentum_team = event_analysis.get("momentum_team", "Equilibrio")
    match_personality = event_analysis.get("match_personality", "Match equilibrato")
    tempo_index = safe_number(event_analysis.get("tempo_index"))

    if momentum_team != "Equilibrio":
        alerts.append(build_alert(
            "MOMENTUM",
            "HIGH",
            "Momentum shift rilevato",
            f"{momentum_team} sta prendendo il controllo emotivo e tattico della partita.",
            momentum_team,
            None
        ))

    if tempo_index >= 80:
        alerts.append(build_alert(
            "TEMPO",
            "HIGH",
            "Ritmo partita molto alto",
            "Il match è in una fase molto intensa con continui ribaltamenti.",
            None,
            tempo_index
        ))

    elif tempo_index <= 25:
        alerts.append(build_alert(
            "TEMPO",
            "LOW",
            "Ritmo basso",
            "La partita è bloccata, con poche accelerazioni offensive.",
            None,
            tempo_index
        ))

    alerts.append(build_alert(
        "MATCH_PERSONALITY",
        "LOW",
        "Match personality",
        match_personality,
        None,
        tempo_index
    ))

    return alerts


def generate_live_alerts(event_analysis: dict):
    alerts = []

    home_data = event_analysis.get("home", {})
    away_data = event_analysis.get("away", {})

    alerts.extend(generate_team_alerts(home_data))
    alerts.extend(generate_team_alerts(away_data))
    alerts.extend(generate_momentum_alerts(event_analysis))

    alerts = sorted(
        alerts,
        key=lambda alert: get_priority(alert.get("level")),
        reverse=True
    )

    return {
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a.get("level") == "CRITICAL"]),
        "high_alerts": len([a for a in alerts if a.get("level") == "HIGH"]),
        "alerts": alerts[:12]
    }