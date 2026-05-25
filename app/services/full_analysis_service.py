"""
app/services/full_analysis_service.py

Servizio Full Analysis MatchIQ Tactical.
Qui sposteremo progressivamente:
- merge_pressure
- build_safe_ai_commentary
- build_safe_live_brain
- build_full_analysis
- get_cached_full_analysis
"""

from datetime import datetime


def full_analysis_service_ready():
    return {
        "service": "full_analysis_service",
        "status": "ready",
        "generated_at": datetime.utcnow().isoformat()
    }
def merge_pressure(base_pressure, live_engine):
    if not isinstance(base_pressure, dict):
        base_pressure = {}

    if not isinstance(live_engine, dict):
        live_engine = {}

    return {
        "generated_at": live_engine.get("generated_at"),
        "minute": live_engine.get("minute"),
        "dominance_score": base_pressure.get("dominance_score", 50),
        "dominance_label": live_engine.get(
            "dominance_label",
            base_pressure.get("dominance_label", "Equilibrio")
        ),
        "dominant_team": live_engine.get(
            "dominant_team",
            base_pressure.get("dominant_team", "Equilibrio")
        ),
        "home": {
            **base_pressure.get("home", {}),
            **live_engine.get("home", {})
        },
        "away": {
            **base_pressure.get("away", {}),
            **live_engine.get("away", {})
        },
        "alerts": live_engine.get(
            "alerts",
            base_pressure.get("alerts", [])
        )
    }
def build_safe_ai_commentary(match_data, pressure, live_flow):
    try:
        commentary = generate_ai_commentary(
            match_data=match_data,
            pressure_data=pressure,
            live_flow=live_flow
        )

        if isinstance(commentary, dict):
            commentary["available"] = True
            commentary["source"] = "ai_commentary_engine"
            return commentary

        return {
            "available": False,
            "source": "ai_commentary_engine",
            "error": "Risposta ai_commentary non valida",
            "commentary": []
        }

    except Exception as e:
        return {
            "available": False,
            "source": "ai_commentary_engine",
            "error": str(e),
            "commentary": []
        }

