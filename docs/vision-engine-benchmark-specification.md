# MatchIQ Vision Engine V3.1

## Specifica ufficiale del benchmark

Data: 2026-07-27
Stato: specifica progettuale, nessun benchmark ancora eseguito
Documenti di riferimento:

- `docs/vision-engine-current-pipeline-audit.md`
- `docs/tactical-moment-selection-design.md`

---

## 0. Principi del protocollo

Questo documento definisce come valutare in modo ripetibile la pipeline corrente
e le future versioni del MatchIQ Vision Engine. Non definisce implementazioni,
database, classi, endpoint o modelli. Non assegna accuratezze alla pipeline
attuale e non stabilisce soglie definitive senza dati.

Il benchmark deve rispettare questi principi:

1. Ogni metrica deve dichiarare l'unita valutata.
2. Qualita tecnica, valore tattico, continuita temporale, sicurezza AI e qualita
   editoriale restano separate.
3. Una pipeline non e migliore solo perche produce piu risultati.
4. Astensione corretta e migliore di una categoria specifica non supportata.
5. Gli errori che fanno perdere tempo allo staff hanno peso operativo.
6. Ground truth e output della pipeline non devono essere confusi.
7. La proposta originale deve restare disponibile dopo la correzione umana.
8. Il benchmark finale non deve essere usato per il tuning quotidiano.
9. I risultati devono essere stratificati per dominio e tipo di ripresa.
10. Costi e latenza fanno parte della valutazione.
11. Nessuna singola percentuale deve riassumere il sistema.
12. Quando un valore non e supportato, la conclusione e: **da determinare tramite
    annotazione pilota o baseline**.

### Terminologia normativa

- **Deve:** requisito obbligatorio del benchmark.
- **Dovrebbe:** requisito raccomandato, derogabile con motivazione.
- **Puo:** opzione consentita.
- **Ground truth:** annotazione congelata ottenuta secondo il protocollo umano.
- **Predizione:** output della pipeline da confrontare.
- **Run:** esecuzione completa con versione e configurazione identificabili.
- **Caso ambiguo:** campione con piu interpretazioni ragionevoli.
- **Astensione:** decisione esplicita di non assegnare una categoria o una
  conclusione.

---

## 1. Scopo del benchmark

### 1.1 Che cosa deve misurare

Il benchmark deve misurare separatamente:

- capacita di trovare momenti tatticamente utili;
- capacita di evitare scene non tattiche;
- accuratezza dei confini temporali;
- correttezza e specificita delle categorie;
- qualita del frame rappresentativo;
- correttezza e utilita delle descrizioni;
- affidabilita degli score;
- efficienza della review umana;
- costo e prestazioni della pipeline;
- stabilita tra esecuzioni;
- robustezza nei diversi domini video;
- regressioni rispetto alla baseline congelata.

### 1.2 Che cosa non deve misurare

Non deve essere usato per misurare:

- qualita calcistica reale di una squadra;
- efficacia di un allenatore;
- risultato sportivo;
- valore assoluto di un giocatore;
- accuratezza futura di componenti non ancora integrati;
- qualita commerciale complessiva del prodotto;
- soddisfazione utente non raccolta con un protocollo dedicato;
- accuratezza tattica tramite una sola metrica generica;
- qualita di OpenAI indipendentemente dall'intera configurazione osservata;
- generalizzazione a domini assenti dal dataset.

### 1.3 Decisioni che deve supportare

Il benchmark deve consentire decisioni documentate su:

- mantenere o sostituire il sampling corrente;
- introdurre Candidate Moment Discovery temporale;
- introdurre un filtro non tattico;
- integrare o respingere un detector;
- scegliere tra due tracker;
- abilitare una categoria;
- aumentare o ridurre la specificita della tassonomia;
- rilasciare una nuova pipeline in shadow mode;
- procedere a rollout limitato;
- interrompere una versione che regredisce;
- accettare un aumento di costo in cambio di un beneficio misurato.

### 1.4 Componenti confrontabili

Devono poter essere confrontati isolatamente:

- sampling/candidate discovery;
- filtri non tattici;
- delimitazione temporale;
- detector;
- tracking;
- calibrazione del campo;
- classificazione tattica;
- ranking del valore tattico;
- selezione editoriale;
- AI interpretation;
- linee/annotazioni suggerite;
- workflow di review;
- pipeline completa.

Ogni confronto deve mantenere costanti, per quanto possibile, dataset, split,
versione della tassonomia e condizioni di esecuzione.

### 1.5 Conclusioni vietate senza dati sufficienti

Non e consentito concludere che:

- "80% significa 80% di correttezza" senza calibrazione;
- una pipeline generalizza al dilettantismo se il dominio e assente;
- una categoria rara funziona con pochi esempi;
- un miglioramento globale elimina regressioni locali;
- un LLM e fattualmente corretto perche un altro LLM lo approva;
- un detector migliora il prodotto senza misurare la pipeline completa;
- una riduzione dei candidati e positiva senza misurare i momenti mancati;
- il costo e sostenibile senza misurarlo su partite complete;
- il feedback raccolto e ground truth senza controllo qualita;
- un risultato e stabile dopo una sola run non deterministica.

### 1.6 Output del benchmark

Il benchmark non produce un vincitore tramite un solo numero. Produce:

- un profilo di metriche;
- intervalli di incertezza;
- risultati stratificati;
- failure mode;
- costi;
- tempi;
- regressioni;
- decisione go/no-go motivata.

---

## 2. Unita di valutazione

Ogni unita deve avere un identificatore stabile interno al benchmark. Gli
identificatori non devono incorporare informazioni personali non necessarie.

### 2.1 Video completo

**Identificatore**

- identificatore benchmark del video;
- versione del file o fingerprint;
- split.

**Dati minimi**

- durata;
- risoluzione;
- frame rate;
- tipo di ripresa;
- contesto/competizione;
- stato dei diritti;
- versione temporale del file;
- partita associata.

**Ground truth**

- intervalli annotati;
- scene non tattiche;
- copertura delle categorie;
- porzioni non valutabili.

**Output da confrontare**

- candidati;
- momenti;
- scarti;
- costi;
- tempi;
- fallimenti;
- report complessivo.

**Metriche**

- recall per video;
- falsi positivi per partita;
- momenti mancati;
- costo e latenza;
- copertura temporale;
- tempo di review.

**Casi ambigui**

- video incompleto;
- cronologia non continua;
- montaggio;
- piu camere;
- tempi supplementari;
- intervalli senza gioco.

### 2.2 Intervallo temporale

**Identificatore**

- video;
- timestamp iniziale;
- timestamp finale;
- versione annotazione.

**Dati minimi**

- inizio;
- fine;
- durata;
- motivazione del confine;
- stato di validita.

**Ground truth**

- intervallo annotato;
- tolleranze;
- trigger;
- esito;
- eventuali confini alternativi.

**Output da confrontare**

- intervallo previsto;
- centro;
- confidenza della sequenza;
- motivo della candidatura.

**Metriche**

- Temporal Intersection over Union;
- errore assoluto di inizio/fine;
- copertura trigger/esito;
- over-segmentation;
- under-segmentation.

**Casi ambigui**

- azioni senza esito;
- confini graduali;
- fasi sovrapposte;
- cambio camera;
- replay.

### 2.3 Momento tattico

**Identificatore**

- video;
- intervallo;
- identificatore ground truth;
- revisione.

**Dati minimi**

- trigger;
- sviluppo;
- esito o sua assenza;
- categoria;
- squadra osservata;
- utilita.

**Ground truth**

- validita come momento;
- confini;
- categoria primaria;
- categorie secondarie;
- livello di utilita;
- note di evidenza.

**Output da confrontare**

- momento candidato;
- score separati;
- categoria;
- interpretazione;
- stato finale.

**Metriche**

- matching candidato-ground truth;
- recall/precision;
- qualita temporale;
- categoria;
- utilita;
- duplicazione.

**Casi ambigui**

- piu principi nella stessa azione;
- trigger fuori campo;
- esito non visibile;
- squadra non distinguibile.

### 2.4 Frame rappresentativo

**Identificatore**

- momento;
- timestamp;
- frame index quando disponibile.

**Dati minimi**

- immagine;
- posizione nella sequenza;
- qualita tecnica;
- motivo della scelta.

**Ground truth**

- frame preferito o insieme accettabile;
- ranking umano di alternative;
- requisiti minimi.

**Output da confrontare**

- frame selezionato;
- Technical Quality;
- Editorial Score;
- Tactical Value associato.

**Metriche**

- appartenenza al momento;
- distanza dal frame preferito;
- ranking agreement;
- idoneita editoriale;
- utilita tattica.

**Casi ambigui**

- piu frame equivalenti;
- frame tattico utile ma meno nitido;
- palla temporaneamente occlusa.

### 2.5 Scena non tattica

**Identificatore**

- video;
- intervallo;
- tipo di esclusione.

**Dati minimi**

- inizio/fine;
- filtro;
- evidenza;
- eventuale relazione con momento live.

**Ground truth**

- classe non tattica;
- severita;
- possibilita di uso editoriale separato.

**Output da confrontare**

- filtro applicato;
- score;
- accettazione/scarto.

**Metriche**

- precision/recall per filtro;
- leakage;
- scene valide eliminate;
- durata accettata erroneamente.

**Casi ambigui**

- replay utile;
- overlay breve;
- primo piano durante azione;
- camera tecnica.

### 2.6 Categoria tattica

**Identificatore**

- momento;
- versione tassonomia;
- livello gerarchico.

**Dati minimi**

- primaria;
- secondarie;
- specificita;
- squadra;
- stato determinabile.

**Ground truth**

- etichette approvate;
- alternative ammissibili;
- livello massimo supportato.

**Output da confrontare**

- categoria proposta;
- alternative;
- astensione;
- AI Confidence.

**Metriche**

- precision/recall/F1;
- macro/weighted F1;
- accuratezza gerarchica;
- multi-label;
- eccesso di specificita;
- astensione.

**Casi ambigui**

- costruzione sotto pressione;
- pressing e transizione;
- restart con sviluppo immediato;
- categoria secondaria rilevante.

### 2.7 Descrizione

**Identificatore**

- momento;
- lingua;
- versione prompt/modello;
- run.

**Dati minimi**

- testo;
- categoria collegata;
- evidenze disponibili;
- limiti dichiarati.

**Ground truth**

- rubric umana;
- fatti osservabili;
- interpretazioni consentite;
- affermazioni vietate.

**Output da confrontare**

- sintesi;
- spiegazione;
- consiglio;
- alternative;
- astensione.

**Metriche**

- correttezza fattuale/tattica;
- completezza;
- prudenza;
- utilita;
- allucinazioni;
- coerenza.

**Casi ambigui**

- interpretazioni tecniche differenti;
- linguaggio equivalente;
- evidenza incompleta.

### 2.8 Annotazione o linea

**Identificatore**

- momento;
- timestamp/intervallo;
- tipo;
- autore o sistema.

**Dati minimi**

- coordinate;
- riferimento spaziale;
- squadra;
- scopo;
- calibrazione disponibile.

**Ground truth**

- linea/area approvata;
- entita collegate;
- tolleranza;
- validita geometrica.

**Output da confrontare**

- geometria proposta;
- confidence;
- categoria;
- spiegazione.

**Metriche**

- distanza geometrica;
- overlap per aree;
- entita corrette;
- utilita umana;
- supporto dell'evidenza.

**Casi ambigui**

- campo non calibrato;
- piu linee didatticamente valide;
- prospettiva forte.

### 2.9 Sessione di review

**Identificatore**

- sessione;
- revisore;
- pipeline;
- benchmark.

**Dati minimi**

- inizio/fine;
- momenti presentati;
- ordine;
- click;
- correzioni;
- esito.

**Ground truth**

- set congelato da revisionare;
- procedura;
- obiettivo;
- livello del revisore.

**Output da confrontare**

- decisioni;
- tempi;
- errori approvati;
- carico percepito.

**Metriche**

- tempo per momento/partita;
- click;
- throughput;
- correzioni;
- conferme/scarti;
- errori accidentali.

**Casi ambigui**

- interruzioni;
- apprendimento del revisore;
- affaticamento;
- differenze di esperienza.

### 2.10 Esecuzione completa della pipeline

**Identificatore**

- versione Git;
- versione pipeline;
- configurazione;
- run;
- ambiente.

**Dati minimi**

- componenti;
- modelli;
- prompt;
- seed quando applicabile;
- risorse;
- orari;
- fallimenti.

**Ground truth**

- benchmark e split congelati.

**Output da confrontare**

- tutti gli artefatti prodotti;
- log metrici;
- costi;
- tempi;
- esiti review.

**Metriche**

- profilo completo;
- regressioni;
- stabilita;
- costo per risultato valido;
- go/no-go.

**Casi ambigui**

- servizi esterni variabili;
- retry;
- risultati parziali;
- cache;
- modifiche non tracciate.

---

## 3. Struttura concettuale del dataset benchmark

### 3.1 Gruppi informativi

Ogni campione deve poter contenere i seguenti gruppi.

#### Provenienza

- identificatore video;
- partita;
- data;
- livello/contesto;
- tipo di ripresa;
- sorgente;
- stato dei diritti;
- limitazioni di utilizzo;
- split.

#### Contesto tecnico

- durata;
- risoluzione;
- frame rate;
- compressione;
- orientamento;
- luce;
- stabilita;
- scoreboard;
- camera fissa/mobile;
- porzione non valutabile.

#### Momento

- inizio;
- trigger;
- centro;
- esito;
- fine;
- confini alternativi;
- continuita;
- replay collegato;
- frame rappresentativo.

#### Tattica

- categoria primaria;
- categorie secondarie;
- squadra osservata;
- direzione di gioco se determinabile;
- livello di utilita;
- livello massimo di specificita;
- evidenze;
- segnali mancanti.

#### Esclusioni

- scena non tattica;
- tipo;
- severita;
- intervallo;
- eccezione editoriale.

#### Qualita

- Technical Quality annotata;
- campo sufficiente;
- giocatori sufficienti;
- palla visibile/non visibile;
- annotabilita;
- ambiguita.

#### Annotazione

- annotatore;
- ruolo;
- data;
- versione tassonomia;
- versione manuale;
- stato di accordo;
- decisione senior;
- motivazione;
- note.

### 3.2 Dati obbligatori

Per ogni video:

- identificatore;
- durata;
- tipo di ripresa;
- dominio professionistico/dilettantistico;
- stato dei diritti;
- split;
- versione del materiale.

Per ogni intervallo annotato:

- video;
- inizio/fine;
- tipo: tattico, non tattico o non determinabile;
- versione tassonomia;
- annotatore;
- stato di accordo.

Per ogni momento tattico:

- trigger o dichiarazione motivata della sua assenza;
- centro;
- esito o `non visibile`;
- categoria primaria;
- squadra o `non determinabile`;
- utilita;
- frame rappresentativo o `nessuno idoneo`;
- motivazione sintetica.

### 3.3 Dati opzionali

- categorie secondarie;
- confini alternativi;
- formazione;
- identita giocatori;
- coordinate di campo;
- linee;
- detection;
- tracking;
- calibrazione;
- descrizione di riferimento;
- esercitazione collegata;
- costo annotazione.

Un dato opzionale assente non deve essere convertito in valore negativo.

### 3.4 Stati espliciti per dati mancanti

Distinguere:

- non annotato;
- non applicabile;
- non visibile;
- non determinabile;
- annotazione in conflitto;
- dato perso;
- dato non consentito dai diritti.

Il valore vuoto non deve rappresentare piu significati.

### 3.5 Versionamento

Ogni campione deve essere riconducibile a:

- versione del video;
- versione tassonomia;
- versione manuale;
- versione ground truth;
- storia delle correzioni;
- split congelato.

Una modifica alla categoria non deve cambiare silenziosamente i risultati storici.

---

## 4. Tipologie di campioni

### 4.1 Positivi chiari

Momenti con trigger, struttura ed esito osservabili.

Necessari per:

- verificare la capacita minima;
- costruire esempi didattici;
- misurare il tetto raggiungibile;
- controllare regressioni evidenti.

### 4.2 Positivi difficili

Momenti validi con camera, luce, occlusioni o struttura meno evidente.

Necessari per:

- misurare robustezza;
- evitare benchmark troppo facile;
- rappresentare il dilettantismo;
- valutare astensione e specificita.

### 4.3 Negativi chiari

Scene senza valore tattico evidente.

Necessari per:

- misurare precisione dei filtri;
- stabilire un controllo negativo;
- evitare che ogni frame diventi una proposta.

### 4.4 Hard negative

Scene visivamente simili a momenti tattici ma non valide:

- densita casuale scambiabile per pressing;
- campo largo senza evento;
- restart non ancora battuto;
- primo piano con porzione di campo;
- replay senza logo evidente.

Necessari per misurare comprensione oltre l'estetica.

### 4.5 Scene ambigue

Scene con piu interpretazioni professionali plausibili.

Necessarie per:

- valutare alternative;
- misurare accordo;
- premiare astensione;
- impedire ground truth artificiale.

### 4.6 Evidenza insufficiente

Scene in cui la categoria non puo essere sostenuta.

Necessarie per misurare:

- astensione corretta;
- prudenza;
- overconfidence;
- specificita eccessiva.

### 4.7 Replay

Includere replay con e senza grafica, slow motion e angolazioni alternative.

Necessari per misurare:

- leakage;
- duplicati;
- associazione al momento live;
- discontinuita temporale.

### 4.8 Esultanze

Includere celebrazioni collettive, individuali e reazioni della panchina.

Necessarie per evitare la confusione gia osservata con `open_play`.

### 4.9 Primi piani

Includere giocatori, arbitri, allenatori e dettagli della palla.

Necessari per distinguere analisi collettiva da immagini tecnicamente nitide ma
inutili.

### 4.10 Pubblico e panchina

Necessari per valutare scene non tattiche con colori e movimento simili al campo.

### 4.11 Grafiche televisive

Includere fullscreen, lower third, formazioni, statistiche, pubblicita e split
screen.

Necessarie per misurare:

- falsa detection;
- perdita di area utile;
- lettura errata di elementi grafici.

### 4.12 Campo insufficiente

Campioni con campo parziale, zoom e bordocampo.

Necessari per definire sufficienza condizionata alla categoria.

### 4.13 Pochi giocatori

Campioni con uno, due o pochi giocatori visibili.

Necessari per impedire categorie collettive non supportate.

### 4.14 Palla non visibile

Distinguere:

- palla temporaneamente occlusa ma traiettoria inferibile;
- palla fuori frame;
- palla assente per tutta la sequenza.

Necessari per valutare continuita e prudenza.

### 4.15 Cambi camera

Includere stacchi compatibili, incompatibili, dissolvenze e camera multipla.

Necessari per valutare confini e tracking.

### 4.16 Domini video

Il benchmark deve includere:

- dilettantistico;
- professionale;
- camera fissa;
- camera mobile;
- luce diurna;
- luce artificiale;
- bassa risoluzione;
- forte compressione;
- scarso contrasto campo/divise;
- presenza/assenza scoreboard.

Ogni gruppo e necessario per impedire che una media globale nasconda il dominio
commerciale reale di MatchIQ.

### 4.17 Bilanciamento

Il dataset non deve essere artificialmente uniforme se la distribuzione reale non
lo e. Deve tuttavia garantire un numero sufficiente di casi per valutare ogni
gruppo critico.

La composizione definitiva e **da determinare tramite annotazione pilota o
baseline**.

---

## 5. Categorie iniziali del benchmark

### 5.1 Non tattico

**Definizione operativa**

Scena priva di comportamento collettivo utile per l'obiettivo del benchmark.

**Segnali minimi**

- assenza di azione tattica osservabile;
- oppure presenza dominante di contenuto escluso.

**Confini**

Include pubblico, panchina, primi piani incompatibili e grafiche; replay puo
restare sottocategoria distinta.

**Confusioni previste**

- campo largo senza evento;
- reazione durante gioco fermo;
- analisi individuale.

**Restare generici**

Quando la scena e chiaramente inutile ma il sottotipo non e certo.

**Astenersi**

Quando non e possibile stabilire se l'azione abbia valore per il focus.

**Prima baseline**

Si, categoria fondamentale.

### 5.2 Replay

**Definizione operativa**

Riproduzione non live di un evento gia avvenuto.

**Segnali minimi**

Almeno uno tra segnale televisivo affidabile, discontinuita temporale o
ripetizione verificabile.

**Confini**

Un replay puo contenere una situazione tattica, ma non e un nuovo momento live.

**Confusioni previste**

- cambio camera live;
- slow motion live;
- clip montata.

**Restare generici**

Se si rileva contenuto non live ma non il tipo.

**Astenersi**

Se il video originale e gia un montaggio senza timeline verificabile.

**Prima baseline**

Si.

### 5.3 Palla inattiva generica

**Definizione operativa**

Fase organizzata attorno a una ripresa del gioco, con tipo non sufficientemente
determinabile.

**Segnali minimi**

- gioco fermo;
- palla posizionata o preparazione;
- giocatori organizzati;
- ripresa imminente o appena avvenuta.

**Confini**

Non forzare corner, punizione o rimessa senza evidenza.

**Confusioni previste**

- pausa;
- rinvio;
- replay;
- costruzione dal portiere.

**Restare generici**

Quando il restart e evidente ma il punto di battuta non lo e.

**Astenersi**

Quando non e chiaro se il gioco fosse fermo.

**Prima baseline**

Si.

### 5.4 Calcio d'angolo

**Definizione operativa**

Ripresa del gioco dall'arco d'angolo con organizzazione offensiva e difensiva.

**Segnali minimi**

- palla o battitore nella zona d'angolo;
- area di rigore e riferimenti coerenti;
- preparazione o battuta osservabile.

**Confini**

Una fase successiva alla respinta diventa open play o seconda palla.

**Confusioni previste**

- punizione laterale;
- rimessa profonda;
- cross in azione.

**Restare generici**

Se e certa la palla inattiva ma non la zona di battuta.

**Astenersi**

Se la battuta non e visibile e il contesto non basta.

**Prima baseline**

Si, solo se il pilota produce accordo sufficiente.

### 5.5 Punizione

**Definizione operativa**

Ripresa del gioco conseguente a fallo, con palla ferma e battuta.

**Segnali minimi**

- palla ferma;
- distanza/posizione coerente;
- organizzazione;
- battuta.

**Confini**

Separare punizione laterale/centrale soltanto se campo calibrabile o zona chiara.

**Confusioni previste**

- corner;
- rinvio;
- calcio d'inizio;
- pausa non ripresa.

**Restare generici**

Usare palla inattiva generica se il tipo non e certo.

**Astenersi**

Se manca la ripresa o la palla.

**Prima baseline**

Si a livello `punizione`; sottotipi rimandabili.

### 5.6 Rimessa laterale

**Definizione operativa**

Ripresa con pallone lanciato da fuori linea laterale.

**Segnali minimi**

- battitore fuori/dietro la linea;
- gesto di rimessa o rilascio;
- riceventi organizzati.

**Confini**

La fase successiva diventa sviluppo quando il possesso si stabilizza.

**Confusioni previste**

- primo piano bordocampo;
- punizione laterale;
- palla fuori non ancora ripresa.

**Restare generici**

Se si osserva restart laterale ma non il gesto.

**Astenersi**

Se linea e palla non sono osservabili.

**Prima baseline**

Si, se rappresentata.

### 5.7 Costruzione dal basso

**Definizione operativa**

Sequenza di possesso che parte dal portiere o dalla prima linea in zona bassa e
cerca di superare la prima pressione.

**Segnali minimi**

- origine bassa;
- possesso controllato;
- relazioni portiere/difensori;
- pressione o linee di passaggio;
- sviluppo osservabile.

**Confini**

Non confondere con rinvio lungo, possesso statico o restart senza sviluppo.

**Confusioni previste**

- rimessa dal fondo;
- ricircolo basso;
- recupero difensivo.

**Restare generici**

Usare possesso in zona bassa se origine/esito non sono osservabili.

**Astenersi**

Se il video inizia a sviluppo gia avanzato.

**Prima baseline**

Categoria candidata; richiede sequenze e puo essere rimandata se l'annotazione
pilota mostra basso accordo.

### 5.8 Pressing

**Definizione operativa**

Comportamento coordinato senza palla volto a limitare tempo, spazio e linee del
possessore.

**Segnali minimi**

- trigger;
- uscita di piu giocatori o reparto;
- orientamento;
- risposta del possessore;
- continuita temporale.

**Confini**

La sola densita non basta. Distinguere pressione individuale, pressing e
riaggressione.

**Confusioni previste**

- duello;
- palla inattiva;
- densita casuale;
- transizione negativa.

**Restare generici**

Usare pressione se la coordinazione collettiva non e dimostrabile.

**Astenersi**

Se mancano i secondi precedenti/successivi.

**Prima baseline**

Rimandare la valutazione specifica finche il benchmark temporale non e solido;
puo restare categoria esplorativa.

### 5.9 Transizione positiva

**Definizione operativa**

Comportamento immediatamente successivo al recupero del possesso.

**Segnali minimi**

- recupero osservabile;
- cambio di possesso;
- risposta offensiva;
- primi secondi di sviluppo.

**Confini**

Termina quando il possesso si stabilizza o l'azione finisce.

**Confusioni previste**

- contropiede gia iniziato;
- seconda palla;
- possesso ordinario.

**Restare generici**

Usare cambio di possesso se la direzione non e chiara.

**Astenersi**

Se il recupero non e visibile.

**Prima baseline**

Categoria candidata dopo annotazione temporale pilota.

### 5.10 Transizione negativa

**Definizione operativa**

Comportamento immediatamente successivo alla perdita del possesso.

**Segnali minimi**

- perdita osservabile;
- cambio di possesso;
- reazione difensiva;
- conseguenza immediata.

**Confini**

Termina con recupero, stabilizzazione del blocco o superamento della prima
reazione.

**Confusioni previste**

- pressing organizzato;
- errore tecnico;
- seconda palla.

**Restare generici**

Usare cambio di possesso quando non e chiara la squadra osservata.

**Astenersi**

Se la perdita avviene fuori campo visivo.

**Prima baseline**

Categoria candidata dopo annotazione temporale pilota.

### 5.11 Linea o blocco difensivo

**Definizione operativa**

Organizzazione collettiva senza palla osservabile per una finestra sufficiente.

**Segnali minimi**

- maggioranza del reparto;
- riferimenti avversari;
- palla o direzione;
- stabilita/variazione della struttura.

**Confini**

Una singola disposizione non dimostra salita, discesa o efficacia.

**Confusioni previste**

- palla inattiva;
- transizione;
- frame largo senza azione.

**Restare generici**

Usare blocco difensivo senza qualificare altezza o comportamento.

**Astenersi**

Se mancano reparto o riferimenti.

**Prima baseline**

Rimandare la specificita; possibile classe generica esplorativa.

### 5.12 Non determinabile

**Definizione operativa**

Evidenza insufficiente o conflittuale per assegnare una categoria affidabile.

**Segnali minimi**

- almeno un limite documentato;
- impossibilita motivata.

**Confini**

Non equivale a non tattico. Un momento puo essere utile ma non classificabile.

**Confusioni previste**

- categoria rara;
- annotazione incompleta;
- disaccordo umano.

**Prima baseline**

Si, obbligatoria per misurare astensione.

### 5.13 Raccomandazione prima baseline

Categorie consigliate come nucleo iniziale:

- non tattico;
- replay;
- palla inattiva generica;
- calcio d'angolo;
- punizione;
- rimessa laterale;
- non determinabile.

Categorie candidate in un secondo strato della stessa fase pilota:

- costruzione dal basso;
- transizione positiva;
- transizione negativa.

Categorie da trattare inizialmente come esplorative:

- pressing;
- linea o blocco difensivo.

La decisione finale e **da determinare tramite annotazione pilota o baseline**.

---

## 6. Protocollo di annotazione

### 6.1 Ruoli

#### Annotatore primario

Competenza minima:

- conoscenza del calcio e delle categorie del manuale;
- formazione sul protocollo;
- esercizio su set di calibrazione;
- comprensione di trigger, sviluppo ed esito.

#### Secondo revisore

Deve essere indipendente dalla prima annotazione per i campioni selezionati.

#### Revisore senior

Competenza raccomandata:

- allenatore qualificato, match analyst o figura equivalente;
- responsabilita sulla risoluzione dei disaccordi;
- autorizzazione a marcare casi non determinabili.

#### Curatore del benchmark

Responsabile di:

- versioni;
- split;
- diritti;
- controlli;
- congelamento;
- audit trail.

Una persona puo ricoprire piu ruoli in un team piccolo, ma le decisioni devono
restare registrate e distinguibili.

### 6.2 Primo passaggio

Ordine consigliato:

1. validare il video e i diritti;
2. marcare porzioni non valutabili;
3. annotare scene non tattiche;
4. individuare momenti;
5. segnare inizio, trigger, centro, esito, fine;
6. assegnare categoria al livello supportato;
7. assegnare squadra;
8. valutare utilita;
9. scegliere frame rappresentativo;
10. registrare motivazione e ambiguita.

L'annotatore non deve vedere la predizione della pipeline quando costruisce la
ground truth iniziale.

### 6.3 Seconda revisione

Deve:

- controllare confini;
- controllare categoria;
- controllare utilita;
- controllare frame;
- dichiarare accordo o disaccordo;
- non modificare silenziosamente la prima annotazione.

### 6.4 Risoluzione dei disaccordi

Processo:

1. confronto strutturato;
2. indicazione delle dimensioni in conflitto;
3. revisione della sequenza;
4. applicazione del manuale;
5. decisione senior o `non determinabile`;
6. registrazione della motivazione.

### 6.5 Stati di accordo

- **Accordo pieno:** confini entro tolleranza, categoria e utilita concordi.
- **Accordo parziale:** principio concorde, differenza su confini, specificita o
  attributi.
- **Disaccordo:** categoria primaria o validita del momento divergenti.
- **Decisione senior:** conflitto risolto da revisore qualificato.
- **Evidenza insufficiente:** nessuna decisione forte supportabile.

### 6.6 Quando basta un annotatore

Puo bastare per:

- negativi chiari;
- replay evidente;
- grafica fullscreen;
- controlli preliminari;
- dataset di sviluppo non congelato.

Deve comunque essere possibile campionare questi casi per audit.

### 6.7 Quando servono almeno due annotatori

Obbligatori per:

- momenti positivi;
- confini temporali del benchmark;
- categorie tattiche;
- utilita ottimo/buono;
- hard negative;
- casi ambigui;
- benchmark congelato;
- campioni usati per calibrare score.

### 6.8 Versionamento delle correzioni

Ogni revisione deve conservare:

- valore precedente;
- valore nuovo;
- dimensione corretta;
- autore;
- motivo;
- data;
- versione manuale.

### 6.9 Controllo qualita

Controlli minimi:

- campioni obbligatori completi;
- timestamp validi;
- categoria compatibile;
- motivazione presente nei casi complessi;
- split corretto;
- diritti validi;
- nessun duplicato cross-split;
- accordo richiesto;
- audit casuale.

### 6.10 Congelamento della ground truth

Una versione e congelata quando:

- manuale e tassonomia sono versionati;
- disaccordi critici sono risolti;
- controlli superati;
- split assegnati;
- fingerprint registrati;
- modifiche successive richiedono una nuova versione.

---

## 7. Annotazione temporale

### 7.1 Punti temporali

- **Inizio:** primo istante necessario a capire il contesto.
- **Trigger:** evento che attiva il comportamento.
- **Centro:** istante piu rappresentativo, non necessariamente meta aritmetica.
- **Esito:** prima conseguenza tatticamente rilevante.
- **Fine:** termine del comportamento o passaggio a nuova fase.

### 7.2 Tolleranza temporale

La tolleranza deve essere:

- dichiarata per categoria;
- distinta per inizio e fine;
- validata nel pilota;
- piu ampia per comportamenti graduali;
- piu stretta per restart e cambi di possesso chiari.

Soglie definitive: **da determinare tramite annotazione pilota o baseline**.

### 7.3 Piu confini plausibili

Registrare:

- intervallo preferito;
- intervallo minimo accettabile;
- intervallo massimo accettabile;
- motivo dell'ambiguita.

Una predizione entro l'insieme accettabile non deve essere trattata come errore
identico a un intervallo irrilevante.

### 7.4 Momenti sovrapposti

Consentiti quando:

- categorie diverse descrivono lo stesso periodo;
- una categoria e primaria e l'altra attributo;
- la relazione e annotata.

Evitare duplicati che differiscono soltanto di pochi frame senza motivo.

### 7.5 Momenti consecutivi

Devono restare separati se:

- cambia possesso;
- cambia fase;
- esiste un nuovo trigger;
- lo staff prenderebbe decisioni diverse.

### 7.6 Replay associati

Il replay deve:

- avere intervallo proprio;
- essere marcato non live;
- essere collegato al momento originale quando determinabile;
- restare nello stesso split.

### 7.7 Azioni interrotte

Annotare:

- fine all'interruzione;
- motivo;
- eventuale ripresa come momento distinto;
- esito `interrotto`.

### 7.8 Momenti senza esito visibile

Possono essere validi se trigger e sviluppo sono chiari. L'esito deve essere
marcato `non visibile`, non inventato.

### 7.9 Cambi camera

Un intervallo puo attraversare un cambio camera solo se:

- la continuita e verificabile;
- non e replay;
- l'evento resta identificabile.

Altrimenti dividere o ridurre la Sequence Confidence.

### 7.10 Temporal Intersection over Union

Per intervallo previsto P e ground truth G:

**tIoU = durata(P intersezione G) / durata(P unione G)**

Uso:

- matching tra predizione e ground truth;
- qualita globale dei confini;
- confronto tra pipeline.

Limiti:

- penalizza duramente momenti brevi per piccoli errori;
- non distingue errore di inizio da errore di fine;
- puo essere alto anche se trigger o esito sono mancati;
- non gestisce da sola confini alternativi;
- richiede una regola di matching per duplicati.

Deve essere accompagnata da:

- errore assoluto inizio;
- errore assoluto fine;
- copertura trigger;
- copertura esito;
- categoria.

Soglie di matching definitive: **da determinare tramite annotazione pilota o
baseline**.

---

## 8. Metriche di Candidate Discovery

### 8.1 Regola di matching

Prima del calcolo, ogni candidato deve essere associato al massimo a un momento
ground truth primario secondo:

- sovrapposizione temporale;
- compatibilita minima;
- regola deterministica di assegnazione;
- gestione esplicita dei duplicati.

La regola definitiva di matching e **da determinare tramite annotazione pilota o
baseline**.

### 8.2 Recall dei momenti

**Definizione**

Quota di momenti ground truth a cui corrisponde almeno un candidato valido.

**Interpretazione**

Misura quanti momenti utili vengono trovati.

**Attenzione**

Un recall alto ottenuto proponendo quasi tutto il video non e sufficiente.

### 8.3 Precisione dei candidati

**Definizione**

Quota di candidati associabili a un momento ground truth.

**Interpretazione**

Misura quanto lavoro proposto allo staff e realmente pertinente.

### 8.4 Falsi positivi per partita

Numero di candidati senza momento corrispondente, normalizzato per partita o ora
video.

Questa metrica rende leggibile il carico operativo meglio di una percentuale su
dataset sbilanciati.

### 8.5 Momenti mancati per partita

Numero di ground truth senza candidato.

Deve essere stratificato per:

- categoria;
- utilita;
- dominio;
- qualita;
- durata.

Perdere un momento ottimo e piu grave che perdere uno mediocre.

### 8.6 Duplicati per momento

Numero di candidati assegnati allo stesso momento oltre il primo.

Misure:

- media;
- mediana;
- percentile alto;
- quota di momenti con duplicati;
- tempo di review causato.

### 8.7 Copertura temporale

Quota del video coperta da candidati.

Serve come controllo:

- copertura troppo alta puo indicare selezione indiscriminata;
- copertura troppo bassa puo spiegare recall insufficiente.

### 8.8 Latenza fino al primo candidato

Tempo tra avvio pipeline e disponibilita del primo candidato revisionabile.

Distinguere:

- primo candidato qualsiasi;
- primo candidato valido;
- primo candidato di alta utilita.

### 8.9 Distribuzione per categoria

Confrontare:

- distribuzione ground truth;
- distribuzione candidati;
- distribuzione dei mancati;
- distribuzione dei falsi positivi.

Serve a rilevare sovrapproduzione di categorie facili o generiche.

### 8.10 Trade-off recall/precision

Candidate Discovery deve inizialmente privilegiare recall, per non perdere
momenti. Tuttavia:

- i falsi positivi devono restare revisionabili;
- i duplicati devono essere controllati;
- il leakage non tattico deve essere misurato;
- il tempo per partita non deve crescere senza limite.

Il punto operativo corretto non e definibile a priori. Deve essere scelto
attraverso curve precision-recall e tempo di review.

### 8.11 Metriche ponderate per utilita

Oltre al recall non ponderato:

- recall dei momenti ottimi;
- recall ottimo+buono;
- valore tattico totale coperto;
- perdita ponderata dei momenti mancati.

I pesi finali sono **da determinare tramite annotazione pilota o baseline**.

---

## 9. Metriche dei filtri non tattici

### 9.1 Valutazione per filtro

Per ciascuno tra:

- replay;
- esultanza;
- primo piano;
- panchina;
- pubblico;
- grafica;
- campo insufficiente;
- pochi giocatori;

misurare:

- precision;
- recall;
- F1;
- falsi negativi;
- falsi positivi;
- durata non tattica accettata;
- momenti validi eliminati;
- errori per camera e dominio.

### 9.2 Non-Tactical Leakage Rate

**Definizione**

Durata o numero di proposte mostrate allo staff che appartengono a scene non
tattiche, diviso per durata o numero totale delle proposte mostrate.

Riportare due varianti:

- **NTLR-count:** per numero di proposte;
- **NTLR-duration:** per durata complessiva.

Entrambe sono necessarie: una lunga scena inutile e diversa da molti falsi
positivi brevi.

### 9.3 Valid Moment Suppression Rate

Quota di momenti validi eliminati dai filtri.

Deve essere stratificata per filtro responsabile e utilita. E una metrica critica:
ridurre leakage sacrificando momenti ottimi non e progresso.

### 9.4 Non-tactical exposure time

Tempo totale che un revisore trascorre su scene non tattiche accettate.

Collega direttamente il filtro al costo umano.

### 9.5 Errori multi-filtro

Una scena puo essere replay e primo piano. Il report deve distinguere:

- etichetta primaria;
- etichette secondarie;
- filtro che ha preso la decisione;
- conflitti tra filtri.

### 9.6 Metriche per tipo camera

Ogni filtro deve essere analizzato per:

- camera fissa;
- camera mobile;
- broadcast;
- ripresa dilettantistica;
- zoom;
- luce.

Una precisione globale non deve nascondere l'eliminazione di momenti validi nelle
camere piu difficili.

---

## 10. Metriche di classificazione tattica

### 10.1 Precision, recall e F1

Calcolare per ogni categoria:

- precision;
- recall;
- F1;
- supporto.

Non riportare soltanto classi con molti esempi.

### 10.2 Macro F1

Media non ponderata delle F1 per categoria.

Uso:

- dare peso alle categorie rare;
- evidenziare sistemi che funzionano solo sulla maggioritaria.

Limite:

- instabile con supporto molto basso; riportare intervalli e supporto.

### 10.3 Weighted F1

Media ponderata per supporto.

Uso:

- rappresentare la distribuzione osservata.

Limite:

- puo nascondere categorie rare importanti.

Macro e weighted F1 devono essere sempre presentate insieme.

### 10.4 Matrice di confusione

Deve mostrare:

- categoria ground truth;
- categoria predetta;
- astensione;
- non determinabile;
- specificita gerarchica.

Fornire versione assoluta e normalizzata per riga.

### 10.5 Accuratezza gerarchica

Attribuisce credito parziale quando la predizione e corretta a un livello piu
generico.

Esempio:

- ground truth: calcio d'angolo;
- predizione: palla inattiva;
- errore meno grave rispetto a pressing.

La funzione di credito deve essere congelata con la tassonomia. I pesi sono **da
determinare tramite annotazione pilota o baseline**.

### 10.6 Accuratezza categoria primaria

Quota di momenti in cui la primaria coincide esattamente.

Non include attributi secondari.

### 10.7 Accuratezza multi-label

Riportare almeno:

- micro/macro precision;
- micro/macro recall;
- micro/macro F1;
- exact-set match;
- Hamming loss.

### 10.8 Tasso di astensione

Quota di momenti per cui il sistema non assegna una categoria forte.

Deve essere letto con:

- accuratezza sui casi non astenuti;
- copertura;
- astensioni appropriate;
- astensioni evitabili.

### 10.9 Accuratezza condizionata

Accuratezza calcolata soltanto sui casi classificati.

Non deve essere presentata senza coverage: una pipeline che classifica solo casi
facili puo sembrare eccellente ma essere poco utile.

### 10.10 Specificita eccessiva

**Unsupported Specificity Rate**

Quota di predizioni piu specifiche del massimo livello supportato dalla ground
truth.

Esempio:

- evidenza: palla inattiva offensiva;
- predizione: calcio d'angolo offensivo.

### 10.11 Costo della specificita

Definire una distanza gerarchica tra:

- predizione;
- categoria supportata;
- categoria corretta.

Penalizzare maggiormente:

- sottocategoria inventata;
- squadra/versante inventato;
- categoria lontana.

Premiare:

- categoria generica corretta;
- astensione quando il sottotipo non e determinabile.

Formula definitiva: **da determinare tramite annotazione pilota o baseline**.

---

## 11. Metriche del valore tattico

La scala e ordinale:

1. inutile;
2. mediocre;
3. buono;
4. ottimo.

### 11.1 Accuratezza esatta

Quota di predizioni uguali al giudizio umano.

### 11.2 Accuratezza entro una classe

Quota con errore ordinale massimo di una categoria.

Non sostituisce l'accuratezza esatta, ma distingue errori lievi e gravi.

### 11.3 Errore assoluto medio ordinale

Media di `|livello previsto - livello umano|`.

Puo essere calcolata solo con ordine congelato e significato stabile.

### 11.4 Confusione grave

Quota di:

- inutile promosso a buono/ottimo;
- mediocre promosso a ottimo;
- ottimo scartato/inutile;
- buono scartato/inutile.

Riportare separatamente ogni direzione.

### 11.5 Useless Promotion Rate

Percentuale di momenti inutili mostrati come buoni o ottimi.

E direttamente collegata al tempo perso e alla fiducia.

### 11.6 High-Value Miss Rate

Percentuale di momenti ottimi non candidati, scartati o classificati inutili.

### 11.7 Agreement ponderato

Puo essere considerato un coefficiente di accordo ordinale tra sistema e staff,
ma la scelta della statistica e **da determinare tramite annotazione pilota o
baseline**.

### 11.8 Costo operativo

Per ogni errore misurare:

- secondi di review;
- click correttivi;
- probabilita di approvazione accidentale;
- impatto sul report.

Gli errori che promuovono inutili devono avere priorita di prodotto elevata.

---

## 12. Metriche del frame rappresentativo

### 12.1 Appartenenza

Il timestamp del frame deve essere dentro:

- intervallo ground truth;
- oppure insieme temporale accettabile.

### 12.2 Rappresentativita temporale

Valutare se mostra:

- trigger;
- configurazione centrale;
- esito;
- oppure il punto definito come piu informativo.

Non assumere che il centro temporale sia il migliore.

### 12.3 Utilita tattica

Rubric:

- relazioni leggibili;
- reparto richiesto visibile;
- palla/riferimento visibile;
- squadra distinguibile;
- geometria informativa.

### 12.4 Qualita editoriale

Rubric separata:

- nitidezza;
- esposizione;
- stabilita;
- assenza overlay invasivi;
- spazio per annotazioni;
- leggibilita in slide/PDF.

### 12.5 Sufficienza del campo

Valutare per categoria. Non usare una soglia unica.

### 12.6 Palla e giocatori

Riportare:

- palla visibile;
- palla inferibile;
- giocatori rilevanti presenti;
- occlusioni;
- primi piani;
- scala.

### 12.7 Confronto con alternative

Presentare al revisore un piccolo insieme di frame dello stesso momento in ordine
casuale o controllato.

Metriche:

- top-1 scelto;
- top-k contiene un frame accettabile;
- ranking correlation;
- preferenza rispetto alla baseline.

### 12.8 Composite vietato

Qualita editoriale, utilita tattica e rappresentativita temporale devono essere
riportate separatamente.

---

## 13. Metriche delle descrizioni

### 13.1 Rubric umana

Ogni dimensione puo essere valutata su scala ordinale definita nel manuale, con
esempi positivi e negativi.

#### Correttezza fattuale

Le affermazioni visive sono osservabili?

#### Correttezza tattica

L'interpretazione e coerente con principi e sequenza?

#### Completezza

Include gli elementi necessari senza pretendere quelli assenti?

#### Prudenza

Distingue fatti, inferenze, alternative e limiti?

#### Utilita per lo staff

Aiuta review, riunione, allenamento o decisione?

#### Affermazioni non supportate

Conta fatti, giocatori, intenzioni o esiti inventati.

#### Coerenza con categoria

Il testo descrive la categoria proposta/corretta?

#### Coerenza con evidenze

Ogni punto forte e legato a un segnale disponibile?

### 13.2 Allucinazione

Conteggiare per descrizione:

- numero di affermazioni non supportate;
- severita;
- tipo;
- presenza in titolo, sintesi o consiglio.

Errori che identificano giocatori o esiti inesistenti sono severi.

### 13.3 Eccesso di sicurezza

Caso in cui il linguaggio e categorico mentre:

- AI Confidence e bassa;
- evidenza e insufficiente;
- annotatori sono in disaccordo;
- categoria e generica.

### 13.4 Prudenza corretta

Premiare quando il sistema:

- dichiara limite reale;
- propone alternativa utile;
- resta generico;
- si astiene.

Non premiare vaghezza automatica quando l'evidenza e chiara.

### 13.5 Alternative

Valutare:

- plausibilita;
- diversita reale;
- utilita;
- assenza di contraddizione gratuita.

### 13.6 Valutazione non esclusivamente LLM

Un LLM puo supportare controlli preliminari, ma il benchmark ufficiale richiede:

- rubric umana;
- campionamento doppio;
- revisione senior dei casi severi;
- fatti collegati alla sequenza.

---

## 14. Calibrazione degli score

### 14.1 Technical Quality

E uno score di qualita/ranking, non necessariamente probabilita.

Valutare:

- correlazione con giudizio tecnico umano;
- ranking dei frame;
- errore per camera;
- stabilita.

Non applicare ECE/Brier finche non viene definito un evento binario probabilistico
esplicito.

### 14.2 Tactical Value

E una scala ordinale, non una confidence.

Valutare con:

- accuratezza ordinale;
- MAE ordinale;
- confusione grave;
- agreement.

Non presentarlo come probabilita.

### 14.3 Sequence Confidence

Puo essere calibrata rispetto a un evento definito, per esempio:

"l'intervallo soddisfa i criteri temporali congelati".

Solo allora valutare:

- reliability diagram;
- Expected Calibration Error;
- Brier score;
- accuracy per fascia;
- over/underconfidence.

### 14.4 AI Confidence

Puo essere calibrata rispetto a:

- categoria primaria corretta;
- oppure interpretazione accettata senza correzione.

L'evento target deve essere dichiarato. Non mescolare i due.

### 14.5 Editorial Score

E ranking/qualita editoriale, non probabilita.

Valutare:

- preferenza umana;
- top-k;
- ranking agreement;
- idoneita per slide.

### 14.6 Reliability diagram

Raggruppa predizioni per fascia di confidence e confronta:

- confidence media;
- frequenza empirica di successo.

Deve riportare supporto per fascia. Fasce vuote o piccole non supportano
conclusioni.

### 14.7 Expected Calibration Error

Media pesata delle differenze tra confidence e frequenza empirica.

Limiti:

- dipende dai bin;
- puo nascondere errori locali;
- non sostituisce reliability diagram;
- richiede target binario chiaro.

### 14.8 Brier score

Errore quadratico medio delle probabilita per target binario.

Uso:

- penalizza overconfidence;
- confronta modelli sullo stesso target.

### 14.9 Dimostrare il significato di 80

Per dichiarare che `80` significa circa 80%:

1. definire il target;
2. congelare un set indipendente;
3. raccogliere un numero sufficiente di casi nella fascia;
4. misurare frequenza empirica;
5. stimare incertezza;
6. verificare per dominio;
7. replicare temporalmente.

Fino ad allora `80` e uno score interno, non attendibilita tattica.

---

## 15. Metriche della review umana

### 15.1 Tempi

- tempo medio e mediano per momento;
- percentili;
- tempo per partita;
- tempo fino alla prima decisione;
- tempo per categoria;
- tempo per tipo di errore.

### 15.2 Interazioni

- click per momento;
- click per partita;
- aperture dettagli;
- riproduzioni;
- seek;
- correzioni;
- azioni annullate.

### 15.3 Esiti

- conferme;
- scarti;
- categorie corrette;
- confini corretti;
- frame sostituiti;
- descrizioni corrette;
- linee corrette.

### 15.4 Throughput

Momenti revisionati per minuto, stratificati per:

- difficolta;
- esperienza revisore;
- pipeline;
- dispositivo.

### 15.5 Tempo risparmiato

Confrontare con review manuale definita nello stesso protocollo:

- stessa partita;
- stesso obiettivo;
- revisori bilanciati;
- ordine controllato;
- periodo di apprendimento gestito.

### 15.6 Carico cognitivo

Raccogliere tramite scala breve e coerente:

- sforzo;
- chiarezza;
- fiducia;
- frustrazione;
- percezione di controllo.

Lo strumento definitivo e **da determinare tramite annotazione pilota o
baseline**.

### 15.7 Errori approvati accidentalmente

Quota di proposte errate confermate. Distinguere:

- errore scoperto in seconda revisione;
- approvazione per distrazione;
- ambiguita reale;
- interfaccia ingannevole.

E una metrica di sicurezza UX, non solo di modello.

---

## 16. Costi e performance

### 16.1 Metriche

- tempo elaborazione per minuto video;
- tempo totale;
- costo totale;
- costo per candidato;
- costo per momento valido;
- memoria massima/media;
- CPU media/massima;
- GPU media/massima;
- storage originale e derivato;
- richieste OpenAI;
- token/input immagini quando disponibili;
- fallimenti;
- retry;
- latenza prima review;
- latenza report.

### 16.2 Ambienti

Separare:

- locale;
- cloud;
- dispositivo lento per operazioni client;
- video breve;
- partita completa;
- cache calda/fredda quando rilevante.

### 16.3 Normalizzazione

Riportare:

- per minuto video;
- per partita;
- per candidato;
- per momento valido;
- per report approvato.

### 16.4 Fallimenti e retry

Ogni retry deve indicare:

- componente;
- causa;
- tempo;
- costo;
- esito;
- duplicazione eventuale.

### 16.5 Confronto costo-beneficio

Il costo aggiuntivo e accettabile soltanto se associato a:

- recall utile maggiore;
- leakage minore;
- review piu breve;
- descrizioni migliori;
- riduzione di errori gravi.

Soglie economiche: **da determinare tramite annotazione pilota o baseline**.

---

## 17. Split del dataset e prevenzione del leakage

### 17.1 Split

- **Development set:** esplorazione e debugging.
- **Validation set:** scelta configurazioni e soglie.
- **Internal benchmark:** confronto ufficiale congelato.
- **Future temporal benchmark:** materiale successivo al rilascio.
- **Domain benchmark:** domini specifici, soprattutto dilettantistico.

### 17.2 Vincoli obbligatori

- nessuna clip della stessa partita tra train e test;
- replay e momento originale nello stesso split;
- duplicati nello stesso split;
- versioni dello stesso video nello stesso split;
- nessun frame estratto dallo stesso momento in split diversi;
- test finale non usato nel tuning.

### 17.3 Leakage visivo

Evitare:

- frame quasi identici cross-split;
- replay cross-split;
- crop dello stesso frame;
- versioni compresse dello stesso video;
- watermark/scoreboard che identificano sempre la categoria.

### 17.4 Leakage temporale

Evitare:

- segmenti adiacenti della stessa azione cross-split;
- primo e secondo tempo della stessa partita distribuiti in modo incoerente;
- future benchmark contenente materiale gia visto.

### 17.5 Leakage semantico

Evitare:

- descrizioni ground truth incluse nei prompt;
- nomi file che rivelano categoria;
- cartelle organizzate per etichetta esposte al modello;
- note staff usate sia come input sia come target senza dichiararlo.

### 17.6 Bilanciamento club/sorgente

Controllare che:

- un club non domini tutti gli split;
- una camera non diventi scorciatoia;
- uno scoreboard non rappresenti una sola classe;
- competizioni e divise non rendano banale la previsione.

### 17.7 Audit degli split

Prima del congelamento:

- fingerprint;
- ricerca duplicati;
- controllo metadati;
- controllo temporale;
- riepilogo per club/camera/categoria;
- revisione dei diritti.

---

## 18. Stratificazione dei risultati

Ogni metrica principale deve poter essere disaggregata per:

- categoria;
- tipo camera;
- risoluzione;
- compressione;
- luce;
- livello competizione;
- professionistico/dilettantistico;
- scoreboard;
- durata;
- campo visibile;
- numero giocatori;
- palla visibile/non visibile;
- video completo/clip;
- versione pipeline.

### 18.1 Regole di reporting

- riportare supporto per strato;
- non confrontare strati troppo piccoli senza avviso;
- mostrare intervalli di incertezza;
- evidenziare regressioni gravi anche con media globale positiva;
- non aggregare professionistico e dilettantistico senza mostrarli separati.

### 18.2 Intersezioni prioritarie

Analizzare almeno:

- dilettantistico + camera fissa;
- dilettantistico + bassa risoluzione;
- camera mobile + forte compressione;
- palla non visibile + transizione;
- pochi giocatori + categoria collettiva;
- replay senza grafica;
- luce artificiale + scarso contrasto.

La fattibilita statistica e **da determinare tramite annotazione pilota o
baseline**.

---

## 19. Baseline attuale

### 19.1 Obiettivo

Congelare la pipeline esistente senza modificarla e documentare cio che produce
oggi. La baseline deve essere ripetibile nei limiti dei servizi esterni.

### 19.2 Identita della baseline

Registrare:

- commit Git;
- stato working tree;
- versione frontend;
- versione PWA;
- ambiente;
- sistema operativo;
- versione Python/browser quando rilevante;
- data e ora;
- identificatore run.

### 19.3 Configurazione

Registrare:

- modello OpenAI richiesto e restituito, quando disponibile;
- parametri del modello;
- prompt completo o fingerprint versionato;
- focus;
- squadra;
- contesto;
- numero frame richiesti;
- numero candidati;
- regole locali;
- soglie;
- fallback;
- feature flag;
- retry policy.

### 19.4 Input e sampling

Per ogni video:

- identificatore;
- durata;
- timestamp campionati;
- frame estratti;
- metadati locali;
- frame inviati;
- frame esclusi prima del modello;
- motivo di esclusione.

### 19.5 Output

Registrare:

- candidati;
- frame selezionati;
- categorie;
- confidence grezze;
- confidence corrette;
- descrizioni;
- linee;
- status verified/candidate/rejected;
- report;
- errori;
- fallback.

### 19.6 Review

Registrare:

- conferma;
- correzione;
- scarto;
- categoria corretta;
- frame sostituito;
- linea modificata;
- tempo;
- click.

### 19.7 Tempi e costi

Registrare:

- preprocessing browser;
- attesa selezione;
- analisi;
- report;
- costo richieste quando disponibile;
- retry;
- fallimenti;
- latenza percepita.

### 19.8 Variabilita dei servizi esterni

Quando modello, infrastruttura o servizio non sono completamente deterministici:

- registrare data/ora;
- registrare identificatore modello restituito;
- conservare input e output consentiti;
- ripetere un sottoinsieme di run;
- calcolare agreement tra run;
- distinguere variabilita di categoria, score, descrizione e linee;
- non scegliere il risultato migliore.

Il numero di ripetizioni e **da determinare tramite annotazione pilota o
baseline**, considerando costo e stabilita osservata.

### 19.9 Stabilita tra run

Metriche candidate:

- percentuale stessi candidati;
- overlap temporale;
- agreement categoria;
- variazione confidence;
- variazione ranking;
- differenze nelle descrizioni;
- linee presenti/assenti;
- costo/tempo.

### 19.10 Non determinabilita

Se non e possibile ricostruire:

- versione esatta del modello;
- costo;
- seed;
- comportamento interno;

il report deve dichiararlo. Non deve imputare la variabilita a un componente senza
evidenza.

### 19.11 Congelamento

La baseline e congelata quando:

- codice e configurazione identificati;
- dataset congelato;
- protocollo eseguito;
- run archiviate;
- metriche calcolate;
- limiti dichiarati.

Nessuna baseline e stata eseguita durante la redazione di questa specifica.

---

## 20. Criteri di successo V3.1

### 20.1 Tre livelli di soglie

#### Soglie iniziali di lavoro

Servono per verificare che pipeline e benchmark funzionino. Non autorizzano un
rilascio.

#### Soglie candidate

Derivano da baseline e pilota. Servono per shadow mode e confronto.

#### Soglie definitive

Vengono congelate prima della decisione go/no-go e devono includere margini di
non regressione.

Tutti i valori numerici sono **da determinare tramite annotazione pilota o
baseline**.

### 20.2 Riduzione scene non tattiche

Valutare:

- NTLR-count;
- NTLR-duration;
- exposure time;
- valid moment suppression.

Successo solo se leakage diminuisce senza perdita grave di momenti ottimi.

### 20.3 Aumento recall dei momenti utili

Valutare:

- recall ottimi;
- recall ottimi+buoni;
- mancati per partita;
- dominio dilettantistico.

### 20.4 Riduzione duplicati

Valutare:

- duplicati per momento;
- tempo di review duplicato;
- copertura invariata.

### 20.5 Miglioramento categoria

Valutare:

- macro F1;
- weighted F1;
- accuratezza gerarchica;
- categorie critiche;
- specificita eccessiva.

### 20.6 Astensione corretta

Valutare:

- astensioni appropriate;
- accuracy condizionata;
- coverage;
- mancata astensione;
- astensione su casi facili.

### 20.7 Riduzione tempo review

Valutare:

- tempo per momento;
- tempo per partita;
- click;
- correzioni;
- errori approvati.

### 20.8 Stabilita costi

Valutare:

- costo per partita;
- costo per momento valido;
- latenza;
- retry;
- varianza.

### 20.9 Non regressione dilettantistica

Definire soglie separate per:

- camera fissa;
- bassa risoluzione;
- luce artificiale;
- compressione;
- scarso contrasto.

Una media professionistica migliore non compensa una regressione grave nel
dominio principale.

### 20.10 Decisione multi-criterio

Il go/no-go deve considerare:

- qualita;
- carico staff;
- costo;
- stabilita;
- failure mode severi;
- domini.

Non usare una media pesata opaca. Le eventuali deroghe devono essere motivate.

---

## 21. Report standard del benchmark

Ogni run ufficiale deve produrre un report con struttura stabile.

### 21.1 Intestazione

1. versione pipeline;
2. commit;
3. versione benchmark;
4. data;
5. ambiente;
6. responsabile;
7. stato working tree;
8. conformita del run.

### 21.2 Configurazione

- componenti;
- modelli;
- prompt;
- soglie;
- focus;
- parametri;
- fallback;
- retry;
- risorse.

### 21.3 Dataset

- split;
- numero video;
- durata;
- momenti;
- distribuzione categorie;
- domini;
- scene non tattiche;
- accordo annotatori;
- diritti.

### 21.4 Metriche globali

- candidate discovery;
- temporal;
- filtri;
- classificazione;
- utilita;
- frame;
- descrizioni;
- calibrazione;
- review;
- costi.

### 21.5 Metriche per categoria

Per ogni categoria:

- supporto;
- precision/recall/F1;
- confusione;
- astensione;
- utilita;
- failure mode.

### 21.6 Metriche per dominio

Per camera, qualita, luce, livello e altri strati dichiarati.

### 21.7 Matrice di confusione

Versione:

- assoluta;
- normalizzata;
- gerarchica;
- con astensione.

### 21.8 Failure mode principali

Ordinati per:

- severita;
- frequenza;
- tempo perso;
- componente;
- regressione.

### 21.9 Esempi positivi

Campioni rappresentativi, non scelti soltanto per estetica.

### 21.10 Esempi negativi

Includere:

- falsi positivi;
- falsi negativi;
- hard negative;
- regressioni.

### 21.11 Astensioni

- appropriate;
- evitabili;
- per categoria;
- per dominio.

### 21.12 Costi e tempi

- totali;
- normalizzati;
- distribuzioni;
- retry/fallimenti.

### 21.13 Confronto baseline

Per ogni metrica:

- baseline;
- candidato;
- differenza assoluta;
- differenza relativa quando sensata;
- incertezza;
- significato operativo.

### 21.14 Regressioni

Elenco esplicito, anche se la decisione finale e positiva.

### 21.15 Decisione go/no-go

Una delle seguenti:

- go shadow;
- go limitato;
- no-go;
- inconclusivo;
- raccolta dati aggiuntiva.

Con motivazione e condizioni.

### 21.16 Limitazioni

Includere sempre:

- domini non coperti;
- supporti bassi;
- dati mancanti;
- servizi esterni;
- conflitti annotativi;
- variazioni di configurazione.

---

## 22. Registro dei failure mode

### 22.1 Scala di severita

- **S0 - Informativo:** nessun impatto pratico.
- **S1 - Minore:** correzione rapida, nessun rischio sul report.
- **S2 - Moderato:** tempo perso o output degradato.
- **S3 - Grave:** decisione tattica/report potenzialmente errato.
- **S4 - Critico:** violazione diritti/isolamento, perdita dati o output
  sistematicamente ingannevole.

La severita definitiva per alcuni casi e **da determinare tramite annotazione
pilota o baseline**.

### 22.2 Tassonomia

| Codice | Failure mode | Definizione | Componente primaria | Severita iniziale |
|---|---|---|---|---|
| FD-01 | Timestamp irrilevante | candidato fuori dal momento utile | discovery | S2 |
| FD-02 | Momento mancato | ground truth senza candidato | discovery | S2-S3 |
| FD-03 | Momento duplicato | piu proposte per lo stesso momento | discovery/dedup | S1-S2 |
| TM-01 | Confini troppo stretti | manca contesto, trigger o esito | segmentation | S2 |
| TM-02 | Confini troppo larghi | include fasi distinte o rumore | segmentation | S1-S2 |
| NT-01 | Replay accettato | replay mostrato come momento live | filter | S2-S3 |
| NT-02 | Esultanza accettata | celebrazione proposta tatticamente | filter | S2 |
| NT-03 | Primo piano accettato | campo/relazioni insufficienti | filter | S2 |
| NT-04 | Campo insufficiente | momento collettivo senza campo | filter/quality | S2 |
| NT-05 | Pochi giocatori | categoria collettiva senza soggetti | filter/detection | S2 |
| VS-01 | Palla non osservabile | affermazioni dipendono dalla palla assente | vision/tracking | S2-S3 |
| TX-01 | Squadra errata | attribuzione alla squadra sbagliata | classification | S3 |
| TX-02 | Categoria errata | principio non corrispondente | classification | S2-S3 |
| TX-03 | Categoria troppo specifica | sottotipo non supportato | classification | S2 |
| TX-04 | Mancata astensione | decisione forte con evidenza insufficiente | classification | S3 |
| DS-01 | Descrizione inventata | affermazione non osservabile | interpretation | S3 |
| CF-01 | Confidence eccessiva | sicurezza non coerente con errori reali | calibration | S2-S3 |
| FR-01 | Frame errato | preview non rappresentativa | editorial | S1-S2 |
| LN-01 | Linea non supportata | geometria non fondata | annotation | S2-S3 |
| OP-01 | Costo eccessivo | costo oltre criterio congelato | operations | S2 |
| OP-02 | Latenza eccessiva | tempo oltre criterio congelato | operations | S2 |

### 22.3 Attributi di ogni occorrenza

- codice;
- video/momento;
- versione pipeline;
- componente;
- severita;
- rilevatore;
- evidenza;
- impatto staff;
- causa nota/ipotizzata;
- riproducibilita;
- stato;
- regressione;
- note.

### 22.4 Responsabilita

La componente primaria indica dove investigare, non una causa dimostrata. Un
errore puo propagarsi.

Esempio:

- palla mancata dal detector;
- track interrotto;
- transizione classificata male;
- descrizione inventata.

Registrare catena e causa radice quando determinabile.

### 22.5 Frequenza e impatto

Ordinare backlog usando almeno:

- frequenza;
- severita;
- minuti staff persi;
- categorie coinvolte;
- regressione rispetto baseline.

---

## 23. Piano minimo di raccolta dati

Il piano e pensato per un founder singolo con budget limitato. I range sono
ipotesi operative da validare, non dimensioni definitive.

### 23.1 Criteri generali di sufficienza

Un livello e sufficiente quando:

- copre le categorie dichiarate;
- contiene domini diversi;
- include positivi e negativi;
- consente doppia revisione dei casi critici;
- produce metriche con incertezza dichiarabile;
- i nuovi campioni iniziano a ripetere failure mode gia noti;
- i diritti sono verificati.

### 23.2 Benchmark minimo per iniziare

Scopo:

- verificare manuale;
- scoprire ambiguita;
- congelare una baseline preliminare;
- non autorizzare un rilascio.

Range di lavoro motivato:

- poche unita di partite complete, indicativamente 4-10;
- decine di ore al massimo, non centinaia;
- alcune centinaia di intervalli/momenti complessivi;
- supporto mirato per categorie iniziali;
- quota deliberata di non tattici e hard negative.

La scelta esatta dipende da:

- durata;
- densita di eventi;
- categorie;
- accordo;
- diritti;
- tempo di annotazione.

### 23.3 Benchmark intermedio

Scopo:

- confrontare componenti;
- misurare domini;
- iniziare calibrazione;
- supportare shadow mode.

Range di lavoro motivato:

- decine di partite;
- migliaia basse di momenti/intervalli;
- almeno piu sorgenti e camere;
- supporto adeguato per categorie abilitate;
- doppia revisione su benchmark e casi difficili.

Non procedere solo per raggiungere un numero: servono diversita e accordo.

### 23.4 Benchmark robusto futuro

Scopo:

- decisioni di rilascio;
- calibrazione affidabile;
- categorie rare;
- generalizzazione.

Range:

- molte decine o centinaia di partite, in funzione del dominio;
- migliaia o decine di migliaia di momenti;
- benchmark temporale indipendente;
- domain benchmark;
- copertura geografica/tecnica appropriata.

La dimensione e **da determinare tramite annotazione pilota o baseline**.

### 23.5 Carico di annotazione

Misurare nel pilota:

- minuti per minuto video;
- minuti per momento;
- tempo seconda revisione;
- tempo adjudication;
- percentuale casi ambigui;
- costo orario.

Usare questi dati per stimare il piano, non ipotesi generiche.

### 23.6 Strategia founder

Ordine consigliato:

1. limitare categorie;
2. selezionare video autorizzati diversi;
3. annotare pilota;
4. misurare tempo e accordo;
5. correggere manuale;
6. congelare benchmark minimo;
7. eseguire baseline;
8. decidere dove raccogliere altro.

### 23.7 Doppia revisione

Applicarla prioritariamente a:

- positivi;
- hard negative;
- casi ambigui;
- categorie critiche;
- campioni benchmark.

I negativi chiari possono essere controllati a campione per contenere il costo.

### 23.8 Diritti e minori

Prima della raccolta:

- confermare autorizzazione;
- definire uso per benchmark/training;
- gestire minori;
- limitare accessi;
- stabilire retention;
- registrare revoche.

Nessun vantaggio statistico giustifica materiale non utilizzabile.

---

## 24. Roadmap operativa del benchmark

### B0 - Specifica benchmark congelata

**Obiettivo**

Approvare questo documento e il perimetro.

**Input**

- audit pipeline;
- design Tactical Moment Selection;
- decisioni di prodotto.

**Output**

- specifica versionata;
- decisioni aperte;
- responsabili.

**Rischio**

Ambiguita nascoste nei termini.

**Criterio completamento**

Tutte le unita, metriche e categorie iniziali sono comprensibili da un revisore
indipendente.

**Non fare prematuramente**

- raccogliere grandi volumi;
- scegliere modelli;
- fissare soglie definitive.

### B1 - Manuale di annotazione

**Obiettivo**

Tradurre la specifica in istruzioni ed esempi.

**Input**

- B0;
- tassonomia candidata.

**Output**

- manuale;
- esempi;
- quiz/calibrazione annotatori;
- modulo disaccordi.

**Rischio**

Regole troppo astratte.

**Criterio completamento**

Due persone possono annotare un set prova e spiegare differenze.

**Non fare prematuramente**

- congelare ground truth;
- misurare il modello.

### B2 - Selezione video autorizzati

**Obiettivo**

Costruire inventario rappresentativo e legittimo.

**Input**

- requisiti dominio;
- policy diritti.

**Output**

- catalogo;
- diritti;
- metadati;
- proposta split provvisoria.

**Rischio**

Dataset comodo ma non rappresentativo.

**Criterio completamento**

Copertura minima dei domini e diritti verificati.

**Non fare prematuramente**

- estrarre migliaia di clip;
- assegnare split definitivo senza deduplica.

### B3 - Annotazione pilota

**Obiettivo**

Misurare difficolta, tempo e accordo.

**Input**

- manuale;
- sottoinsieme B2.

**Output**

- annotazioni pilota;
- tempi;
- disaccordi;
- failure del manuale.

**Rischio**

Confondere pilota con benchmark.

**Criterio completamento**

Problemi ricorrenti identificati e quantificati.

**Non fare prematuramente**

- pubblicare accuratezze;
- calibrare confidence;
- addestrare.

### B4 - Revisione e correzione tassonomia

**Obiettivo**

Rendere categorie annotabili e misurabili.

**Input**

- B3;
- disaccordi.

**Output**

- tassonomia/manuale aggiornati;
- categorie rimandate;
- regole di astensione.

**Rischio**

Adattare eccessivamente la tassonomia ai pochi video pilota.

**Criterio completamento**

Accordo e ambiguita compatibili con l'uso previsto.

**Non fare prematuramente**

- aggiungere molte sottocategorie;
- scegliere soglie modello.

### B5 - Benchmark minimo congelato

**Obiettivo**

Creare il primo riferimento ripetibile.

**Input**

- B2;
- B4;
- annotazioni controllate.

**Output**

- versione benchmark;
- split;
- ground truth;
- audit diritti/deduplica.

**Rischio**

Leakage o supporto insufficiente.

**Criterio completamento**

Controlli qualita superati e modifiche bloccate.

**Non fare prematuramente**

- usare test per tuning;
- dichiarare generalizzazione.

### B6 - Esecuzione baseline attuale

**Obiettivo**

Misurare la pipeline senza modificarla.

**Input**

- B5;
- configurazione congelata.

**Output**

- report standard;
- output archiviati;
- stabilita run;
- costi/tempi.

**Rischio**

Configurazione non riproducibile o servizio esterno variabile.

**Criterio completamento**

Run conformi e limiti documentati.

**Non fare prematuramente**

- scegliere il run migliore;
- modificare prompt a meta valutazione.

### B7 - Analisi failure mode

**Obiettivo**

Trasformare errori in priorita.

**Input**

- B6;
- registro failure.

**Output**

- frequenze;
- severita;
- cause probabili;
- costo staff;
- backlog evidence-based.

**Rischio**

Confondere correlazione e causa.

**Criterio completamento**

Ogni priorita e collegata a metriche e campioni.

**Non fare prematuramente**

- scegliere RF-DETR come soluzione universale;
- risolvere solo esempi vistosi.

### B8 - Criteri di successo V3.1

**Obiettivo**

Congelare soglie candidate e non regressioni.

**Input**

- B6;
- B7;
- vincoli costi.

**Output**

- criteri go/no-go;
- guardrail dominio;
- metriche primarie/secondarie.

**Rischio**

Soglie scelte per favorire una soluzione gia desiderata.

**Criterio completamento**

Criteri approvati prima di valutare V3.1.

**Non fare prematuramente**

- cambiare soglie dopo aver visto il risultato senza nuova versione.

### B9 - Benchmark runner futuro

**Obiettivo**

Automatizzare esecuzione e raccolta in modo ripetibile.

**Input**

- specifica B0;
- benchmark B5;
- report B6.

**Output**

- runner progettato/implementato in sprint futuro;
- manifest run;
- validazioni;
- artefatti.

**Rischio**

Automatizzare metriche non definite.

**Criterio completamento**

Due esecuzioni equivalenti producono report confrontabili.

**Non fare prematuramente**

- integrare nel prodotto;
- nascondere fallimenti;
- sovrascrivere run.

### B10 - Versionamento e report automatico

**Obiettivo**

Rendere ogni confronto auditabile.

**Input**

- B9;
- schema report standard.

**Output**

- report versionati;
- confronto baseline;
- regressioni;
- decisione tracciata.

**Rischio**

Dashboard sintetica che nasconde strati.

**Criterio completamento**

Una persona diversa puo ripetere il run e interpretare il risultato.

**Non fare prematuramente**

- ridurre tutto a uno score;
- pubblicare benchmark non rappresentativi.

---

## 25. Decisioni aperte

Tutte le seguenti decisioni sono **da determinare tramite annotazione pilota o
baseline**:

1. dimensione del benchmark minimo;
2. numero di partite;
3. minuti video;
4. numero di momenti;
5. categorie iniziali definitive;
6. inclusione di pressing e linea/blocco;
7. tolleranze temporali;
8. soglia tIoU per matching;
9. matching dei momenti sovrapposti;
10. soglie dei filtri;
11. soglie metriche go/no-go;
12. numero di annotatori;
13. quota di doppia revisione;
14. livello minimo di accordo;
15. procedura statistica per intervalli;
16. peso dei failure mode;
17. severita definitiva;
18. costo massimo per partita;
19. costo massimo per momento valido;
20. latenza massima prima review;
21. latenza massima report;
22. modalita di sampling baseline;
23. numero di run ripetute;
24. durata ideale per categoria;
25. gestione camere multiple;
26. uso di materiale professionistico;
27. distribuzione professionistico/dilettantistico;
28. policy per minori;
29. retention;
30. trattamento categorie rare;
31. livello massimo di specificita;
32. target probabilistico di Sequence Confidence;
33. target probabilistico di AI Confidence;
34. strumento per carico cognitivo;
35. qualita minima per frame rappresentativo;
36. definizione di campo sufficiente per categoria;
37. numero giocatori minimo per categoria;
38. modalita di valutazione delle linee;
39. gestione delle descrizioni multilingua;
40. strategia di adjudication con team ridotto.

---

## 26. Checklist di ripetibilita

Prima di dichiarare valido un run:

- [ ] pipeline identificata;
- [ ] commit identificato;
- [ ] working tree dichiarato;
- [ ] benchmark e split identificati;
- [ ] tassonomia identificata;
- [ ] configurazione completa;
- [ ] modello/prompt identificati;
- [ ] ambiente identificato;
- [ ] input integri;
- [ ] output archiviati;
- [ ] retry registrati;
- [ ] costi e tempi registrati;
- [ ] metriche calcolate con la versione corretta;
- [ ] risultati stratificati;
- [ ] failure mode registrati;
- [ ] regressioni esplicite;
- [ ] limitazioni dichiarate;
- [ ] decisione motivata;
- [ ] nessun test set usato per tuning;
- [ ] diritti validi.

---

## 27. Sintesi normativa

Il benchmark ufficiale V3.1 deve rispondere a otto domande senza ricorrere a una
confidence generica:

1. Trova i momenti giusti?
2. Evita le scene inutili?
3. Delimita correttamente le sequenze?
4. Assegna categorie al livello realmente supportato?
5. Seleziona materiale utile per lo staff?
6. Descrive soltanto cio che l'evidenza sostiene?
7. Riduce il lavoro umano?
8. Il beneficio giustifica costo e latenza?

La pipeline corrente costituisce la baseline soltanto dopo una run congelata e
documentata. La V3.1 potra essere considerata migliore solo se supera criteri
definiti prima del confronto, senza regressioni gravi nei video dilettantistici e
senza nascondere gli errori dietro una media globale.

