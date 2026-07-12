import hashlib
import json
from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List

from app.models.weekly_briefing import WeeklyBriefingGenerateRequest
from app.repositories import knowledge_repository, weekly_briefing_repository


def initialize_weekly_briefing() -> None:
    weekly_briefing_repository.initialize_weekly_briefing_schema()


def current_week_key(today: date = None) -> str:
    value = today or date.today()
    monday = value - timedelta(days=value.weekday())
    return monday.isoformat()


def _fingerprint(sources: Dict[str, Any]) -> str:
    stable_sources = json.loads(json.dumps(sources, ensure_ascii=False, default=str))
    if isinstance(stable_sources.get("local"), dict):
        stable_sources["local"].pop("captured_at", None)
    normalized = json.dumps(stable_sources, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _events(local: Dict[str, Any]) -> List[Dict[str, Any]]:
    latest = local.get("latest_match") if isinstance(local.get("latest_match"), dict) else {}
    return latest.get("events") if isinstance(latest.get("events"), list) else []


def _ratings(local: Dict[str, Any]) -> List[Dict[str, Any]]:
    latest = local.get("latest_match") if isinstance(local.get("latest_match"), dict) else {}
    return latest.get("ratings") if isinstance(latest.get("ratings"), list) else []


def _source(label: str, count: int, module: str, url: str) -> Dict[str, Any]:
    return {"label": label, "count": count, "module": module, "url": url}


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def build_briefing(sources: Dict[str, Any]) -> Dict[str, Any]:
    local = sources.get("local") or {}
    cloud = sources.get("cloud") or {}
    latest = local.get("latest_match") if isinstance(local.get("latest_match"), dict) else {}
    cloud_match = (cloud.get("saved_matches") or [{}])[0]
    match = latest.get("match") or {}
    metadata = latest.get("metadata") or {}
    events = _events(local)
    ratings = _ratings(local)
    report = str(latest.get("report") or "").strip()
    home = match.get("homeTeam") or metadata.get("homeTeam") or cloud_match.get("home") or ""
    away = match.get("awayTeam") or metadata.get("awayTeam") or cloud_match.get("away") or ""
    general = {
        "available": bool(home or away), "title": f"{home} - {away}" if home or away else "Nessuna partita disponibile",
        "result": f"{latest.get('homeGoals', 0)} - {latest.get('awayGoals', 0)}" if home or away else "—",
        "date": match.get("date") or metadata.get("date") or latest.get("savedAt") or cloud_match.get("created_at"),
        "competition": match.get("category") or metadata.get("category") or cloud_match.get("league") or "Non indicata",
        "status": "Report disponibile" if report else ("Partita disponibile" if home or away else "Dati da completare"),
        "missing": [] if report else (["Report Coach"] if home or away else ["Partita Coach"]),
    }

    voice = cloud.get("voice_observations") or []
    positive_voice = [item for item in voice if item.get("polarity") == "positive"]
    negative_voice = [item for item in voice if item.get("polarity") == "negative" or item.get("priority") in {"high", "critical"}]
    topic_counts = Counter((item.get("tactical_topic") or "general_note", item.get("topic_label") or "Nota staff") for item in voice)
    player_counts = Counter(name for item in voice for name in (item.get("player_names") or []))
    event_counts = Counter(str(item.get("type") or "") for item in events)
    went_well = []
    if positive_voice:
        went_well.append({"title":"Segnali positivi registrati dallo staff", "reason":f"Sono presenti {len(positive_voice)} osservazioni positive Voice Coach.", "evidence":[_source("Osservazioni positive", len(positive_voice), "Voice Coach", "/coach.html")]})
    recoveries = event_counts.get("recupero", 0)
    if recoveries >= 2:
        went_well.append({"title":"Recuperi palla registrati", "reason":f"La timeline Coach contiene {recoveries} recuperi. È un dato inserito dallo staff, non una valutazione automatica.", "evidence":[_source("Recuperi", recoveries, "Coach Timeline", "/coach.html")]})
    valid_votes = [_number(item.get("vote")) for item in ratings if isinstance(item, dict) and _number(item.get("vote")) > 0]
    if valid_votes and sum(valid_votes) / len(valid_votes) >= 6.5:
        went_well.append({"title":"Valutazioni positive nelle pagelle", "reason":f"Media pagelle {sum(valid_votes)/len(valid_votes):.1f} su {len(valid_votes)} giocatori valutati.", "evidence":[_source("Pagelle", len(valid_votes), "Coach", "/coach.html")]})

    improve = []
    for (topic, label), count in topic_counts.most_common(3):
        related = [item for item in negative_voice if (item.get("tactical_topic") or "general_note") == topic]
        if related:
            improve.append({"title":label, "reason":f"Tema segnalato {count} volte; {len(related)} osservazioni hanno polarità negativa o priorità alta.", "level":"alta" if len(related) >= 3 else "media", "evidence":[_source("Osservazioni", count, "Voice Coach", "/coach.html")]})
    for event_type, label in (("palla_persa", "Palle perse"), ("errore_difensivo", "Errori difensivi")):
        count = event_counts.get(event_type, 0)
        if count and len(improve) < 3:
            improve.append({"title":label, "reason":f"La timeline Coach contiene {count} registrazioni di questo tipo.", "level":"media", "evidence":[_source(label, count, "Coach Timeline", "/coach.html")]})
    if general["available"] and not report and len(improve) < 3:
        improve.append({"title":"Completare il post-partita", "reason":"L'ultima partita disponibile non contiene ancora un report Coach.", "level":"operativa", "evidence":[_source("Report mancanti", 1, "Coach", "/coach.html")]})

    patterns = [item for item in (local.get("patterns") or []) if isinstance(item, dict) and item.get("label") and item.get("count")]
    priorities = [{"rank":index + 1, "title":item["title"], "reason":item["reason"], "origin":item["evidence"], "level":item.get("level", "media")} for index, item in enumerate(improve[:3])]
    materials = {
        "reports": len(cloud.get("video_reports") or []) + (1 if report else 0),
        "clips": int(local.get("clips_count") or 0),
        "frames": int(cloud.get("reviewed_frames") or 0),
        "video_sessions": len(cloud.get("video_sessions") or []),
        "ratings": len(ratings),
        "history": int(local.get("history_count") or 0) + len(cloud.get("saved_matches") or []),
    }
    if general["available"] and not report:
        next_action = {"label":"Completa il report Coach", "url":"/coach.html", "reason":"L'ultima partita non ha ancora un report disponibile."}
    elif materials["ratings"] == 0 and general["available"]:
        next_action = {"label":"Completa le pagelle", "url":"/coach.html", "reason":"Non risultano pagelle nell'ultima partita disponibile."}
    elif materials["video_sessions"] and not cloud.get("video_reports"):
        next_action = {"label":"Analizza la Sessione Video", "url":"/video.html", "reason":"Esiste materiale video, ma non risulta ancora un report Video AI."}
    else:
        next_action = {"label":"Apri il Coach", "url":"/coach.html", "reason":"Continua a raccogliere dati reali per rendere più preciso il prossimo briefing."}
    return {
        "title":"Buongiorno Mister.", "subtitle":"Ecco cosa abbiamo imparato dall'ultima settimana.",
        "general":general, "went_well":went_well[:3], "improve":improve[:3],
        "voice": {"total":len(voice), "themes":[{"topic":topic, "label":label, "count":count} for (topic,label),count in topic_counts.most_common(5)], "positive":len(positive_voice), "critical":len(negative_voice), "players":[{"name":name,"count":count} for name,count in player_counts.most_common(5)]},
        "patterns":patterns[:5], "priorities":priorities, "materials":materials, "next_action":next_action,
        "disclaimer":"Le indicazioni derivano esclusivamente dai dati disponibili e devono essere verificate dallo staff tecnico.",
    }


def generate(user_id: int, request: WeeklyBriefingGenerateRequest) -> Dict[str, Any]:
    workspace = knowledge_repository.get_or_create_workspace(user_id)
    week_key = current_week_key()
    sources = {"cloud": weekly_briefing_repository.collect_cloud_sources(user_id, week_key), "local": request.local_sources, "week_key": week_key}
    fingerprint = _fingerprint(sources)
    existing = weekly_briefing_repository.get_week(user_id, week_key)
    if existing and existing["source_fingerprint"] == fingerprint:
        return {"generated": False, "changed": False, "briefing": existing}
    content = build_briefing(sources)
    briefing = weekly_briefing_repository.save_week(user_id, int(workspace["id"]), week_key, fingerprint, sources, content, content["priorities"])
    return {"generated": True, "changed": bool(existing), "briefing": briefing}
