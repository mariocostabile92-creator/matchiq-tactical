import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.services.pattern_intelligence_config import SOURCE_WEIGHTS
from app.services.pattern_intelligence_normalizer import match_phase, normalize_event
from app.services.voice_coach_taxonomy import classify_tactical_topic
from database import fetchall, get_connection, q


def _json(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _match_id(item: Dict[str, Any], index: int) -> str:
    match = item.get("match") or {}
    metadata = item.get("metadata") or {}
    raw = item.get("id") or item.get("match_id") or item.get("savedAt") or match.get("date")
    if raw:
        return f"coach:{raw}"
    seed = "|".join([str(match.get("homeTeam") or metadata.get("homeTeam") or ""),str(match.get("awayTeam") or metadata.get("awayTeam") or ""),str(index)])
    return "coach:" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:14]


def _iso(value: Any) -> str:
    text=str(value or "")
    return text if text else datetime.now(timezone.utc).isoformat()


def _date_value(value: Any) -> datetime:
    text=str(value or "").replace("Z","+00:00")
    try:
        parsed=datetime.fromisoformat(text)
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
    except (TypeError,ValueError):
        return datetime.now(timezone.utc)


def _evidence(source_type: str, source_id: str, match_id: str, topic: str, label: str, summary: str, classification: str, **extra) -> Dict[str, Any]:
    return {
        "source_type":source_type,"source_id":source_id,"match_id":match_id,"topic":topic,
        "topic_label":label,"evidence_summary":summary[:1200],"objective_or_subjective":classification,
        "evidence_weight":SOURCE_WEIGHTS[classification],**extra,
    }


def collect_sources(user_id: int, local_matches: List[Dict[str, Any]], period_days: int) -> Dict[str, Any]:
    now=datetime.now(timezone.utc); start=now-timedelta(days=period_days)
    matches: Dict[str, Dict[str, Any]]={}; evidence=[]
    for index,item in enumerate(local_matches[:100]):
        if not isinstance(item,dict): continue
        match=item.get("match") or {}; metadata=item.get("metadata") or {}; match_id=_match_id(item,index)
        played=_iso(item.get("savedAt") or match.get("date") or metadata.get("date"))
        if _date_value(played)<start: continue
        matches[match_id]={"id":match_id,"date":played,"home":match.get("homeTeam") or metadata.get("homeTeam"),"away":match.get("awayTeam") or metadata.get("awayTeam"),"category":match.get("category") or metadata.get("category"),"formation":match.get("formation") or metadata.get("formation")}
        seen=set()
        for event_index,event in enumerate(item.get("events") or []):
            if not isinstance(event,dict): continue
            if event.get("voiceObservationId"): continue
            normalized=normalize_event(event); source_id=str(event.get("id") or f"{match_id}:event:{event_index}")
            dedup=(match_id,source_id,normalized["topic"],normalized["zone"])
            if dedup in seen: continue
            seen.add(dedup)
            evidence.append(_evidence("coach_event",source_id,match_id,normalized["topic"],normalized["label"],str(event.get("note") or event.get("type") or normalized["label"]),"objective",minute=int(event.get("minute") or 0),event_type=str(event.get("type") or ""),player_id=str(event.get("player") or ""),zone=normalized["zone"],phase=normalized["phase"],formation=match.get("formation") or metadata.get("formation"),polarity=normalized["polarity"],created_at=played))
        for rating_index,rating in enumerate(item.get("ratings") or []):
            if not isinstance(rating,dict): continue
            try: vote=float(rating.get("vote") or 0)
            except (TypeError,ValueError): vote=0
            if vote <= 0: continue
            polarity="positive" if vote>=7 else ("negative" if vote<6 else "neutral")
            topic="positive_behavior" if polarity=="positive" else ("individual_difficulty" if polarity=="negative" else "general_note")
            evidence.append(_evidence("coach_rating",str(rating.get("id") or f"{match_id}:rating:{rating_index}"),match_id,topic,"Valutazione giocatore",f"{rating.get('player') or 'Giocatore'}: voto {vote:g}. {rating.get('note') or ''}".strip(),"staff_observation",player_id=str(rating.get("player") or ""),zone="individual",phase="post_match",formation=match.get("formation") or metadata.get("formation"),polarity=polarity,created_at=played))

    conn=get_connection(); cur=conn.cursor(); cutoff=start.isoformat()
    cur.execute(q("SELECT id,match_id,home,away,league,created_at FROM saved_matches WHERE user_id=? AND created_at>=? ORDER BY created_at,id"),(user_id,cutoff))
    for row in fetchall(cur):
        item=dict(row); match_id=f"saved:{item.get('match_id') or item['id']}"
        matches.setdefault(match_id,{"id":match_id,"date":item.get("created_at"),"home":item.get("home"),"away":item.get("away"),"category":item.get("league"),"formation":None})
    cur.execute(q("""SELECT id,client_id,match_key,match_id,minute,match_phase,tactical_topic,topic_label,zone,polarity,priority,player_ids,original_text,created_at
      FROM voice_coach_observations WHERE user_id=? AND status='confirmed' AND created_at>=? ORDER BY created_at,id"""),(user_id,cutoff))
    for row in fetchall(cur):
        item=dict(row); match_id=str(item.get("match_key") or item.get("match_id") or f"voice:{item['id']}")
        matches.setdefault(match_id,{"id":match_id,"date":item.get("created_at"),"home":None,"away":None,"category":None,"formation":None})
        topic=item.get("tactical_topic") or "general_note"
        evidence.append(_evidence("voice_observation",str(item.get("client_id") or item["id"]),match_id,topic,item.get("topic_label") or topic.replace("_"," ").title(),item.get("original_text") or item.get("topic_label") or "Osservazione staff","staff_observation",minute=int(item.get("minute") or 0),event_type="voice_note",player_id=str((_json(item.get("player_ids"),[]) or [""])[0]),zone=item.get("zone") or "not_specified",phase=item.get("match_phase") or match_phase(item.get("minute")),polarity=item.get("polarity") or "neutral",created_at=item.get("created_at")))
    cur.execute(q("""SELECT id,report_id,video_asset_id,frame_index,frame_time,status,requested_phase,detected_phase,corrected_phase,confidence,notes,created_at
      FROM video_frame_feedback WHERE user_id=? AND created_at>=? AND status NOT IN ('non pertinente','scartato') ORDER BY created_at,id"""),(user_id,cutoff))
    for row in fetchall(cur):
        item=dict(row); text=" ".join(str(item.get(key) or "") for key in ("corrected_phase","detected_phase","requested_phase","notes")); classified=classify_tactical_topic(text)
        if classified["topic"]=="general_note": continue
        match_id=f"video:{item.get('video_asset_id') or item.get('report_id') or item['id']}"
        matches.setdefault(match_id,{"id":match_id,"date":item.get("created_at"),"home":None,"away":None,"category":"Video AI","formation":None})
        evidence.append(_evidence("video_frame",str(item["id"]),match_id,classified["topic"],classified["topic_label"],text or "Frame Video AI classificato","ai_interpretation",minute=int(float(item.get("frame_time") or 0)//60),event_type="video_frame",player_id="",zone=classified["zone"],phase=match_phase(float(item.get("frame_time") or 0)//60),polarity="neutral",created_at=item.get("created_at")))
    cur.execute(q("SELECT id,title,focus,observed_team,frames_analyzed,created_at FROM video_reports WHERE user_id=? AND created_at>=? ORDER BY created_at,id"),(user_id,cutoff))
    for row in fetchall(cur):
        item=dict(row); classified=classify_tactical_topic(" ".join([str(item.get("title") or ""),str(item.get("focus") or "")]))
        if classified["topic"]=="general_note": continue
        match_id=f"video-report:{item['id']}"; matches.setdefault(match_id,{"id":match_id,"date":item.get("created_at"),"home":item.get("observed_team"),"away":None,"category":"Video AI","formation":None})
        evidence.append(_evidence("video_report",str(item["id"]),match_id,classified["topic"],classified["topic_label"],f"Report Video AI: {item.get('title') or classified['topic_label']}","ai_interpretation",minute=None,event_type="video_report",player_id="",zone=classified["zone"],phase="video_analysis",polarity="neutral",created_at=item.get("created_at")))
    conn.close()
    evidence=deduplicate(evidence)
    ordered=sorted(matches.values(),key=lambda item:str(item.get("date") or ""))
    source_types=sorted({item["source_type"] for item in evidence})
    return {"period_start":start.date().isoformat(),"period_end":now.date().isoformat(),"matches":ordered,"evidence":evidence,"source_types":source_types}


def deduplicate(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique={}
    for item in evidence:
        key=(item["source_type"],item["source_id"],item["match_id"],item["topic"],item.get("phase"),item.get("zone"))
        unique[key]=item
    return list(unique.values())


def fingerprint(bundle: Dict[str, Any]) -> str:
    stable={"matches":bundle["matches"],"evidence":bundle["evidence"]}
    raw=json.dumps(stable,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
