"""
matchiq_ai_core.py
MatchIQ Tactical AI Core Engine PRO
"""

from datetime import datetime


def clamp(value, minimum=0, maximum=100):
    try:
        value = float(value)
    except Exception:
        value = 0

    return max(minimum, min(maximum, value))


def safe(stats, key, default=0):
    try:
        return stats.get(key, default)
    except Exception:
        return default


def get_team_stats(match_data, side):
    return match_data.get("team_stats", {}).get(side, {}) or {}


# =========================================================
# PRESSURE ENGINE
# =========================================================

def calculate_pressure(stats):

    possession = safe(stats, "possession")
    shots = safe(stats, "shots")
    shots_on_target = safe(stats, "shots_on_target")
    corners = safe(stats, "corners")
    dangerous_attacks = safe(stats, "dangerous_attacks")

    score = (
        possession * 0.28
        + shots * 3
        + shots_on_target * 9
        + corners * 4
        + dangerous_attacks * 0.45
    )

    return round(clamp(score), 1)


# =========================================================
# DANGER ENGINE
# =========================================================

def calculate_danger(stats):

    shots = safe(stats, "shots")
    shots_on_target = safe(stats, "shots_on_target")
    corners = safe(stats, "corners")
    xg = safe(stats, "xg")
    dangerous_attacks = safe(stats, "dangerous_attacks")

    score = (
        dangerous_attacks * 0.40
        + shots * 2.5
        + shots_on_target * 11
        + corners * 3
        + xg * 24
    )

    return round(clamp(score), 1)


# =========================================================
# ATTACK WAVE ENGINE
# =========================================================

def detect_attack_wave(
        home_pressure,
        away_pressure,
        home_danger,
        away_danger
):

    home_wave = (
        home_pressure * 0.45 +
        home_danger * 0.55
    )

    away_wave = (
        away_pressure * 0.45 +
        away_danger * 0.55
    )

    if home_wave > away_wave + 15:
        return "HOME", round(home_wave, 1)

    if away_wave > home_wave + 15:
        return "AWAY", round(away_wave, 1)

    return "BALANCED", round(max(home_wave, away_wave), 1)


# =========================================================
# TRANSITION RISK
# =========================================================

def calculate_transition_risk(home_stats, away_stats):

    home_lost = safe(home_stats, "lost_balls")
    away_lost = safe(away_stats, "lost_balls")

    home_fouls = safe(home_stats, "fouls")
    away_fouls = safe(away_stats, "fouls")

    home_danger = safe(home_stats, "dangerous_attacks")
    away_danger = safe(away_stats, "dangerous_attacks")

    risk = (
        (home_lost + away_lost) * 2.4
        + (home_fouls + away_fouls) * 1.5
        + (home_danger + away_danger) * 0.20
    )

    return round(clamp(risk), 1)


# =========================================================
# FATIGUE ENGINE
# =========================================================

def estimate_fatigue(
        minute,
        home_pressure,
        away_pressure
):

    minute = minute or 0

    base = minute * 0.60
    intensity = (
        home_pressure +
        away_pressure
    ) * 0.20

    fatigue = base + intensity

    return round(clamp(fatigue), 1)


# =========================================================
# CHAOS ENGINE
# =========================================================

def calculate_chaos(
        home_pressure,
        away_pressure,
        home_danger,
        away_danger,
        transition_risk
):

    dominance_gap = abs(home_pressure - away_pressure)

    chaos = (
        max(home_pressure, away_pressure) * 0.25
        + max(home_danger, away_danger) * 0.35
        + dominance_gap * 0.15
        + transition_risk * 0.25
    )

    return round(clamp(chaos), 1)


# =========================================================
# MATCH TEMPO
# =========================================================

def calculate_tempo(intensity):

    if intensity >= 72:
        return "ALTO"

    if intensity >= 40:
        return "MEDIO"

    return "BASSO"


# =========================================================
# CONFIDENCE SCORE
# =========================================================

def calculate_confidence(
        match_data,
        home_pressure,
        away_pressure,
        home_danger,
        away_danger
):

    minute = match_data.get("minute") or 0
    players = match_data.get("players", []) or []

    data_score = 25

    if minute > 0:
        data_score += 20

    if home_pressure or away_pressure:
        data_score += 20

    if home_danger or away_danger:
        data_score += 20

    if len(players) >= 8:
        data_score += 15

    return round(clamp(data_score), 1)


# =========================================================
# COMMENTARY ENGINE
# =========================================================

def build_ai_commentary(
        match_data,
        wave_team,
        tempo,
        risk,
        fatigue,
        chaos,
        home_pressure,
        away_pressure
):

    commentary = []

    home = match_data.get("home", "Home")
    away = match_data.get("away", "Away")

    # -----------------------------------------------------

    if wave_team == "HOME":
        commentary.append(
            f"{home} sta controllando il ritmo territoriale del match."
        )

    elif wave_team == "AWAY":
        commentary.append(
            f"{away} sta aumentando pressione e iniziativa offensiva."
        )

    else:
        commentary.append(
            "La partita resta tatticamente equilibrata."
        )

    # -----------------------------------------------------

    if tempo == "ALTO":
        commentary.append(
            "Il ritmo è elevato con transizioni molto rapide."
        )

    elif tempo == "MEDIO":
        commentary.append(
            "Il ritmo è controllato ma con fasi di pressione alternate."
        )

    else:
        commentary.append(
            "La gara si sviluppa con un ritmo basso e più ragionato."
        )

    # -----------------------------------------------------

    if risk >= 70:
        commentary.append(
            "Il rischio transizione è molto alto: possibili ribaltamenti improvvisi."
        )

    elif risk >= 45:
        commentary.append(
            "Le transizioni stanno diventando un fattore importante."
        )

    # -----------------------------------------------------

    if fatigue >= 78:
        commentary.append(
            "La fatica sta incidendo sulla lucidità difensiva."
        )

    elif fatigue >= 60:
        commentary.append(
            "L'intensità accumulata potrebbe modificare il pressing nei prossimi minuti."
        )

    # -----------------------------------------------------

    if chaos >= 75:
        commentary.append(
            "La partita è entrata in una fase caotica ad alta instabilità."
        )

    elif chaos >= 55:
        commentary.append(
            "Il match sta aumentando il livello di imprevedibilità."
        )

    # -----------------------------------------------------

    pressure_gap = abs(home_pressure - away_pressure)

    if pressure_gap >= 28:

        dominant = (
            home if home_pressure > away_pressure
            else away
        )

        commentary.append(
            f"{dominant} sta imponendo una superiorità territoriale evidente."
        )

    return commentary[:6]


# =========================================================
# MAIN ENGINE
# =========================================================

def analyze_ai_core(match_data):

    home_stats = get_team_stats(match_data, "home")
    away_stats = get_team_stats(match_data, "away")

    minute = match_data.get("minute") or 0

    home_pressure = calculate_pressure(home_stats)
    away_pressure = calculate_pressure(away_stats)

    home_danger = calculate_danger(home_stats)
    away_danger = calculate_danger(away_stats)

    wave_team, wave_score = detect_attack_wave(
        home_pressure,
        away_pressure,
        home_danger,
        away_danger
    )

    if wave_team == "HOME":
        dominant_team = match_data.get("home")

    elif wave_team == "AWAY":
        dominant_team = match_data.get("away")

    else:
        dominant_team = "Equilibrio"

    combined_intensity = (
        home_pressure +
        away_pressure +
        home_danger +
        away_danger
    ) / 4

    tempo = calculate_tempo(combined_intensity)

    transition_risk = calculate_transition_risk(
        home_stats,
        away_stats
    )

    fatigue = estimate_fatigue(
        minute,
        home_pressure,
        away_pressure
    )

    chaos = calculate_chaos(
        home_pressure,
        away_pressure,
        home_danger,
        away_danger,
        transition_risk
    )

    confidence = calculate_confidence(
        match_data,
        home_pressure,
        away_pressure,
        home_danger,
        away_danger
    )

    commentary = build_ai_commentary(
        match_data,
        wave_team,
        tempo,
        transition_risk,
        fatigue,
        chaos,
        home_pressure,
        away_pressure
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),

        "home_pressure": home_pressure,
        "away_pressure": away_pressure,

        "home_danger": home_danger,
        "away_danger": away_danger,

        "attack_wave": {
            "team": wave_team,
            "score": wave_score
        },

        "dominant_team": dominant_team,

        "match_tempo": tempo,

        "transition_risk": transition_risk,

        "fatigue_index": fatigue,

        "chaos_index": chaos,

        "confidence_score": confidence,

        "commentary": commentary
    }