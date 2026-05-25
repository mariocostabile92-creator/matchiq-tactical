import time
from datetime import datetime

from fastapi import APIRouter, Query

from app.utils.safe import safe_int
from app.utils.cache import cache_valid

router = APIRouter(prefix="/api", tags=["live"])


def create_live_router(
    get_live_matches_func,
    live_matches_cache,
    live_matches_cache_seconds,
):
    @router.get("/live")
    def api_live(top_only: bool = Query(False)):
        return get_live_matches_func(top_only=top_only)

    @router.get("/live-matches")
    def live_matches(top_only: bool = Query(False)):
        cache_key = f"top_only_{top_only}"
        cached = live_matches_cache.get(cache_key)

        # tutto il resto della funzione live_matches
    """
    Endpoint production-ready per la dashboard live.

    Migliorie:
    - default ALL LIVE, così la home mostra partite anche se non sono top leagues
    - normalizza risposta per frontend: matches / data / live_matches
    - gestisce score sia dict sia stringa tipo "1-0"
    - gestisce league sia stringa sia dict
    - gestisce nested fixture/teams/goals API-Football
    - evita crash con .get() su stringhe
    - usa cache se la live API fallisce
    """
    cache_key = f"top_only_{top_only}"
    cached = live_matches_cache.get(cache_key)

    if cache_valid(cached, live_matches_cache_seconds):
        data = cached["data"]
        data["cache"] = True
        data["api_safe"] = True
        return data

    try:
        data = get_live_matches_func(top_only=top_only)

        if isinstance(data, dict):
            raw_matches = (
                data.get("matches")
                or data.get("data")
                or data.get("live_matches")
                or []
            )
        elif isinstance(data, list):
            raw_matches = data
        else:
            raw_matches = []

        matches = []

        for m in raw_matches:
            if not isinstance(m, dict):
                continue

            fixture_obj = m.get("fixture") if isinstance(m.get("fixture"), dict) else {}
            teams_obj = m.get("teams") if isinstance(m.get("teams"), dict) else {}
            goals_obj = m.get("goals") if isinstance(m.get("goals"), dict) else {}
            league_obj = m.get("league") if isinstance(m.get("league"), dict) else {}

            home_obj = teams_obj.get("home") if isinstance(teams_obj.get("home"), dict) else {}
            away_obj = teams_obj.get("away") if isinstance(teams_obj.get("away"), dict) else {}

            status_obj = fixture_obj.get("status") if isinstance(fixture_obj.get("status"), dict) else {}

            match_id = (
                m.get("match_id")
                or m.get("fixture_id")
                or m.get("id")
                or fixture_obj.get("id")
            )

            home = (
                m.get("home")
                or m.get("home_team")
                or home_obj.get("name")
                or "Home"
            )

            away = (
                m.get("away")
                or m.get("away_team")
                or away_obj.get("name")
                or "Away"
            )

            score = m.get("score", {})

            if isinstance(score, str):
                parts = score.replace(" ", "").split("-")
                score = {
                    "home": safe_int(parts[0], 0) if len(parts) > 0 else 0,
                    "away": safe_int(parts[1], 0) if len(parts) > 1 else 0
                }

            if not isinstance(score, dict):
                score = {}

            home_goals = (
                m.get("home_goals")
                if m.get("home_goals") is not None
                else goals_obj.get("home")
                if goals_obj.get("home") is not None
                else score.get("home")
                if score.get("home") is not None
                else 0
            )

            away_goals = (
                m.get("away_goals")
                if m.get("away_goals") is not None
                else goals_obj.get("away")
                if goals_obj.get("away") is not None
                else score.get("away")
                if score.get("away") is not None
                else 0
            )

            minute = (
                m.get("minute")
                if m.get("minute") is not None
                else m.get("elapsed")
                if m.get("elapsed") is not None
                else status_obj.get("elapsed")
                if status_obj.get("elapsed") is not None
                else 0
            )

            status = (
                m.get("status")
                or m.get("fixture_status")
                or status_obj.get("short")
                or "LIVE"
            )

            status_long = (
                m.get("status_long")
                or status_obj.get("long")
                or status
            )

            league_name = (
                league_obj.get("name")
                if league_obj
                else m.get("league")
                or m.get("league_name")
                or "Live"
            )

            country = (
                m.get("country")
                or league_obj.get("country")
                or ""
            )

            home_logo = (
                m.get("home_logo")
                or home_obj.get("logo")
                or ""
            )

            away_logo = (
                m.get("away_logo")
                or away_obj.get("logo")
                or ""
            )

            if not match_id:
                continue

            item = {
                "id": match_id,
                "match_id": match_id,
                "fixture_id": match_id,

                "home": home,
                "away": away,
                "home_team": home,
                "away_team": away,

                "home_logo": home_logo,
                "away_logo": away_logo,

                "score": f"{safe_int(home_goals)}-{safe_int(away_goals)}",
                "score_obj": {
                    "home": safe_int(home_goals),
                    "away": safe_int(away_goals)
                },

                "home_goals": safe_int(home_goals),
                "away_goals": safe_int(away_goals),

                "minute": safe_int(minute),
                "elapsed": safe_int(minute),
                "status": str(status),
                "status_long": str(status_long),
                "league": league_name,
                "country": country,

                "memory_mode": bool(m.get("memory_mode", False)),
                "live_label": m.get("live_label", "LIVE"),
                "last_seen_live": m.get("last_seen_live"),

                "url_match": f"/match.html?id={match_id}",
                "url_scout": f"/scout.html?match_id={match_id}"
            }

            matches.append(item)

        response = {
            "source": "api-football",
            "top_only": top_only,
            "total_matches": len(matches),
            "matches": matches,
            "data": matches,
            "live_matches": matches,
            "cache": False,
            "api_safe": True,
            "generated_at": datetime.utcnow().isoformat()
        }

        if matches:
            live_matches_cache[cache_key] = {
                "timestamp": time.time(),
                "data": response
            }
            return response

        if cached:
            cached["data"]["cache"] = True
            cached["data"]["cache_warning"] = "Nessuna partita live nuova, uso cache precedente"
            return cached["data"]

        return response

    except Exception as e:
        if cached:
            cached["data"]["cache"] = True
            cached["data"]["cache_warning"] = str(e)
            return cached["data"]

        return {
            "source": "api-football",
            "top_only": top_only,
            "total_matches": 0,
            "matches": [],
            "data": [],
            "live_matches": [],
            "error": str(e),
            "api_safe": True,
            "generated_at": datetime.utcnow().isoformat()
        }