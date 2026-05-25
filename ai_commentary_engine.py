"""
ai_commentary_engine.py
MatchIQ Tactical - LIVE AI COMMENTARY ENGINE
"""

from datetime import datetime
import random


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def build_commentary(
    pressure_home,
    pressure_away,
    danger_home,
    danger_away,
    momentum_home,
    momentum_away,
    minute
):

    commentary = []

    # =====================================================
    # DOMINANCE
    # =====================================================

    if pressure_home >= 78 and pressure_home > pressure_away + 10:
        commentary.append(
            "🔥 Pressione offensiva molto alta della squadra di casa."
        )

    if pressure_away >= 78 and pressure_away > pressure_home + 10:
        commentary.append(
            "🔥 La squadra ospite sta dominando il ritmo del match."
        )

    # =====================================================
    # DANGER
    # =====================================================

    if danger_home >= 80:
        commentary.append(
            "⚠️ Situazione estremamente pericolosa nell'area ospite."
        )

    if danger_away >= 80:
        commentary.append(
            "⚠️ La difesa di casa è sotto forte pressione."
        )

    # =====================================================
    # MOMENTUM
    # =====================================================

    if momentum_home >= 75:
        commentary.append(
            "📈 Momentum in forte crescita per la squadra di casa."
        )

    if momentum_away >= 75:
        commentary.append(
            "📈 La squadra ospite sta aumentando intensità e fiducia."
        )

    # =====================================================
    # MATCH TEMPERATURE
    # =====================================================

    total_temperature = (
        pressure_home
        + pressure_away
        + danger_home
        + danger_away
    ) / 4

    if total_temperature >= 82:
        commentary.append(
            "🔥 Il match è entrato in una fase ad altissima intensità."
        )

    # =====================================================
    # END GAME
    # =====================================================

    if minute >= 75:
        commentary.append(
            "⏳ Ultima fase del match: ogni episodio può cambiare tutto."
        )

    # =====================================================
    # RANDOM VARIATION
    # =====================================================

    random_lines = [
        "🧠 MatchIQ AI rileva cambiamenti tattici interessanti.",
        "⚡ Ritmo partita in continuo aumento.",
        "🎯 Le squadre stanno cercando spazi tra le linee.",
        "🛡️ Le difese stanno iniziando a concedere qualcosa.",
        "🚨 Possibile momento decisivo nei prossimi minuti."
    ]

    if len(commentary) < 3:
        commentary.append(random.choice(random_lines))

    return commentary


def generate_ai_commentary(
    match_data,
    pressure_data,
    live_flow
):

    home_pressure = (
        pressure_data.get("home", {})
        .get("pressure", 50)
    )

    away_pressure = (
        pressure_data.get("away", {})
        .get("pressure", 50)
    )

    home_danger = (
        pressure_data.get("home", {})
        .get("danger", 50)
    )

    away_danger = (
        pressure_data.get("away", {})
        .get("danger", 50)
    )

    home_momentum = (
        live_flow.get("home", {})
        .get("momentum", 50)
    )

    away_momentum = (
        live_flow.get("away", {})
        .get("momentum", 50)
    )

    minute = match_data.get("minute", 0)

    commentary = build_commentary(
        pressure_home=home_pressure,
        pressure_away=away_pressure,
        danger_home=home_danger,
        danger_away=away_danger,
        momentum_home=home_momentum,
        momentum_away=away_momentum,
        minute=minute
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "minute": minute,
        "commentary": commentary
    }