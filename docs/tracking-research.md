# VE-004 - Ricerca tecnica sul Multi-Object Tracking

Data della ricerca: 28 luglio 2026

Stato: documento progettuale, nessuna implementazione

Roadmap di riferimento:

- VE-001 Baseline Runner: completato;
- VE-002 Player Detection con RF-DETR: completato;
- VE-003 Team Assignment: completato;
- VE-004 Tracking: da implementare dopo questa ricerca;
- VE-005 calibrazione e geometria tattica: futuro.

---

## 1. Executive summary

Per MatchIQ il tracker migliore oggi non e necessariamente quello con il punteggio
assoluto piu alto su MOT17. Il prodotto deve lavorare su calcio dilettantistico,
camere fisse, smartphone, zoom, compressione video, detection RF-DETR e una futura
calibrazione del campo. Deve inoltre restare leggibile, misurabile e correggibile.

La scelta consigliata e:

1. **ByteTrack come baseline primaria di VE-004**;
2. **BoT-SORT come challenger obbligatorio**, inizialmente senza ReID, per misurare
   il vantaggio della compensazione del movimento camera su smartphone e zoom;
3. **OC-SORT come challenger motion-only** per sequenze con occlusioni e movimenti
   non lineari;
4. **Norfair come alternativa da prototipazione**, soprattutto per la sua
   trasparenza e personalizzabilita;
5. StrongSORT e DeepSORT non consigliati come prima implementazione.

Per l'integrazione concreta, la raccomandazione e non copiare l'intero repository
originale ByteTrack, legato a uno stack YOLOX datato. Va preferita una
reimplementazione detector-agnostic, mantenuta e con licenza permissiva. Al
momento della ricerca, **Roboflow Trackers** soddisfa questi requisiti: supporta
RF-DETR, offre ByteTrack, BoT-SORT e OC-SORT con una API uniforme ed e rilasciato
con licenza Apache-2.0.

Questa decisione non dichiara ByteTrack definitivamente superiore. Stabilisce il
punto di partenza con il minor rischio tecnico. La scelta finale tra ByteTrack,
BoT-SORT e OC-SORT deve essere misurata sugli stessi video professionistici e
dilettantistici gia usati in VE-002 e VE-003.

---

## 2. Contesto MatchIQ

### 2.1 Input gia disponibile

VE-002 produce detection di persone con:

- `detection_id`;
- bounding box in pixel;
- bounding box normalizzata;
- centro;
- foot point;
- confidence RF-DETR;
- dimensioni e riferimenti del frame.

VE-003 arricchisce ogni detection con:

- `team_assignment`: `TEAM_A`, `TEAM_B` oppure `UNKNOWN`;
- `team_confidence`;
- colore dominante;
- cluster cromatico;
- informazioni sulla ROI del busto;
- motivazione dell'assegnazione o dell'astensione.

VE-004 non deve reinterpretare RF-DETR e non deve rieseguire il detector quando
riceve manifest gia elaborati. Il suo compito e associare nel tempo detection
appartenenti, con sufficiente probabilita, allo stesso soggetto.

### 2.2 Vincoli reali del dominio

Il calcio presenta difficolta diverse dal tracking pedonale urbano:

- molti soggetti vestiti nello stesso modo;
- incroci e occlusioni frequenti;
- dimensioni molto piccole nelle inquadrature larghe;
- accelerazioni, arresti e cambi di direzione non lineari;
- ingressi e uscite dal bordo;
- portiere, arbitro e staff non ancora classificati da VE-003;
- cambi di scala prodotti da zoom e movimento smartphone;
- frame persi, compressi o sfocati;
- frequenza dei frame variabile;
- cambio inquadratura, replay e primi piani nei broadcast;
- illuminazione non uniforme nei campi dilettantistici.

Il tracker deve quindi essere giudicato soprattutto su continuita temporale,
numero di cambi ID, gestione delle detection mancanti e trasparenza
dell'incertezza. Un ID plausibile ma sbagliato e piu pericoloso di una traccia
interrotta, perche VE-005 potrebbe trasformarlo in distanza, velocita o struttura
tattica false.

### 2.3 Cosa VE-004 non deve promettere

Un `track_id` non e l'identita anagrafica del giocatore. E un identificatore
temporale valido dentro una singola sequenza o partita. Senza un modello ReID
calcistico e senza numeri di maglia affidabili, non deve essere riutilizzato tra
inquadrature disgiunte o partite differenti.

---

## 3. Criteri di valutazione

La valutazione usa una scala qualitativa da 1 a 5:

- 5: molto adatto;
- 4: adatto;
- 3: adeguato con limiti;
- 2: debole o costoso da rendere affidabile;
- 1: non consigliato per il primo VE-004.

I punteggi sono una valutazione progettuale contestualizzata a MatchIQ, non una
metrica di benchmark. Devono essere validati sperimentalmente.

Pesi raccomandati per la futura decisione misurata:

| Criterio | Peso |
| --- | ---: |
| ID stability e continuita | 20% |
| Occlusioni e detection mancanti | 15% |
| Camera fissa dilettantistica | 12% |
| Smartphone, pan e zoom | 12% |
| Integrazione RF-DETR e VE-003 | 12% |
| Trasparenza per VE-005 | 10% |
| CPU, memoria e latenza | 7% |
| Manutenibilita e licenza | 7% |
| Debug e riproducibilita | 5% |

Il peso non deve essere trasformato in classifica definitiva senza un benchmark
MatchIQ annotato.

---

## 4. Tabella comparativa

| Tracker | Occlusioni | Stabilita ID | Camera fissa | Smartphone / zoom | RF-DETR | CPU | GPU | Debug | Dipendenze | Licenza originale | Stato progetto originale | Rischio MatchIQ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| ByteTrack | 4 | 4 | 5 | 3 | 5 | 5 | non necessaria per association | 5 | basse nel core, alte nel repo YOLOX originale | MIT | algoritmo maturo, repo originale poco attivo | basso |
| BoT-SORT | 5 | 5 | 4 | 5 | 4 | 3 senza ReID, 2 con ReID | utile con ReID | 3 | medie/alte: CMC, ReID, FastReID nel repo originale | MIT | repo originale poco attivo | medio-alto |
| OC-SORT | 4 | 4 | 5 | 3 | 4 | 5 | non necessaria per association | 4 | basse nel core | MIT | aggiornato e rifattorizzato nel 2026 | medio |
| DeepSORT | 4 | 3 | 3 | 2 | 3 | 2 | consigliata per embedding | 3 | alte e datate nel repo originale TensorFlow | GPL-3.0 | repository legacy | alto |
| StrongSORT | 5 | 5 | 4 | 4 | 3 | 2 | consigliata | 2 | molto alte: ReID, CMC, AFLink, GSI | GPL-3.0 | ricerca matura, stack originale datato | alto |
| Norfair | 3 | 3 | 4 | 4 | 5 | 4 | non necessaria | 5 | basse, moduli opzionali per video/metriche | BSD-3-Clause | libreria generalista mantenuta | medio-basso |

Note:

- il punteggio smartphone/zoom di BoT-SORT presuppone Camera Motion
  Compensation correttamente configurata;
- i punteggi DeepSORT e StrongSORT scendono nel calcio perche il ReID pedonale
  generico distingue male compagni con maglia identica;
- la GPU indicata riguarda il tracker. RF-DETR mantiene il proprio costo di
  inferenza separato;
- la licenza della reimplementazione scelta deve essere controllata
  indipendentemente dalla licenza del paper o repository originale.

---

## 5. ByteTrack

### 5.1 Principio

ByteTrack associa prima le detection ad alta confidence, poi prova a recuperare
track esistenti usando detection a confidence piu bassa. L'idea e particolarmente
utile quando un giocatore e parzialmente occluso o distante e RF-DETR ne abbassa
temporaneamente il punteggio.

L'input minimo e naturale per MatchIQ:

- `x1, y1, x2, y2`;
- detector confidence;
- frame corrente.

Non richiede un modello appearance e non dipende dal detector originale.

### 5.2 Punti forti per MatchIQ

- integrazione diretta con il manifest VE-002;
- nessun nuovo checkpoint;
- nessun uso di OpenAI;
- association veloce su CPU;
- comportamento deterministico a configurazione fissata;
- algoritmo piccolo e facilmente ispezionabile;
- seconda associazione utile per giocatori lontani o parzialmente coperti;
- ottimo baseline per isolare gli errori del detector da quelli del tracker;
- licenza MIT nell'implementazione originale;
- basso rischio di cambiare la semantica dei dati VE-002 e VE-003.

Su camera fissa, dove il movimento globale e nullo o minimo, la mancanza di
Camera Motion Compensation pesa poco. La geometria dell'immagine resta stabile e
il Kalman filter opera in condizioni favorevoli.

### 5.3 Limiti

- non usa appearance: dopo un'occlusione lunga puo assegnare un nuovo ID;
- negli incroci tra compagni con traiettorie simili puo effettuare ID switch;
- pan, vibrazione e zoom spostano simultaneamente tutte le box;
- un falso positivo a bassa confidence puo essere recuperato se compatibile con
  una traccia;
- richiede soglie calibrate sul detector RF-DETR e sul frame rate reale;
- il repository originale include una base YOLOX non necessaria e datata.

Per MatchIQ questi limiti sono accettabili nella prima baseline se:

- l'incertezza viene esportata;
- le interpolazioni non vengono presentate come osservazioni;
- la durata massima di una traccia persa resta conservativa;
- i risultati vengono misurati separatamente per camera fissa e smartphone.

### 5.4 Robustezza per scenario

**Camera fissa:** molto alta come prima scelta.

**Smartphone stabile:** buona con soglie conservative.

**Pan e zoom:** media; senza CMC l'associazione puo frammentarsi.

**Video dilettantistici:** buona, soprattutto se RF-DETR conserva detection
deboli ma corrette. Peggiora con motion blur e compressione estrema.

**Occlusioni brevi:** buona grazie alla seconda associazione.

**Occlusioni lunghe:** limitata senza appearance.

### 5.5 Manutenzione e integrazione

Il repository originale e autorevole ma non deve diventare una dipendenza
monolitica di MatchIQ. Include training, YOLOX e componenti non necessari. La
scelta piu sicura e usare un package moderno e detector-agnostic con licenza
permissiva, bloccandone la versione e testandone il contratto.

---

## 6. BoT-SORT

### 6.1 Principio

BoT-SORT estende la famiglia ByteTrack con:

- un modello di stato Kalman migliorato;
- Camera Motion Compensation;
- associazione basata su IoU;
- appearance/ReID opzionale.

La CMC e il motivo principale per cui BoT-SORT e importante per MatchIQ: pan,
vibrazioni e zoom possono essere stimati come movimento globale anziche
interpretati come movimento simultaneo dei giocatori.

### 6.2 Punti forti per MatchIQ

- migliore adattamento potenziale a smartphone e camere con zoom;
- forte continuita dopo occlusioni, soprattutto con ReID;
- base ByteTrack conosciuta;
- risultati sportivi pubblici molto competitivi;
- licenza MIT nel repository originale;
- puo essere usato inizialmente senza ReID.

### 6.3 Limiti

- piu componenti significano piu failure mode;
- una CMC errata puo deformare l'associazione di tutte le tracce;
- il ReID generico non e automaticamente adatto a giocatori con la stessa maglia;
- embedding appearance aumenta latenza, memoria e dipendenze;
- il repository originale richiede uno stack datato e componenti FastReID;
- la trasformazione camera puo creare ambiguita tra coordinate raw e stabilizzate.

### 6.4 Impatto sulla futura geometria

Per VE-005 la CMC non puo essere una correzione invisibile. Occorre conservare:

- coordinate originali;
- coordinate stabilizzate, se usate;
- matrice o trasformazione stimata per frame;
- metodo CMC;
- confidence o esito della stima;
- flag di fallback quando CMC non e affidabile.

La calibrazione del campo deve sapere in quale spazio si trova ogni punto. Senza
questa separazione si rischia di stimare distanze tattiche su coordinate gia
trasformate in modo non documentato.

### 6.5 Valutazione

BoT-SORT e il miglior challenger per MatchIQ. Non e la prima baseline perche
risolverebbe insieme association, camera motion e potenzialmente appearance,
rendendo piu difficile capire l'origine dei miglioramenti o delle regressioni.

La prova raccomandata e:

1. BoT-SORT senza ReID;
2. CMC disattivata su camera fissa;
3. CMC attivata su smartphone/zoom;
4. ReID escluso finche non esiste un benchmark calcistico specifico.

---

## 7. OC-SORT

### 7.1 Principio

OC-SORT e un tracker motion-only observation-centric. Corregge alcuni limiti del
Kalman filter classico usando maggiormente le osservazioni reali, con l'obiettivo
di gestire occlusioni e moto non lineare senza appearance.

### 7.2 Punti forti per MatchIQ

- nessun modello ReID;
- core leggero e veloce su CPU;
- adatto a cambi di direzione e movimenti non lineari;
- robustezza interessante alle occlusioni;
- algoritmo trasparente e riproducibile;
- licenza MIT;
- repository ufficiale aggiornato con refactoring Python nel 2026.

### 7.3 Limiti

- non risolve da solo il movimento globale della camera;
- senza appearance puo ancora cambiare ID dopo occlusioni lunghe;
- richiede adattamento pulito del formato RF-DETR;
- le prestazioni dichiarate dal paper non sostituiscono un benchmark su calcio
  dilettantistico;
- l'associazione motion-only puo soffrire nei gruppi densi che si muovono insieme.

### 7.4 Valutazione

OC-SORT e il terzo candidato e deve essere incluso nel benchmark iniziale se il
costo lo consente. E particolarmente utile come controllo scientifico:

- se migliora ByteTrack a camera fissa, il vantaggio deriva dal modello di moto;
- se BoT-SORT migliora soltanto su smartphone, il vantaggio deriva probabilmente
  dalla CMC;
- se nessuno migliora, il collo di bottiglia puo essere RF-DETR o il frame rate.

---

## 8. DeepSORT

### 8.1 Principio

DeepSORT aggiunge un descrittore appearance al motion tracking. La distanza tra
embedding aiuta a riassociare persone dopo un'occlusione.

### 8.2 Punti forti

- concetto consolidato e molto documentato;
- appearance utile quando i soggetti hanno abiti diversi;
- buona base accademica per studiare ID re-association;
- molte reimplementazioni disponibili.

### 8.3 Problemi per MatchIQ

- i compagni indossano la stessa divisa;
- i giocatori sono piccoli e poco dettagliati nel campo largo;
- numeri e volti non sono sempre leggibili;
- il modello appearance originale e pedonale, non calcistico;
- il repository ufficiale usa TensorFlow 1.5 e un encoder MARS legacy;
- la licenza GPL-3.0 richiede una valutazione legale per l'integrazione nel
  prodotto;
- checkpoint e inferenza appearance aggiungono costo e punti di guasto.

### 8.4 Valutazione

DeepSORT non e consigliato per VE-004. L'idea del ReID potra tornare utile in uno
sprint separato con un benchmark sport-specific e dati autorizzati. Inserirlo ora
confonderebbe il tracking temporale con un problema di identita non ancora
progettato.

---

## 9. StrongSORT

### 9.1 Principio

StrongSORT raccoglie numerosi miglioramenti rispetto a DeepSORT:

- appearance BoT;
- Camera Motion Compensation con ECC;
- aggiornamenti di stato e confidence;
- AFLink;
- Gaussian-smoothed interpolation.

### 9.2 Punti forti

- alta stabilita ID nei benchmark pedonali;
- migliore gestione di occlusioni e rientri;
- CMC utile con camera mobile;
- pipeline completa per esperimenti di alto livello.

### 9.3 Problemi per MatchIQ

- troppi componenti per la prima baseline;
- dipendenze e checkpoint multipli;
- costo GPU e memoria superiore;
- debug difficile: un errore puo provenire da detector, Kalman, CMC, ReID,
  linking o interpolazione;
- interpolazioni e linking post-processati sono rischiosi per misure tattiche;
- stack originale non moderno;
- licenza GPL-3.0;
- ReID generico poco discriminante tra compagni.

### 9.4 Valutazione

StrongSORT non e consigliato come VE-004. Potrebbe essere rivalutato soltanto se:

- MatchIQ costruisce un ReID calcistico;
- esiste ground truth sufficiente;
- il prodotto accetta elaborazione offline piu pesante;
- ogni fase del post-processing esporta la propria incertezza.

---

## 10. Norfair

### 10.1 Principio

Norfair e una libreria generalista e leggera. Associa detection tramite funzioni
di distanza personalizzabili e puo lavorare con box, centri o punti. Offre moduli
opzionali per movimento camera e ReID.

### 10.2 Punti forti per MatchIQ

- API semplice e Python-native;
- facile integrazione con foot point VE-002;
- funzioni di distanza personalizzabili;
- ottima leggibilita e facilita di debug;
- dipendenze contenute;
- CPU-friendly;
- licenza BSD-3-Clause;
- utile per prototipare vincoli di squadra o geometria.

### 10.3 Limiti

- non e un singolo algoritmo con configurazione canonica;
- la qualita dipende fortemente dalla funzione di distanza scelta;
- meno comparabilita con benchmark MOT standard;
- rischio di creare presto logica MatchIQ non sufficientemente validata;
- gestione delle occlusioni meno forte senza componenti aggiuntivi;
- puo spingere a usare foot point rumorosi prima della calibrazione.

### 10.4 Valutazione

Norfair e un'ottima alternativa ingegneristica, ma non la prima baseline
scientifica. Puo diventare un harness di prototipazione per:

- distanza su foot point;
- vincoli `TEAM_A`/`TEAM_B`;
- gating personalizzato;
- visualizzazione e debug.

Va mantenuto fuori dal percorso principale finche ByteTrack, BoT-SORT e OC-SORT
non sono stati confrontati sul benchmark MatchIQ.

---

## 11. Alternative mature e framework di integrazione

### 11.1 Roboflow Trackers

Non e un nuovo algoritmo. E un framework con reimplementazioni modulari di
ByteTrack, BoT-SORT, OC-SORT e SORT.

Vantaggi:

- licenza Apache-2.0;
- compatibilita dichiarata con RF-DETR;
- Python moderno;
- API uniforme;
- benchmark pubblici su SportsMOT e SoccerNet;
- permette di cambiare tracker senza cambiare il contratto VE-002;
- riduce il rischio di importare stack YOLOX/FastReID legacy.

I benchmark pubblicati dal progetto riportano, tra gli altri:

| Tracker | SportsMOT HOTA | SoccerNet HOTA |
| --- | ---: | ---: |
| ByteTrack | 73.0 | 84.0 |
| BoT-SORT | 73.8 | 84.5 |
| OC-SORT | 71.7 | 78.4 |
| SORT | 70.9 | 81.6 |

Questi dati rendono BoT-SORT un challenger serio, ma la differenza ridotta non
giustifica da sola la maggiore complessita. I dataset sportivi pubblici non
rappresentano necessariamente smartphone e campi dilettantistici MatchIQ.

Raccomandazione:

- valutare Roboflow Trackers come dipendenza di ricerca;
- bloccare esattamente la versione;
- creare un adapter MatchIQ in VE-004;
- non importare i tipi del package nei manifest permanenti;
- mantenere la possibilita di sostituire l'implementazione.

### 11.2 BoxMOT

BoxMOT e molto attivo e offre numerosi tracker sotto un'unica interfaccia.
Rappresenta un eccellente benchmark harness, ma la licenza AGPL-3.0 e un rischio
commerciale e legale per un prodotto SaaS proprietario. Inoltre porta un
perimetro piu ampio del necessario.

Conclusione: utile come riferimento esterno o benchmark isolato, non consigliato
come dipendenza runtime senza revisione legale formale.

### 11.3 SORT

SORT resta una baseline minima utile per misurare il valore aggiunto degli altri
tracker, ma non e consigliato come soluzione VE-004: elimina detection deboli e
gestisce peggio occlusioni e frammentazioni. Puo essere incluso soltanto come
controllo sperimentale.

---

## 12. Classifica finale per MatchIQ

### 1. ByteTrack

**Ruolo:** baseline primaria e prima implementazione raccomandata.

Motivo: massimizza semplicita, integrazione RF-DETR, CPU, debug e
riproducibilita. Permette di misurare il tracking senza introdurre subito ReID o
camera compensation.

### 2. BoT-SORT

**Ruolo:** challenger principale.

Motivo: migliore candidato per smartphone, pan e zoom grazie alla CMC. Va
confrontato senza ReID e con coordinate raw/stabilizzate separate.

### 3. OC-SORT

**Ruolo:** challenger motion-only.

Motivo: robustezza a occlusioni e movimento non lineare, core veloce e progetto
ufficiale attivo.

### 4. Norfair

**Ruolo:** ambiente di prototipazione e fallback.

Motivo: facile da integrare, personalizzare e diagnosticare, ma meno canonico
come benchmark calcistico.

### 5. StrongSORT

**Ruolo:** ricerca futura.

Motivo: prestazioni potenziali elevate, ma complessita, ReID, licenza e
post-processing non sono adatti alla prima integrazione.

### 6. DeepSORT

**Ruolo:** riferimento storico, non candidato operativo.

Motivo: stack originale legacy, ReID non sport-specific e licenza GPL-3.0.

---

## 13. Tracker consigliato oggi

### Decisione

Scegliere **ByteTrack**, attraverso un adapter interno e una reimplementazione
moderna con licenza permissiva. La candidata da verificare e Roboflow Trackers
Apache-2.0.

### Perche

1. VE-002 produce gia esattamente box e confidence richiesti.
2. Non serve rieseguire RF-DETR.
3. Non introduce un modello ReID non validato sul calcio.
4. Recupera detection deboli, frequenti in campo largo.
5. Funziona bene su camera fissa, sorgente prioritaria MatchIQ.
6. E veloce su CPU rispetto al costo gia dominante di RF-DETR.
7. E facile attribuire ogni errore a detector o association.
8. Offre il rischio piu basso di regressioni sui moduli di ricerca esistenti.
9. Produce un baseline comprensibile per il futuro benchmark.
10. Lascia BoT-SORT come evoluzione misurabile, non come complessita prematura.

### Limiti accettati

- fragilita su pan e zoom;
- ID switch negli incroci;
- riassociazione debole dopo occlusioni lunghe;
- nessuna identita persistente;
- sensibilita a soglie e frame rate;
- dipendenza dalla qualita RF-DETR.

### Compatibilita con la roadmap

La scelta e compatibile se VE-004 conserva coordinate, detection originali,
incertezza e stato della traccia. VE-005 non deve ricevere soltanto una polilinea
finale, ma anche l'evidenza che l'ha prodotta.

### Difficolta di implementazione

Valutazione: **media-bassa per il prototipo**, **media per una validazione
affidabile**.

La parte meccanica dell'adapter e semplice. La parte difficile e:

- ordinare correttamente i frame;
- gestire frame rate e timestamp;
- calibrare le soglie RF-DETR/ByteTrack;
- definire quando una traccia diventa confermata;
- rilevare e annotare ID switch;
- non propagare predizioni come osservazioni;
- confrontare camere differenti con ground truth.

---

## 14. Contratto dati necessario per VE-005

VE-004 deve produrre un manifest versionato e indipendente dal package scelto.

### 14.1 Metadati run

- `schema_version`;
- `pipeline_version`;
- `tracker_name`;
- `tracker_implementation`;
- `tracker_version`;
- configurazione e soglie complete;
- seed, se applicabile;
- video ID e hash;
- fps dichiarato ed effettivo;
- risoluzione;
- frame iniziale/finale;
- timestamp elaborazione;
- coordinate space disponibili;
- stato CMC e metodo, se presente.

### 14.2 Dati per osservazione

- `frame_index`;
- `timestamp_ms`;
- `track_id`;
- `track_scope`: video o segmento;
- `source_detection_id`;
- `bbox_xyxy` in pixel;
- `normalized_bbox_xyxy`;
- `foot_point_xy` originale;
- `normalized_foot_point_xy`;
- detector class e confidence;
- `team_assignment`;
- `team_confidence`;
- cluster VE-003;
- `observation_type`: detected, predicted oppure interpolated;
- `association_stage`: high-confidence, low-confidence o recovery;
- costo/score di associazione, se disponibile;
- spazio coordinate: raw o stabilized;
- trasformazione camera associata, se presente.

### 14.3 Dati per track

- frame e timestamp di inizio/fine;
- eta della traccia;
- numero di detection osservate;
- numero di frame predetti;
- numero e durata dei gap;
- numero di frame consecutivi mancanti;
- stato: tentative, confirmed, lost, removed;
- continuita osservata;
- qualita/confidence del track separata dalla detector confidence;
- sospetto ID switch;
- motivo di terminazione;
- traiettoria foot point;
- velocita e direzione in image space, marcate come preliminari;
- percentuale di osservazioni `UNKNOWN` per squadra;
- eventuali cambi di team assignment;
- intervalli di occlusione.

### 14.4 Regole di sicurezza semantica

- `track_id` non deve essere chiamato player ID;
- una predizione non deve diventare una detection;
- un punto interpolato non deve alimentare VE-005 senza flag;
- la velocita in pixel non deve essere chiamata velocita reale;
- coordinate stabilizzate e raw non devono essere mescolate;
- un cambio di squadra dentro la stessa traccia deve generare warning;
- gap lunghi devono ridurre la track quality;
- l'incertezza deve propagarsi alle misure geometriche.

---

## 15. Rischi introdotti

### 15.1 Error propagation

Una detection RF-DETR errata puo creare una traccia stabile ma falsa. VE-004
deve conservare la detector confidence e non produrre una confidence unica.

### 15.2 ID switch invisibili

Un cambio ID non rilevato puo alterare velocita, posizione media e distanza tra
reparti. Servono metriche IDF1, HOTA, ID switches, fragmentation e track
continuity su dati annotati.

### 15.3 Team leakage

VE-003 puo assegnare arbitri o portieri a uno dei due cluster. Usare il team come
vincolo rigido troppo presto potrebbe rendere persistente un errore cromatico.
Nella baseline, il team va registrato e usato come segnale diagnostico. Il gating
rigido deve essere un esperimento separato.

### 15.4 Camera motion

Con smartphone e zoom, ByteTrack puo frammentare. Con BoT-SORT, una CMC errata
puo spostare tutte le tracce. Entrambi gli errori devono essere visibili nei
report.

### 15.5 Frame rate

Video a 25, 30 o frame rate variabile cambiano la distanza temporale tra
osservazioni. Le soglie non devono essere tarate solo in numero di frame.

### 15.6 Scene cut e replay

Un tracker non deve attraversare tagli di camera, replay o primi piani. VE-004
necessitera in seguito di segment boundaries, ma questo appartiene alla
progettazione della pipeline e non va anticipato senza benchmark.

### 15.7 Licenze e supply chain

- evitare dipendenze GPL/AGPL senza revisione legale;
- bloccare versione e hash della dipendenza;
- produrre SBOM e avvisi licenza prima dell'integrazione;
- non dipendere dai tipi interni del package nei manifest permanenti;
- mantenere adapter e test di contratto.

---

## 16. Piano di benchmark prima dell'implementazione definitiva

Il primo VE-004 dovrebbe confrontare almeno:

- ByteTrack;
- BoT-SORT senza ReID;
- OC-SORT;
- SORT come controllo minimo, se il costo e contenuto.

Stratificazione video:

1. professionistico, camera fissa;
2. dilettantistico, camera fissa;
3. smartphone stabile;
4. smartphone con pan;
5. zoom;
6. luce difficile;
7. occlusioni dense;
8. palla inattiva con molti giocatori in area;
9. transizione con accelerazioni;
10. ingresso/uscita dal bordo.

Metriche:

- HOTA;
- DetA e AssA;
- IDF1;
- numero ID switch;
- frammentazioni;
- percentuale di track confermate;
- durata media track;
- gap medio e massimo;
- latenza association-only;
- memoria;
- percentuale di osservazioni predicted/interpolated;
- stabilita del `TEAM_A`/`TEAM_B` lungo la traccia;
- errore del foot point rispetto alla ground truth.

La metrica principale per VE-005 non deve essere soltanto MOTA. La priorita e
association quality e continuita verificabile. HOTA, AssA, IDF1 e ID switch sono
piu informativi per la geometria temporale.

Criterio di promozione suggerito:

- ByteTrack resta default se BoT-SORT non migliora chiaramente gli scenari
  smartphone/zoom senza peggiorare camera fissa, latenza e trasparenza;
- BoT-SORT diventa profilo camera-mobile se CMC produce un vantaggio stabile;
- OC-SORT sostituisce ByteTrack solo con miglioramento consistente su AssA/IDF1
  e nessun aumento rilevante di regressioni;
- nessun tracker viene promosso su benchmark professionistici soltanto.

Tutte le soglie sono **da validare durante il benchmark VE-004**.

---

## 17. Dubbi ancora aperti

1. Quale frequenza di detection usera VE-004: ogni frame, frame saltati o sampling
   adattivo?
2. RF-DETR mantiene recall sufficiente con soglie basse nei campi dilettantistici?
3. I video smartphone contengono abbastanza movimento camera da giustificare due
   profili tracker?
4. Qual e la durata massima accettabile di una traccia persa?
5. Come verranno annotate le identita temporali nel benchmark?
6. VE-005 usera foot point raw, stabilizzati o entrambi?
7. Il portiere e l'arbitro devono essere separati prima del tracking o possono
   restare `UNKNOWN`?
8. Il team assignment deve essere un vincolo di association o soltanto un
   segnale di controllo?
9. Come rilevare automaticamente scene cut e replay senza anticipare moduli fuori
   scope?
10. Quale budget CPU/GPU e latenza e accettabile per elaborazione offline?
11. La licenza e la supply chain del package scelto soddisfano i requisiti
    commerciali MatchIQ?
12. VE-005 indica calibrazione del campo, geometria tattica o un contratto
    intermedio ancora da definire?

Questi punti sono da risolvere con un benchmark annotato, non con assunzioni.

---

## 18. Decisione operativa proposta

Quando verra autorizzata l'implementazione:

1. congelare un piccolo benchmark VE-002/VE-003;
2. definire ground truth temporale;
3. creare un adapter tracker separato nel perimetro research;
4. integrare ByteTrack senza modificare RF-DETR;
5. esportare il contratto dati completo;
6. misurare ByteTrack;
7. aggiungere BoT-SORT senza ReID come challenger;
8. aggiungere OC-SORT se il budget sperimentale lo consente;
9. confrontare per sorgente video;
10. scegliere il profilo operativo soltanto dopo le metriche.

Nessun risultato del tracking deve entrare nel prodotto operativo prima di
questa validazione.

---

## 19. Fonti primarie e ufficiali

- ByteTrack, repository ufficiale e paper ECCV 2022:
  <https://github.com/FoundationVision/ByteTrack>
  e <https://arxiv.org/abs/2110.06864>
- BoT-SORT, repository ufficiale e paper:
  <https://github.com/NirAharon/BoT-SORT>
  e <https://arxiv.org/abs/2206.14651>
- OC-SORT, repository ufficiale e paper CVPR 2023:
  <https://github.com/noahcao/OC_SORT>
  e <https://arxiv.org/abs/2203.14360>
- DeepSORT, repository ufficiale:
  <https://github.com/nwojke/deep_sort>
- StrongSORT, repository ufficiale:
  <https://github.com/dyhBUPT/StrongSORT>
- Norfair, repository ufficiale:
  <https://github.com/tryolabs/norfair>
- Roboflow Trackers, repository ufficiale e benchmark:
  <https://github.com/roboflow/trackers>
- BoxMOT, repository ufficiale:
  <https://github.com/mikel-brostrom/boxmot>
- SportsMOT, paper ICCV 2023:
  <https://openaccess.thecvf.com/content/ICCV2023/html/Cui_SportsMOT_A_Large_Multi-Object_Tracking_Dataset_in_Multiple_Sports_Scenes_ICCV_2023_paper.html>
- SoccerNet Tracking:
  <https://www.soccer-net.org/tasks/tracking>

Le informazioni su manutenzione, dipendenze e licenze sono riferite allo stato
visibile delle fonti ufficiali alla data di questa ricerca. Devono essere
ricontrollate prima di aggiungere qualsiasi dipendenza.

---

## 20. Conclusione

La raccomandazione per MatchIQ non e "ByteTrack per sempre". E:

- partire dal tracker piu semplice che usa bene l'output RF-DETR;
- misurare gli errori prima di aggiungere appearance e camera compensation;
- usare BoT-SORT per dimostrare o smentire il valore della CMC;
- conservare coordinate e incertezza per VE-005;
- considerare `UNKNOWN`, track persa e astensione risultati validi;
- scegliere sui video dilettantistici MatchIQ, non soltanto sui benchmark
  pubblici.

ByteTrack offre oggi il miglior equilibrio tra qualita, integrazione, costo,
debug e rischio. BoT-SORT e il candidato piu probabile per un profilo futuro
dedicato a smartphone e zoom. La decisione definitiva deve restare benchmark-
driven.
