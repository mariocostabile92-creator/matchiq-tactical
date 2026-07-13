from typing import Any, Dict, List


def evaluate(phase: str, context: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    reliable=sum(1 for item in sources if item.get("reliability_level") in {"media","alta"})
    matches=len({str(item.get("match_id")) for item in sources if item.get("match_id")})
    has_roster=bool(context.get("lineup") or context.get("players") or context.get("bench"))
    has_live=phase not in {"live_match","halftime"} or context.get("minute") is not None
    limitations=[]
    if reliable < 2: limitations.append("Poche fonti affidabili disponibili.")
    if matches < 2 and phase in {"pre_match","weekly"}: limitations.append("Storico partite ancora limitato.")
    if not has_roster: limitations.append("Rosa o disponibilita giocatori non complete.")
    if not has_live: limitations.append("Minuto o contesto live non disponibili.")
    if reliable == 0: state="non_valutabile"
    elif reliable < 3 or not has_live: state="parzialmente_valutabile"
    elif reliable >= 6 and (matches >= 2 or phase in {"live_match","halftime"}): state="fortemente_supportato"
    else: state="valutabile"
    return {"state":state,"reliable_sources":reliable,"match_count":matches,"has_roster":has_roster,"limitations":limitations}
