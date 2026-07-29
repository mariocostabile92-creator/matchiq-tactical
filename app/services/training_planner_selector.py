from copy import deepcopy
from typing import Any,Dict,List


def _score(drill: Dict[str,Any],priority: Dict[str,Any],settings: Dict[str,Any]) -> int:
    score=0
    if drill["tactical_theme"]==priority["topic"]: score+=70
    if int(drill["min_players"])<=settings["players"]<=int(drill["max_players"]): score+=12
    if int(drill["goalkeepers"])<=settings["goalkeepers"]: score+=6
    if drill["intensity"]==settings["intensity"]: score+=5
    if settings["category"] in (drill.get("recommended_category") or []): score+=7
    return score


def select(priorities: List[Dict[str,Any]],library: List[Dict[str,Any]],settings: Dict[str,Any]) -> List[Dict[str,Any]]:
    selected=[]; used=set()
    for priority in priorities:
        ranked=sorted((( _score(item,priority,settings),item) for item in library if item["id"] not in used),key=lambda row:(row[0],row[1]["id"]),reverse=True)
        matches=[item for score,item in ranked if score>=70][:2]
        drills=[]
        for item in matches:
            used.add(item["id"]); drill=deepcopy(item); drill["players"]=min(settings["players"],drill["max_players"]); drill["selected_duration"]=drill["duration"]; drill["selected_intensity"]=settings["intensity"] if settings["intensity"] in {"bassa","media","alta"} else drill["intensity"]; drills.append(drill)
        selected.append({
            "priority_id":priority.get("priority_id"),
            "topic":priority["topic"],
            "title":priority["title"],
            "reason":priority["reason"],
            "reliability":priority["level"],
            "priority_level":priority.get("priority_level"),
            "confidence":priority.get("confidence"),
            "phase":priority.get("phase"),
            "sources":priority["sources"],
            "references":priority.get("references") or {},
            "drills":drills,
        })
    return selected


def build_week(priorities: List[Dict[str,Any]],days: List[str],settings: Dict[str,Any]) -> Dict[str,Any]:
    sessions=[{"day":day,"objective":"","theme":"","duration":settings["session_duration"],"intensity":settings["intensity"],"drills":[],"notes":"","status":"proposta_ai"} for day in days]
    if not sessions: return {"sessions":[]}
    for index,priority in enumerate(priorities):
        session=sessions[index%len(sessions)]; session["objective"]=priority["title"] if not session["objective"] else f"{session['objective']} + {priority['title']}"; session["theme"]=priority["topic"] if not session["theme"] else f"{session['theme']}, {priority['topic']}"; session["drills"].extend(priority["drills"])
    for session in sessions:
        if not session["drills"]: session["status"]="bozza"
    return {"title":"Piano settimanale MatchIQ","sessions":sessions,"priorities":priorities,"disclaimer":"Le proposte sono un supporto decisionale basato sui dati disponibili. Lo staff decide sempre contenuti e carichi definitivi."}


def build_priority_drafts(
    proposals: List[Dict[str,Any]],
    settings: Dict[str,Any],
) -> Dict[str,Any]:
    sessions=[]
    for proposal in proposals:
        priority_id=str(proposal.get("priority_id") or "")
        references=proposal.get("references") or {
            "canonical_match_ids":[],
            "pattern_ids":[],
            "evidence_ids":[],
        }
        sessions.append({
            "session_id":f"session_{priority_id}",
            "title":f"Seduta: {proposal['title']}",
            "day":"Da programmare",
            "objective":proposal["title"],
            "why":proposal["reason"],
            "theme":proposal["topic"],
            "duration":settings["session_duration"],
            "players":settings["players"],
            "goalkeepers":settings["goalkeepers"],
            "intensity":settings["intensity"],
            "drills":proposal["drills"],
            "notes":"",
            "status":"proposta_ai",
            "priority_ids":[priority_id],
            "references":references,
        })
    return {
        "contract":"weekly-priority-training-draft-v1",
        "title":"Bozze allenamento dalle priorita",
        "sessions":sessions,
        "priorities":proposals,
        "disclaimer":"Le proposte sono bozze basate su priorita confermate. Lo staff modifica e conferma sempre contenuti e carichi definitivi.",
    }
