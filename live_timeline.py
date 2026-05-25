"""
live_timeline.py
MatchIQ Tactical - Smart AI Timeline Engine

Genera una timeline tattica più realistica usando:
- pressione
- danger
- eventi live
- alert
- minuto
- risultato
- fase partita

Non chiama nuove API.
"""

from datetime import datetime


def _num(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, _num(value)))


def _get_score(match_data):
    score = match_data.get("score", {})

    if isinstance(score, dict):
        return {
            "home": int(_num(score.get("home"), 0)),
            "away": int(_num(score.get("away"), 0)),
        }

    return {
        "home": int(_num(match_data.get("home_goals"), 0)),
        "away": int(_num(match_data.get("away_goals"), 0)),
    }


def _add_event(events, minute, event_type, team, icon, title, message, priority="MEDIUM"):
    events.append({
        "minute": int(_num(minute, 0)),
        "type": event_type,
        "team": team,
        "icon": icon,
        "title": title,
        "message": message,
        "priority": priority
    })


def generate_timeline(match_data, tactical_data, alerts_data):
    """
    Genera timeline tattica live intelligente.
    """

    timeline = []

    minute = int(_num(match_data.get("minute"), 0))

    home = match_data.get("home") or match_data.get("home_team") or "Home"
    away = match_data.get("away") or match_data.get("away_team") or "Away"

    score = _get_score(match_data)

    tactical = tactical_data.get("tactical", {}) if isinstance(tactical_data, dict) else {}

    raw_alerts = []
    if isinstance(alerts_data, dict):
        live_alerts = alerts_data.get("live_alerts", {})
        if isinstance(live_alerts, dict):
            raw_alerts = live_alerts.get("alerts", [])
        elif isinstance(live_alerts, list):
            raw_alerts = live_alerts

    pressure_home = _clamp(tactical.get("home_pressure", 0))
    pressure_away = _clamp(tactical.get("away_pressure", 0))

    danger_home = _clamp(tactical.get("home_danger", 0))
    danger_away = _clamp(tactical.get("away_danger", 0))

    dominance_gap = abs(pressure_home - pressure_away)
    danger_gap = abs(danger_home - danger_away)

    # ---------------------------------------------------
    # MATCH PHASE
    # ---------------------------------------------------

    if minute <= 15:
        _add_event(
            timeline,
            minute,
            "MATCH_PHASE",
            None,
            "🧭",
            "Fase iniziale",
            "Le squadre stanno definendo ritmo, pressione e prime zone di controllo.",
            "LOW"
        )

    elif 16 <= minute <= 35:
        _add_event(
            timeline,
            minute,
            "MATCH_PHASE",
            None,
            "📊",
            "Fase di studio avanzata",
            "Il match inizia a mostrare pattern tattici più chiari.",
            "LOW"
        )

    elif 36 <= minute <= 45:
        _add_event(
            timeline,
            minute,
            "MATCH_PHASE",
            None,
            "⏱️",
            "Fine primo tempo",
            "La gestione emotiva diventa importante prima dell'intervallo.",
            "MEDIUM"
        )

    elif 46 <= minute <= 65:
        _add_event(
            timeline,
            minute,
            "MATCH_PHASE",
            None,
            "🔁",
            "Fase di riassestamento",
            "Le squadre stanno adattando pressione e coperture dopo l'intervallo.",
            "LOW"
        )

    elif 66 <= minute <= 80:
        _add_event(
            timeline,
            minute,
            "MATCH_PHASE",
            None,
            "🔥",
            "Fase decisiva",
            "Il peso degli episodi aumenta: ogni transizione può cambiare la partita.",
            "MEDIUM"
        )

    elif minute > 80:
        _add_event(
            timeline,
            minute,
            "MATCH_PHASE",
            None,
            "🚨",
            "Finale ad alta tensione",
            "Il match entra nella fase più sensibile dal punto di vista mentale e tattico.",
            "HIGH"
        )

    # ---------------------------------------------------
    # SCORE STATE
    # ---------------------------------------------------

    if score["home"] > score["away"]:
        _add_event(
            timeline,
            minute,
            "SCORE_CONTEXT",
            home,
            "🔵",
            "Gestione vantaggio",
            f"{home} è avanti nel punteggio e può scegliere se controllare o continuare ad attaccare.",
            "MEDIUM"
        )

    elif score["away"] > score["home"]:
        _add_event(
            timeline,
            minute,
            "SCORE_CONTEXT",
            away,
            "🔴",
            "Gestione vantaggio",
            f"{away} è avanti nel punteggio: la squadra di casa potrebbe aumentare pressione e rischio.",
            "MEDIUM"
        )

    else:
        _add_event(
            timeline,
            minute,
            "SCORE_CONTEXT",
            None,
            "⚖️",
            "Match in equilibrio",
            "Il risultato è ancora aperto: la prossima fase può pesare molto sull'inerzia.",
            "LOW"
        )

    # ---------------------------------------------------
    # PRESSURE EVENTS
    # ---------------------------------------------------

    if pressure_home >= 82:
        _add_event(
            timeline,
            minute,
            "PRESSURE",
            home,
            "🔥",
            "Pressione molto alta",
            f"{home} sta comprimendo l'avversario e aumentando il volume offensivo.",
            "HIGH"
        )

    elif pressure_home >= 70:
        _add_event(
            timeline,
            minute,
            "PRESSURE",
            home,
            "🔥",
            "Pressione offensiva",
            f"{home} sta prendendo campo e alzando il ritmo della partita.",
            "MEDIUM"
        )

    if pressure_away >= 82:
        _add_event(
            timeline,
            minute,
            "PRESSURE",
            away,
            "🔥",
            "Pressione molto alta",
            f"{away} sta comprimendo l'avversario e aumentando il volume offensivo.",
            "HIGH"
        )

    elif pressure_away >= 70:
        _add_event(
            timeline,
            minute,
            "PRESSURE",
            away,
            "🔥",
            "Pressione offensiva",
            f"{away} sta prendendo campo e alzando il ritmo della partita.",
            "MEDIUM"
        )

    # ---------------------------------------------------
    # DANGER EVENTS
    # ---------------------------------------------------

    if danger_home >= 82:
        _add_event(
            timeline,
            minute,
            "DANGER",
            home,
            "🚨",
            "Zona pericolo",
            f"{home} sta generando una fase offensiva ad alto rischio.",
            "HIGH"
        )

    elif danger_home >= 68:
        _add_event(
            timeline,
            minute,
            "DANGER",
            home,
            "⚠️",
            "Fase pericolosa",
            f"{home} sta costruendo situazioni potenzialmente decisive.",
            "MEDIUM"
        )

    if danger_away >= 82:
        _add_event(
            timeline,
            minute,
            "DANGER",
            away,
            "🚨",
            "Zona pericolo",
            f"{away} sta generando una fase offensiva ad alto rischio.",
            "HIGH"
        )

    elif danger_away >= 68:
        _add_event(
            timeline,
            minute,
            "DANGER",
            away,
            "⚠️",
            "Fase pericolosa",
            f"{away} sta costruendo situazioni potenzialmente decisive.",
            "MEDIUM"
        )

    # ---------------------------------------------------
    # MOMENTUM / DOMINANCE
    # ---------------------------------------------------

    if dominance_gap >= 30:
        dominant = home if pressure_home > pressure_away else away

        _add_event(
            timeline,
            minute,
            "MOMENTUM",
            dominant,
            "⚡",
            "Momentum netto",
            f"{dominant} sta controllando il flusso della partita con una pressione superiore.",
            "HIGH"
        )

    elif dominance_gap >= 18:
        dominant = home if pressure_home > pressure_away else away

        _add_event(
            timeline,
            minute,
            "MOMENTUM",
            dominant,
            "📈",
            "Vantaggio territoriale",
            f"{dominant} sta guadagnando metri e influenza tattica.",
            "MEDIUM"
        )

    if danger_gap >= 30:
        dangerous_team = home if danger_home > danger_away else away

        _add_event(
            timeline,
            minute,
            "DANGER_GAP",
            dangerous_team,
            "💥",
            "Pericolosità superiore",
            f"{dangerous_team} sta creando occasioni più incisive rispetto all'avversario.",
            "HIGH"
        )

    # ---------------------------------------------------
    # CHAOS DETECTION
    # ---------------------------------------------------

    chaos_score = _clamp(
        max(pressure_home, pressure_away) * 0.35 +
        max(danger_home, danger_away) * 0.45 +
        dominance_gap * 0.10 +
        danger_gap * 0.10
    )

    if chaos_score >= 78:
        _add_event(
            timeline,
            minute,
            "CHAOS",
            None,
            "🌪️",
            "Partita caotica",
            "Il match è entrato in una fase instabile: transizioni rapide e rischio elevato.",
            "HIGH"
        )

    elif chaos_score >= 60:
        _add_event(
            timeline,
            minute,
            "INTENSITY",
            None,
            "⚡",
            "Intensità crescente",
            "Il ritmo sta salendo e la partita può aprirsi nei prossimi minuti.",
            "MEDIUM"
        )

    # ---------------------------------------------------
    # IMPORT ALERTS
    # ---------------------------------------------------

    for alert in raw_alerts:
        if not isinstance(alert, dict):
            continue

        _add_event(
            timeline,
            minute,
            alert.get("type", "AI_ALERT"),
            alert.get("team"),
            alert.get("icon", "🧠"),
            alert.get("title", "AI Event"),
            alert.get("message", alert.get("detail", "")),
            alert.get("priority", alert.get("level", "MEDIUM"))
        )

    # ---------------------------------------------------
    # FALLBACK
    # ---------------------------------------------------

    if not timeline:
        _add_event(
            timeline,
            minute,
            "INFO",
            None,
            "🧠",
            "Monitoraggio AI attivo",
            "MatchIQ sta monitorando pressione, pericolosità e andamento tattico.",
            "LOW"
        )

    # ---------------------------------------------------
    # SORT + LIMIT
    # ---------------------------------------------------

    priority_weight = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "INFO": 1
    }

    timeline = sorted(
        timeline,
        key=lambda x: (
            x.get("minute", 0),
            priority_weight.get(str(x.get("priority", "LOW")).upper(), 1)
        ),
        reverse=True
    )

    timeline = timeline[:12]

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "minute": minute,
        "match_state": {
            "home": home,
            "away": away,
            "score": score,
            "chaos_score": round(chaos_score, 1),
            "pressure_home": round(pressure_home, 1),
            "pressure_away": round(pressure_away, 1),
            "danger_home": round(danger_home, 1),
            "danger_away": round(danger_away, 1),
        },
        "events": timeline
    }