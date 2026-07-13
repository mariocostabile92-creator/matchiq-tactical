from typing import Any, Dict, List


def _titles(sources: List[Dict[str,Any]],limit: int=3) -> List[str]:
    return [source["title"] for source in sources[:limit]]


def build(question: str,query: Dict[str,Any],retrieval: Dict[str,Any],assessment: Dict[str,Any],sources: List[Dict[str,Any]]) -> Dict[str,Any]:
    if query.get("needs_clarification"):
        return {"answer_type":"clarification","direct_answer":query["clarification_question"],"why":[],"meaning":"Serve una sola precisazione per interrogare la memoria corretta.","options":["Mostra tutto cio che e disponibile"],"next_action":None,"claims":[],"contradictions":[],"provider":"deterministic"}
    if assessment["level"]=="insufficiente":
        return {"answer_type":"insufficient","direct_answer":"Non ho ancora dati sufficienti per rispondere in modo affidabile.","why":[],"meaning":"La memoria tecnica non contiene fonti pertinenti sufficienti. Non completo la risposta con conoscenza calcistica generica.","options":["Registra osservazioni in Coach o Voice Coach","Collega partite, report o Video AI alla Knowledge"],"next_action":{"label":"Apri Knowledge","url":"/knowledge.html"},"claims":[],"contradictions":[],"provider":"deterministic"}
    titles=_titles(sources); topic=(query.get("themes") or [None])[0] or "il tema richiesto"; partial=assessment["level"]=="parziale"
    if query["intent"]=="context_comparison":
        direct=f"Con i dati disponibili posso descrivere differenze su {topic}, ma il campione non consente di stabilire in assoluto quale soluzione sia migliore."
    elif query["intent"]=="temporal_comparison":
        direct=f"La memoria mostra segnali utili sull'andamento di {topic}; la lettura resta {'parziale' if partial else 'sufficientemente supportata'} e non dimostra un rapporto causale."
    elif query["intent"]=="pattern_explanation":
        direct=f"MatchIQ collega {topic} a {len(sources)} fonti indicizzate. Il pattern va letto come ricorrenza documentata, non come causa certa."
    else:
        direct=f"Ho trovato {len(sources)} fonti pertinenti su {topic}. " + ("Il quadro e ancora parziale e va verificato dallo staff." if partial else "Il quadro e supportato da fonti diverse, sempre da verificare con lo staff.")
    why=[f"{source['title']} ({source['reliability_level']})" for source in sources[:3]]
    contradictions=[source["title"] for source in sources if source.get("validation_state") in {"contested_by_staff","dismissed_by_staff"}]
    if retrieval.get("contradictions") and not contradictions: contradictions=["Sono presenti fonti con indicazioni non concordi."]
    return {
      "answer_type":"evidence_based","direct_answer":direct,"why":why,
      "meaning":"Le evidenze descrivono cio che e stato registrato. Le osservazioni dello staff, i pattern e le interpretazioni AI mantengono natura distinta.",
      "options":["Apri le fonti principali","Limita il confronto a un periodo o a una partita"],
      "next_action":{"label":"Apri la fonte principale","url":sources[0]["action_url"]} if sources else {"label":"Apri Knowledge","url":"/knowledge.html"},
      "claims":[{"type":"evidenza","text":title} for title in titles],"contradictions":contradictions[:3],"provider":"deterministic",
    }
