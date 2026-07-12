import hashlib
import json
from collections import defaultdict
from typing import Any,Dict,List

from app.repositories import knowledge_repository,pattern_intelligence_repository,weekly_briefing_repository,voice_coach_repository
from app.services.pattern_intelligence_normalizer import normalize_event
from app.services.voice_coach_taxonomy import classify_tactical_topic


TOPIC_FALLBACK={"lost_ball":"negative_transition","right_flank":"right_flank","left_flank":"right_flank","individual_difficulty":"duels","positive_behavior":"recovery"}


def _source(module: str,label: str,count: int,url: str,kind: str) -> Dict[str,Any]:
    return {"module":module,"label":label,"count":count,"url":url,"kind":kind}


def collect(user_id: int,local_context: Dict[str,Any]) -> Dict[str,Any]:
    workspace=knowledge_repository.get_or_create_workspace(user_id); knowledge_id=int(workspace["id"])
    team=knowledge_repository.get_profile("knowledge_team_profiles",knowledge_id,knowledge_repository.TEAM_COLUMNS)
    roster=knowledge_repository.list_roster(knowledge_id)
    candidates=[]
    pattern_data=pattern_intelligence_repository.list_patterns(user_id,{"page":1,"page_size":50})
    for item in pattern_data["items"]:
        if item["status"] not in {"established","confirmed_by_staff","monitoring"} or item.get("contradictory") or int(item.get("confidence_score") or 0)<55: continue
        candidates.append({"topic":item["canonical_topic"],"title":item["title"],"reason":item["normalized_summary"],"level":item["confidence_level"],"rank_score":90+int(item["confidence_score"]),"sources":[_source("Pattern Intelligence",item["title"],int(item["matches_count"]),f"/pattern-intelligence.html?pattern={item['id']}","derived")],"pattern_id":item["id"]})
    weekly=weekly_briefing_repository.get_latest(user_id)
    if weekly:
        for priority in weekly.get("priorities") or []:
            classified=classify_tactical_topic(" ".join([str(priority.get("title") or ""),str(priority.get("reason") or "")]))
            if classified["topic"]=="general_note": continue
            candidates.append({"topic":classified["topic"],"title":priority.get("title") or classified["topic_label"],"reason":priority.get("reason") or "Priorità del Weekly AI Briefing.","level":priority.get("level") or "media","rank_score":75,"sources":[_source("Weekly AI Briefing",priority.get("title") or classified["topic_label"],1,"/weekly-briefing.html","derived")]})
    observations=[]
    conn=voice_coach_repository.get_connection(); cur=conn.cursor()
    from database import fetchall,q
    cur.execute(q("SELECT tactical_topic,topic_label,match_key,polarity,priority FROM voice_coach_observations WHERE user_id=? AND status='confirmed' ORDER BY created_at DESC LIMIT 200"),(user_id,)); observations=fetchall(cur); conn.close()
    voice_groups=defaultdict(list)
    for item in observations: voice_groups[item.get("tactical_topic") or "general_note"].append(item)
    for topic,items in voice_groups.items():
        distinct=len({str(x.get("match_key")) for x in items});
        if topic=="general_note" or len(items)<3 or distinct<2: continue
        label=items[0].get("topic_label") or topic.replace("_"," ").title(); candidates.append({"topic":topic,"title":label,"reason":f"Voice Coach: {len(items)} osservazioni in {distinct} partite.","level":"media","rank_score":55+min(20,len(items)),"sources":[_source("Voice Coach",label,len(items),"/coach.html","staff_observation")]})
    history=local_context.get("history") if isinstance(local_context.get("history"),list) else []
    coach_groups=defaultdict(lambda:{"count":0,"matches":set(),"label":""})
    for index,match in enumerate(history[:50]):
        if not isinstance(match,dict): continue
        match_id=str(match.get("id") or index)
        for event in match.get("events") or []:
            if not isinstance(event,dict) or event.get("voiceObservationId"): continue
            normalized=normalize_event(event); group=coach_groups[normalized["topic"]]; group["count"]+=1; group["matches"].add(match_id); group["label"]=normalized["label"]
    for topic,data in coach_groups.items():
        if data["count"]<3 or len(data["matches"])<2: continue
        candidates.append({"topic":topic,"title":data["label"],"reason":f"Coach: {data['count']} eventi in {len(data['matches'])} partite.","level":"media","rank_score":60+min(15,data["count"]),"sources":[_source("Coach",data["label"],data["count"],"/coach.html","objective")]})
    merged={}
    for item in sorted(candidates,key=lambda value:value["rank_score"],reverse=True):
        topic=TOPIC_FALLBACK.get(item["topic"],item["topic"]); item["topic"]=topic
        if topic not in merged: merged[topic]=item
        else:
            merged[topic]["sources"].extend(source for source in item["sources"] if source not in merged[topic]["sources"]); merged[topic]["rank_score"]+=10; merged[topic]["reason"]+=" "+item["reason"]
    priorities=sorted(merged.values(),key=lambda value:(len(value["sources"]),value["rank_score"]),reverse=True)[:3]
    constraints={"category":team.get("category"),"physical_level":team.get("physical_level"),"technical_level":team.get("technical_level"),"player_count":team.get("player_count") or len(roster),"goalkeeper_count":team.get("goalkeeper_count") or len([p for p in roster if str(p.get("role") or "").lower() in {"portiere","gk"}]),"formations":team.get("formations_used") or [],"roster_count":len(roster)}
    return {"workspace":workspace,"priorities":priorities,"constraints":constraints,"sources_count":sum(len(item["sources"]) for item in priorities),"pattern_run_id":pattern_data.get("run",{}).get("id") if pattern_data.get("run") else None,"weekly_id":weekly.get("id") if weekly else None}


def fingerprint(bundle: Dict[str,Any],request_data: Dict[str,Any]) -> str:
    stable={"priorities":bundle["priorities"],"constraints":bundle["constraints"],"request":request_data}
    raw=json.dumps(stable,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
