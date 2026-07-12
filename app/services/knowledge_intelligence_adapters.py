import json
from typing import Any, Dict, List

from database import fetchall, get_connection, q


def _load(value: Any,fallback: Any=None) -> Any:
    if isinstance(value,(dict,list)): return value
    try: return json.loads(value) if value else ({} if fallback is None else fallback)
    except (TypeError,ValueError): return {} if fallback is None else fallback


def _rows(sql: str,params: tuple=()) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor()
    try: cur.execute(q(sql),params); rows=[dict(row) for row in fetchall(cur)]
    except Exception as exc:
        message=str(exc).lower()
        if "no such table" in message or "does not exist" in message: rows=[]
        else: raise
    finally: conn.close()
    return rows


def foundation(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]
    coaches=_rows("SELECT * FROM knowledge_coach_profiles WHERE knowledge_id=?",(workspace_id,))
    teams=_rows("SELECT * FROM knowledge_team_profiles WHERE knowledge_id=?",(workspace_id,))
    players=_rows("SELECT * FROM knowledge_roster_players WHERE knowledge_id=?",(workspace_id,))
    for row in coaches:
        nodes.append({"node_type":"coach_profile","source_type":"coach_profile","source_id":str(row["id"]),"title":row.get("coach_name") or "Profilo allenatore","summary":row.get("playing_philosophy") or "Profilo tecnico dello staff.","source_updated_at":row.get("updated_at"),"reliability_level":"alta","validation_state":"staff_source","nature":"decisione_staff","metadata":{"preferred_formation":row.get("preferred_formation"),"alternative_formation":row.get("alternative_formation")},"tags":["staff","filosofia"]})
    for row in teams:
        nodes.append({"node_type":"team_profile","source_type":"team_profile","source_id":str(row["id"]),"team_profile_id":row["id"],"title":"Profilo squadra","summary":row.get("notes") or row.get("playing_principles") or "Profilo tecnico della squadra.","source_updated_at":row.get("updated_at"),"reliability_level":"alta","validation_state":"staff_source","nature":"decisione_staff","metadata":{"category":row.get("category"),"formations":_load(row.get("formations_used"),[])},"tags":["squadra",row.get("category") or ""]})
    for row in players:
        nodes.append({"node_type":"player","source_type":"roster_player","source_id":str(row["id"]),"player_id":str(row["id"]),"player_name":row.get("name"),"title":row.get("name") or "Giocatore","summary":" - ".join(x for x in (row.get("role"),row.get("coach_notes")) if x),"source_updated_at":row.get("updated_at"),"reliability_level":"alta","validation_state":"staff_source","nature":"decisione_staff","metadata":{"role":row.get("role"),"preferred_foot":row.get("preferred_foot")},"tags":["rosa",row.get("role") or ""]})
    return {"module":"knowledge","nodes":nodes,"edges":[]}


def coach(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]
    for row in _rows("SELECT * FROM saved_matches WHERE user_id=? ORDER BY created_at",(user_id,)):
        title=f"{row.get('home') or 'Casa'} - {row.get('away') or 'Trasferta'}"
        nodes.append({"node_type":"match","source_type":"saved_match","source_id":str(row["id"]),"match_id":str(row.get("match_id") or row["id"]),"title":title,"summary":row.get("league") or "Partita salvata","occurred_at":row.get("created_at"),"source_updated_at":row.get("created_at"),"reliability_level":"alta","validation_state":"source_confirmed","nature":"oggettiva","team_name":row.get("home"),"competition":row.get("league"),"opponent":row.get("away"),"metadata":{"home":row.get("home"),"away":row.get("away"),"league":row.get("league")},"tags":["partita",row.get("league") or ""]})
    return {"module":"coach","nodes":nodes,"edges":[]}


def voice(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]; edges=[]
    observations=_rows("SELECT * FROM voice_coach_observations WHERE user_id=? ORDER BY created_at",(user_id,))
    for row in observations:
        source_id=str(row.get("client_id") or row["id"]); players=_load(row.get("player_ids"),[]); names=_load(row.get("player_names"),[])
        nodes.append({"node_type":"voice_observation","source_type":"voice_observation","source_id":source_id,"match_id":str(row.get("match_id") or row.get("match_key") or ""),"player_id":str(players[0]) if players else None,"player_name":names[0] if names else None,"title":row.get("topic_label") or "Osservazione Voice Coach","summary":row.get("normalized_summary") or row.get("original_text") or "","occurred_at":row.get("created_at"),"source_updated_at":row.get("updated_at"),"reliability_level":"alta" if row.get("status")=="confirmed" else "bassa","validation_state":row.get("status") or "to_verify","nature":"osservazione_staff","polarity":row.get("polarity"),"tactical_topic":row.get("tactical_topic"),"zone":row.get("zone"),"metadata":{"minute":row.get("minute"),"priority":row.get("priority"),"match_key":row.get("match_key"),"player_names":names},"tags":[row.get("tactical_topic") or "",row.get("zone") or ""]})
        if row.get("match_id") or row.get("match_key"): edges.append({"from":("voice_observation","voice_observation",source_id),"to_match":str(row.get("match_id") or row.get("match_key")),"relation":"occurred_in","explanation":"Osservazione registrata durante la partita."})
        for player_id in players: edges.append({"from":("voice_observation","voice_observation",source_id),"to":("player","roster_player",str(player_id).replace("knowledge:","")),"relation":"involves_player","explanation":"Giocatore indicato esplicitamente dallo staff."})
    for row in _rows("SELECT * FROM voice_coach_match_themes WHERE user_id=? ORDER BY created_at",(user_id,)):
        sid=str(row["id"]); nodes.append({"node_type":"voice_match_theme","source_type":"voice_match_theme","source_id":sid,"match_id":str(row.get("match_key") or ""),"title":row.get("label") or "Tema partita","summary":f"{row.get('count') or 0} osservazioni collegate.","occurred_at":row.get("created_at"),"source_updated_at":row.get("updated_at"),"reliability_level":"media","validation_state":row.get("status") or "active","nature":"dato_derivato","polarity":row.get("polarity"),"tactical_topic":row.get("topic"),"zone":row.get("zone"),"metadata":{"count":row.get("count"),"first_minute":row.get("first_minute"),"last_minute":row.get("last_minute")},"tags":[row.get("topic") or "",row.get("zone") or ""]})
        for obs_id in _load(row.get("source_observation_ids"),[]): edges.append({"from":("voice_match_theme","voice_match_theme",sid),"to":("voice_observation","voice_observation",str(obs_id)),"relation":"includes","explanation":"Tema costruito da osservazioni confermate."})
        if row.get("match_key"): edges.append({"from":("voice_match_theme","voice_match_theme",sid),"to_match":str(row["match_key"]),"relation":"occurred_in","explanation":"Tema osservato durante la partita."})
    return {"module":"voice_coach","nodes":nodes,"edges":edges}


def patterns(user_id: int,workspace_id: int) -> Dict[str,Any]:
    runs=_rows("SELECT * FROM pattern_intelligence_runs WHERE user_id=? AND status='completed' ORDER BY created_at DESC LIMIT 1",(user_id,))
    if not runs: return {"module":"pattern_intelligence","nodes":[],"edges":[]}
    run=runs[0]; nodes=[]; edges=[]
    rows=_rows("SELECT * FROM pattern_intelligence_patterns WHERE run_id=? ORDER BY id",(run["id"],))
    for row in rows:
        sid=f"{row.get('canonical_topic')}:{row.get('phase')}:{row.get('zone')}:{row.get('context_player_id') or ''}"
        nodes.append({"node_type":"historical_pattern","source_type":"pattern","source_id":sid,"title":row.get("title") or "Pattern","summary":row.get("normalized_summary") or "","occurred_at":row.get("last_seen_at") or row.get("created_at"),"source_updated_at":row.get("updated_at"),"reliability_level":row.get("confidence_level") or "bassa","validation_state":row.get("status") or "candidate","nature":"pattern_confermato" if row.get("status") in {"established","confirmed_by_staff","resolved"} else "pattern_candidato","polarity":row.get("polarity"),"tactical_topic":row.get("canonical_topic"),"zone":row.get("zone"),"player_id":row.get("context_player_id"),"metadata":{"source_record_id":row["id"],"run_id":run["id"],"trend":row.get("trend_direction"),"matches_count":row.get("matches_count"),"contradictory":bool(row.get("contradictory"))},"tags":[row.get("canonical_topic") or "",row.get("phase") or "",row.get("zone") or ""]})
        evidence=_rows("SELECT * FROM pattern_intelligence_evidence WHERE pattern_id=? ORDER BY id",(row["id"],))
        for item in evidence:
            eid=f"{sid}:{item.get('source_type')}:{item.get('source_id')}"; nodes.append({"node_type":"evidence","source_type":"pattern_evidence","source_id":eid,"match_id":str(item.get("match_id") or ""),"player_id":item.get("player_id"),"title":"Evidenza: "+str(row.get("title") or "Pattern"),"summary":item.get("evidence_summary") or "","occurred_at":item.get("created_at"),"source_updated_at":item.get("created_at"),"reliability_level":"alta" if float(item.get("evidence_weight") or 0)>=1 else "media","validation_state":"source_confirmed","nature":item.get("objective_or_subjective") or "dato_derivato","polarity":item.get("polarity"),"tactical_topic":item.get("topic"),"zone":item.get("zone"),"metadata":{"minute":item.get("minute"),"event_type":item.get("event_type")},"tags":[item.get("topic") or "",item.get("zone") or ""]}); edges.append({"from":("historical_pattern","pattern",sid),"to":("evidence","pattern_evidence",eid),"relation":"supported_by" if not row.get("contradictory") else "contradicts","explanation":"Evidenza persistente del motore Pattern."})
    return {"module":"pattern_intelligence","nodes":nodes,"edges":edges}


def weekly(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]; edges=[]
    for row in _rows("SELECT * FROM weekly_ai_briefings WHERE user_id=? ORDER BY created_at",(user_id,)):
        content=_load(row.get("content")); priorities=_load(row.get("priorities"),[])
        nodes.append({"node_type":"weekly_briefing","source_type":"weekly_briefing","source_id":str(row.get("week_key") or row["id"]),"title":content.get("title") or f"Briefing settimana {row.get('week_key')}","summary":content.get("summary") or content.get("subtitle") or "Briefing settimanale dello staff.","occurred_at":row.get("created_at"),"source_updated_at":row.get("updated_at"),"reliability_level":"media","validation_state":"generated","nature":"interpretazione_ai","metadata":{"record_id":row["id"],"week_key":row.get("week_key"),"priorities":priorities,"sources":_load(row.get("sources"))},"tags":["briefing",*[str(p.get("topic") or p.get("title") or "") for p in priorities[:5]]]})
        briefing_id=str(row.get("week_key") or row["id"])
        for priority in priorities:
            topic=priority.get("topic")
            if topic: edges.append({"from":("weekly_briefing","weekly_briefing",briefing_id),"to_pattern_topic":topic,"relation":"summarizes","explanation":"Il briefing riassume una priorita emersa dai pattern."})
    return {"module":"weekly_briefing","nodes":nodes,"edges":edges}


def training(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]; edges=[]
    for row in _rows("SELECT * FROM training_plans WHERE user_id=? ORDER BY created_at",(user_id,)):
        current=_load(row.get("current_plan")); original=_load(row.get("original_plan")); priorities=_load(row.get("priorities"),[]); plan_id=str(row["id"])
        nodes.append({"node_type":"training_plan","source_type":"training_plan","source_id":plan_id,"title":current.get("title") or "Piano settimanale MatchIQ","summary":"; ".join(str(p.get("title") or "") for p in priorities[:3]),"occurred_at":row.get("created_at"),"source_updated_at":row.get("updated_at"),"reliability_level":"media","validation_state":row.get("status") or "proposta_ai","nature":"decisione_staff" if row.get("status") in {"accettata","modificata","completata"} else "suggerimento","metadata":{"week_key":row.get("week_key"),"version":row.get("version"),"has_staff_changes":current!=original,"priority_topics":[p.get("topic") for p in priorities]},"tags":["allenamento",*[str(p.get("topic") or "") for p in priorities]]})
        for index,session in enumerate(current.get("sessions") or []):
            session_id=f"{plan_id}:{index}"; nodes.append({"node_type":"training_session","source_type":"training_session","source_id":session_id,"title":f"Seduta {session.get('day') or index+1}","summary":session.get("objective") or session.get("theme") or "","occurred_at":row.get("updated_at"),"source_updated_at":row.get("updated_at"),"reliability_level":"media","validation_state":session.get("status") or row.get("status") or "proposta_ai","nature":"decisione_staff" if session.get("status") in {"accettata","modificata","completata"} else "suggerimento","tactical_topic":session.get("theme"),"metadata":{"plan_id":row["id"],"day":session.get("day"),"duration":session.get("duration"),"intensity":session.get("intensity")},"tags":[session.get("theme") or ""]}); edges.append({"from":("training_session","training_session",session_id),"to":("training_plan","training_plan",plan_id),"relation":"belongs_to","explanation":"Seduta inclusa nel piano settimanale."})
            for drill_index,drill in enumerate(session.get("drills") or []):
                drill_id=f"{session_id}:{drill.get('id') or drill_index}"; nodes.append({"node_type":"training_exercise","source_type":"training_exercise","source_id":drill_id,"title":drill.get("title") or "Esercitazione","summary":drill.get("objective") or drill.get("description") or "","occurred_at":row.get("updated_at"),"source_updated_at":row.get("updated_at"),"reliability_level":drill.get("reliability_level") or "media","validation_state":session.get("status") or "proposta_ai","nature":"suggerimento","tactical_topic":drill.get("tactical_theme"),"metadata":{"plan_id":row["id"],"session_id":session_id,"duration":drill.get("selected_duration") or drill.get("duration")},"tags":[drill.get("tactical_theme") or ""]}); edges.append({"from":("training_session","training_session",session_id),"to":("training_exercise","training_exercise",drill_id),"relation":"includes","explanation":"Esercitazione selezionata per la seduta."})
        for priority in priorities:
            if priority.get("topic"): edges.append({"from":("training_plan","training_plan",plan_id),"to_pattern_topic":priority["topic"],"relation":"generated_from","explanation":"Piano motivato da una priorita tecnica persistente."})
    return {"module":"training_planner","nodes":nodes,"edges":edges}


def video(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]; edges=[]
    for row in _rows("SELECT * FROM video_assets WHERE user_id=? ORDER BY created_at",(user_id,)):
        metadata=_load(row.get("metadata")); sid=str(row["id"]); nodes.append({"node_type":"video_session","source_type":"video_asset","source_id":sid,"title":row.get("title") or row.get("file_name") or "Sessione Video","summary":"Sessione video persistente.","occurred_at":row.get("created_at"),"source_updated_at":row.get("updated_at"),"reliability_level":"alta","validation_state":row.get("status") or "ready","nature":"oggettiva","team_name":row.get("club_name"),"match_id":str(metadata.get("match_id")) if metadata.get("match_id") else None,"metadata":{"category":row.get("category"),"source_type":row.get("source_type"),"rights_confirmed":bool(row.get("rights_confirmed"))},"tags":["video",row.get("category") or ""]})
    for row in _rows("SELECT * FROM video_frame_feedback WHERE user_id=? ORDER BY created_at",(user_id,)):
        sid=str(row["id"]); topic=row.get("corrected_phase") or row.get("detected_phase") or row.get("requested_phase"); nodes.append({"node_type":"video_frame","source_type":"video_frame","source_id":sid,"title":f"Frame {row.get('frame_index') or 0}","summary":row.get("notes") or topic or "Frame Video AI","occurred_at":row.get("created_at"),"source_updated_at":row.get("created_at"),"reliability_level":"alta" if row.get("status") in {"confirmed","accepted"} else "media","validation_state":row.get("status") or "to_verify","nature":"interpretazione_ai","tactical_topic":topic,"metadata":{"frame_time":row.get("frame_time"),"confidence":row.get("confidence"),"report_id":row.get("report_id")},"tags":[topic or ""]})
        if row.get("video_asset_id"): edges.append({"from":("video_frame","video_frame",sid),"to":("video_session","video_asset",str(row["video_asset_id"])),"relation":"belongs_to","explanation":"Frame estratto dalla sessione video."})
        if row.get("report_id"): edges.append({"from":("video_frame","video_frame",sid),"to":("video_report","video_report",str(row["report_id"])),"relation":"belongs_to","explanation":"Frame utilizzato nel report video."})
    for row in _rows("SELECT * FROM video_reports WHERE user_id=? ORDER BY created_at",(user_id,)):
        payload=_load(row.get("payload")); sid=str(row["id"]); nodes.append({"node_type":"video_report","source_type":"video_report","source_id":sid,"title":row.get("title") or "Report Video AI","summary":" - ".join(x for x in (row.get("focus"),row.get("observed_team")) if x),"occurred_at":row.get("created_at"),"source_updated_at":row.get("created_at"),"reliability_level":"media","validation_state":"generated","nature":"interpretazione_ai","tactical_topic":row.get("focus"),"team_name":row.get("club_name") or row.get("observed_team"),"match_id":str(payload.get("match_id")) if payload.get("match_id") else None,"metadata":{"frames_analyzed":row.get("frames_analyzed"),"report_style":row.get("report_style"),"video_asset_id":payload.get("video_asset_id")},"tags":["video_report",row.get("focus") or ""]})
        if payload.get("video_asset_id"): edges.append({"from":("video_report","video_report",sid),"to":("video_session","video_asset",str(payload["video_asset_id"])),"relation":"generated_from","explanation":"Report generato dalla sessione video collegata."})
        if payload.get("match_id"): edges.append({"from":("video_report","video_report",sid),"to_match":str(payload["match_id"]),"relation":"occurred_in","explanation":"Report collegato esplicitamente alla partita."})
    return {"module":"video_ai","nodes":nodes,"edges":edges}


def scout(user_id: int,workspace_id: int) -> Dict[str,Any]:
    nodes=[]; edges=[]
    for row in _rows("SELECT * FROM scout_reports WHERE user_id=? ORDER BY created_at",(user_id,)):
        payload=_load(row.get("payload")); sid=str(row["id"]); player_id=str(payload.get("player_id")) if payload.get("player_id") else None; nodes.append({"node_type":"scout_report","source_type":"scout_report","source_id":sid,"match_id":str(row.get("match_id")) if row.get("match_id") else None,"player_id":player_id,"player_name":payload.get("player_name"),"title":row.get("title") or "Report Scout","summary":payload.get("summary") or payload.get("note") or "Report scouting persistente.","occurred_at":row.get("created_at"),"source_updated_at":row.get("created_at"),"reliability_level":"media","validation_state":"staff_source","nature":"osservazione_staff","metadata":{"report_type":row.get("report_type")},"tags":["scout"]})
        if player_id: edges.append({"from":("scout_report","scout_report",sid),"to":("player","roster_player",player_id.replace("knowledge:","")),"relation":"involves_player","explanation":"Report associato al giocatore salvato."})
    return {"module":"scout","nodes":nodes,"edges":edges}


ADAPTERS={"knowledge":foundation,"coach":coach,"voice_coach":voice,"pattern_intelligence":patterns,"weekly_briefing":weekly,"training_planner":training,"video_ai":video,"scout":scout}
