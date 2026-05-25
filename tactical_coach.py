"""
tactical_coach.py
MatchIQ Tactical Coach AI
"""

import random


def generate_tactical_coach(match_data, pressure_data):
    home = match_data.get("home_team", "Home")
    away = match_data.get("away_team", "Away")

    minute = match_data.get("minute", 0)

    home_pressure = pressure_data.get("home", {}).get("pressure", 0)
    away_pressure = pressure_data.get("away", {}).get("pressure", 0)

    home_danger = pressure_data.get("home", {}).get("danger", 0)
    away_danger = pressure_data.get("away", {}).get("danger", 0)

    home_transition = pressure_data.get("home", {}).get("transition_risk", 0)
    away_transition = pressure_data.get("away", {}).get("transition_risk", 0)

    home_fatigue = pressure_data.get("home", {}).get("fatigue", 0)
    away_fatigue = pressure_data.get("away", {}).get("fatigue", 0)

    tactical_advice = []

    # PRESSING
    if home_pressure > 80:
        tactical_advice.append({
            "team": home,
            "type": "PRESSING",
            "priority": "HIGH",
            "message": "Pressing offensivo molto efficace."
        })

    if away_pressure > 80:
        tactical_advice.append({
            "team": away,
            "type": "PRESSING",
            "priority": "HIGH",
            "message": "La squadra ospite sta dominando il ritmo."
        })

    # TRANSIZIONI
    if home_transition > 70:
        tactical_advice.append({
            "team": home,
            "type": "TRANSITION",
            "priority": "HIGH",
            "message": "Rischio elevato nelle transizioni difensive."
        })

    if away_transition > 70:
        tactical_advice.append({
            "team": away,
            "type": "TRANSITION",
            "priority": "HIGH",
            "message": "La linea difensiva soffre le ripartenze."
        })

    # FATIGUE
    if home_fatigue > 75:
        tactical_advice.append({
            "team": home,
            "type": "FATIGUE",
            "priority": "MEDIUM",
            "message": "Intensità fisica in calo."
        })

    if away_fatigue > 75:
        tactical_advice.append({
            "team": away,
            "type": "FATIGUE",
            "priority": "MEDIUM",
            "message": "Possibile calo atletico nei minuti finali."
        })

    # DANGER
    if home_danger > 85:
        tactical_advice.append({
            "team": home,
            "type": "ATTACK",
            "priority": "HIGH",
            "message": "Momento ideale per aumentare il pressing offensivo."
        })

    if away_danger > 85:
        tactical_advice.append({
            "team": away,
            "type": "ATTACK",
            "priority": "HIGH",
            "message": "La squadra sta creando occasioni ad alta qualità."
        })

    # EQUILIBRIO
    diff = abs(home_pressure - away_pressure)

    if diff < 10:
        tactical_advice.append({
            "team": "MATCH",
            "type": "BALANCED",
            "priority": "LOW",
            "message": "Partita tatticamente equilibrata."
        })

    # FASE FINALE
    if minute > 75:
        tactical_advice.append({
            "team": "MATCH",
            "type": "FINAL_PHASE",
            "priority": "HIGH",
            "message": "Gli episodi potranno decidere il risultato."
        })

    # FALLBACK
    if not tactical_advice:
        tactical_advice.append({
            "team": "MATCH",
            "type": "CONTROL",
            "priority": "LOW",
            "message": "Partita sotto controllo tattico."
        })

    return {
        "coach_score": random.randint(75, 99),
        "tactical_advice": tactical_advice
    }