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
def build_safe_live_brain(
    match_data,
    pressure,
    xg_analysis,
    live_flow,
    future_prediction,
    timeline,
    build_live_match_brain_func,
    live_match_brain_available=False
):
    try:
        timeline_events = []

        if isinstance(timeline, dict):
            timeline_events = timeline.get("events", [])
        elif isinstance(timeline, list):
            timeline_events = timeline

        brain = build_live_match_brain_func(
            match=match_data,
            pressure_engine=pressure,
            xg_analysis=xg_analysis,
            live_flow=live_flow,
            future_prediction=future_prediction,
            timeline=timeline_events,
        )

        if isinstance(brain, dict):
            brain["available"] = live_match_brain_available
            brain["source"] = "live_match_brain"
            return brain

        return {
            "available": False,
            "source": "live_match_brain",
            "error": "Risposta live_brain non valida",
            "commentary": [],
            "prediction": {},
        }

    except Exception as e:
        return {
            "available": False,
            "source": "live_match_brain",
            "error": str(e),
            "commentary": [],
            "prediction": {},
        }
def build_full_analysis(
    match_id: int,
    *,
    get_match_live_data_func,
    analyze_match_tactical_func,
    generate_live_engine_func,
    analyze_pressure_func,
    generate_xg_analysis_func,
    generate_live_flow_func,
    generate_tactical_coach_func,
    generate_future_prediction_func,
    analyze_ai_core_func,
    generate_player_ratings_func,
    generate_win_probability_func,
    generate_tactical_events_func,
    generate_live_alerts_func,
    build_live_events_func,
    generate_ai_report_func,
    generate_timeline_func,
    build_live_match_brain_func,
    live_match_brain_available=False
):
    match_data = get_match_live_data_func(match_id)

    if "error" in match_data:
        return match_data

    tactical = analyze_match_tactical_func(match_data)
    live_engine = generate_live_engine_func(match_data)

    pressure_base = analyze_pressure_func(match_data)
    pressure = merge_pressure(pressure_base, live_engine)

    xg_analysis = generate_xg_analysis_func(
        match_data=match_data,
        tactical_data={
            "home_pressure": pressure.get("home", {}).get("pressure", 50),
            "away_pressure": pressure.get("away", {}).get("pressure", 50),
        }
    )

    live_flow = generate_live_flow_func(
        match_data=match_data,
        pressure_data=pressure,
        xg_data=xg_analysis
    )

    ai_commentary = build_safe_ai_commentary(
        match_data=match_data,
        pressure=pressure,
        live_flow=live_flow
    )

    tactical_coach = generate_tactical_coach_func(
        match_data=match_data,
        pressure_data=pressure
    )

    future_prediction = generate_future_prediction_func(
        match_data=match_data,
        pressure_data=pressure
    )

    ai_core = analyze_ai_core_func(match_data)

    if isinstance(ai_core, dict):
        commentary_lines = ai_commentary.get("commentary", [])

        ai_core["commentary"] = (
            commentary_lines
            or live_engine.get("commentary")
            or ai_core.get("commentary", [])
        )

        ai_core["confidence_score"] = live_engine.get(
            "confidence_score",
            ai_core.get("confidence_score", 70)
        )

        ai_core["live_flow_story"] = live_flow.get("story")

    players = generate_player_ratings_func(match_data)

    win_probability = generate_win_probability_func({
        "goals": match_data.get("score", {}),
        "minute": match_data.get("minute", 0),
        "tactical_analysis": {
            "home_pressure": pressure.get("home", {}).get("pressure", 0),
            "away_pressure": pressure.get("away", {}).get("pressure", 0),
            "home_danger": pressure.get("home", {}).get("danger", 0),
            "away_danger": pressure.get("away", {}).get("danger", 0),
            "home_win_momentum": live_flow.get("home", {}).get("momentum", 50),
            "away_win_momentum": live_flow.get("away", {}).get("momentum", 50),
        }
    })

    events = generate_tactical_events_func(match_data)
    alerts = generate_live_alerts_func(events)
    live_events = build_live_events_func(match_data)
    report = generate_ai_report_func(match_data, tactical, players)

    try:
        timeline = generate_timeline_func(
            match_data=match_data,
            tactical_data={
                "tactical": tactical,
                "events": events
            },
            alerts_data={
                "live_alerts": alerts
            }
        )
    except Exception:
        timeline = {
            "events": live_engine.get("timeline", [])
        }

    live_brain = build_safe_live_brain(
    match_data=match_data,
    pressure=pressure,
    xg_analysis=xg_analysis,
    live_flow=live_flow,
    future_prediction=future_prediction,
    timeline=timeline,
    build_live_match_brain_func=build_live_match_brain_func,
    live_match_brain_available=live_match_brain_available
)

    if isinstance(ai_core, dict) and isinstance(live_brain, dict):
        prediction = live_brain.get("prediction", {})
        if isinstance(prediction, dict):
            ai_core["live_brain_prediction"] = prediction.get("next_5_minutes")

    return {
        "match": match_data,
        "tactical_analysis": tactical,
        "ai_core": ai_core,
        "ai_commentary": ai_commentary,
        "pressure_engine": pressure,
        "live_engine": live_engine,
        "live_flow": live_flow,
        "live_brain": live_brain,
        "tactical_coach": tactical_coach,
        "future_prediction": future_prediction,
        "xg_analysis": xg_analysis,
        "win_probability": win_probability,
        "players_analysis": players,
        "event_analysis": events,
        "live_alerts": pressure.get("alerts", alerts),
        "live_events": live_events,
        "timeline": timeline,
        "ai_report": report
    }

def get_cached_full_analysis(
    match_id: int,
    *,
    full_analysis_cache,
    full_analysis_cache_seconds,
    get_dynamic_match_cache_func,
    launch_background_refresh_func,
    build_full_analysis_func
):
    cached = full_analysis_cache.get(match_id)

    dynamic_seconds = full_analysis_cache_seconds

    if cached:
        try:
            cached_match = cached["data"].get("match", {})
            dynamic_seconds = get_dynamic_match_cache_func(cached_match)
        except Exception:
            pass

    if cache_valid(cached, dynamic_seconds):
        try:
            launch_background_refresh_func(match_id)
        except Exception:
            pass

        cached["data"]["cache"] = True
        cached["data"]["cache_seconds"] = dynamic_seconds

        return cached["data"]

    try:
        data = build_full_analysis_func(match_id)

        if "error" not in data:
            full_analysis_cache[match_id] = {
                "timestamp": time.time(),
                "data": data
            }

            data["cache"] = False
            data["cache_seconds"] = dynamic_seconds

        elif cached:
            cached["data"]["cache_warning"] = data.get("error")
            return cached["data"]

        return data

    except Exception as e:
        if cached:
            cached["data"]["cache_warning"] = str(e)
            return cached["data"]

        return {
            "error": str(e),
            "match_id": match_id
        }


