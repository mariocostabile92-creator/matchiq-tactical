# MatchIQ Vision Engine - Audit della pipeline corrente

Data audit: 2026-07-27  
Commit analizzato: `6bb79b1 feat(video): polish analysis workspace experience`

## 1. Executive summary

La Video AI di produzione non esegue oggi una comprensione continua della partita.
La pipeline principale campiona timestamp equidistanti nel browser, estrae singoli
fotogrammi JPEG, calcola euristiche visive locali e invia le immagini statiche a
OpenAI. OpenAI propone categoria, descrizione, qualita e linee; regole testuali
locali moderano o respingono parte delle risposte.

Esiste inoltre una pipeline Video Intelligence strutturata che trasforma i
timestamp e i metadati gia prodotti dal selettore in segmenti, evidenze, clip,
review e report. Questa pipeline non decodifica il video e non esegue un nuovo
modello visivo: costruisce finestre temporali attorno ai fotogrammi rappresentativi
e propaga le categorie gia presenti nei metadati.

RF-DETR non e collegato al runtime del prodotto. Le sue implementazioni sono
isolate sotto `research/vision_spike/`, non sono importate da `main.py`, `app/` o
`frontend/`, e nel repository non risultano checkpoint `.pt`, `.pth`, `.onnx` o
`.engine`. Il detector COCO sperimentale rileva solo `person`; la variante football
V3 prevede player, goalkeeper, referee e ball, ma richiede un checkpoint locale
che non e presente.

Le percentuali visualizzate non sono probabilita calibrate di correttezza tattica.
Sono punteggi eterogenei: autovalutazione OpenAI corretta da soglie testuali,
confidence delle linee suggerite da OpenAI, score euristico di qualita/presentazione
del frame o avanzamento del workflow. Non sono direttamente confrontabili.

Conclusione netta: oggi MatchIQ classifica principalmente immagini statiche e
organizza i risultati in un workflow professionale. Non determina in modo
indipendente un momento tattico da una sequenza video.

## 2. Diagramma completo della pipeline

### 2.1 Pipeline legacy attiva: frame statici, OpenAI e PDF

```text
Video locale o asset Libreria
  -> browser carica il video nel tag <video>
  -> timestamp candidati equidistanti
  -> seek del player a ogni timestamp
  -> canvas estrae JPEG statico
  -> euristiche locali su colore/luminosita/bordi
  -> POST /api/video/select-frames
  -> OpenAI Frame Selector vede i JPEG e il contesto
  -> normalizzazione risposta JSON
  -> validazione tassonomica e testuale locale
  -> frame verificati / candidati / scartati
  -> review umana e linee tattiche
  -> POST /api/video/analyze con i frame selezionati
  -> OpenAI genera report testuale
  -> seconda chiamata OpenAI genera le slide
  -> ReportLab genera il PDF
  -> report e metadati sono salvati nell'archivio cloud
```

### 2.2 Pipeline Video Intelligence: evidenze e review

```text
Frame gia selezionati dalla pipeline precedente
  -> frontend prepara timestamp e metadati
  -> POST /api/video/intelligence/projects/{asset_id}/pipeline
  -> costruzione candidate pool
  -> deduplicazione temporale
  -> categoria letta dai metadati testuali
  -> finestra temporale sintetica attorno al frame
  -> ranking euristico del fotogramma
  -> evidenza con frame rappresentativo e clip suggerita
  -> review: conferma / correggi / scarta
  -> solo evidenze confermate o corrette entrano nel report
  -> report strutturato e PDF
  -> persistenza nel metadata del video asset
```

Le due pipeline coesistono. La seconda non sostituisce il selettore OpenAI:
consuma i suoi timestamp e metadati.

## 3. Tabella file e funzioni

| Passaggio | File | Funzione/classe | Input | Output / fallback |
|---|---|---|---|---|
| Caricamento video | `frontend/video.html` | listener `videoFile` | File/Blob video | URL locale per il player |
| Sampling | `frontend/video.html` | `extractFrames` | durata, focus, numero frame | 16-44 timestamp equidistanti |
| Seek | `frontend/video.html` | `seekVideo` | player, timestamp | frame corrente; timeout seek 3.5 s |
| Estrazione JPEG | `frontend/video.html` | `extractFrames` | canvas, frame video | data URL JPEG, qualita 0.72 |
| Score locale | `frontend/video.html` | `scoreTacticalFrame` | pixel statici | score e metadati visivi euristici |
| Ranking locale | `frontend/video.html` | `selectBestTacticalCandidates` | candidati | fallback ordinato per score e distanza |
| Selezione AI | `frontend/video.html` | `performFrameSelectionRequest` | JPEG, contesto, metadati | chiamata autenticata al backend |
| Endpoint selezione | `app/routers/video.py` | `select_video_frames` | `FrameSelectionRequest` | frame verificati/candidati/scartati |
| OpenAI selector | `app/routers/video.py` | `_call_openai_frame_selector` | immagini statiche + prompt | JSON OpenAI; errore HTTP 502 |
| Tassonomia | `app/services/video_taxonomy.py` | `validate_frame_note` | nota OpenAI + meta locale | categoria, score limitato, stato |
| Deduplica | `app/services/video_taxonomy.py` | `_dedupe_by_time` | indici e tempi | minimo 7 s tra verificati |
| Linee AI | `app/routers/video.py` | `_normalize_line_suggestions` | coordinate OpenAI | massimo 2 geometrie normalizzate |
| Linee manuali | `frontend/video.html` | canvas tactical handlers | due click / effetto | geometria locale salvata nel payload |
| Feedback legacy | `app/routers/video.py` | `create_frame_feedback` | stato/categoria/note | riga DB con ownership |
| Report legacy | `app/routers/video.py` | `_build_prompt`, `_call_openai` | frame statici e contesto | report testuale OpenAI |
| Slide legacy | `app/routers/video.py` | `_call_openai_slides`, `_sanitize_slides` | stessi frame statici | storyboard OpenAI |
| PDF legacy | `app/routers/video.py` | `_build_pdf_base64` | report e slide | PDF ReportLab base64 |
| Payload Intelligence | `frontend/js/video-intelligence.js` | `pipelinePayload` | frame primari e candidati | timestamp in ms e metadati |
| Pipeline Intelligence | `app/services/video_intelligence_engine.py` | `run_pipeline` | timestamp, meta, eventi staff | progetto `review_ready` |
| Segmentazione | `app/services/video_segmentation_service.py` | `segment_frames` | timestamp e meta | finestre sintetiche e categorie |
| Ranking frame | `app/services/video_frame_ranking_service.py` | `score_frame`, `rank_segments` | metadati dichiarati | score 0-0.98 e tier |
| Evidenze | `app/services/video_evidence_service.py` | `build_evidence`, `review_evidence` | segmenti e review | evidenze persistenti |
| Report evidenze | `app/services/video_report_service.py` | `generate_evidence_report_delivery` | evidenze revisionate | report/PDF strutturato |
| Persistenza | `app/repositories/video_intelligence_repository.py` | `load_project`, `save_project` | user e asset | metadata del video asset |

Dipendenza esterna di produzione: OpenAI Chat Completions, modello configurato da
`OPENAI_VIDEO_MODEL`, default `gpt-4.1-mini`.

## 4. Selezione dei frame

### 4.1 Timestamp

- Il campionamento e fisso ed equidistante, non casuale e non event-based.
- Formula: `duration * ((i + 1) / (candidateCount + 1))`.
- Per focus stretti (palle inattive e costruzione dal basso) vengono campionati
  44 timestamp.
- Negli altri casi vengono campionati da 16 a 32 timestamp:
  `min(32, max(frame_richiesti * 4, 16))`.
- Il primo e l'ultimo 3% del video ricevono solo una penalita locale; non sono
  esclusi in modo assoluto.
- Il browser cattura un'immagine JPEG per timestamp, con larghezza massima 720 px.

Non vengono cercati prima eventi, interruzioni, variazioni di possesso o cambi
inquadratura per decidere i timestamp.

### 4.2 Criteri locali realmente implementati

`scoreTacticalFrame` stima dai pixel:

- rapporto verde;
- rapporto bianco;
- rapporto scuro;
- luminosita media;
- contrasto;
- variazioni di luminanza usate come proxy dei bordi;
- sharpness derivata dallo stesso edge score;
- visual information;
- equilibrio verticale del verde;
- presenza di verde al centro.

Il valore `motion` non viene calcolato dal video. `scene_change`, numero di persone,
bounding box, posizione della palla, distribuzione reale dei giocatori e geometria
del campo non vengono ricavati dal browser.

Il focus modifica soltanto i pesi numerici. Esempio: pressing aumenta il peso dei
bordi; linee e reparti aumentano verde, bianco, equilibrio verticale e centro campo.

### 4.3 Scarto e ordinamento

Se OpenAI risponde:

- propone ordine e note;
- il backend applica compatibilita tassonomica, soglie e keyword;
- i frame verificati sono deduplicati con distanza minima di 7 secondi;
- i candidati sono tenuti separati per review;
- i frame respinti non entrano nella selezione verificata.

Se la chiamata OpenAI fallisce per un errore non bloccante:

- il frontend usa `selectBestTacticalCandidates`;
- ordina per score locale;
- preferisce campo verde;
- applica una distanza temporale minima;
- non produce una vera classificazione visiva.

Gli errori 401 e 402 non attivano il fallback: il workspace precedente viene
preservato.

### 4.4 Filtri contro scene non tattiche

Esistono istruzioni esplicite nel prompt e keyword backend per:

- esultanza;
- primo piano;
- giocatore isolato;
- panchina;
- arbitro isolato;
- replay;
- scena non tattica.

Il ranking Video Intelligence aggiunge keyword per pubblico e intervista.

Limite decisivo: questi filtri dipendono dalla descrizione testuale restituita da
OpenAI o dai label presenti nei metadati. Non esiste un detector locale che
dimostri che il frame e un'esultanza, un replay o un primo piano. Se OpenAI non
nomina la scena correttamente, la regola non si attiva.

Non risultano filtri visivi specifici per cartelloni, grafiche televisive o
interruzioni. Lo score locale puo favorire immagini nitide, verdi e ricche di
bordi anche quando tatticamente inutili.

## 5. Significato degli score e delle percentuali

### 5.1 Percentuale sulla card del frame

- Nome UI: `meta.confidence`.
- Origine: `quality` richiesta a OpenAI dal Frame Selector.
- Range: intero 0-100.
- Moderazione: `validate_frame_note` puo limitarla a 58 per palla inattiva
  generica o a 44 quando le regole trovano motivi di rifiuto.
- Soglie: dipendono dalla categoria richiesta, circa 55-84.
- Visualizzazione: card frame in `frontend/video.html`.

Misura reale: autovalutazione del modello sulla qualita/utilita del singolo frame,
moderata da regole testuali. Non e una probabilita calibrata di correttezza
tattica e non deriva da un benchmark.

### 5.2 Score locale browser

- Nome interno: `meta.score`.
- Formula: bonus dipendenti dal focus, basati su verde, bianco, bordi,
  equilibrio verticale e centro campo, meno penalita close-up/scuro/inizio-fine.
- Range: non normalizzato formalmente a 0-100.
- Uso: ordinamento fallback e informazione inviata al prompt.
- Visualizzazione: normalmente non come percentuale principale.

Misura reale: compatibilita visiva euristica con un'inquadratura di campo.

### 5.3 Confidence delle linee

- Origine: valore `line_suggestions[].confidence` restituito da OpenAI.
- Range atteso: 0-100; il backend non lo ricalibra.
- Uso UI: suggerimento considerato affidabile da circa 55-60 in su.
- Misura reale: autovalutazione del modello sulla propria geometria suggerita.

Non deriva da player detection, regressione geometrica o calibrazione del campo.

### 5.4 Confidence delle slide

- Origine: seconda chiamata OpenAI dedicata alle slide.
- Range: limitato a 0-100 da `_sanitize_slides`.
- Fallback UI: puo essere derivato da `ai_quality`, score e presenza di linee con
  soglie arbitrarie.
- Misura reale: idoneita narrativa/presentativa proposta per lo storyboard.

### 5.5 Confidence delle evidenze Video Intelligence

- Nome: `confidence_score`.
- Origine: copia `ai_quality`, poi `quality`, poi `confidence`.
- Normalizzazione: valori sopra 1 sono divisi per 100; massimo 0.90.
- Se fase non classificata: massimo 0.35.
- Misura reale: propagazione normalizzata del punteggio del selettore.

Non e una nuova valutazione del video.

### 5.6 Frame ranking Video Intelligence

Formula in `score_frame`:

- base 0.16;
- contributi pesati di qualita dichiarata, sharpness, esposizione, contrasto,
  informazione visiva, rilevanza temporale, stabilita, inquadratura tattica e
  numero giocatori dichiarato;
- penalita per blur, nero, sovraesposizione, close-up, scene irrilevanti,
  cambio scena, movimento, duplicati e bordi segmento;
- clamp 0-0.98.

Tier:

- `slide_ready`: almeno 0.70;
- `useful_hint`: almeno 0.42;
- `discard`: sotto 0.42.

Molte grandezze sono assenti e ricevono valori di default. `visible_players`
contribuisce solo se e gia presente nei metadati; non viene contato dal servizio.

### 5.7 Risposta netta

Un valore dell'86% o del 90% non significa attendibilita tattica misurata. Significa
che il modello ha dichiarato un alto valore di qualita/utilita per quell'immagine
e che le regole locali non lo hanno abbassato abbastanza. Non certifica categoria,
movimento, disposizione dei reparti o veridicita della descrizione.

## 6. Ruolo reale di RF-DETR

### 6.1 Runtime di produzione

RF-DETR non viene eseguito dal flusso di produzione attuale.

- `main.py` registra `video_router` e `video_intelligence_router`.
- Nessun file in `app/`, `frontend/` o `main.py` importa
  `research.vision_spike`.
- `tests/test_vision_spike.py` e `tests/test_vision_spike_v2.py` contengono anche
  controlli espliciti di isolamento dal prodotto.
- `requirements-vision.txt` descrive dipendenze opzionali di ricerca.

Di conseguenza RF-DETR non influenza timestamp, selezione frame, categorie,
percentuali, linee, report o UI.

### 6.2 Esperimento COCO V2

`research/vision_spike/rfdetr_detector.py`:

- classe: `RFDETRDetector`;
- soglia default: 0.30;
- risoluzione default: 512;
- class mapping operativo: solo `person`;
- output: bounding box e confidence per persona;
- `ball_supported`: false;
- `roles_supported`: false;
- pesi football-specific: unavailable.

Queste detection appartengono al benchmark isolato, non al prodotto.

### 6.3 Esperimento football V3

`research/vision_spike/v3/football_detector.py` prevede:

- player;
- goalkeeper;
- referee;
- ball.

Richiede un checkpoint locale approvato. Nel repository analizzato non sono
presenti checkpoint `.pt`, `.pth`, `.onnx` o `.engine`; lo stato esportato in
`research/vision_spike/v3/__init__.py` e `DATASET_NOT_READY`.

Porte, linee del campo, identita dei giocatori e associazione squadra non sono
classi della variante V3.

### 6.4 Tracking e fallback

Il research spike contiene componenti di tracking e team-color clustering per
benchmark, ma non sono collegati a Video AI. Nel prodotto non esiste un fallback
RF-DETR/Torch: la pipeline di produzione usa canvas, OpenAI e metadati. Se
RF-DETR/Torch non sono installati il prodotto continua perche non li importa.

## 7. Origine delle categorie

### 7.1 Pipeline OpenAI

OpenAI assegna `phase`, `set_piece_type`, `restart_type`, `field_zone`,
`ball_state` e segnali visivi guardando i singoli JPEG e leggendo:

- focus;
- timestamp;
- squadre;
- moduli;
- note formazione;
- pre-score locale.

Il backend non esegue un classificatore visivo aggiuntivo. Converte testo e
segnali in tassonomia attraverso `resolve_situation` e `detected_situation`.

Categorie supportate dalla tassonomia legacy:

- calcio d'angolo offensivo/difensivo;
- punizione laterale offensiva/difensiva;
- punizione centrale offensiva/difensiva;
- rimessa laterale offensiva/difensiva;
- rimessa dal fondo;
- costruzione dal basso;
- linea difensiva, centrocampo, offensiva;
- pressing e transizioni;
- ampiezza;
- spazio tra reparti;
- rest defense;
- palla inattiva offensiva/difensiva/generica;
- analisi tattica generale.

`open_play` non e una categoria autonoma nella tassonomia legacy: compare come
valore di `restart_type` o come testo usato per escludere una palla inattiva.

### 7.2 Pipeline Video Intelligence

`video_segmentation_service._normalized_phase` esegue substring matching sui
metadati gia disponibili. Supporta:

- build-up, sviluppo, rifinitura, finalizzazione;
- transizione positiva/negativa;
- pressione/pressing alto;
- recupero/perdita palla;
- palle inattive, corner, punizioni e rimesse;
- fase di non possesso;
- linea difensiva;
- ampiezza;
- spazio tra reparti;
- rest defense.

Non guarda l'immagine. Se nessuna stringa coincide restituisce `unclassified`.

Una categoria puo quindi essere assegnata senza evidenze visive sufficienti se
OpenAI o i metadati la dichiarano e i filtri testuali non intercettano la
contraddizione.

Il comportamento interno con cui OpenAI decide una categoria non e
determinabile dal codice attuale.

## 8. Origine delle descrizioni

Esistono tre origini:

1. Il Frame Selector OpenAI genera `reason`, `evidence`, `grade_reason`,
   `visual_signals` e suggerimenti di linea vedendo i JPEG statici.
2. Il report legacy OpenAI riceve i JPEG selezionati, contesto partita, note,
   timestamp, metadati e una sintesi testuale delle linee.
3. La pipeline Video Intelligence usa template prudenti:
   `Possibile ...`, `Fotogramma reale disponibile...` e segnali dichiarati dal
   selettore.

OpenAI non riceve bounding box RF-DETR, track, velocita, optical flow o
posizionamento metrico. Riceve l'immagine statica e il contesto testuale.

Il prompt chiede prudenza, obbliga a dichiarare i limiti e vieta di inventare
nomi. Questi sono vincoli linguistici, non verifiche geometriche indipendenti.
La pipeline strutturata distingue `observation` da `interpretation` e usa
`Possibile`; il report legacy resta testo generato dal modello.

Frasi come "situazione di pressing e transizione con campo aperto" possono
provenire:

- direttamente da `reason/evidence` OpenAI;
- dal focus richiesto e dai template dello storyboard;
- dalla label locale basata su verde/bordi, se si attiva il fallback.

Quale contenuto visivo interno abbia portato OpenAI a quella frase non e
determinabile dal codice attuale.

## 9. Frame singolo o sequenza

### Selezione e classificazione

- Ogni candidato e un singolo JPEG statico.
- OpenAI riceve piu JPEG nella stessa richiesta, ma ciascuno e indicizzato come
  frame; non riceve clip video.
- Non vengono inviati frame adiacenti organizzati come sequenza.
- Non vengono calcolati movimento, traiettoria della palla o variazioni di
  disposizione tra istanti.

### Video Intelligence

`segment_frames` costruisce una finestra attorno a ogni timestamp:

- inizio: fino a 5 secondi prima;
- fine: fino a 7 secondi dopo;
- confini adattati alla distanza dai timestamp vicini;
- minimo segmento: 1 secondo;
- frame entro 1.2 secondi sono deduplicati.

Questa finestra e un riferimento temporale per clip e review. La categoria viene
dal metadato del fotogramma rappresentativo, non dall'analisi dei secondi
precedenti e successivi.

### Risposta netta

Oggi MatchIQ classifica principalmente un'immagine. Organizza poi quell'immagine
in una finestra temporale, ma non comprende il momento tattico attraverso una
vera analisi di sequenza.

## 10. Linee tattiche

### Linee suggerite

OpenAI restituisce al massimo due `line_suggestions` per frame:

- phase;
- team;
- color;
- confidence;
- reason;
- effect (`line`, `shadow`, `zone`, `player`);
- start/end normalizzati tra 0 e 1.

Il backend verifica tipo, colore e range delle coordinate. Non ricalcola la
geometria dai giocatori.

### Linee manuali

Il canvas permette all'utente di:

- mettere in pausa;
- scegliere frame, fase, squadra, colore ed effetto;
- cliccare punti;
- correggere o eliminare la grafica.

Le coordinate sono salvate nel workspace frontend e inviate nel payload del
report. `_format_tactical_lines` passa al prompt solo una sintesi di fase,
squadra, frame e tempo: il report testuale non riceve una misura geometrica.

### Capacita assenti nel runtime

- player detection;
- fit di una linea sui difensori;
- omografia;
- calibrazione prospettica;
- coordinate metriche del campo;
- stima automatica della distanza tra reparti;
- verifica della palla;
- continuita della linea tra frame.

Le linee automatiche sono quindi geometrie proposte dal modello su immagine
statica e sempre da verificare, non linee calcolate dal Vision Engine.

## 11. Feedback umano e dataset

### Feedback legacy

Azioni supportate:

- corretto;
- non pertinente;
- categoria corretta;
- approvato;
- scartato.

`POST /api/video/frame-feedback` salva in `video_frame_feedback`:

- user id;
- video asset id;
- report id;
- frame index;
- timestamp;
- sorgente;
- stato;
- fase richiesta/rilevata/corretta;
- confidence;
- note;
- metadata;
- data.

Ownership di asset e report e verificata. Le correzioni persistono nel database.

### Review Video Intelligence

Le evidenze hanno stati pending, confirmed, corrected o rejected. Sono salvati
reviewer, data, correzione e motivazione. Solo confirmed/corrected alimentano le
conclusioni del report strutturato.

### Uso effettivo

Il feedback viene letto da Knowledge e Pattern Intelligence. Nella sessione
corrente `corrected_phase` puo influenzare la successiva normalizzazione della
fase.

Non risulta un collegamento dal database feedback al prompt del Frame Selector,
a RF-DETR, a un processo di training o a un benchmark automatico. Il feedback
costituisce una base dati proprietaria grezza e tracciabile, ma oggi non addestra
il selettore.

Per diventare dataset di training mancano almeno:

- immagini/frame persistiti e versionati con riferimento certo;
- schema annotazioni completo;
- bounding box o keypoint;
- sequenze temporali e confini evento verificati;
- annotatore e accordo tra annotatori;
- versioni tassonomia;
- split train/validation/test per partita;
- licenze e diritti di uso per training;
- controllo qualita e benchmark.

## 12. Diagnosi dei quattro casi reali

### Caso A - Esultanza classificata `open_play` con percentuale alta

Causa tecnica piu probabile:

1. timestamp equidistante capitato sull'esultanza;
2. score locale alto per campo verde, luce, contrasto e bordi;
3. nessun detector locale di celebrazione/primo piano;
4. filtro backend attivato solo se OpenAI scrive keyword come `esultanza`;
5. percentuale generata dal modello, non calibrata.

Se OpenAI descrive il frame come open play e non menziona l'esultanza, la regola
non possiede un'evidenza indipendente per correggerlo.

### Caso B - Frame laterale classificato pressing

Causa tecnica piu probabile:

1. il focus pressing aumenta il peso locale dei bordi e del bianco;
2. OpenAI vede una sola immagine e puo confondere vicinanza/densita con pressione;
3. non vengono analizzati avvicinamento, velocita, possesso o frame adiacenti;
4. pressing non e una categoria strict e usa soglia 64;
5. la pipeline strutturata propaga poi la label testuale.

La conferma di un pressing richiederebbe dinamica temporale non disponibile.

### Caso C - Pochi giocatori visibili classificati `open_play`

Causa tecnica piu probabile:

1. il browser non conta persone;
2. RF-DETR non e nel runtime;
3. `visible_players` nel ranking vale zero se non e gia dichiarato;
4. campo verde e inquadratura leggibile possono comunque produrre uno score
   visivo discreto;
5. `open_play` puo essere un valore prudente/default del modello sul restart, non
   prova di valore tattico.

Il numero reale di giocatori non e verificato da un detector di produzione.

### Caso D - Frame largo utile classificato linea di centrocampo

Causa tecnica piu probabile:

1. un frame largo riceve bonus per verde, equilibrio e inquadratura tattica;
2. OpenAI puo associare la disposizione visibile alla linea di centrocampo;
3. le categorie line/spacing sono compatibili in modo permissivo con general e
   pressing;
4. non esiste una stima geometrica dei reparti o identificazione dei ruoli;
5. la singola immagine puo essere realmente utile, ma la categoria specifica non
   e dimostrata da tracking o coordinate.

La correttezza tattica della label non e determinabile dal codice attuale senza
ground truth del caso osservato.

## 13. Matrice di attendibilita

Le valutazioni seguenti sono giudizi tecnici basati sul codice, non risultati di
un benchmark misurato.

| Componente | Implementazione attuale | Dati usati | Attendibilita stimata | Limite principale | File responsabili |
|---|---|---|---|---|---|
| Timestamp | Griglia equidistante | durata video | Bassa per eventi, alta per copertura uniforme | nessuna event detection | `frontend/video.html` |
| Qualita tecnica | Euristiche pixel e ranking pesato | verde, bianco, luminosita, bordi, meta | Media | proxy semplici, dati mancanti | `frontend/video.html`, `video_frame_ranking_service.py` |
| Giocatori | Nessun detector runtime | eventuale testo/meta OpenAI | Bassa | RF-DETR isolato | `video.py`, `research/vision_spike/` |
| Palla | Nessun detector runtime | interpretazione OpenAI | Bassa | palla piccola e nessuna bbox | `video.py` |
| Squadre | Colori/numeri ipotizzati da OpenAI | JPEG, nomi e formazione | Bassa-media | nessun team classifier runtime | `video.py` |
| Categoria tattica | OpenAI + keyword/soglie | singoli JPEG e contesto | Bassa-media | niente sequenza o ground truth | `video.py`, `video_taxonomy.py` |
| Descrizione | OpenAI o template prudenti | immagini statiche, meta, contesto | Media come supporto, bassa come fatto | puo razionalizzare una label errata | `video.py`, `video_segmentation_service.py` |
| Linee | Coordinate OpenAI o click utente | singolo frame | Bassa automatiche, alta come annotazione manuale | nessuna geometria del campo | `video.py`, `frontend/video.html` |
| Segmenti/clip | Finestre attorno ai timestamp | tempi gia selezionati | Media come navigazione | non sono segmenti rilevati dal contenuto | `video_segmentation_service.py`, `video_clip_service.py` |
| Report legacy | OpenAI su frame statici | JPEG, note, focus, linee sintetiche | Media come bozza | dipende dagli errori upstream | `video.py` |
| Report evidenze | Solo review confirmed/corrected | evidenze revisionate | Media-alta per tracciabilita | qualita dipende dalla review | `video_report_service.py` |
| Feedback umano | Persistenza DB e collegamento Knowledge/Pattern | stato, fase, tempo, note | Alta come traccia | non addestra ancora i modelli | `database.py`, `video.py` |

## 14. Limiti attuali

1. Sampling uniforme anziche guidato dagli eventi.
2. Analisi statica invece di sequenziale.
3. Nessun RF-DETR nel prodotto.
4. Nessuna detection di palla/giocatori/porte nel runtime.
5. Nessun tracking.
6. Nessuna associazione squadra robusta.
7. Nessuna calibrazione del campo.
8. Confidence non calibrate.
9. Filtri non tattici dipendenti dal testo del modello.
10. Categorie propagate tra pipeline senza verifica visiva indipendente.
11. Segmenti temporali costruiti, non rilevati.
12. Feedback persistente ma non usato per training o benchmark.

## 15. Domande ancora aperte

1. Accuratezza reale per categoria su un dataset annotato: non determinabile dal
   codice attuale.
2. Calibrazione empirica dei valori 70/80/90: non determinabile dal codice attuale.
3. Tasso reale di esultanze/replay selezionati: non determinabile dal codice
   attuale.
4. Precision/recall RF-DETR football su video MatchIQ: non determinabile dal
   codice attuale; il checkpoint non e presente.
5. Affidabilita delle coordinate suggerite da OpenAI: non determinabile dal codice
   attuale.
6. Qualita delle associazioni squadra/numero/nome: non determinabile dal codice
   attuale.
7. Percentuale di feedback con immagine legalmente riutilizzabile per training:
   non determinabile dal codice attuale.
8. Prestazioni reali della pipeline su PWA e dispositivi lenti: non determinabile
   dal solo codice attuale.

## 16. Verifiche eseguite per questo audit

- Lettura del flusso frontend in `frontend/video.html`.
- Lettura del client strutturato in `frontend/js/video-intelligence.js`.
- Lettura dei router `video.py` e `video_intelligence.py`.
- Lettura di tassonomia, segmentazione, ranking, evidenze, report e repository.
- Ricerca di tutti i riferimenti RF-DETR nel prodotto e nei test.
- Lettura degli adapter RF-DETR V2 e football V3.
- Verifica dell'assenza di checkpoint di modello nel repository.
- Verifica dell'inclusione effettiva dei router in `main.py`.
- Lettura dello schema e del salvataggio `video_frame_feedback`.
- Controllo dello stato Git prima della creazione del presente documento.

Non sono stati:

- eseguiti upload reali;
- chiamati servizi OpenAI;
- installati pacchetti;
- avviati training;
- modificati test o configurazioni;
- eseguiti commit o push.
