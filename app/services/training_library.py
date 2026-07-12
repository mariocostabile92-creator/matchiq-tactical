from typing import Any, Dict, List


def _drill(identifier: str,title: str,theme: str,objective: str,description: str,**overrides) -> Dict[str,Any]:
    item={
        "id":identifier,"title":title,"category":"tattica","tactical_theme":theme,"objective":objective,"description":description,
        "min_players":10,"max_players":22,"goalkeepers":2,"field_dimensions":"45x40 m","duration":20,
        "materials":["cinesini","palloni","casacche"],"intensity":"media","difficulty":"intermedia","recommended_category":["Dilettanti","Juniores"],
        "progression":"Riduci tempi e spazi dopo una prima serie corretta.","regression":"Aumenta spazio e limita la pressione.",
        "coach_corrections":["Distanze coerenti","Comunicazione continua","Qualità della prima giocata"],"keywords":[theme],
        "source":"MatchIQ Methodology Seed","reliability_level":"editoriale","validation_status":"reviewed_demo","version":"1.0","notes":"Esercitazione base adattabile dallo staff.",
    }
    item.update(overrides); return item


EXERCISES: List[Dict[str,Any]]=[
    _drill("build-01","Uscita 6 contro 4 dal portiere","build_up","Superare la prima pressione con linee di passaggio pulite.","Costruzione guidata con portiere, linea difensiva e due centrocampisti.",field_dimensions="50x45 m",intensity="media"),
    _drill("press-01","Pressing coordinato a settori","pressing","Coordinare uscita, copertura e riaggressione.","Tre settori verticali con trigger di pressione definiti.",intensity="alta",duration=18),
    _drill("trans-pos-01","Recupero e attacco in 8 secondi","positive_transition","Attaccare rapidamente dopo il recupero.","Partita condizionata con bonus per finalizzazione rapida.",intensity="alta"),
    _drill("trans-neg-01","Rest defense e rientro","negative_transition","Proteggere il centro dopo perdita del possesso.","Possesso con transizione immediata e porte di uscita avversarie.",intensity="alta",field_dimensions="50x40 m"),
    _drill("post-02","Difesa del secondo palo","second_post","Migliorare marcatura, postura e copertura sul lato debole.","Cross alternati con difensori chiamati a proteggere area e secondo palo.",field_dimensions="55x45 m"),
    _drill("post-01","Attacco e difesa del primo palo","first_post","Gestire anticipo e traiettorie sul primo palo.","Sequenze di cross con riferimenti di zona e marcatura."),
    _drill("mark-01","Marcature e coperture in area","marking","Coordinare marcatura, copertura e comunicazione.","Situazioni 6 contro 5 con ingressi palla variabili."),
    _drill("set-01","Organizzazione palle inattive","set_piece","Definire responsabilità su corner e punizioni laterali.","Blocchi ripetuti offensivi e difensivi con seconda palla.",intensity="bassa",duration=16),
    _drill("width-01","Ampiezza e cambio gioco","width","Creare spazio sul lato debole.","Possesso direzionato con corsie laterali e cambio obbligatorio.",field_dimensions="60x45 m"),
    _drill("depth-01","Attacco della profondità","depth","Sincronizzare smarcamento e passaggio alle spalle.","Sequenze reparto offensivo contro linea difensiva."),
    _drill("possession-01","Possesso orientato 8 contro 8","possession","Conservare palla avanzando tra zone.","Tre zone orizzontali e punti per ricezione tra le linee.",goalkeepers=0,field_dimensions="55x40 m"),
    _drill("duel-01","Duelli e seconde palle","duels","Aumentare aggressività controllata e lettura della seconda palla.","Duelli a coppie con sostegno e continuità dell'azione.",intensity="alta",duration=15),
    _drill("recover-01","Recupero alto e finalizzazione","recovery","Trasformare il recupero in occasione.","Pressione su costruzione avversaria e attacco immediato alla porta.",intensity="alta"),
    _drill("finish-01","Rifinitura tra le linee","central_zone","Migliorare ultimo passaggio e ricezione orientata.","Sviluppo con trequartista e due attaccanti contro quattro difensori."),
    _drill("cross-01","Cross, occupazione area e ribattuta","right_flank","Coordinare cross, attacco area e copertura preventiva.","Azioni alternate dalle fasce con quattro zone di arrivo."),
    _drill("cover-01","Linea, copertura e scivolamento","team_distance","Ridurre distanze tra difesa e centrocampo.","Partita a tema con linea difensiva e centrocampo collegati.",field_dimensions="60x50 m",intensity="media"),
]


def library_items() -> List[Dict[str,Any]]:
    return [dict(item) for item in EXERCISES]
