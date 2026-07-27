# MatchIQ Tactical Moment Selection

## Documento di progettazione della pipeline V3.1

Data: 2026-07-27
Stato: design architetturale, non implementato
Documento di partenza: `docs/vision-engine-current-pipeline-audit.md`

---

## 0. Scopo e confini

Questo documento definisce l'architettura concettuale della futura pipeline
Tactical Moment Selection. Il suo obiettivo e stabilire come MatchIQ dovra
passare dalla selezione di fotogrammi statici alla selezione di momenti calcistici
temporalmente coerenti, tatticamente utili e verificabili dallo staff.

Il documento non introduce codice, classi, endpoint, database, modelli o nuove
funzioni nel prodotto. Non decide ancora quale detector, tracker o framework
utilizzare. Definisce invece:

- cosa deve essere osservato;
- quali informazioni devono essere separate;
- come deve essere delimitato un momento tattico;
- quali scene devono essere escluse;
- come deve essere misurata l'affidabilita;
- come il feedback umano deve diventare patrimonio proprietario;
- quali milestone devono precedere l'integrazione di RF-DETR.

### Principi non negoziabili

1. L'unita di analisi e il momento, non il fotogramma.
2. Una buona immagine non e necessariamente una buona evidenza tattica.
3. Una categoria plausibile non e necessariamente una categoria corretta.
4. Ogni score deve avere un solo significato.
5. La mancanza di evidenza deve produrre astensione, non sicurezza artificiale.
6. Il sistema deve spiegare perche propone un momento.
7. Lo staff conserva l'ultima parola.
8. Le correzioni umane devono essere versionate e riutilizzabili per benchmark.
9. Detector, tracking e calibrazione devono essere valutati separatamente.
10. Un momento non deve entrare nel report solo perche visivamente gradevole.

---

## 1. Perche il frame statico e insufficiente

Un frame descrive una configurazione visiva istantanea, ma il calcio e un sistema
dinamico. Molti concetti tattici esistono soltanto nel rapporto tra cio che
accade prima, durante e dopo una configurazione.

### 1.1 Il frame non contiene la direzione dell'azione

Da una sola immagine spesso non e possibile stabilire:

- quale squadra stia avanzando;
- se il pallone sia appena stato recuperato o perso;
- se un giocatore stia attaccando o abbandonando uno spazio;
- se la linea difensiva stia salendo, scappando o sia ferma;
- se la pressione sia coordinata o casuale;
- se la squadra sia in costruzione o in semplice possesso sterile.

Due frame quasi identici possono appartenere a eventi tatticamente opposti.

### 1.2 Il frame confonde stato e transizione

Un'immagine puo mostrare giocatori vicini e venire interpretata come pressing.
Senza i secondi precedenti e successivi non si sa se:

- la distanza e stata chiusa intenzionalmente;
- il portatore ha ricevuto pressione;
- la squadra ha orientato il gioco;
- la pressione ha prodotto un recupero;
- la densita e dovuta a una rimessa o a un fermo immagine televisivo.

Il pressing non e una forma geometrica: e un comportamento nel tempo.

### 1.3 Il frame non distingue causa ed effetto

Una linea difensiva bassa puo essere:

- una scelta organizzata;
- la conseguenza di una transizione negativa;
- una situazione da palla inattiva;
- il momento successivo a una respinta;
- un'immagine presa durante un replay.

La sola disposizione non permette di ricostruire la causa.

### 1.4 Il frame sovrastima la qualita visiva

Campo ampio, luce corretta, contrasto e molti pixel verdi rendono un frame
editorialmente gradevole. Questi elementi non garantiscono:

- presenza della palla;
- leggibilita delle due squadre;
- completezza dei reparti;
- rilevanza per il focus scelto;
- continuita dell'azione;
- utilita per una decisione tecnica.

Per questo Technical Quality e Tactical Value devono restare separati.

### 1.5 Il frame e vulnerabile alla regia televisiva

Replay, primi piani, esultanze, pubblico, panchina e grafiche possono avere una
qualita visiva molto alta. Un selettore che premia nitidezza e contrasto puo
preferirli a una ripresa tattica piu distante ma realmente utile.

### 1.6 Il frame non misura l'esito

Per un allenatore e importante sapere se una situazione:

- ha superato la prima pressione;
- ha creato superiorita;
- ha portato a una rifinitura;
- ha costretto a un passaggio all'indietro;
- ha generato una perdita o un recupero;
- ha prodotto un tiro o una transizione.

L'esito vive dopo il frame rappresentativo.

### 1.7 Conseguenza progettuale

Il frame deve diventare:

- un'anteprima del momento;
- un punto di accesso alla sequenza;
- un'immagine rappresentativa per slide e report;
- una fonte di controllo visivo.

Non deve piu essere considerato, da solo, la prova completa della categoria
tattica.

---

## 2. Perche il calcio deve essere analizzato come sequenza

Una sequenza consente di osservare cambiamenti, relazioni e risultati. La nuova
pipeline deve ragionare su finestre temporali sufficientemente lunghe da
descrivere un'azione, ma abbastanza corte da restare revisionabili.

### 2.1 Informazioni disponibili solo nel tempo

Una sequenza rende osservabili:

- direzione del possesso;
- velocita di avanzamento;
- origine e destinazione del pallone;
- movimenti coordinati di reparto;
- altezza della pressione;
- cambiamenti nelle distanze;
- occupazione e liberazione degli spazi;
- salita o discesa della linea;
- ampiezza e profondita dinamiche;
- rottura di una linea;
- recupero, perdita e seconda palla;
- esito dell'azione.

### 2.2 Struttura minima: prima, evento, dopo

Ogni candidato deve comprendere tre porzioni logiche:

- **Contesto precedente:** mostra come nasce la situazione.
- **Evento centrale:** contiene il comportamento da classificare.
- **Conseguenza:** mostra il risultato immediato.

Una clip senza contesto precedente rischia di perdere la causa. Una clip senza
conseguenza non permette di valutarne l'efficacia.

### 2.3 Continuita e identita

La sequenza consente di verificare se gli stessi giocatori e la stessa palla
restano osservabili. Questo riduce errori dovuti a:

- stacchi di regia;
- replay;
- cambio camera;
- dissolvenze;
- sovrimpressioni;
- immagini di reazione;
- interruzioni del gioco.

### 2.4 Dipendenza dalla categoria

Non tutte le categorie richiedono la stessa durata:

- una rimessa laterale puo essere compresa in pochi secondi;
- una costruzione dal basso richiede origine, sviluppo e superamento;
- una transizione richiede perdita/recupero e risposta successiva;
- un blocco difensivo richiede stabilita per piu secondi;
- una palla inattiva richiede preparazione, battuta e prima conseguenza.

La durata deve quindi adattarsi alla dinamica osservata.

### 2.5 Principio di astensione

Se la sequenza:

- inizia troppo tardi;
- termina prima dell'esito;
- contiene un cambio camera;
- perde la palla;
- non mostra abbastanza campo;
- non consente di distinguere le squadre;

il sistema deve ridurre Sequence Confidence o astenersi dalla classificazione.

---

## 3. Nuova pipeline ideale

La pipeline di riferimento e:

**Video**

↓

**Candidate Moments**

↓

**Sequence Analysis**

↓

**Tactical Score**

↓

**Editorial Score**

↓

**AI Interpretation**

↓

**Review umana**

↓

**Report**

Le fasi devono essere indipendenti e osservabili. Un errore in una fase non deve
essere nascosto dentro un'unica percentuale finale.

### 3.1 Video

Responsabilita concettuali:

- validare durata e integrita;
- rilevare risoluzione, frame rate e orientamento;
- individuare eventuali discontinuita;
- mantenere il riferimento temporale originale;
- preservare il legame con proprietario, partita e contesto dichiarato.

Output concettuale:

- video identificato;
- timeline stabile;
- metadati tecnici;
- eventuali avvisi di qualita;
- vincoli di utilizzo dichiarati.

Il video non riceve ancora un giudizio tattico.

### 3.2 Candidate Moments

Questa fase individua zone temporali potenzialmente interessanti. Non assegna
ancora una verita tattica definitiva.

Le sorgenti future dei candidati potranno comprendere:

- variazioni nel possesso;
- accelerazioni della palla;
- cambiamenti nella densita dei giocatori;
- entrata o uscita da zone del campo;
- restart;
- interruzioni;
- cambi camera;
- picchi di pressione;
- superamento di linee;
- ingresso nell'ultimo terzo;
- eventi dichiarati dallo staff;
- timestamp provenienti da Coach o Voice Coach.

Ogni candidato deve conservare:

- inizio provvisorio;
- centro provvisorio;
- fine provvisoria;
- motivo della candidatura;
- segnali che lo hanno generato;
- eventuali segnali contrari;
- provenienza dei segnali.

Questa fase deve preferire recall: e accettabile generare candidati in eccesso,
purche le fasi successive possano scartarli in modo trasparente.

### 3.3 Sequence Analysis

Questa fase verifica la coerenza temporale del candidato.

Deve chiedere:

- la camera resta tatticamente utile?
- la palla e osservabile?
- le squadre restano distinguibili?
- i track sono sufficientemente continui?
- esiste un evento iniziale riconoscibile?
- esiste una conseguenza osservabile?
- il candidato contiene piu azioni diverse?
- i confini temporali devono essere estesi o ristretti?

Output concettuale:

- momento temporalmente rifinito;
- frame rappresentativo;
- Sequence Confidence;
- indicatori di continuita;
- motivo di eventuale astensione.

### 3.4 Tactical Score

Questa fase misura l'utilita calcistica del momento rispetto a:

- focus selezionato;
- squadra osservata;
- fase di gioco;
- completezza delle relazioni tra reparti;
- presenza di causa, comportamento ed esito;
- chiarezza della struttura;
- ripetibilita del comportamento;
- potenziale valore per allenamento o decisione.

Il Tactical Score non misura la bellezza dell'immagine.

### 3.5 Editorial Score

Questa fase stabilisce se il momento puo essere presentato bene:

- in review;
- in una slide;
- in un report;
- in una riunione;
- in un'esportazione.

Valuta inquadratura, nitidezza, stabilita, leggibilita e possibilita di tracciare
annotazioni. Non decide se la categoria tattica e corretta.

Editorial Score e il nome architetturale della futura valutazione editoriale.
Non deve essere mostrato come attendibilita tattica.

### 3.6 AI Interpretation

L'interpretazione AI riceve soltanto momenti che hanno superato i controlli
tecnici e temporali minimi.

Deve produrre:

- categoria proposta;
- eventuale sottocategoria;
- squadra osservata;
- spiegazione fondata sui segnali disponibili;
- evidenze a favore;
- evidenze mancanti;
- interpretazioni alternative;
- AI Confidence;
- proposta di utilizzo: review, slide, report o scarto;
- eventuale suggerimento di annotazione.

L'AI deve poter rispondere "evidenza insufficiente".

### 3.7 Review umana

La review non deve essere un semplice controllo formale. Deve validare
separatamente:

- confini temporali;
- categoria;
- squadra;
- descrizione;
- frame rappresentativo;
- valore tattico;
- idoneita editoriale;
- linee e annotazioni.

La decisione umana deve essere registrata senza sovrascrivere la proposta
originale.

### 3.8 Report

Il report deve utilizzare soltanto:

- momenti approvati;
- momenti corretti;
- evidenze esplicitamente accettate;
- descrizioni coerenti con la review;
- limiti e livelli di confidenza separati.

I momenti scartati possono alimentare benchmark e dataset, ma non il documento
finale.

---

## 4. Separazione degli score

La nuova pipeline deve vietare una percentuale generica chiamata semplicemente
"confidence". Ogni score deve dichiarare oggetto, origine e significato.

### 4.1 Technical Quality

**Domanda a cui risponde:** il materiale e tecnicamente analizzabile?

Misura:

- nitidezza;
- esposizione;
- contrasto utile;
- risoluzione effettiva;
- stabilita;
- occlusione;
- continuita della camera;
- presenza di grafiche invasive;
- porzione di campo visibile;
- degradazioni di compressione.

Non misura:

- correttezza tattica;
- importanza dell'azione;
- qualita della squadra;
- probabilita della categoria.

Uso:

- filtro tecnico iniziale;
- scelta del frame rappresentativo;
- avviso allo staff;
- idoneita per annotazioni e report.

### 4.2 Tactical Value

**Domanda a cui risponde:** quanto e utile questo momento per un allenatore o
match analyst rispetto al focus richiesto?

Misura:

- pertinenza con il focus;
- leggibilita delle relazioni collettive;
- presenza della palla e delle squadre rilevanti;
- completezza causa-comportamento-esito;
- osservabilita dei reparti;
- chiarezza del principio tattico;
- valore decisionale;
- potenziale trasferibilita in allenamento;
- rilevanza rispetto ad altri momenti della stessa partita.

Non misura:

- certezza del modello;
- qualita estetica;
- precisione del tracking.

Tactical Value deve essere assegnato soltanto dopo la Sequence Analysis.

### 4.3 Sequence Confidence

**Domanda a cui risponde:** quanto e affidabile la ricostruzione temporale di
questo momento?

Misura:

- continuita dei track;
- continuita della palla;
- assenza di stacchi incompatibili;
- chiarezza di inizio e fine;
- presenza del contesto precedente;
- presenza della conseguenza;
- coerenza del possesso;
- stabilita della categoria lungo la finestra;
- assenza di contaminazione con un secondo evento.

Non misura:

- valore tattico;
- gradevolezza del frame;
- sicurezza linguistica dell'AI.

Una Sequence Confidence bassa deve impedire dichiarazioni temporali forti.

### 4.4 AI Confidence

**Domanda a cui risponde:** quanto l'interprete AI considera supportata la propria
categoria e spiegazione dai dati ricevuti?

Misura:

- coerenza tra segnali strutturati e categoria;
- disponibilita delle evidenze richieste;
- distanza rispetto alle interpretazioni alternative;
- completezza del contesto;
- assenza di segnali contraddittori.

Non misura direttamente:

- verita tattica;
- accuratezza calibrata sul mondo reale;
- qualita tecnica;
- continuita del tracking.

AI Confidence deve essere calibrata in futuro su esempi annotati. Prima della
calibrazione deve essere presentata come sicurezza interna dell'interpretazione,
non come probabilita di verita.

### 4.5 Editorial Score

**Domanda a cui risponde:** questo momento e pronto per essere mostrato?

Misura:

- chiarezza del frame rappresentativo;
- leggibilita su schermo e PDF;
- spazio per annotazioni;
- assenza di elementi televisivi distraenti;
- inquadratura comprensibile senza lunga spiegazione;
- durata adatta alla review;
- valore narrativo nel report.

Non misura:

- correttezza della categoria;
- valore allenante;
- affidabilita del detector.

### 4.6 Regole di presentazione

- Gli score non devono essere sommati in una percentuale unica.
- Nessuno score deve sostituire un altro.
- Ogni score deve avere un'etichetta testuale.
- Un valore alto deve poter convivere con un altro valore basso.
- Le cause di penalizzazione devono essere consultabili.
- Le soglie devono essere versionate e valutate su benchmark.
- I valori non calibrati non devono essere descritti come accuratezza.

Esempio concettuale:

| Dimensione | Valore possibile | Interpretazione |
|---|---:|---|
| Technical Quality | alta | immagine leggibile |
| Tactical Value | basso | momento poco utile |
| Sequence Confidence | alta | confini temporali chiari |
| AI Confidence | media | due categorie plausibili |
| Editorial Score | alto | ottimo per una slide, se approvato |

Questo esempio dimostra perche un solo "85%" sarebbe ambiguo.

---

## 5. Nuova definizione di Momento Tattico

Un **Momento Tattico** e una finestra video continua, delimitata da un'origine
osservabile e da una conseguenza immediata, nella quale una o entrambe le squadre
manifestano un comportamento collettivo pertinente a un principio di gioco.

Non e:

- un singolo frame;
- una scena semplicemente gradevole;
- una clip arbitraria attorno a un timestamp;
- un evento nominale senza evidenza;
- una descrizione generata senza continuita temporale.

### 5.1 Componenti obbligatorie

Un momento deve contenere, quando la categoria lo richiede:

1. **Trigger:** cio che avvia il comportamento.
2. **Organizzazione:** come la squadra si dispone o reagisce.
3. **Sviluppo:** come cambiano palla, spazi e relazioni.
4. **Esito immediato:** che cosa produce il comportamento.

Se una componente non e visibile, deve essere indicata come mancante.

### 5.2 Durata ideale

La durata non deve essere fissa. Intervallo progettuale generale:

- minimo operativo: circa 4 secondi;
- durata tipica: 8-18 secondi;
- durata estesa: fino a 25-30 secondi quando necessaria;
- oltre 30 secondi: probabile presenza di piu momenti, da segmentare.

Durate indicative per famiglia:

| Famiglia | Contesto prima | Evento e conseguenza | Durata tipica |
|---|---:|---:|---:|
| Rimessa laterale | 2-4 s | 4-8 s | 6-12 s |
| Calcio d'angolo | 3-6 s | 5-10 s | 8-16 s |
| Punizione | 3-6 s | 5-12 s | 8-18 s |
| Costruzione dal basso | 3-5 s | 10-20 s | 13-25 s |
| Pressing | 3-5 s | 6-12 s | 9-17 s |
| Transizione | 2-4 s | 6-12 s | 8-16 s |
| Linea/blocco | 3-5 s | 6-12 s | 9-17 s |
| Rifinitura/finalizzazione | 2-4 s | 5-10 s | 7-14 s |

Questi intervalli sono ipotesi di progettazione da validare, non soglie definitive.

### 5.3 Quando inizia

Il momento inizia nel primo istante utile a comprendere il trigger. Esempi:

- costruzione: controllo o rimessa in gioco che avvia l'uscita;
- pressing: segnale che attiva l'uscita coordinata;
- transizione negativa: perdita del possesso;
- transizione positiva: recupero del possesso;
- linea difensiva: azione avversaria che costringe il reparto ad adattarsi;
- palla inattiva: organizzazione immediatamente precedente alla battuta;
- rimessa: preparazione e posizionamento prima del rilascio.

L'inizio non coincide necessariamente con il primo movimento evidente. Deve
includere il contesto minimo necessario.

### 5.4 Quando termina

Il momento termina quando:

- il comportamento produce un esito;
- il possesso cambia stabilmente;
- la palla esce;
- l'azione entra in una nuova fase distinta;
- la struttura si dissolve;
- la camera interrompe la continuita;
- non e piu possibile seguire palla e giocatori rilevanti.

Una conseguenza utile puo estendere il momento di alcuni secondi.

### 5.5 Criteri di validita

Per essere considerato valido, il momento deve soddisfare:

- continuita temporale sufficiente;
- campo visibile in misura coerente con la categoria;
- palla osservabile o stato della palla inferibile con evidenza;
- numero di giocatori adeguato alla categoria;
- squadre distinguibili;
- trigger o esito osservabile;
- assenza di filtri di esclusione dominanti;
- pertinenza con il focus;
- possibilita di revisione umana.

### 5.6 Frame rappresentativo

Il frame rappresentativo deve:

- appartenere al momento;
- mostrare la configurazione piu informativa;
- non sostituire la sequenza;
- evitare primi piani e occlusioni;
- mantenere visibile la palla quando rilevante;
- mostrare il maggior numero utile di relazioni;
- consentire annotazioni leggibili.

La selezione del frame rappresentativo avviene dopo la delimitazione del momento,
non prima.

---

## 6. Filtri automatici delle scene non tattiche

I filtri devono operare prima dell'interpretazione tattica e continuare a
controllare l'intera sequenza. Non basta escludere un frame se i secondi vicini
appartengono a una scena televisiva diversa.

Ogni filtro deve produrre:

- presenza o assenza;
- intervallo temporale coinvolto;
- livello di evidenza;
- motivi osservati;
- decisione: esclusione, penalizzazione o richiesta di review;
- eccezioni applicabili.

### 6.1 Replay

Segnali futuri:

- logo o transizione di replay;
- cambio improvviso di camera e scala;
- ripetizione di una sequenza gia osservata;
- discontinuita del cronometro televisivo;
- velocita anomala o slow motion;
- dissolvenza;
- angolazione incompatibile con la ripresa principale.

Decisione:

- escludere dal rilevamento primario;
- collegare eventualmente al momento originale come materiale editoriale;
- non usarlo per ricostruire la timeline reale;
- non confondere il replay con un secondo evento.

Eccezione:

Un replay puo essere utile nel report, ma solo se associato a un momento reale
gia identificato e chiaramente etichettato come replay.

### 6.2 Esultanze e reazioni

Segnali futuri:

- primi piani di uno o pochi giocatori;
- giocatori abbracciati o in corsa fuori dalla struttura di gioco;
- palla assente per una finestra prolungata;
- interruzione del cronometro o ripartenza non imminente;
- pubblico, panchina o staff in primo piano;
- inquadrature di reazione.

Decisione:

- esclusione forte dalla selezione tattica;
- eventuale conservazione come evento narrativo separato;
- Tactical Value pari a zero per focus strutturali.

### 6.3 Primi piani

Segnali futuri:

- una persona occupa una porzione dominante dell'immagine;
- porzione di campo ridotta;
- meno giocatori del minimo richiesto;
- palla non visibile;
- impossibilita di osservare relazioni collettive.

Decisione:

- esclusione per linee, reparti, pressing, ampiezza e costruzione;
- possibile eccezione solo per analisi individuale esplicitamente richiesta.

### 6.4 Panchina e area tecnica

Segnali futuri:

- sedute, staff, area tecnica o bordocampo dominanti;
- assenza della superficie di gioco necessaria;
- persone non coinvolte nell'azione;
- camera rivolta fuori dal rettangolo utile.

Decisione:

- esclusione dalla pipeline tattica;
- nessuna categoria di fase di gioco.

### 6.5 Pubblico

Segnali futuri:

- prevalenza di tribune e volti;
- assenza del terreno;
- nessuna palla;
- nessuna struttura di squadra.

Decisione:

- esclusione immediata;
- nessuna interpretazione AI.

### 6.6 Grafiche televisive

Tipologie:

- grafica a schermo intero;
- tabellino;
- formazione;
- replay card;
- pubblicita;
- lower third invasivo;
- split screen.

Decisione:

- grafica a schermo intero: esclusione;
- overlay parziale: penalizzazione Technical Quality e area utile;
- scoreboard limitato: tollerabile se non copre evidenze;
- formazione televisiva: non deve essere scambiata per giocatori reali.

### 6.7 Campo insufficiente

La soglia deve dipendere dalla categoria. Una ripresa utile per una finalizzazione
puo non esserlo per ampiezza o distanze tra reparti.

Segnali futuri:

- percentuale di superficie di gioco visibile;
- linee del campo osservabili;
- numero di zone calibrate presenti;
- scala media dei giocatori;
- presenza simultanea dei reparti richiesti.

Decisione:

- esclusione per categorie collettive se il campo utile e insufficiente;
- penalizzazione graduata per categorie locali;
- richiesta di review se la categoria non e ancora nota.

### 6.8 Pochi giocatori

Il numero minimo deve essere condizionato dalla categoria:

- pressing collettivo: piu giocatori di entrambe le squadre;
- linea difensiva: maggioranza del reparto e riferimenti avversari;
- costruzione: portiere/difensori e prima pressione;
- palla inattiva: battitore, area bersaglio e marcature;
- duello individuale: eccezione esplicita.

Decisione:

- esclusione per categorie incompatibili;
- non assegnare automaticamente `open_play`;
- segnalare "contesto collettivo insufficiente".

### 6.9 Filtri combinati e isteresi

Una singola rilevazione rumorosa non deve spezzare una sequenza valida. I filtri
devono considerare persistenza e maggioranza temporale.

Esempi:

- un overlay di un secondo non invalida quindici secondi di azione;
- tre secondi di primo piano al centro di una clip possono richiedere divisione;
- un cambio camera breve puo collegare due viste dello stesso evento solo se la
  continuita e dimostrabile;
- replay seguito dalla ripresa live deve produrre due intervalli distinti.

### 6.10 Ordine dei filtri

Ordine concettuale:

1. integrita tecnica;
2. grafica/replay;
3. tipo di inquadratura;
4. superficie di campo;
5. giocatori e palla;
6. continuita temporale;
7. compatibilita con la categoria;
8. utilita tattica;
9. idoneita editoriale.

Un momento escluso da un hard filter non deve essere recuperato soltanto perche
ha un alto Editorial Score.

---

## 7. Classificazione dell'utilita per allenatore e match analyst

La classificazione finale deve descrivere l'utilita professionale, non la
sicurezza generica del sistema.

### 7.1 Ottimo

Un momento e **ottimo** quando:

- trigger, comportamento ed esito sono osservabili;
- la sequenza e continua;
- palla e giocatori rilevanti sono leggibili;
- la categoria e chiaramente supportata;
- il momento risponde al focus;
- offre un'indicazione concreta allo staff;
- puo essere mostrato senza spiegazioni correttive lunghe;
- il frame rappresentativo e annotabile;
- non contiene filtri di esclusione;
- le interpretazioni alternative sono deboli.

Uso:

- slide principale;
- report;
- riunione;
- collegamento a esercitazione;
- benchmark positivo o negativo.

### 7.2 Buono

Un momento e **buono** quando:

- il comportamento e leggibile;
- manca un elemento non essenziale;
- l'esito puo essere parziale;
- la camera e adeguata ma non ideale;
- la categoria e utile dopo una breve verifica;
- le annotazioni possono chiarire il punto.

Uso:

- review;
- report secondario;
- supporto a un pattern;
- clip didattica con nota dello staff.

### 7.3 Mediocre

Un momento e **mediocre** quando:

- l'idea tattica e soltanto plausibile;
- il contesto e incompleto;
- palla o reparto si perdono per parte della sequenza;
- la camera rende ambigua la struttura;
- piu categorie restano plausibili;
- l'esito non e visibile;
- serve una spiegazione lunga per giustificarlo.

Uso:

- coda di review;
- spunto da confermare;
- dataset di casi difficili;
- non inserire automaticamente nel report.

### 7.4 Inutile

Un momento e **inutile** quando:

- e replay non collegato;
- mostra esultanza, pubblico, panchina o primo piano incompatibile;
- non mostra campo sufficiente;
- contiene troppo pochi giocatori;
- la palla e assente quando indispensabile;
- non esiste continuita;
- non risponde al focus;
- categoria e descrizione sono fondate su supposizioni;
- non produce alcuna decisione o osservazione per lo staff.

Uso:

- esclusione dal report;
- eventuale negativo per benchmark;
- possibile cancellazione dai materiali derivati secondo policy.

### 7.5 Regola di promozione

Un momento non puo essere "ottimo" solo per un alto score editoriale.

Per la promozione a ottimo servono almeno:

- Technical Quality adeguata;
- Tactical Value alto;
- Sequence Confidence alta;
- AI Confidence non contraddetta;
- nessun hard filter;
- oppure approvazione umana esplicita che documenti l'eccezione.

### 7.6 Linguaggio per l'interfaccia futura

Termini consigliati:

- **Pronto per lo staff** invece di "95% corretto";
- **Utile, verifica consigliata**;
- **Spunto incompleto**;
- **Non utilizzabile**.

Gli score numerici possono restare disponibili nei dettagli tecnici, ma
l'interfaccia professionale deve comunicare decisioni e limiti.

---

## 8. Informazioni future da RF-DETR

RF-DETR non viene integrato in questo sprint. La sua futura responsabilita deve
essere limitata alla detection per frame, senza attribuirgli interpretazioni
tattiche.

### 8.1 Detection richieste

Per ogni frame campionato:

- bounding box dei giocatori;
- bounding box dei portieri;
- bounding box degli arbitri;
- bounding box della palla;
- classe proposta;
- confidence del detector;
- coordinate nell'immagine;
- dimensione apparente;
- eventuale stato di occlusione;
- indicatore di rilevazione al margine.

### 8.2 Informazioni aggregate utili

Da detection ripetute, ma prima del tracking:

- numero di persone calcistiche visibili;
- distribuzione spaziale grezza;
- presenza della palla;
- scala media dei giocatori;
- densita per area immagine;
- percentuale di frame con detection sufficiente;
- possibili primi piani;
- possibili scene non tattiche.

### 8.3 Informazioni che RF-DETR non deve dichiarare da solo

- identita del giocatore;
- squadra;
- possesso;
- pressing;
- modulo;
- linea difensiva;
- fase di gioco;
- categoria tattica;
- esito dell'azione;
- valore per l'allenatore.

Questi concetti richiedono tracking, colore squadra, calibrazione, sequenza e
interpretazione.

### 8.4 Requisiti di affidabilita futuri

Prima dell'uso runtime serviranno benchmark separati per:

- giocatore;
- portiere;
- arbitro;
- palla;
- scene ravvicinate;
- scene ampie;
- luce e ombra;
- risoluzioni basse;
- compressione;
- campi dilettantistici;
- camera fissa e camera mobile.

Il benchmark deve usare video rappresentativi del dominio MatchIQ, non solo
dataset professionistici televisivi.

---

## 9. Informazioni future dal tracking

Il tracking deve trasformare detection isolate in entita temporali coerenti.

### 9.1 Output fondamentali

Per ogni track:

- identificatore temporaneo;
- classe;
- serie di posizioni;
- inizio e fine;
- continuita;
- occlusioni;
- velocita apparente;
- direzione;
- accelerazione;
- qualita del track;
- cambi di scala;
- associazioni incerte.

Per la palla:

- traiettoria;
- velocita;
- cambi di direzione;
- intervalli non osservati;
- possibili tocchi;
- possibili passaggi;
- possibili uscite dal campo.

### 9.2 Informazioni collettive derivate

Con squadra e calibrazione disponibili:

- centroidi di squadra;
- larghezza;
- lunghezza;
- altezza dei reparti;
- distanze verticali e orizzontali;
- compattezza;
- occupazione delle corsie;
- sincronizzazione delle uscite;
- velocita di ricomposizione;
- giocatori oltre/sotto la linea della palla;
- superiorita e inferiorita locali;
- rotture e ricostruzioni dei reparti.

### 9.3 Informazioni temporali necessarie alla segmentazione

- cambio di possesso probabile;
- accelerazione collettiva;
- inizio pressione;
- fine pressione;
- restart;
- battuta;
- uscita dalla prima pressione;
- ingresso in nuova zona;
- tiro o cross;
- interruzione;
- stabilizzazione in una nuova fase.

### 9.4 Limiti da conservare

Un track non equivale a un giocatore identificato. Le associazioni possono
rompersi per:

- occlusioni;
- zoom;
- stacchi camera;
- giocatori sovrapposti;
- maglie simili;
- uscita e rientro dall'inquadratura.

Ogni informazione derivata deve propagare la qualita del tracking e non nascondere
le interruzioni.

---

## 10. Informazioni future dalla calibrazione del campo

La calibrazione deve trasformare coordinate immagine in coordinate calcistiche
comparabili.

### 10.1 Output richiesti

- confini del terreno visibili;
- linee laterali e di fondo;
- linea di meta campo;
- aree di rigore;
- area di porta;
- cerchio centrale;
- punti e segmenti di riferimento;
- trasformazione prospettica;
- qualita della calibrazione;
- porzione di campo osservabile;
- zone non calibrabili.

### 10.2 Coordinate normalizzate

Le posizioni future devono poter essere espresse:

- nell'immagine originale;
- in coordinate normalizzate del campo;
- per corsia;
- per terzo;
- per zona funzionale.

Questo permette di confrontare camere, partite e risoluzioni diverse.

### 10.3 Capacita abilitate

Calibrazione + tracking potranno rendere misurabili:

- altezza reale della linea;
- larghezza e lunghezza della squadra;
- distanza tra reparti;
- occupazione delle corsie;
- profondita;
- densita per zona;
- posizione della palla;
- ingresso e uscita da aree;
- geometria delle palle inattive;
- correttezza delle linee tattiche suggerite.

### 10.4 Qualita e astensione

La calibrazione deve indicare quando:

- le linee sono insufficienti;
- la camera cambia;
- zoom e pan invalidano la trasformazione;
- il campo e parzialmente occultato;
- la trasformazione e instabile.

Senza calibrazione affidabile non devono essere esposte distanze metriche o
dichiarazioni geometriche forti.

### 10.5 Relazione con le linee tattiche

Le linee future non devono nascere soltanto da coordinate linguistiche suggerite.
Dovranno essere ancorate a:

- giocatori rilevati;
- track coerenti;
- coordinate di campo;
- categoria;
- momento temporale;
- squadra;
- qualita geometrica.

Le linee manuali resteranno importanti come correzione e supervisione.

---

## 11. Feedback umano come benchmark e dataset proprietario

Il feedback non deve essere soltanto uno stato dell'interfaccia. Deve diventare
una registrazione strutturata della differenza tra proposta del sistema e
decisione dello staff.

### 11.1 Principio di conservazione

Per ogni review devono restare distinguibili:

- proposta originale;
- score originali;
- segnali disponibili al momento della proposta;
- decisione umana;
- correzione;
- identita e ruolo del revisore;
- timestamp della review;
- versione della pipeline;
- eventuali revisioni successive.

La correzione non deve cancellare l'errore originale: proprio quella differenza
ha valore per il benchmark.

### 11.2 Significato dei click

#### Corretto

Conferma separatamente, quando applicabile:

- confini temporali;
- categoria;
- squadra;
- descrizione;
- frame rappresentativo;
- valore tattico;
- annotazioni.

Un unico "Corretto" non deve essere interpretato automaticamente come conferma
di ogni campo se l'interfaccia non li rende verificabili.

#### Correggi

Deve permettere di indicare quale dimensione era errata:

- categoria;
- sottocategoria;
- squadra;
- inizio;
- fine;
- frame rappresentativo;
- descrizione;
- utilita;
- linea;
- giocatore;
- motivo di esclusione.

#### Scarta

Deve acquisire un motivo strutturato:

- replay;
- esultanza;
- primo piano;
- panchina;
- pubblico;
- grafica;
- campo insufficiente;
- pochi giocatori;
- palla assente;
- sequenza interrotta;
- categoria errata;
- duplicato;
- non pertinente;
- altro specificato.

#### Categoria

La categoria corretta deve provenire da una tassonomia versionata. Il sistema
deve poter conservare:

- categoria proposta;
- categoria corretta;
- eventuale seconda categoria valida;
- livello di specificita consentito dall'evidenza.

#### Linee manuali

Ogni linea manuale deve essere associata a:

- momento;
- timestamp o intervallo;
- categoria;
- squadra;
- punti geometrici;
- tipo di linea/area;
- scopo didattico;
- eventuali entita collegate;
- trasformazione di campo disponibile;
- revisore.

Una linea manuale non e automaticamente ground truth geometrica se il campo non
e calibrato.

### 11.3 Unita del dataset

L'unita proprietaria non deve essere soltanto l'immagine. Deve comprendere:

- riferimento al video autorizzato;
- intervallo temporale;
- frame rappresentativo;
- campioni interni alla sequenza;
- detection disponibili;
- track disponibili;
- calibrazione disponibile;
- categoria proposta e corretta;
- filtri positivi e negativi;
- score separati;
- descrizione proposta e corretta;
- annotazioni;
- decisione finale;
- provenienza e diritti.

### 11.4 Livelli di annotazione

Per controllare costi e qualita:

1. **Livello evento:** valido/scartato e confini.
2. **Livello tattico:** categoria, squadra e utilita.
3. **Livello visuale:** frame, palla, giocatori e campo.
4. **Livello geometrico:** linee, zone e coordinate.
5. **Livello semantico:** spiegazione e indicazione allo staff.

Non tutti i momenti devono essere annotati a tutti i livelli.

### 11.5 Qualita dell'annotazione

Il benchmark deve distinguere:

- singolo revisore;
- doppia revisione concorde;
- disaccordo;
- decisione di un revisore senior;
- caso ambiguo;
- evidenza insufficiente.

Per categorie critiche, un campione benchmark dovrebbe richiedere:

- almeno due valutazioni indipendenti;
- risoluzione dei disaccordi;
- motivazione breve;
- versione congelata della tassonomia.

### 11.6 Dataset positivi, negativi e difficili

Servono:

- positivi chiari;
- negativi chiari;
- hard negative visivamente simili;
- casi ambigui;
- errori sistematici del modello;
- esempi con camera o luce difficili;
- esempi dilettantistici reali;
- esempi di astensione corretta.

Sono particolarmente preziosi:

- esultanza scambiata per open play;
- densita casuale scambiata per pressing;
- campo largo senza struttura;
- palla inattiva generica classificata troppo precisamente;
- frame bello ma tatticamente inutile;
- momento tattico utile con qualita visiva mediocre.

### 11.7 Separazione dei dataset

Per evitare leakage:

- le clip della stessa partita non devono essere distribuite tra train e test;
- idealmente le squadre e le competizioni devono essere separate nei benchmark
  piu severi;
- duplicati e replay devono restare nello stesso split del momento originale;
- le versioni del benchmark devono essere congelate;
- il test set non deve alimentare tuning quotidiano.

Split concettuali:

- sviluppo;
- validazione;
- benchmark interno;
- benchmark temporale futuro;
- benchmark per dominio dilettantistico.

### 11.8 Metriche future

Il benchmark deve misurare separatamente:

- precisione e recall dei candidati;
- accuratezza dei confini temporali;
- tasso di replay/esultanze accettati;
- accuratezza della categoria;
- matrice di confusione;
- calibrazione degli score;
- precisione per livello di utilita;
- accordo con lo staff;
- tempo medio di review;
- percentuale di astensioni corrette;
- qualita del frame rappresentativo;
- precisione geometrica delle linee;
- robustezza per camera e categoria.

### 11.9 Feedback online e training

Il click dell'utente non deve aggiornare automaticamente un modello in
produzione.

Flusso sicuro:

1. raccolta;
2. controllo diritti e integrita;
3. normalizzazione;
4. revisione;
5. deduplicazione;
6. versionamento;
7. costruzione benchmark;
8. esperimento offline;
9. confronto con baseline;
10. approvazione;
11. rilascio versionato;
12. monitoraggio.

Questo evita che errori, click accidentali o preferenze individuali degradino il
sistema.

### 11.10 Proprietarieta, privacy e diritti

Prima di usare materiale per dataset devono essere definiti:

- base giuridica;
- autorizzazione sul video;
- finalita consentite;
- durata di conservazione;
- segregazione per club;
- anonimizzazione quando necessaria;
- diritto di esclusione;
- policy per minori;
- accesso ai dati;
- tracciabilita delle esportazioni.

Il valore proprietario nasce dalla qualita delle annotazioni e dalla loro
legittima riutilizzabilita, non dalla sola quantita.

---

## 12. Governance della tassonomia

Una pipeline affidabile richiede una tassonomia stabile, gerarchica e versionata.

### 12.1 Livelli consigliati

**Livello 1 - Stato del gioco**

- live;
- restart;
- interruzione;
- replay;
- non tattico;
- non determinabile.

**Livello 2 - Fase**

- possesso;
- non possesso;
- transizione positiva;
- transizione negativa;
- palla inattiva offensiva;
- palla inattiva difensiva.

**Livello 3 - Principio**

- costruzione;
- sviluppo;
- rifinitura;
- finalizzazione;
- pressing;
- blocco;
- linea;
- ampiezza;
- profondita;
- compattezza;
- rest defense;
- seconda palla.

**Livello 4 - Sottocategoria**

- costruzione dal portiere;
- uscita laterale;
- uscita centrale;
- corner;
- punizione laterale;
- punizione centrale;
- rimessa laterale;
- rinvio;
- altre specificazioni supportate dall'evidenza.

### 12.2 Specificita controllata

Il sistema deve scegliere la categoria piu specifica supportata dai dati. Se sa
riconoscere una palla inattiva ma non il tipo, deve restare generico.

E preferibile:

- "palla inattiva offensiva, tipo non determinato"

rispetto a:

- "calcio d'angolo offensivo 88%"

quando il corner non e realmente osservabile.

### 12.3 Multi-label

Alcuni momenti possono avere piu significati:

- costruzione + pressione avversaria;
- transizione + rest defense;
- palla inattiva + marcatura;
- ampiezza + rifinitura.

La pipeline deve distinguere:

- categoria primaria;
- attributi secondari;
- interpretazioni alternative.

Non deve forzare tutto in una singola etichetta.

---

## 13. Contratto concettuale del Momento Tattico

Senza definire classi o API, ogni momento futuro dovra essere descrivibile
attraverso gruppi di informazioni coerenti.

### Identita

- riferimento al video;
- riferimento alla partita;
- proprietario;
- versione della pipeline;
- origine del candidato.

### Tempo

- inizio;
- centro;
- fine;
- frame rappresentativo;
- trigger;
- esito;
- qualita dei confini.

### Visione

- qualita tecnica;
- campo visibile;
- palla;
- giocatori;
- track;
- calibrazione;
- filtri.

### Tattica

- squadra osservata;
- fase;
- categoria;
- sottocategoria;
- attributi;
- valore tattico;
- evidenze;
- alternative.

### Interpretazione

- descrizione;
- spiegazione;
- indicazione staff;
- limiti;
- AI Confidence.

### Editoriale

- idoneita review;
- idoneita slide;
- idoneita report;
- frame;
- annotazioni;
- Editorial Score.

### Review

- stato;
- correzioni;
- revisore;
- motivazione;
- data;
- versione.

Questi gruppi impediscono di confondere dato osservato, dato derivato,
interpretazione e decisione umana.

---

## 14. Osservabilita e spiegabilita

Ogni momento proposto deve poter rispondere:

- perche e stato candidato?
- quali secondi sono stati analizzati?
- quale frame lo rappresenta?
- quali filtri ha superato?
- quali segnali visivi sono presenti?
- quali segnali mancano?
- perche questa categoria?
- quali alternative erano possibili?
- perche e utile allo staff?
- quali score sono bassi?
- che cosa ha corretto il revisore?

### Stati consigliati

- candidato;
- analisi sequenza incompleta;
- pronto per interpretazione;
- da revisionare;
- approvato;
- corretto;
- scartato;
- astensione;
- pronto per report.

Non devono esistere passaggi invisibili che trasformano un frame in verita
tattica senza evidenze consultabili.

---

## 15. Rischi architetturali

### 15.1 Falsa precisione

Mostrare numeri non calibrati puo aumentare la fiducia proprio nei casi errati.
Mitigazione progettuale: score separati, etichette testuali e astensione.

### 15.2 Bias del dominio

Modelli allenati su broadcast professionistici possono degradare su:

- camere fisse;
- campi dilettantistici;
- illuminazione irregolare;
- maglie senza contrasto;
- video verticali;
- compressione WhatsApp;
- assenza di scoreboard.

Il benchmark deve rappresentare il prodotto reale.

### 15.3 Propagazione dell'errore

Un errore del detector puo contaminare tracking, calibrazione, categoria e report.
Ogni fase deve conservare la propria confidence e consentire l'astensione.

### 15.4 Over-segmentation e under-segmentation

- Troppi momenti piccoli perdono contesto.
- Momenti troppo lunghi mescolano fasi diverse.

La qualita dei confini deve essere misurata indipendentemente dalla categoria.

### 15.5 Conferma automatica

Un'interfaccia troppo convincente puo spingere lo staff ad approvare senza
guardare. La review deve mostrare evidenza e limiti, non soltanto una CTA.

### 15.6 Dataset rumoroso

Click rapidi, categorie personali e linee non calibrate non sono automaticamente
ground truth. Servono controllo qualita, ruoli e versionamento.

### 15.7 Costi e latenza

L'analisi sequenziale e piu costosa del sampling statico. La roadmap dovra
misurare:

- tempo per minuto di video;
- costo per partita;
- memoria;
- storage derivato;
- latenza fino alla prima review;
- qualita ottenuta per costo.

Non e ancora definito quale compromesso sia corretto.

---

## 16. Protocollo di valutazione prima del runtime

Prima di sostituire la pipeline esistente, ogni componente dovra essere valutato
offline.

### 16.1 Baseline congelata

La pipeline statica corrente deve essere misurata su un set congelato:

- candidati utili trovati;
- scene non tattiche accettate;
- categorie corrette;
- tempo di review;
- qualita del report.

Senza baseline non sara possibile dimostrare il miglioramento.

### 16.2 Benchmark minimo

Il benchmark dovra includere:

- piu partite complete;
- piu tipi di ripresa;
- categorie diverse;
- positivi e negativi;
- casi semplici e difficili;
- focus da allenatore e match analyst;
- camere professionali e dilettantistiche;
- palle inattive;
- costruzione;
- pressing;
- transizioni;
- scene non tattiche.

La dimensione minima e non determinabile dal solo codice attuale: dovra essere
definita tramite analisi statistica e disponibilita dei diritti.

### 16.3 Confronti obbligatori

Ogni milestone dovra confrontare:

- pipeline corrente;
- nuova componente isolata;
- nuova pipeline completa;
- review umana;
- costo;
- latenza;
- tasso di astensione.

### 16.4 Criteri di avanzamento

Una componente avanza solo se:

- migliora metriche dichiarate;
- non peggiora categorie critiche oltre una soglia concordata;
- mantiene isolamento utenti e diritti;
- produce spiegazioni verificabili;
- non trasforma score interni in promesse ingannevoli.

---

## 17. Roadmap V3.1 ordinata per priorita

La roadmap e deliberatamente incrementale. RF-DETR entra soltanto dopo che
unita, tassonomia, benchmark e metriche sono definiti.

### Milestone 0 - Specifica congelata

Priorita: massima.

Obiettivi:

- approvare la definizione di Momento Tattico;
- approvare tassonomia e livelli di utilita;
- approvare significato degli score;
- definire ruoli di revisione;
- definire diritti e conservazione;
- selezionare categorie iniziali limitate.

Uscita:

- glossario condiviso;
- regole di annotazione;
- nessuna ambiguita su cosa misurare.

### Milestone 1 - Benchmark della pipeline corrente

Priorita: massima.

Obiettivi:

- congelare un insieme rappresentativo di video;
- annotare i quattro fallimenti gia osservati;
- misurare sampling statico e selezione attuale;
- registrare precisione, recall, errori non tattici e tempo di review;
- separare risultati per categoria e tipo camera.

Uscita:

- baseline quantitativa;
- elenco dei failure mode dominanti;
- criteri di successo V3.1.

### Milestone 2 - Dataset e strumento di annotazione temporale

Priorita: massima.

Obiettivi:

- annotare inizio, centro e fine;
- registrare filtri;
- correggere categorie;
- classificare utilita;
- conservare proposta e correzione;
- definire doppia revisione per benchmark.

Uscita:

- primo dataset proprietario di momenti;
- benchmark versionato;
- processo di qualita documentato.

Questa milestone puo riusare concettualmente i feedback attuali, ma richiedera in
futuro una progettazione applicativa separata.

### Milestone 3 - Candidate Moment Discovery temporale

Priorita: alta.

Obiettivi:

- superare i timestamp uniformi;
- proporre finestre temporali;
- rilevare discontinuita e restart;
- privilegiare recall;
- spiegare il motivo di ogni candidato;
- confrontare contro sampling corrente.

Uscita:

- candidati temporali migliori senza interpretazione tattica definitiva.

### Milestone 4 - Filtri non tattici

Priorita: alta.

Obiettivi:

- replay;
- esultanze;
- primi piani;
- panchina;
- pubblico;
- grafiche;
- campo insufficiente;
- pochi giocatori.

Uscita:

- drastica riduzione dei falsi positivi editorialmente belli ma inutili;
- metriche per filtro e dominio.

Questa milestone puo richiedere segnali visivi specifici, ma non deve attendere
necessariamente la classificazione tattica completa.

### Milestone 5 - RF-DETR detection benchmark

Priorita: alta, dopo dataset e baseline.

Obiettivi:

- integrare soltanto in ambiente sperimentale;
- valutare player, goalkeeper, referee e ball;
- misurare per camera e qualita;
- verificare costi e velocita;
- definire fallback e astensione.

Uscita:

- decisione go/no-go per runtime;
- nessuna interpretazione tattica affidata al detector.

### Milestone 6 - Tracking e continuita

Priorita: alta.

Obiettivi:

- tracciare giocatori e palla;
- misurare continuita;
- gestire occlusioni e cambi camera;
- derivare possibili trigger;
- calcolare Sequence Confidence.

Uscita:

- momenti con confini temporali verificabili;
- possibilita di distinguere stato e transizione.

### Milestone 7 - Calibrazione del campo

Priorita: medio-alta.

Obiettivi:

- coordinate normalizzate;
- qualita della trasformazione;
- gestione di zoom e pan;
- zone e reparti;
- validazione geometrica delle annotazioni.

Uscita:

- misure spaziali confrontabili;
- fondamenta per linee tattiche affidabili.

### Milestone 8 - Tactical Scoring limitato

Priorita: medio-alta.

Obiettivi:

- partire con poche categorie ad alto valore;
- usare segnali sequenziali, tracking e campo;
- separare Tactical Value da AI Confidence;
- supportare multi-label e astensione;
- valutare matrici di confusione.

Categorie iniziali candidate:

- replay/non tattico;
- palla inattiva generica e tipo quando evidente;
- costruzione dal basso;
- transizione positiva/negativa;
- pressing;
- linea/blocco.

La selezione definitiva dipendera dal benchmark.

### Milestone 9 - AI Interpretation grounded

Priorita: media.

Obiettivi:

- interpretare soltanto segnali strutturati;
- citare evidenze;
- dichiarare alternative e limiti;
- calibrare AI Confidence;
- evitare descrizioni non supportate.

Uscita:

- testo professionale verificabile;
- riduzione delle allucinazioni tattiche.

### Milestone 10 - Editorial Selection e linee

Priorita: media.

Obiettivi:

- scegliere frame rappresentativi dopo la sequenza;
- calcolare Editorial Score;
- suggerire linee ancorate a detection e campo;
- mantenere correzione manuale;
- separare slide e analisi.

Uscita:

- materiali pronti per staff senza confondere estetica e verita.

### Milestone 11 - Human Review e apprendimento offline

Priorita: media.

Obiettivi:

- trasformare click in annotazioni strutturate;
- costruire code di casi difficili;
- misurare accordo;
- versionare benchmark;
- sperimentare offline;
- impedire training automatico da feedback grezzo.

Uscita:

- ciclo di miglioramento proprietario e controllato.

### Milestone 12 - Shadow mode

Priorita: prima del rilascio.

Obiettivi:

- eseguire V3.1 senza cambiare l'esperienza utente;
- confrontare suggerimenti vecchi e nuovi;
- misurare regressioni;
- verificare costi;
- monitorare astensioni;
- validare con staff selezionati.

Uscita:

- evidenza reale di superiorita;
- piano di rollback;
- decisione di rilascio.

### Milestone 13 - Rilascio progressivo

Priorita: finale.

Obiettivi:

- rollout limitato;
- monitoraggio per categoria;
- review obbligatoria;
- confronto continuo con baseline;
- espansione solo dopo soglie concordate.

Uscita:

- Tactical Moment Selection V3.1 disponibile senza presentare score non calibrati
  come verita.

---

## 18. Criteri di accettazione architetturali V3.1

La progettazione puo considerarsi rispettata soltanto quando la futura pipeline:

1. seleziona intervalli temporali, non immagini isolate;
2. conserva trigger, sviluppo ed esito;
3. filtra scene non tattiche prima dell'interpretazione;
4. distingue qualita tecnica e valore tattico;
5. calcola una confidenza della sequenza;
6. separa AI Confidence da accuratezza reale;
7. sceglie il frame dopo la selezione del momento;
8. supporta astensione e categorie generiche;
9. rende consultabili evidenze e segnali mancanti;
10. conserva proposta e correzione umana;
11. costruisce benchmark senza leakage;
12. non usa RF-DETR come interprete tattico;
13. propaga incertezza da detector, tracking e calibrazione;
14. include nel report soltanto momenti approvati o corretti;
15. dimostra miglioramento contro una baseline congelata.

---

## 19. Decisioni ancora da prendere prima dello sviluppo

Le seguenti decisioni non devono essere anticipate senza benchmark:

1. categorie iniziali definitive;
2. durata ottimale per ciascuna categoria;
3. frequenza di campionamento;
4. detector e checkpoint;
5. strategia di tracking;
6. metodo di calibrazione;
7. soglie dei filtri;
8. pesi degli score;
9. definizione statistica della calibrazione;
10. costo massimo per partita;
11. tempo massimo alla prima review;
12. dimensione minima del benchmark;
13. numero di revisori;
14. gestione dei disaccordi;
15. policy di conservazione e training;
16. categorie abilitate su video con qualita bassa;
17. comportamento con camere multiple;
18. livello di spiegazione mostrato all'utente.

Ognuno di questi punti e non determinabile dal codice attuale e richiede dati,
esperimenti o decisioni di prodotto.

---

## 20. Sintesi finale

La nuova Tactical Moment Selection non deve essere un selettore di frame piu
sofisticato. Deve essere una pipeline temporale verificabile:

**Video**

↓

**Momenti candidati con motivazione**

↓

**Sequenze delimitate e controllate**

↓

**Filtri tecnici e non tattici**

↓

**Valore tattico separato dalla qualita editoriale**

↓

**Interpretazione AI fondata su evidenze**

↓

**Review umana strutturata**

↓

**Benchmark proprietario**

↓

**Report con soli momenti approvati**

Il vantaggio competitivo non nascera da una percentuale piu alta, ma dalla
capacita di mostrare allo staff il momento giusto, con il contesto giusto, una
spiegazione verificabile e un livello di incertezza onesto.
