from datetime import datetime
from typing import Any, Dict, List


OPPOSITES={"buildup.short":"buildup.direct","buildup.direct":"buildup.short","defence.high_press":"defence.low_block","defence.low_block":"defence.high_press","attack.possession":"buildup.direct"}


def confidence(observed: Dict[str,Any],validated: bool=False) -> str:
    if not observed: return "bassa"
    score=min(3,observed.get("matches",0))+min(2,observed.get("source_classes",0))+min(2,int(observed.get("weighted",0)>=2))+(2 if validated else 0)-min(2,len(observed.get("contradictions") or []))
    return "alta" if score>=7 else ("media" if score>=4 else "bassa")


def alignment(key: str,declared: Dict[str,Any],observed_all: Dict[str,Any],validated: str=None) -> str:
    observed=observed_all.get(key); opposite=observed_all.get(OPPOSITES.get(key,""))
    if not declared and not observed: return "insufficient_data"
    if observed and observed.get("contradictions"): return "contradictory"
    if declared and observed:
        if opposite and opposite.get("weighted",0)>observed.get("weighted",0)*1.25: return "partially_aligned"
        return "aligned"
    if declared and opposite: return "not_aligned"
    return "insufficient_data"


def trend(items: List[Dict[str,Any]]) -> Dict[str,Any]:
    dated=[]
    for item in items:
        try: dated.append((datetime.fromisoformat(str(item.get("occurred_at") or "").replace("Z","+00:00")),item))
        except ValueError: continue
    dated.sort(key=lambda pair:pair[0])
    if len(dated)<4: return {"direction":"non_determinabile","previous":{"count":0},"recent":{"count":len(dated)},"limit":"Servono finestre temporali comparabili."}
    half=len(dated)//2; previous=dated[:half]; recent=dated[-half:]
    if len(previous)!=len(recent): return {"direction":"non_determinabile","previous":{"count":len(previous)},"recent":{"count":len(recent)},"limit":"Finestre non comparabili."}
    p=sum(1 for _,item in previous if item.get("polarity")!="negative"); r=sum(1 for _,item in recent if item.get("polarity")!="negative")
    previous_polarities={item.get("polarity") for _,item in previous}; recent_polarities={item.get("polarity") for _,item in recent}
    direction="in_trasformazione" if previous_polarities!=recent_polarities and p==r else ("stabile" if p==r else ("in_aumento" if r>p else "in_diminuzione"))
    return {"direction":direction,"previous":{"count":len(previous),"supporting":p,"from":previous[0][0].isoformat(),"to":previous[-1][0].isoformat()},"recent":{"count":len(recent),"supporting":r,"from":recent[0][0].isoformat(),"to":recent[-1][0].isoformat()},"limit":"Confronto descrittivo; non dimostra causalita."}
