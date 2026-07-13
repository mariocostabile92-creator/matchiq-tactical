from typing import Any, Dict, List


INTENTS: Dict[str, Dict[str, Any]] = {
    "memory_search":{"label":"Ricerca nella memoria","keywords":["cerca","fammi vedere","tutte le volte","osservazioni","partite"]},
    "pattern_explanation":{"label":"Spiegazione pattern","keywords":["perche","pattern","su quali partite","si basa"]},
    "temporal_comparison":{"label":"Confronto temporale","keywords":["migliorati","ultimo mese","diminuendo","andamento","cambiato"]},
    "context_comparison":{"label":"Confronto descrittivo","keywords":["confronta","4-3-3","4-2-3-1","blocco medio","pressione alta","meglio"]},
    "squad_analysis":{"label":"Analisi rosa","keywords":["rosa","giocatori","rossi","caratteristiche","piu citati"]},
    "weekly_preparation":{"label":"Preparazione settimana","keywords":["settimana","priorita","piano allenamento","esercitazione"]},
    "match_preparation":{"label":"Preparazione partita","keywords":["prossima partita","problemi ricorrenti","preparazione partita"]},
    "available_material":{"label":"Materiale disponibile","keywords":["clip","video","report","materiale","abbiamo sulla"]},
    "clarification":{"label":"Approfondimento","keywords":["spiegami meglio","fonti","solo le evidenze","approfondisci"]},
    "operational_action":{"label":"Azione operativa","keywords":["apri","portami","vai al"]},
    "tactical_identity":{"label":"Identita tattica","keywords":["identita tattica","come giochiamo","come vorrei","mia filosofia","coerenti","blocco medio","perche matchiq dice"]},
    "decision_support":{"label":"Supporto decisionale","keywords":["cosa conviene","quale opzione","decisione","rischi e benefici","alternative","cosa cambieresti"]},
}

THEMES={
  "secondo palo":["secondo palo","cross lato debole"],"pressing":["pressing","pressione alta"],
  "transizione negativa":["transizione negativa","palla persa","palle perse"],
  "costruzione dal basso":["costruzione dal basso","uscita dal portiere"],
  "palle inattive":["palla inattiva","palle inattive","calcio d'angolo","corner","punizione","rimessa"],
  "linea difensiva":["linea difensiva","linea bassa"],"ampiezza":["ampiezza","squadra stretta"],
}

SOURCE_BY_INTENT={
  "pattern_explanation":["historical_pattern"],"weekly_preparation":["weekly_briefing","training_plan"],
  "match_preparation":["historical_pattern","weekly_briefing"],"squad_analysis":["player","voice_observation","scout_report"],
  "available_material":["video_session","video_frame","video_report","coach_report"],
  "tactical_identity":["tactical_identity_profile","tactical_identity_dimension"],
  "decision_support":["decision_case","decision_option","staff_decision","observed_outcome"],
}


def detect_intent(text: str) -> str:
    clean=text.lower(); scored=[]
    for name,item in INTENTS.items(): scored.append((sum(2 if key in clean else 0 for key in item["keywords"]),name))
    score,intent=max(scored)
    return intent if score else "memory_search"


def detect_themes(text: str) -> List[str]:
    clean=text.lower(); return [theme for theme,words in THEMES.items() if any(word in clean for word in words)][:3]


def supported_intents() -> List[Dict[str,str]]:
    return [{"id":name,"label":value["label"]} for name,value in INTENTS.items()]
