# VE-005 - Pitch Calibration Research

## Stato del documento

- **Tipo:** ricerca tecnica pre-implementazione
- **Ambito:** trasformazione delle coordinate immagine prodotte da VE-002, VE-003 e VE-004 in coordinate del campo
- **Dominio prioritario:** calcio dilettantistico, settori giovanili, camera fissa e smartphone
- **Fuori ambito:** implementazione, training, API, frontend, tracking, analisi tattica
- **Decisione richiesta:** architettura consigliata per VE-005B
- **Data di valutazione:** 28 luglio 2026

---

## 1. Executive summary

Per MatchIQ non è consigliabile adottare un singolo metodo accademico come soluzione definitiva. Il dominio reale del prodotto è più difficile dei benchmark broadcast: campi non sempre regolamentari, linee usurate, illuminazione irregolare, riprese da smartphone, zoom, camera inclinata e porzioni limitate di terreno visibili.

La raccomandazione è costruire **una pipeline automatica ibrida e temporale**, composta da:

1. rilevamento semantico di keypoint e linee del campo;
2. stima iniziale robusta dell'omografia con DLT e RANSAC;
3. raffinamento con punti e linee, ispirato all'approccio PnLCalib;
4. continuità temporale e propagazione controllata tra frame appartenenti alla stessa inquadratura;
5. controllo qualità esplicito che possa restituire `UNCALIBRATED` invece di produrre coordinate errate;
6. mapping dei `foot_point` di VE-004 verso coordinate normalizzate e, solo quando le dimensioni reali del terreno sono note o attendibili, verso metri.

La distinzione tra **prototipo di confronto** e **architettura di prodotto** è fondamentale:

- **Baseline pratica consigliata per VE-005B:** TVCalib, perché offre un flusso completo, un esempio pixel-to-world e licenza MIT. Deve essere usato come benchmark tecnico, non assunto come soluzione già valida sul dilettantismo.
- **Riferimento algoritmico consigliato:** approccio ibrido punti + linee di PnLCalib. Il repository è GPL-2.0, quindi il codice non deve essere incorporato nel prodotto proprietario senza valutazione legale; le idee scientifiche possono guidare una implementazione MatchIQ indipendente.
- **Soluzione definitiva raccomandata:** un calibratore MatchIQ proprietario, sequence-aware, addestrato e valutato sul dominio dilettantistico.

L'omografia classica, da sola, non risolve il problema automatico: trasforma coordinate solo dopo che sono state trovate corrispondenze affidabili tra immagine e modello del campo. Il vero problema di VE-005 è quindi riconoscere automaticamente quelle corrispondenze e stabilire quando sono abbastanza affidabili.

### Risposta breve alle domande principali

1. **Soluzione consigliata oggi:** pipeline ibrida punti + linee + raffinamento geometrico + stabilizzazione temporale.
2. **Perché:** combina evidenza locale, struttura globale del campo e continuità del video.
3. **Minor rischio tecnico iniziale:** TVCalib come baseline isolata, accompagnata da un quality gate severo.
4. **Miglior rapporto accuratezza/complessità:** keypoint e linee con DLT/RANSAC iniziale e raffinamento leggero, eseguito su keyframe e propagato nella sequenza.
5. **Integrazione con VE-004:** usare il `foot_point` di ogni track e associare a ogni timestamp una calibrazione valida, propagata o non disponibile.
6. **Supporto a VE-006:** coordinate campo, direzione e velocità metriche, distanze tra giocatori, larghezza, profondità e compattezza, sempre accompagnate da confidence e validità.
7. **Rischi principali:** domain shift broadcast/dilettantismo, dimensioni reali del campo sconosciute, ambiguità destra/sinistra, linee poco visibili, zoom e propagazione di calibrazioni errate.

---

## 2. Contratto reale con VE-002, VE-003 e VE-004

### 2.1 Input disponibile

VE-005 non deve ricostruire detection o tracking. Deve consumare gli output già prodotti:

- VE-002:
  - bounding box in pixel;
  - bounding box normalizzata;
  - confidence della detection;
  - centro della detection;
  - `foot_point`;
  - riferimento al frame.
- VE-003:
  - `TEAM_A`, `TEAM_B` oppure `UNKNOWN`;
  - team confidence;
  - colore dominante e cluster;
  - ROI del busto usata per l'assegnazione.
- VE-004:
  - track ID temporaneo;
  - timestamp;
  - sequenza dei bounding box;
  - sequenza dei `foot_point`;
  - traiettoria e velocità preliminare in spazio immagine.

### 2.2 Punto da proiettare

Per un giocatore il punto corretto da trasformare non è il centro del bounding box, ma il **punto di contatto con il terreno**, già rappresentato da `foot_point`.

Il centro del box varia con:

- altezza apparente del giocatore;
- posa;
- salto;
- occlusione;
- ritaglio del corpo;
- prospettiva.

Il `foot_point` è invece l'approssimazione più coerente della posizione sul piano di gioco. Rimane comunque soggetto a errore quando i piedi sono occlusi o il box è troncato; VE-005 dovrà quindi conservare anche l'incertezza della detection e del tracking.

### 2.3 Output concettuale richiesto a VE-005

Per ogni segmento di camera e per ogni timestamp calibrato, VE-005 dovrà in futuro produrre almeno:

- matrice immagine-verso-campo;
- matrice campo-verso-immagine;
- sistema di coordinate;
- dimensioni del modello di campo utilizzato;
- coordinate normalizzate;
- coordinate metriche, se legittimamente disponibili;
- stato della calibrazione;
- origine della calibrazione: stimata, raffinata, propagata o fallback;
- errore di riproiezione;
- copertura delle linee/keypoint;
- coerenza temporale;
- regione dell'immagine in cui la proiezione è considerata valida;
- confidence della calibrazione;
- motivo di rifiuto, se non calibrata.

Questi campi sono un contratto progettuale per VE-005B, non un'implementazione.

### 2.4 Compatibilità con RF-DETR, Team Assignment e ByteTrack

La calibrazione deve rimanere indipendente dai modelli che hanno generato le osservazioni:

- **RF-DETR:** VE-005 non modifica né riesegue il detector. Consuma esclusivamente bounding box, confidence e `foot_point` già prodotti da VE-002.
- **Team Assignment:** TEAM_A, TEAM_B e UNKNOWN non servono per stimare l'omografia, ma possono aiutare in seguito a risolvere direzione di gioco e orientamento senza contaminare la geometria di base.
- **ByteTrack:** VE-005 conserva gli ID temporanei e trasforma ogni `foot_point` della traiettoria. La calibrazione deve essere associata al timestamp e al camera segment, perché uno stesso track non può usare una matrice diventata obsoleta dopo pan, zoom o cambio inquadratura.

Questo disaccoppiamento permette di sostituire o aggiornare RF-DETR e ByteTrack senza riscrivere il solutore geometrico, purché il contratto di detection e tracking resti stabile.

---

## 3. Il problema tecnico reale

### 3.1 Dalla prospettiva al campo

La maggior parte delle posizioni VE-002/003/004 vive in coordinate pixel. Una omografia permette di trasformare punti appartenenti allo stesso piano tra immagine e modello del terreno.

Per stimarla servono corrispondenze tra:

- elementi riconosciuti nell'immagine;
- elementi semanticamente equivalenti nel modello del campo.

Quattro punti non collineari sono il minimo matematico, ma non il minimo operativo. In un prodotto reale servono:

- più corrispondenze;
- distribuzione spaziale sufficiente;
- gestione degli outlier;
- controllo dell'errore;
- verifica temporale;
- capacità di non rispondere.

### 3.2 Coordinate normalizzate e coordinate reali

È necessario distinguere tre livelli:

1. **Coordinate pixel:** direttamente osservate nel frame.
2. **Coordinate canoniche:** posizione su un modello standard normalizzato, ad esempio lunghezza e larghezza in intervallo 0-1.
3. **Coordinate metriche reali:** posizione in metri sullo specifico campo.

Le coordinate metriche non possono essere garantite se le dimensioni reali del campo non sono note. Nei campi dilettantistici lunghezza e larghezza possono variare entro i limiti regolamentari. Usare sempre 105 x 68 metri produce coordinate coerenti su un campo canonico, ma non necessariamente distanze fisiche esatte.

Pertanto:

- VE-005 deve poter produrre sempre coordinate normalizzate quando la geometria è valida;
- deve definire esplicitamente `canonical_meters` quando usa un modello standard;
- deve usare `physical_meters` solo quando le dimensioni del campo sono note o stimate con attendibilità sufficiente;
- l'inferenza automatica delle dimensioni reali è **da validare durante la raccolta dati**.

### 3.3 Ambiguità

Una singola immagine può essere geometricamente compatibile con più interpretazioni:

- metà campo sinistra o destra;
- camera dietro una porta;
- orientamento invertito;
- centrocampo visto da lati opposti.

SoccerNet considera esplicitamente alcune ambiguità nella propria valutazione. MatchIQ deve risolverle usando la sequenza:

- continuità della camera;
- posizione delle porte;
- direzione prevalente di gioco;
- identità TEAM_A/TEAM_B;
- eventi temporali;
- eventuale informazione pre-partita sul lato di attacco.

Quando l'ambiguità non è risolta, il sistema non deve presentare coordinate orientate come certe.

---

## 4. Famiglie di approcci

### 4.1 Omografia classica

**Meccanismo:** corrispondenze immagine-modello, DLT, RANSAC e raffinamento.

**Punti di forza**

- matematica semplice e ben compresa;
- costo CPU basso dopo il rilevamento delle corrispondenze;
- facile da testare e debuggare;
- integrazione diretta con i `foot_point`.

**Limiti**

- non trova da sola i punti del campo;
- quattro punti manuali violano il flusso automatico richiesto;
- sensibile a corrispondenze concentrate, errate o quasi collineari;
- non gestisce autonomamente distorsione, zoom e cambio camera;
- può produrre una matrice numericamente valida ma semanticamente sbagliata.

**Valutazione MatchIQ:** componente necessaria, ma non soluzione completa.

### 4.2 Metodi classici basati su linee

**Meccanismo:** segmentazione o rilevamento di linee, Hough/contorni, intersezioni e matching con il modello.

**Punti di forza**

- sfruttano molti pixel;
- possono funzionare anche quando gli incroci sono fuori immagine;
- hanno costo contenuto se il rilevamento è tradizionale;
- le linee sono direttamente collegate alla geometria del campo.

**Limiti**

- confondono linee del campo, ombre, strisce del taglio, recinzioni e pubblicità;
- soffrono linee consumate, pioggia e sovraesposizione;
- la semantica della linea rimane difficile;
- cerchio di centrocampo e archi richiedono modelli specifici;
- i metodi puramente handcrafted sono fragili nel dominio smartphone.

**Valutazione MatchIQ:** utili come evidenza complementare e per il raffinamento, non come unico detector.

### 4.3 Metodi basati su keypoint

**Meccanismo:** rilevamento di punti semanticamente noti, poi DLT/RANSAC.

**Punti di forza**

- output direttamente utilizzabile dal solutore geometrico;
- facile attribuire una confidence per punto;
- efficace quando sono visibili intersezioni, angoli dell'area, centrocampo o porte;
- pipeline chiara e debuggabile.

**Limiti**

- pochi punti visibili nelle inquadrature centrali o ravvicinate;
- punti mancanti e falsi positivi possono destabilizzare la stima;
- forte domain shift tra broadcast e campi dilettantistici;
- simmetrie e porzioni ridotte creano ambiguità.

**Valutazione MatchIQ:** buona inizializzazione, da unire alle linee e alla sequenza.

### 4.4 Metodi ibridi punti + linee

**Meccanismo:** keypoint e linee producono una prima calibrazione e una ottimizzazione successiva riduce l'errore globale.

**Punti di forza**

- mantiene una stima quando una delle due fonti è incompleta;
- usa la semantica dei punti e la densità delle linee;
- può includere distorsione e parametri camera;
- adatto a quality gate basati su più segnali.

**Limiti**

- maggiore complessità;
- due detector da mantenere;
- richiede validazione fuori dominio;
- raffinamento non lineare può convergere a soluzioni errate se l'inizializzazione è debole.

**Valutazione MatchIQ:** migliore architettura target.

### 4.5 Metodi temporali

**Meccanismo:** calibrazione di keyframe affidabili, propagazione nel segmento video, smoothing e nuova stima quando camera o zoom cambiano.

**Punti di forza**

- riduce costo e instabilità;
- sfrutta camera fissa;
- recupera frame con poche linee;
- evita oscillazioni nelle coordinate VE-004.

**Limiti**

- una calibrazione sbagliata può propagarsi;
- serve rilevare tagli, pan, tilt e zoom;
- smartphone introduce rolling shutter e movimento brusco;
- la confidence deve decadere nel tempo.

**Valutazione MatchIQ:** indispensabile per trasformare un calibratore di immagini in un modulo video affidabile.

---

## 5. Analisi delle soluzioni

### 5.1 SoccerNet Calibration

SoccerNet fornisce dataset, ontologia di 26 elementi del campo, protocollo di valutazione e baseline. Il dataset dichiarato contiene 400 partite complete broadcast. La baseline ufficiale:

1. segmenta semanticamente le linee con DeepLabv3;
2. ricava estremità e polilinee;
3. stima l'omografia;
4. decompone l'omografia in parametri camera.

Il risultato pubblicato della baseline è modesto: JaC@5 11,7%, completezza 68%, punteggio finale 7,96%. Il repository stesso suggerisce RANSAC, uso delle mask e raffinamento con linee/ellissi come miglioramenti.

**Per MatchIQ**

- valore molto alto come benchmark, tassonomia e formato di annotazione;
- valore medio-basso come soluzione pronta;
- dominio prevalentemente broadcast;
- non dimostra robustezza su smartphone e campi dilettantistici;
- utile per definire metriche di riproiezione e completezza.

### 5.2 KpSFR

KpSFR usa una griglia di keypoint virtuali distribuiti sul campo e un rilevatore condizionato dall'identità del punto. Il repository ufficiale è MIT, ma mostra:

- solo 6 commit;
- dipendenze datate, tra cui PyTorch 1.9 e CUDA 11;
- inferenza dichiarata sui dataset WorldCup e TS-WorldCup;
- limitata evidenza di manutenzione e generalizzazione fuori benchmark.

**Per MatchIQ**

- idea utile per aumentare le corrispondenze in pose diverse;
- licenza favorevole;
- rischio elevato di integrazione diretta e domain shift;
- candidato di confronto, non prima scelta operativa.

### 5.3 TVCalib

TVCalib parte dalla segmentazione semantica dei segmenti del campo, seleziona punti lungo le linee e ottimizza parametri camera minimizzando la perdita di riproiezione. Può valutare omografia e calibrazione 3D e include self-verification tramite la loss.

Il repository ufficiale:

- è MIT;
- fornisce notebook di inferenza;
- include un esempio pixel-to-world;
- fornisce pesi per la segmentazione;
- documenta esecuzione CPU-only e CUDA;
- ha una base di codice relativamente piccola, con 13 commit.

**Per MatchIQ**

- migliore punto di partenza per una baseline sperimentale legalmente semplice;
- integrazione concettuale pulita;
- self-verification utile per restituire `UNCALIBRATED`;
- dipendenza da segmentazione broadcast e validazione insufficiente sul dilettantismo;
- non risolve da solo la continuità temporale.

### 5.4 PnLCalib

PnLCalib combina:

- rilevamento di keypoint;
- rilevamento delle estremità delle linee;
- calibrazione iniziale;
- raffinamento non lineare con punti e linee;
- ottimizzazione della distorsione.

La versione pubblicata nel 2026 dichiara risultati forti nella calibrazione 3D e competitivi nell'omografia su SoccerNet, WorldCup 2014, TS-WorldCup e WorldPose. Il repository è aggiornato e supporta inferenza su immagini/video, ma usa licenza GPL-2.0.

**Per MatchIQ**

- riferimento scientifico più vicino all'architettura desiderata;
- buon equilibrio tra corrispondenze semanticamente forti e linee dense;
- maggiore complessità computazionale e di manutenzione;
- codice non adatto a incorporazione diretta in un prodotto proprietario senza revisione legale;
- i pesi pubblicati restano orientati a distribuzioni broadcast.

La raccomandazione è studiarne paper e protocollo, poi realizzare una implementazione indipendente MatchIQ se i benchmark VE-005B ne confermano il valore.

### 5.5 No Bells, Just Whistles e geometria esplicita

Questa linea di ricerca genera keypoint usando le proprietà geometriche delle linee annotate e impiega solutori classici robusti. Il valore per MatchIQ è metodologico:

- massimizzare l'uso della geometria nota;
- evitare che una rete debba imparare ciò che può essere calcolato;
- combinare predizione e vincoli.

È particolarmente interessante nei casi in cui punti e linee hanno copertura parziale. Le viste centrali, tuttavia, rimangono difficili; lavori successivi mostrano che la geometria del cerchio centrale può recuperare alcuni casi ma non elimina il problema generale.

### 5.6 SoccerNet Game State Reconstruction

Il progetto SoccerNet Game State dimostra che TVCalib e PnLCalib possono essere inseriti in pipeline con detection e tracking per produrre posizioni 2D. È quindi una prova di compatibilità architetturale con una catena simile a:

detector → tracker → team/ruolo → calibrazione → minimappa.

Il repository è GPL-3.0 e non deve essere incorporato direttamente senza valutazione. Per MatchIQ rappresenta soprattutto una reference integration.

### 5.7 Foundation model

I foundation model visuali generici possono aiutare:

- segmentazione del prato;
- segmentazione delle linee;
- selezione di prompt visuali;
- robustezza a condizioni differenti;
- generazione di pseudo-label.

Non risolvono automaticamente:

- identità semantica delle linee;
- corrispondenza con il modello;
- ambiguità di orientamento;
- scala metrica reale;
- quality gate geometrico.

SoccerMaster, presentato nel 2026 come foundation model per il calcio, include la field registration ma continua a ricorrere a detector di keypoint/linee e a un modulo PnL. Questo conferma che un foundation model è un possibile supporto futuro, non un sostituto della geometria.

**Per MatchIQ:** non scegliere un foundation model come nucleo di VE-005B. Valutarlo in una milestone successiva per feature extraction o pseudo-labeling, dopo benchmark su dati autorizzati dilettantistici.

---

## 6. Tabella comparativa completa

Scala qualitativa: **Alta**, **Media**, **Bassa**. Le valutazioni sul dilettantismo sono inferenze tecniche da verificare su dati MatchIQ.

| Metodo | Accuratezza potenziale | Camera fissa | Smartphone | Zoom | Campi dilettantistici | Linee parziali | CPU | GPU | Integrazione VE-004 | Licenza/manutenzione | Rischio MatchIQ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Omografia manuale classica | Alta con punti corretti | Alta | Media | Richiede nuova calibrazione | Alta se i punti sono corretti | Media | Ottima | Non richiesta | Molto semplice | OpenCV permissivo e maturo | Incompatibile con il flusso automatico |
| Linee handcrafted + RANSAC | Bassa-Media | Media | Bassa | Bassa | Bassa | Bassa | Buona | Non richiesta | Semplice | Componenti mature | Ombre, strisce e linee usurate |
| SoccerNet baseline | Bassa come baseline ufficiale | Media | Bassa | Media | Bassa | Media | Media | Consigliata | Media | Repo di ricerca, benchmark maturo | Domain shift e qualità insufficiente |
| KpSFR | Media-Alta sul benchmark | Media | Bassa-Media | Media | Da validare | Media | Bassa | Richiesta in pratica | Media | MIT, dipendenze datate, pochi commit | Manutenzione e generalizzazione |
| TVCalib | Alta nel dominio valutato | Alta | Media | Media con ricalibrazione | Da validare | Alta se segmenti affidabili | Possibile, più lenta | Consigliata | Alta | MIT, codice compatto, manutenzione limitata | Segmentazione broadcast e drift video |
| PnLCalib | Molto alta nel dominio valutato | Alta | Media | Alta con keyframe | Da validare | Alta | Possibile ma costosa | Consigliata | Alta | GPL-2.0, aggiornato nel 2026 | Licenza, complessità e domain shift |
| Geometria centrale/NBJW | Media-Alta in viste adatte | Alta | Media | Media | Da validare | Alta in casi specifici | Media | Consigliata per detector | Alta | Ricerca recente, implementazione non sempre plug-and-play | Copertura non universale |
| SoccerNet Game State stack | Alta come reference integration | Alta | Media | Media | Da validare | Dipende dal calibratore | Media | Consigliata | Molto alta | GPL-3.0, progetto mantenuto | Licenza e stack pesante |
| Foundation model generico | Incerta | Media | Potenzialmente alta | Media | Da validare | Media | Bassa | Alta richiesta | Indiretta | Licenze/pesi variabili | Complessità senza garanzia geometrica |
| **Ibrido temporale MatchIQ** | **Alta, se addestrato sul dominio** | **Molto alta** | **Alta con quality gate** | **Alta con segmentazione camera** | **Target principale** | **Alta tramite propagazione controllata** | **Media su keyframe** | **Consigliata** | **Nativa** | **Proprietaria; dipendenze da selezionare** | **Costo di sviluppo e dataset** |

### Note sulle prestazioni

- La trasformazione omografica dei `foot_point` è economica su CPU.
- Il costo dominante è il detector di linee/keypoint.
- La calibrazione non deve essere eseguita su ogni frame:
  - camera fissa: keyframe iniziale e verifiche periodiche;
  - pan/tilt/zoom: keyframe per segmento e ricalibrazione al cambio;
  - smartphone: frequenza adattiva basata su movimento e quality decay.
- Il raffinamento non lineare può essere eseguito su CPU per pochi keyframe, ma una GPU è consigliabile per il rilevamento.

---

## 7. Robustezza nelle condizioni MatchIQ

### 7.1 Linee non visibili

Strategia raccomandata:

- non forzare una nuova calibrazione;
- usare un keyframe affidabile precedente nello stesso segmento;
- propagare con confidence decrescente;
- verificare la coerenza con optical flow o trasformazione globale della camera;
- tornare `UNCALIBRATED` quando la propagazione supera soglie temporali o geometriche.

### 7.2 Solo metà campo visibile

Una metà campo può essere calibrabile se:

- sono riconosciuti elementi semanticamente distintivi;
- le corrispondenze coprono una regione sufficiente;
- l'orientamento è risolto dalla sequenza.

Rischi:

- simmetria;
- porta sinistra/destra;
- extrapolazione lontano dalla regione osservata.

La regione valida della proiezione deve essere esplicita. Una calibrazione buona vicino all'area non deve essere automaticamente considerata affidabile sull'altra metà campo.

### 7.3 Telecamera storta

Una calibrazione completa può stimare roll e prospettiva. Prima del mapping non conviene “raddrizzare” l'immagine con una regola grafica separata: il roll deve entrare nel modello geometrico. Una pre-rotazione può essere usata solo come inizializzazione, non come correzione definitiva.

### 7.4 Ombre e illuminazione

Le soglie colore handcrafted non sono sufficienti. Servono:

- segmentazione semantica;
- augmentation con ombre, controluce, sovraesposizione e temperatura colore;
- normalizzazione fotometrica moderata;
- consenso temporale;
- quality gate basato sulla geometria, non sulla sola confidence della rete.

### 7.5 Pioggia

La pioggia riduce contrasto e nitidezza e introduce riflessi. Il sistema deve:

- privilegiare keyframe meno degradati;
- integrare evidenza su più frame;
- non interpretare la stabilità temporale come prova di correttezza se le linee non sono visibili;
- abbassare la confidence o rifiutare.

### 7.6 Zoom

Lo zoom modifica i parametri intrinseci e rende obsoleta una calibrazione precedente. VE-005 deve:

- rilevare il cambio di scala globale;
- aprire un nuovo camera segment;
- ricalibrare;
- evitare di propagare una matrice attraverso uno zoom significativo.

### 7.7 Porzioni di campo mancanti

Quando l'inquadratura non contiene geometria sufficiente:

- non generare coordinate nuove;
- mantenere temporaneamente l'ultima calibrazione solo se il movimento camera è stimabile;
- dichiarare l'origine `propagated`;
- far decadere la confidence;
- escludere le coordinate da VE-006 oltre la soglia.

### 7.8 Smartphone

Le criticità specifiche sono:

- pan bruschi;
- zoom digitale;
- autofocus;
- rolling shutter;
- orizzonte inclinato;
- frame mossi;
- giocatori grandi che coprono le linee.

Per smartphone il modello singolo-frame deve essere affiancato da:

- shot/camera-motion segmentation;
- selezione dei keyframe più nitidi;
- stima temporale;
- ricalibrazione frequente ma adattiva;
- rifiuto esplicito.

---

## 8. Separazione delle confidence

VE-005 non deve esporre una percentuale generica. Deve distinguere:

### 8.1 Detection confidence

Quanto il modello crede di avere riconosciuto un keypoint o una linea.

Non misura la correttezza della calibrazione finale.

### 8.2 Geometric confidence

Qualità della soluzione geometrica:

- errore di riproiezione;
- numero di corrispondenze;
- distribuzione spaziale;
- condizionamento;
- numero di inlier;
- copertura semantica.

### 8.3 Temporal confidence

Coerenza della calibrazione nel segmento video:

- stabilità dei parametri;
- drift;
- continuità delle traiettorie;
- compatibilità con il movimento camera.

### 8.4 Domain confidence

Quanto il frame assomiglia ai dati su cui il detector è stato validato:

- camera broadcast;
- camera fissa dilettantistica;
- smartphone;
- notte;
- pioggia;
- linee usurate.

### 8.5 Calibration status

Stati raccomandati:

- `VALIDATED`: qualità sufficiente e coerente;
- `ESTIMATED`: nuova calibrazione plausibile, non ancora confermata temporalmente;
- `PROPAGATED`: derivata da un keyframe precedente;
- `AMBIGUOUS`: geometria plausibile ma orientamento non risolto;
- `UNCALIBRATED`: evidenza insufficiente;
- `REJECTED`: soluzione trovata ma fallita ai controlli.

VE-006 deve consumare solo stati e soglie esplicitamente autorizzati.

---

## 9. Integrazione con VE-004

### 9.1 Flusso consigliato

1. VE-004 produce track e `foot_point` nel tempo.
2. VE-005 divide il video in segmenti omogenei di camera.
3. Su keyframe selezionati rileva linee e keypoint.
4. Stima e raffina la calibrazione.
5. Verifica qualità geometrica e temporale.
6. Propaga la calibrazione nei frame intermedi.
7. Trasforma i `foot_point`.
8. Associa coordinate e confidence a ogni osservazione del track.

### 9.2 Perché calibrare dopo il tracking

L'ordine attuale è corretto:

- il tracker funziona in pixel;
- non dipende dalla calibrazione;
- la calibrazione può usare traiettorie e stabilità come segnale di controllo;
- una calibrazione rifiutata non distrugge i track.

### 9.3 Informazioni da conservare per track

Per ogni osservazione futura:

- track ID;
- team assignment;
- timestamp;
- `foot_point_pixel`;
- `pitch_position_normalized`;
- `pitch_position_canonical_meters`;
- `pitch_position_physical_meters`, se disponibile;
- calibration status;
- calibration confidence;
- camera segment ID;
- validità della regione;
- eventuale motivo di esclusione.

---

## 10. Come VE-005 abilita VE-006

VE-006 potrà costruire geometria tattica solo dopo VE-005. Le coordinate campo permetteranno:

- distanze tra giocatori;
- distanza tra reparti;
- larghezza e profondità;
- baricentro;
- compattezza;
- altezza della linea;
- occupazione delle corsie;
- densità attorno alla palla;
- velocità e direzione reali;
- sincronizzazione tra TEAM_A e TEAM_B;
- mappe di posizione.

### Vincoli per VE-006

VE-006 non deve:

- usare coordinate calibrate senza status/confidence;
- confrontare metri canonici e metri fisici come se fossero equivalenti;
- derivare velocità attraverso un cambio di camera;
- colmare buchi lunghi con interpolazione;
- trasformare una ambiguità geometrica in una conclusione tattica.

### Requisito centrale

VE-005 deve produrre non soltanto coordinate, ma anche **la prova della loro affidabilità**. Senza questo contratto, VE-006 genererebbe metriche precise nell'aspetto ma non attendibili.

---

## 11. Classifica finale

### 11.1 Classifica per adozione immediata come baseline

1. **TVCalib**
   - licenza MIT;
   - pipeline completa;
   - pixel-to-world già dimostrato;
   - self-verification;
   - rischio di integrazione controllabile.
2. **PnLCalib**
   - miglior riferimento tecnico;
   - codice aggiornato;
   - penalizzato da GPL-2.0 e maggiore complessità.
3. **KpSFR**
   - MIT e concetto interessante;
   - dipendenze datate e inferenza molto legata ai dataset supportati.
4. **SoccerNet baseline**
   - eccellente benchmark;
   - qualità insufficiente come calibratore di prodotto.
5. **Omografia/linee classiche**
   - utili come fallback diagnostico;
   - non risolvono l'automazione.

### 11.2 Classifica per architettura target

1. **Ibrido temporale MatchIQ: punti + linee + raffinamento + quality gate**
2. **PnLCalib-like con implementazione indipendente e adattamento dilettantistico**
3. **TVCalib-like con segmenti e ottimizzazione di riproiezione**
4. **Keypoint-aware con geometria esplicita**
5. **Line segmentation + omografia**
6. **Foundation model come soluzione autonoma**

---

## 12. Metodo consigliato

### Decisione

Per VE-005B si raccomanda:

> **TVCalib come baseline di confronto, seguita da un prototipo MatchIQ ibrido che combina keypoint, linee, DLT/RANSAC, raffinamento geometrico e continuità temporale.**

### Perché è il migliore per MatchIQ

1. Non richiede quattro click all'utente.
2. Funziona naturalmente con i `foot_point` VE-004.
3. Sfrutta la camera fissa senza dipendere da essa.
4. Può ricalibrare su pan, tilt e zoom.
5. Può restituire `UNCALIBRATED` nei casi pericolosi.
6. Può essere addestrato sul dominio proprietario dilettantistico.
7. Separa l'algoritmo di rilevamento dalla geometria.
8. Permette benchmark progressivi contro TVCalib e PnLCalib.
9. Prepara un contratto affidabile per VE-006.

### Minor rischio tecnico

Il minor rischio non è il metodo con meno righe di codice, ma quello che:

- ha un benchmark riproducibile;
- fallisce in modo esplicito;
- non obbliga l'utente;
- non contamina VE-004;
- non introduce vincoli di licenza incompatibili.

Per questo la baseline TVCalib MIT con quality gate è il primo passo più prudente. La soluzione finale dovrà comunque essere verificata sui video MatchIQ.

### Miglior rapporto accuratezza/complessità

Il punto di equilibrio è:

- detector keypoint + linee;
- DLT/RANSAC per inizializzazione;
- un solo raffinamento per keyframe;
- propagazione temporale;
- ricalibrazione solo quando cambia la camera o decade la qualità.

Eseguire un modello pesante e un'ottimizzazione completa su ogni frame aumenterebbe costi e latenza senza un beneficio proporzionato.

---

## 13. Rischi

### 13.1 Domain shift

Tutti i principali metodi pubblici sono valutati soprattutto su broadcast professionale. Il comportamento su:

- tribune basse;
- camere decentrate;
- smartphone;
- campi sintetici o scoloriti;
- illuminazione serale;
- marcature non perfette;

è **da validare durante la raccolta dati**.

### 13.2 Licenze

- TVCalib: MIT, favorevole.
- KpSFR: MIT, favorevole ma stack datato.
- PnLCalib: GPL-2.0, richiede valutazione legale prima di qualsiasi incorporazione.
- SoccerNet Game State: GPL-3.0, reference integration ma rischio per prodotto proprietario.
- Dataset, pesi e video possono avere termini distinti dalla licenza del codice.

Ogni dipendenza e peso deve essere verificato separatamente prima dell'implementazione.

### 13.3 Falsa precisione

Coordinate in metri possono sembrare esatte pur derivando da:

- campo canonico errato;
- foot point impreciso;
- calibrazione ambigua;
- zoom non rilevato;
- propagazione troppo lunga.

Ogni metrica deve conservare provenienza e incertezza.

### 13.4 Drift temporale

La propagazione migliora copertura ma può accumulare errore. Servono:

- keyframe periodici;
- trigger di ricalibrazione;
- confronto della riproiezione;
- confidence decay;
- reset ai cambi di camera.

### 13.5 Costi

L'inferenza GPU è consigliata per i detector. Il costo deve essere limitato con:

- inferenza su keyframe;
- batching;
- segmentazione camera;
- cache dei risultati;
- riuso della calibrazione quando valida.

### 13.6 Orientamento squadra

VE-003 separa le squadre ma non determina automaticamente quale attacca verso una porta. Questa informazione richiede sequenza, evento, porta visibile o un segnale iniziale. È **da validare durante la raccolta dati**.

---

## 14. Dubbi ancora aperti

1. Qual è la distribuzione reale delle camere MatchIQ tra fissa, smartphone e broadcast?
2. Quanto spesso le dimensioni effettive del campo sono disponibili?
3. Quale accuratezza metrica è necessaria per VE-006?
4. Quale percentuale di tempo può legittimamente restare `UNCALIBRATED`?
5. Quanto è stabile TVCalib su campi dilettantistici non presenti nei benchmark?
6. Quanto migliorano PnL refinement e lens distortion sui video MatchIQ?
7. È sufficiente un modello unico o servono profili camera distinti?
8. Come rilevare in modo robusto zoom digitale e rolling shutter?
9. Quale frequenza di keyframe minimizza costo e drift?
10. Le porte e i pali devono diventare una fonte aggiuntiva di corrispondenze?
11. Come trattare campi con dimensioni non note senza presentare metri falsamente reali?
12. Quale protocollo di annotazione serve per il benchmark dilettantistico VE-005?

Tutte queste decisioni sono **da validare durante la raccolta dati**.

---

## 15. Roadmap consigliata per VE-005B

### Milestone 0 - Contratto e benchmark

- congelare formato input VE-004;
- definire coordinate canoniche e fisiche;
- definire status e confidence;
- creare benchmark professionistico e dilettantistico autorizzato;
- annotare punti/linee e omografie di riferimento;
- definire metriche: reprojection error, completezza, stabilità temporale, errore posizione giocatore.

**Criterio di uscita:** benchmark ripetibile, senza integrazione prodotto.

### Milestone 1 - Baseline TVCalib isolata

- eseguire TVCalib fuori dal runtime operativo;
- verificare licenza, pesi e dipendenze;
- misurare accuratezza e tasso di rifiuto;
- salvare output diagnostici;
- confrontare broadcast, camera fissa e smartphone.

**Criterio di uscita:** baseline numerica reale sui video MatchIQ.

### Milestone 2 - Quality gate

- definire errore di riproiezione;
- copertura minima;
- distribuzione spaziale;
- coerenza con modello del campo;
- status `VALIDATED`, `AMBIGUOUS`, `UNCALIBRATED`;
- impedire coordinate quando la qualità è insufficiente.

**Criterio di uscita:** nessuna calibrazione palesemente errata accettata nel benchmark.

### Milestone 3 - Segmentazione temporale della camera

- rilevare tagli;
- rilevare pan/tilt;
- rilevare zoom;
- creare camera segment;
- selezionare keyframe;
- propagare con confidence decay.

**Criterio di uscita:** coordinate stabili dentro un segmento e reset corretto ai cambi.

### Milestone 4 - Baseline ibrida MatchIQ

- keypoint e linee;
- inizializzazione DLT/RANSAC;
- raffinamento geometrico indipendente;
- confronto con TVCalib e PnLCalib;
- nessuna incorporazione di codice GPL senza autorizzazione.

**Criterio di uscita:** miglioramento misurabile su dilettantismo senza regressione sul broadcast.

### Milestone 5 - Mapping VE-004

- trasformare `foot_point`;
- conservare coordinate pixel e campo;
- invalidare osservazioni fuori regione;
- interpolare solo buchi brevi;
- misurare jitter e velocità.

**Criterio di uscita:** traiettorie campo coerenti e accompagnate da confidence.

### Milestone 6 - Adattamento al dominio

- raccogliere errori e hard negative;
- annotare camera fissa e smartphone;
- fine-tuning del detector;
- augmentation meteo/luce;
- calibrazione della confidence.

**Criterio di uscita:** prestazioni separate e documentate per ogni dominio.

### Milestone 7 - Readiness VE-006

- definire soglie accettate da VE-006;
- distinguere metri canonici e reali;
- risolvere orientamento;
- versionare il calibratore;
- produrre audit trail per ogni coordinata.

**Criterio di uscita:** VE-006 può rifiutare dati non affidabili senza ambiguità.

---

## 16. Fonti primarie

### Dataset, benchmark e protocolli

- [SoccerNet Camera Calibration Challenge](https://github.com/SoccerNet/sn-calibration)
- [A Universal Protocol to Benchmark Camera Calibration for Sports](https://arxiv.org/abs/2404.09807)
- [SoccerNet Game State Reconstruction](https://github.com/SoccerNet/sn-gamestate)

### Metodi

- [TVCalib - repository ufficiale](https://github.com/MM4SPA/tvcalib)
- [TVCalib - paper WACV 2023](https://openaccess.thecvf.com/content/WACV2023/papers/Theiner_TVCalib_Camera_Calibration_for_Sports_Field_Registration_in_Soccer_WACV_2023_paper.pdf)
- [PnLCalib - repository ufficiale](https://github.com/mguti97/PnLCalib)
- [PnLCalib - paper](https://arxiv.org/abs/2404.08401)
- [KpSFR - repository ufficiale](https://github.com/ericsujw/KpSFR)
- [Sports Field Registration via Keypoints-Aware Label Condition](https://openaccess.thecvf.com/content/CVPR2022W/CVSports/papers/Chu_Sports_Field_Registration_via_Keypoints-Aware_Label_Condition_CVPRW_2022_paper.pdf)
- [No Bells, Just Whistles](https://openaccess.thecvf.com/content/CVPR2024W/CVsports/papers/Gutierrez-Perez_No_Bells_Just_Whistles_Sports_Field_Registration_by_Leveraging_Geometric_CVPRW_2024_paper.pdf)
- [Can Geometry Save Central Views for Sports Field Registration?](https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Magera_Can_Geometry_Save_Central_Views_for_Sports_Field_Registration_CVPRW_2025_paper.pdf)

### Foundation model

- [SoccerMaster: A Vision Foundation Model for Soccer Understanding](https://openaccess.thecvf.com/content/CVPR2026/papers/Yang_SoccerMaster_A_Vision_Foundation_Model_for_Soccer_Understanding_CVPR_2026_paper.pdf)

---

## 17. Decisione finale

VE-005B non dovrebbe iniziare implementando subito “la calibrazione definitiva”.

Deve iniziare con:

1. benchmark MatchIQ;
2. baseline TVCalib isolata;
3. quality gate;
4. segmentazione temporale;
5. mapping controllato dei `foot_point`;
6. confronto con una implementazione ibrida indipendente.

La decisione più importante è impedire che una matrice numericamente valida venga trattata come verità tattica. Per MatchIQ è preferibile non produrre coordinate in una parte del video piuttosto che alimentare VE-006 con posizioni sbagliate.

La calibrazione manuale può rimanere un fallback futuro per utenti avanzati, ma non deve essere il flusso principale.
