"""
live_match_brain.py
MatchIQ Tactical - Central Live Match Brain

Questo modulo non chiama nuove API.
Riceve i dati già disponibili dagli altri engine e li trasforma in:
- chaos index
- match temperature
- pressure wave
- panic level
- emotional control
- tactical identity
- next 5 minutes prediction
- AI commentary
"""

from typing import Dict, Any, List


def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, _num(value)))


def _get_score(match: Dict[str, Any]):
    score = match.get("score", {})

    if isinstance(score, dict):
        return {
            "home": int(_num(score.get("home"), 0)),
            "away": int(_num(score.get("away"), 0)),
        }

    return {
        "home": int(_num(match.get("home_goals"), 0)),
        "away": int(_num(match.get("away_goals"), 0)),
    }


def _temperature_label(value: float) -> str:
    if value >= 85:
        return "CHAOTIC"
    if value >= 70:
        return "CRITICAL"
    if value >= 55:
        return "INTENSE"
    if value >= 35:
        return "BALANCED"
    return "CONTROLLED"


def _risk_label(value: float) -> str:
    if value >= 80:
        return "CRITICAL"
    if value >= 65:
        return "HIGH"
    if value >= 45:
        return "ELEVATED"
    if value >= 25:
        return "MEDIUM"
    return "LOW"


def _detect_tactical_identity(
    team_name: str,
    pressure: float,
    danger: float,
    xg: float,
    momentum: float,
    panic: float,
    is_losing: bool,
) -> Dict[str, Any]:

    identity = "Balanced Control"
    description = "Squadra in equilibrio: alterna gestione, possesso e pressione senza un'identità dominante."
    tags = ["BALANCED", "CONTROL", "STABLE"]

    if pressure >= 78 and danger >= 68:
        identity = "High Pressing Machine"
        description = "Pressione alta e recupero aggressivo: la squadra sta cercando di soffocare l'avversario."
        tags = ["HIGH PRESS", "AGGRESSIVE", "TERRITORIAL"]

    elif danger >= 75 and pressure < 65:
        identity = "Vertical Attack"
        description = "Approccio diretto: poche fasi di possesso, ma forte capacità di generare pericolo rapidamente."
        tags = ["DIRECT", "FAST ATTACK", "RISK"]

    elif pressure >= 70 and danger < 55:
        identity = "Possession Control"
        description = "Controllo territoriale: la squadra gestisce ritmo e campo senza forzare troppo."
        tags = ["POSSESSION", "CONTROL", "TEMPO"]

    elif momentum >= 72 and danger >= 60:
        identity = "Momentum Surge"
        description = "Momento favorevole evidente: intensità e fiducia stanno spostando il match."
        tags = ["MOMENTUM", "CONFIDENCE", "PUSH"]

    elif is_losing and pressure >= 62:
        identity = "Chasing Mode"
        description = "La squadra sta inseguendo il risultato e aumenta rischio, pressione e volume offensivo."
        tags = ["CHASING", "HIGH RISK", "REACTION"]

    elif panic >= 75 and pressure < 55:
        identity = "Defensive Stress"
        description = "Fase di sofferenza: la squadra sembra reattiva e sotto pressione psicologica."
        tags = ["LOW BLOCK", "STRESS", "DEFENSIVE"]

    identity_score = _clamp(
        pressure * 0.30 +
        danger * 0.35 +
        momentum * 0.22 +
        xg * 8
    )

    return {
        "team": team_name,
        "identity": identity,
        "description": description,
        "tags": tags,
        "identity_score": round(identity_score, 1),
    }


def build_live_match_brain(
    match: Dict[str, Any],
    pressure_engine: Dict[str, Any] = None,
    xg_analysis: Dict[str, Any] = None,
    live_flow: Dict[str, Any] = None,
    future_prediction: Dict[str, Any] = None,
    timeline: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    pressure_engine = pressure_engine or {}
    xg_analysis = xg_analysis or {}
    live_flow = live_flow or {}
    future_prediction = future_prediction or {}
    timeline = timeline or []

    home = match.get("home") or match.get("home_team") or "Home"
    away = match.get("away") or match.get("away_team") or "Away"
    minute = _num(match.get("minute"), 0)
    score = _get_score(match)

    home_pressure = _clamp(pressure_engine.get("home", {}).get("pressure"))
    away_pressure = _clamp(pressure_engine.get("away", {}).get("pressure"))
    home_danger = _clamp(pressure_engine.get("home", {}).get("danger"))
    away_danger = _clamp(pressure_engine.get("away", {}).get("danger"))

    home_xg = _num(xg_analysis.get("home_xg"), 0)
    away_xg = _num(xg_analysis.get("away_xg"), 0)

    home_momentum = _clamp(
        live_flow.get("home", {}).get("momentum", home_pressure)
        if isinstance(live_flow.get("home"), dict)
        else home_pressure
    )

    away_momentum = _clamp(
        live_flow.get("away", {}).get("momentum", away_pressure)
        if isinstance(live_flow.get("away"), dict)
        else away_pressure
    )

    pressure_max = max(home_pressure, away_pressure)
    danger_max = max(home_danger, away_danger)
    pressure_gap = abs(home_pressure - away_pressure)
    danger_gap = abs(home_danger - away_danger)
    momentum_gap = abs(home_momentum - away_momentum)
    xg_gap = abs(home_xg - away_xg)

    timeline_intensity = min(len(timeline) * 4, 24)

    chaos_index = _clamp(
        danger_max * 0.32 +
        pressure_max * 0.24 +
        momentum_gap * 0.18 +
        pressure_gap * 0.10 +
        xg_gap * 10 +
        timeline_intensity
    )

    pressure_wave = _clamp(
        pressure_max * 0.48 +
        danger_max * 0.34 +
        momentum_gap * 0.10 +
        timeline_intensity * 0.8
    )

    home_panic = _clamp(
        away_danger * 0.42 +
        away_pressure * 0.28 +
        (18 if score["away"] > score["home"] else 0) +
        (minute * 0.12)
    )

    away_panic = _clamp(
        home_danger * 0.42 +
        home_pressure * 0.28 +
        (18 if score["home"] > score["away"] else 0) +
        (minute * 0.12)
    )

    emotional_control = _clamp(
        100 -
        ((home_panic + away_panic) / 2) -
        (chaos_index * 0.12) +
        12
    )

    fatigue_pressure = _clamp(
        minute * 0.45 +
        (home_pressure + away_pressure) * 0.22
    )

    if home_momentum > away_momentum:
        dominant_team = home
        dominant_side = "home"
    elif away_momentum > home_momentum:
        dominant_team = away
        dominant_side = "away"
    else:
        dominant_team = "Equilibrio"
        dominant_side = "balanced"

    match_temperature_value = _clamp(
        chaos_index * 0.42 +
        pressure_wave * 0.28 +
        max(home_panic, away_panic) * 0.18 +
        fatigue_pressure * 0.12
    )

    match_temperature = _temperature_label(match_temperature_value)

    next_goal_probability = _clamp(
        danger_max * 0.34 +
        pressure_wave * 0.24 +
        max(home_xg, away_xg) * 10 +
        chaos_index * 0.18
    )

    collapse_risk = _clamp(
        max(home_panic, away_panic) * 0.38 +
        fatigue_pressure * 0.25 +
        chaos_index * 0.25 +
        pressure_wave * 0.12
    )

    counter_attack_risk = _risk_label(
        chaos_index * 0.45 +
        momentum_gap * 0.35 +
        danger_gap * 0.20
    )

    home_identity = _detect_tactical_identity(
        home,
        home_pressure,
        home_danger,
        home_xg,
        home_momentum,
        home_panic,
        score["home"] < score["away"],
    )

    away_identity = _detect_tactical_identity(
        away,
        away_pressure,
        away_danger,
        away_xg,
        away_momentum,
        away_panic,
        score["away"] < score["home"],
    )

    if chaos_index >= 75:
        match_dna = "Chaotic Transition Game"
    elif pressure_wave >= 78:
        match_dna = "High Pressure Match"
    elif abs(home_identity["identity_score"] - away_identity["identity_score"]) <= 8:
        match_dna = "Tactical Chess Match"
    elif dominant_side == "home":
        match_dna = f"{home} Control Phase"
    elif dominant_side == "away":
        match_dna = f"{away} Control Phase"
    else:
        match_dna = "Balanced Tactical Battle"

    commentary = _generate_commentary(
        home=home,
        away=away,
        dominant_team=dominant_team,
        chaos_index=chaos_index,
        pressure_wave=pressure_wave,
        next_goal_probability=next_goal_probability,
        home_pressure=home_pressure,
        away_pressure=away_pressure,
        home_panic=home_panic,
        away_panic=away_panic,
        match_temperature=match_temperature,
    )

    return {
        "chaos_index": round(chaos_index, 1),
        "match_temperature": match_temperature,
        "match_temperature_value": round(match_temperature_value, 1),
        "pressure_wave": round(pressure_wave, 1),
        "dominant_team": dominant_team,
        "dominant_side": dominant_side,
        "panic_level_home": round(home_panic, 1),
        "panic_level_away": round(away_panic, 1),
        "emotional_control": round(emotional_control, 1),
        "fatigue_pressure": round(fatigue_pressure, 1),
        "next_goal_probability": round(next_goal_probability, 1),
        "collapse_risk": round(collapse_risk, 1),
        "counter_attack_risk": counter_attack_risk,
        "match_dna": match_dna,
        "home_identity": home_identity,
        "away_identity": away_identity,
        "commentary": commentary,
        "prediction": {
            "next_5_minutes": _next_5_minutes_prediction(
                dominant_team,
                next_goal_probability,
                pressure_wave,
                collapse_risk,
                match_temperature,
            ),
            "risk_level": _risk_label(collapse_risk),
            "confidence": round(_clamp(55 + pressure_wave * 0.25 + chaos_index * 0.15), 1),
        },
    }


def _generate_commentary(
    home: str,
    away: str,
    dominant_team: str,
    chaos_index: float,
    pressure_wave: float,
    next_goal_probability: float,
    home_pressure: float,
    away_pressure: float,
    home_panic: float,
    away_panic: float,
    match_temperature: str,
) -> List[str]:

    lines = []

    if dominant_team != "Equilibrio":
        lines.append(
            f"{dominant_team} sta prendendo progressivamente il controllo del flusso partita."
        )
    else:
        lines.append(
            "Il match resta equilibrato, ma ci sono segnali tattici in evoluzione."
        )

    if pressure_wave >= 75:
        lines.append(
            "La pressione offensiva è alta: la difesa sta entrando in una fase di stress continuo."
        )
    elif pressure_wave >= 55:
        lines.append(
            "Il ritmo sta salendo: le squadre stanno aumentando intensità e aggressività."
        )

    if next_goal_probability >= 65:
        lines.append(
            "La probabilità di un episodio decisivo nei prossimi minuti è elevata."
        )
    elif next_goal_probability >= 45:
        lines.append(
            "Il sistema rileva una possibile finestra offensiva nei prossimi minuti."
        )

    if home_panic >= 75:
        lines.append(
            f"{home} mostra segnali di pressione mentale e perdita di controllo difensivo."
        )

    if away_panic >= 75:
        lines.append(
            f"{away} mostra segnali di pressione mentale e difficoltà nel gestire il momento."
        )

    if chaos_index >= 75:
        lines.append(
            "La partita è entrata in una fase caotica: transizioni rapide e alto margine d'errore."
        )

    if match_temperature in ["CRITICAL", "CHAOTIC"]:
        lines.append(
            "Match temperature molto alta: ogni episodio può cambiare completamente l'inerzia."
        )

    return lines[:6]


def _next_5_minutes_prediction(
    dominant_team: str,
    next_goal_probability: float,
    pressure_wave: float,
    collapse_risk: float,
    match_temperature: str,
) -> str:

    if next_goal_probability >= 70:
        return f"Possibile grande occasione per {dominant_team} nei prossimi 5 minuti."

    if pressure_wave >= 75:
        return f"{dominant_team} può generare una nuova fase di pressione offensiva."

    if collapse_risk >= 70:
        return "Possibile errore difensivo o perdita di controllo tattico nei prossimi minuti."

    if match_temperature in ["CRITICAL", "CHAOTIC"]:
        return "Fase instabile: probabile aumento di transizioni, falli e situazioni sporche."

    return "Match equilibrato: probabile gestione del ritmo senza shock immediati."