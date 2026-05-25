"""
live_event_engine.py
MatchIQ Tactical PRO
AI Live Tactical Engine
"""

import random
from datetime import datetime


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def calculate_pressure(stats, is_home=True):
    dangerous = stats.get("dangerous_attacks", 0)
    shots = stats.get("shots_on_target", 0)
    possession = stats.get("possession", 50)
    corners = stats.get("corners", 0)

    pressure = (
        dangerous * 0.45 +
        shots * 6 +
        corners * 3 +
        possession * 0.35
    )

    if not is_home:
        pressure *= 0.97

    return clamp(round(pressure))


def calculate_danger(stats):
    dangerous = stats.get("dangerous_attacks", 0)
    shots = stats.get("shots_on_target", 0)
    attacks = stats.get("attacks", 0)

    score = (
        dangerous * 0.6 +
        shots * 9 +
        attacks * 0.15
    )

    return clamp(round(score))


def calculate_fatigue(minute):
    fatigue = 20 + (minute * 0.7)

    if minute > 70:
        fatigue += 12

    return clamp(round(fatigue))


def calculate_goal_probability(pressure, danger):
    value = (pressure * 0.55) + (danger * 0.45)
    probability = value / 10

    return round(clamp(probability, 0, 99), 1)


def get_dominance(home_pressure, away_pressure):
    diff = home_pressure - away_pressure

    if diff > 20:
        return "HOME", "Dominio Home"

    if diff < -20:
        return "AWAY", "Dominio Away"

    if abs(diff) <= 8:
        return "BALANCED", "Equilibrio dinamico"

    if diff > 0:
        return "HOME", "Leggera superiorità Home"

    return "AWAY", "Leggera superiorità Away"


def generate_alerts(
    home_pressure,
    away_pressure,
    home_danger,
    away_danger,
    minute
):
    alerts = []

    if home_pressure > 75:
        alerts.append({
            "level": "HIGH",
            "title": "Pressione estrema Home",
            "message": "La squadra di casa sta dominando il ritmo offensivo."
        })

    if away_pressure > 75:
        alerts.append({
            "level": "HIGH",
            "title": "Pressione estrema Away",
            "message": "La squadra ospite sta imponendo un forcing elevato."
        })

    if home_danger > 70:
        alerts.append({
            "level": "HIGH",
            "title": "Pericolo alto Home",
            "message": "Possibile gol imminente per la squadra di casa."
        })

    if away_danger > 70:
        alerts.append({
            "level": "HIGH",
            "title": "Pericolo alto Away",
            "message": "Possibile gol imminente per la squadra ospite."
        })

    if minute > 70:
        alerts.append({
            "level": "MEDIUM",
            "title": "Fase critica finale",
            "message": "La fatica sta influenzando le transizioni difensive."
        })

    if not alerts:
        alerts.append({
            "level": "LOW",
            "title": "Ritmo stabile",
            "message": "La partita è sotto controllo tattico."
        })

    return alerts


def generate_commentary(
    dominance_label,
    home_pressure,
    away_pressure,
    home_danger,
    away_danger
):
    commentary = []

    commentary.append(
        f"Scenario tattico attuale: {dominance_label}."
    )

    if home_pressure > away_pressure:
        commentary.append(
            "La squadra di casa controlla maggiormente il possesso territoriale."
        )

    if away_pressure > home_pressure:
        commentary.append(
            "La squadra ospite sta cercando di alzare il ritmo offensivo."
        )

    if home_danger > 70:
        commentary.append(
            "La squadra di casa sta creando occasioni ad alta pericolosità."
        )

    if away_danger > 70:
        commentary.append(
            "La squadra ospite è molto aggressiva negli ultimi metri."
        )

    commentary.append(
        "Le transizioni saranno decisive nei prossimi minuti."
    )

    return commentary


def generate_timeline(minute, dominance):
    return [
        {
            "minute": max(1, minute - 10),
            "icon": "⚡",
            "title": "Cambio ritmo",
            "message": "L'intensità della partita è aumentata."
        },
        {
            "minute": max(1, minute - 5),
            "icon": "🔥",
            "title": "Momentum",
            "message": f"Fase favorevole: {dominance}"
        },
        {
            "minute": minute,
            "icon": "🧠",
            "title": "AI Tactical Update",
            "message": "Le transizioni offensive stanno diventando decisive."
        }
    ]


def generate_live_engine(match):
    """
    Genera analisi tattica live completa.
    """

    minute = match.get("minute", 1)

    home_stats = {
        "dangerous_attacks": random.randint(20, 90),
        "attacks": random.randint(40, 120),
        "shots_on_target": random.randint(1, 10),
        "corners": random.randint(0, 9),
        "possession": random.randint(35, 65)
    }

    away_stats = {
        "dangerous_attacks": random.randint(20, 90),
        "attacks": random.randint(40, 120),
        "shots_on_target": random.randint(1, 10),
        "corners": random.randint(0, 9),
        "possession": 100 - home_stats["possession"]
    }

    home_pressure = calculate_pressure(home_stats, True)
    away_pressure = calculate_pressure(away_stats, False)

    home_danger = calculate_danger(home_stats)
    away_danger = calculate_danger(away_stats)

    home_goal_prob = calculate_goal_probability(
        home_pressure,
        home_danger
    )

    away_goal_prob = calculate_goal_probability(
        away_pressure,
        away_danger
    )

    dominant_team, dominance_label = get_dominance(
        home_pressure,
        away_pressure
    )

    alerts = generate_alerts(
        home_pressure,
        away_pressure,
        home_danger,
        away_danger,
        minute
    )

    commentary = generate_commentary(
        dominance_label,
        home_pressure,
        away_pressure,
        home_danger,
        away_danger
    )

    fatigue = calculate_fatigue(minute)

    return {
        "generated_at": str(datetime.now()),
        "minute": minute,

        "dominant_team": dominant_team,
        "dominance_label": dominance_label,

        "home": {
            "pressure": home_pressure,
            "danger": home_danger,
            "fatigue": fatigue,
            "goal_probability": home_goal_prob,
            "transition_risk": clamp(random.randint(20, 80))
        },

        "away": {
            "pressure": away_pressure,
            "danger": away_danger,
            "fatigue": fatigue,
            "goal_probability": away_goal_prob,
            "transition_risk": clamp(random.randint(20, 80))
        },

        "alerts": alerts,

        "commentary": commentary,

        "timeline": generate_timeline(
            minute,
            dominance_label
        ),

        "confidence_score": random.randint(70, 99)
    }