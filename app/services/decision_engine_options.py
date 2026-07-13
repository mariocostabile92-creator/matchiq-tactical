from typing import Any, Dict, List

from app.services.decision_engine_identity import alignment
from app.services.decision_engine_policy import cautious


TEMPLATES = {
 "pre_match":[("pressing_height","Pressione selettiva","Valutare una pressione orientata sui riferimenti piu affidabili.","medium"),("initial_shape","Struttura iniziale prudente","Mantenere distanze corte e verificare l'uscita avversaria nei primi minuti.","conservative")],
 "live_match":[("side_protection","Proteggere il lato critico","Ridurre lo spazio sul lato piu esposto senza perdere l'uscita offensiva.","medium"),("pressing_adjustment","Ricalibrare la pressione","Scegliere trigger piu chiari e abbassare l'aggressivita se le distanze aumentano.","conservative")],
 "halftime":[("priority_correction","Correzione prioritaria all'intervallo","Intervenire sul tema ricorrente piu supportato dagli eventi registrati.","medium"),("positive_maintenance","Conservare cio che funziona","Mantenere il principio efficace e correggere soltanto le coperture fragili.","conservative")],
 "post_match":[("decision_review","Rivedere la decisione chiave","Confrontare intenzione, applicazione ed eventi successivi senza attribuire causalita certa.","medium"),("training_followup","Portare il tema in allenamento","Trasformare il segnale piu affidabile in una proposta di lavoro verificabile.","conservative")],
 "weekly":[("weekly_priority","Priorita tecnica della settimana","Concentrare il carico sul pattern piu ricorrente e confermato.","medium"),("session_focus","Seduta di consolidamento","Conservare un blocco prudente per verificare il principio prima di aumentare la complessita.","conservative")],
}


def _available_bench(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    unavailable={str(item) for item in context.get("unavailable_players",[])}
    used={str(item) for item in context.get("substituted_players",[])}
    return [p for p in context.get("bench",[]) if str(p.get("id") or p.get("name")) not in unavailable|used]


def generate(phase: str, situation: Dict[str, Any], eligibility: Dict[str, Any], sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if eligibility["state"] == "non_valutabile": return []
    context=situation["context"]; candidates=list(TEMPLATES[phase])
    if phase=="live_match" and _available_bench(context):
        player=_available_bench(context)[0]
        candidates.insert(1,("substitution","Valutare una sostituzione",f"Considerare {player.get('name') or 'un giocatore disponibile'} solo dopo verifica dello staff.","medium"))
    options=[]
    for kind,title,summary,profile in candidates[:3]:
        confidence="alta" if eligibility["state"]=="fortemente_supportato" else ("media" if eligibility["state"]=="valutabile" else "bassa")
        risks=["La modifica puo alterare equilibri che i dati disponibili non descrivono completamente."]
        if kind=="pressing_adjustment" and context.get("fatigue") in {"high","alta",True}: risks.append("La fatica segnalata puo rendere fragile una pressione piu aggressiva.")
        item={"option_type":kind,"title":title,"summary":cautious(summary),"tactical_changes":[summary],"player_changes":[],"formation_changes":[],"benefits":["Rende esplicita una priorita osservabile.","Permette allo staff di verificare rapidamente il segnale."],"risks":risks[:3],"prerequisites":["Conferma dello staff tecnico prima dell'applicazione."],"confidence_level":confidence,"suitability_score":78 if profile=="medium" else 64,"identity_alignment":"non_valutabile","evidence_summary":f"Proposta basata su {eligibility['reliable_sources']} fonti affidabili.","limitations":eligibility["limitations"],"status":"conservative" if profile=="conservative" else "proposed"}
        if kind=="substitution": item["player_changes"]=[{"player_in":_available_bench(context)[0].get("name"),"requires_staff_confirmation":True}]
        item["identity_alignment"]=alignment(item,sources); options.append(item)
    return options
