# MatchIQ Vision Engine V3.1

## Strategia di acquisizione dati proprietari - Milestone B2

**Stato:** documento progettuale

**Orizzonte operativo principale:** 24 mesi

**Orizzonte strategico:** 5 anni

**Dominio prioritario:** calcio dilettantistico e semi-professionistico

**Input normativi:**

- `vision-engine-current-pipeline-audit.md`;
- `tactical-moment-selection-design.md`;
- `vision-engine-benchmark-specification.md`;
- `vision-engine-annotation-manual.md`.

---

## Scopo e confini

Questo documento definisce come MatchIQ puo costruire, nei prossimi 24 mesi, un
patrimonio dati proprietario utile a:

- valutare la pipeline corrente;
- costruire benchmark affidabili;
- misurare i failure mode;
- migliorare la selezione dei momenti tattici;
- preparare futuri esperimenti di Computer Vision;
- trasformare la review dello staff in conoscenza verificata.

Il documento non autorizza la raccolta di alcun video e non sostituisce una
valutazione legale. Prima dell'uso operativo, i modelli di consenso, le basi
giuridiche, le condizioni contrattuali, la policy sui minori e i periodi di
conservazione devono essere approvati da un professionista competente.

Questo documento non:

- crea un dataset;
- definisce un database;
- implementa strumenti;
- modifica il prodotto;
- autorizza il training;
- rende riutilizzabili per AI i video caricati dagli utenti;
- sostituisce il benchmark;
- congela numeri o soglie non ancora osservati.

Quando una decisione dipende da evidenze non ancora disponibili, viene indicata
con la formula:

> da validare durante la raccolta dati

---

# 1. Perche il dataset sara il principale vantaggio competitivo

## 1.1 Tesi

Il vantaggio difendibile di MatchIQ non sara semplicemente possedere un
software, usare un modello o collegarsi a un servizio AI. Sara possedere una
raccolta crescente di sequenze calcistiche:

- autorizzate;
- provenienti dal dominio reale dei clienti;
- annotate secondo un protocollo stabile;
- corrette da allenatori e match analyst;
- collegate a errori, categorie, frame e geometrie;
- versionate nel tempo;
- separate tra sviluppo e benchmark.

La differenza non e la quantita grezza di ore video. La differenza e il numero
di decisioni affidabili e ripetibili che MatchIQ riesce a ricavare da quelle
ore.

## 1.2 Software

Il software ha valore perche:

- rende possibile acquisire, revisionare e riutilizzare le evidenze;
- riduce il costo operativo della review;
- permette allo staff di correggere il sistema;
- crea un workflow coerente dal video al report.

Il software, pero:

- puo essere replicato;
- cambia rapidamente;
- dipende da framework e servizi disponibili anche ai concorrenti;
- non dimostra da solo che un momento sia tatticamente utile.

Il software e quindi il mezzo con cui il patrimonio dati viene generato e
curato, non il patrimonio in se.

## 1.3 Modelli

I modelli sono importanti per:

- detection;
- tracking;
- classificazione;
- ranking;
- interpretazione;
- generazione di descrizioni.

I modelli, tuttavia:

- possono diventare commodity;
- possono essere sostituiti;
- possono essere acquistati o integrati da terzi;
- non conoscono automaticamente il dominio MatchIQ;
- non distinguono in modo affidabile il valore tattico senza esempi adeguati;
- possono produrre confidence non calibrate.

Un modello forte senza benchmark e dati rappresentativi puo risultare
convincente su clip selezionate e debole nelle partite reali.

## 1.4 Dataset

Un dataset MatchIQ ben costruito puo contenere:

- partite complete e segmenti;
- momenti tattici delimitati temporalmente;
- scene non tattiche;
- hard negative;
- categoria proposta e categoria corretta;
- valore tattico per lo staff;
- frame rappresentativo;
- alternative scartate;
- descrizione originale e revisione umana;
- linee o annotazioni geometriche;
- provenienza, diritti e limiti d'uso;
- qualita tecnica e dominio video.

Queste informazioni consentono di valutare e migliorare separatamente:

- candidate discovery;
- filtri non tattici;
- classificazione;
- ranking;
- selezione del frame;
- generazione del testo;
- calibrazione delle confidence.

## 1.5 Feedback umano

Il feedback umano e il moltiplicatore del dataset. Un video senza review e un
input grezzo. Lo stesso video, dopo la review, puo diventare:

- un esempio positivo;
- un esempio negativo;
- un caso ambiguo;
- un hard negative;
- una correzione di categoria;
- una preferenza editoriale;
- una geometria tattica;
- una spiegazione utile a un altro analista.

Il feedback ha valore soltanto quando:

- l'utente e autorizzato a produrlo;
- il suo ruolo e noto;
- l'azione e contestualizzata;
- la versione precedente resta tracciata;
- il feedback non viene interpretato automaticamente come ground truth;
- una quota viene sottoposta a controllo qualita.

## 1.6 Confronto sintetico

| Asset | Velocita di replica | Dipendenza da terzi | Valore cumulativo | Difendibilita |
|---|---:|---:|---:|---:|
| Interfaccia software | media | media | media | media |
| Modello generalista | alta | alta | limitato senza dati | bassa |
| Modello specializzato | media | media | alta | media |
| Dataset autorizzato e annotato | bassa | bassa dopo acquisizione | molto alta | alta |
| Feedback verificato dello staff | molto bassa | bassa | crescente con l'uso | molto alta |
| Benchmark congelato e rappresentativo | bassa | bassa | strategico | alta |

## 1.7 Conseguenza strategica

MatchIQ non deve ottimizzare per "piu video possibili". Deve ottimizzare per:

1. piu diritti verificati;
2. piu varieta reale;
3. piu momenti correttamente delimitati;
4. piu errori difficili documentati;
5. piu feedback qualificato;
6. meno leakage;
7. benchmark piu affidabili.

---

# 2. Principi guida

## 2.1 Qualita prima della quantita

Un'ora di video con:

- provenienza certa;
- diritti chiari;
- metadati completi;
- momenti annotati;
- hard negative;
- revisione documentata;

vale piu di molte ore prive di contesto e autorizzazione.

La crescita del catalogo non deve essere usata da sola come KPI di successo.

## 2.2 Momenti prima dei frame

L'unita informativa principale e il momento temporale, non il JPEG isolato.

Ogni acquisizione deve preservare, quando consentito:

- una finestra prima dell'evento;
- lo sviluppo;
- una finestra dopo l'evento;
- continuita e cambi camera;
- relazione tra momento e frame rappresentativo.

Il frame resta utile per review, presentazione e geometrie, ma non deve
sostituire la sequenza.

## 2.3 Dilettantismo come dominio principale

Il dataset deve rappresentare in modo intenzionale:

- camere non professionali;
- riprese da tribuna;
- smartphone;
- camere fisse;
- zoom imperfetti;
- luce disomogenea;
- campi e divise variabili;
- grafiche assenti o non standard;
- giocatori spesso non identificabili;
- contesti con minori.

Il professionismo potra ampliare la robustezza, ma non deve dominare il dataset
al punto da rendere invisibile il caso d'uso principale.

## 2.4 Dati realmente annotati

Un output prodotto dall'AI non diventa etichetta solo perche esiste.

Devono essere distinti:

- predizione AI;
- conferma utente;
- correzione utente;
- annotazione primaria;
- seconda revisione;
- decisione senior;
- ground truth congelata.

## 2.5 Miglioramento continuo

Ogni ciclo deve produrre:

- nuovi esempi;
- failure mode;
- revisioni del manuale;
- correzioni della tassonomia;
- metriche per dominio;
- una decisione su cosa raccogliere dopo.

La raccolta non e una fase una tantum. E un circuito governato.

## 2.6 Benchmark prima del training

Prima di addestrare o adattare un modello devono esistere:

- benchmark congelato;
- split senza leakage noto;
- baseline ripetibile;
- metriche per categoria e dominio;
- protocollo di revisione;
- regole di go/no-go.

Il training senza benchmark rende impossibile sapere se il prodotto e
realmente migliorato.

## 2.7 Diritti prima dell'accesso tecnico

Poter scaricare, visualizzare o ricevere un video non implica il diritto di:

- conservarlo;
- annotarlo;
- usarlo nel benchmark;
- usarlo per training;
- generare materiale dimostrativo;
- condividerlo con annotatori esterni.

Ogni finalita deve essere esplicita.

## 2.8 Provenienza sempre tracciata

Ogni asset deve mantenere almeno:

- soggetto che lo ha fornito;
- origine dichiarata;
- data di acquisizione;
- squadra/partita, se consentito;
- tipo di autorizzazione;
- finalita consentite;
- eventuale scadenza;
- presenza di minori;
- restrizioni;
- stato di revoca.

## 2.9 Astensione invece di invenzione

Quando provenienza, diritti, identita o contenuto non sono sufficienti:

- il dato viene messo in quarantena;
- la categoria puo essere `non determinabile`;
- il video non entra nel benchmark congelato;
- non viene colmato il vuoto con inferenze.

## 2.10 Separazione delle finalita

Le finalita minime da separare sono:

- erogazione del servizio;
- conservazione operativa;
- miglioramento del prodotto;
- benchmark interno;
- addestramento;
- demo e marketing;
- ricerca con partner;
- condivisione esterna.

Il consenso o contratto per una finalita non si estende automaticamente alle
altre.

## 2.11 Reversibilita

La strategia deve poter:

- bloccare un asset;
- revocare l'accesso;
- propagare una revoca ai derivati;
- ricostruire dove il dato e stato usato;
- escluderlo da versioni future;
- documentare i limiti quando la rimozione da un modello gia addestrato non e
  tecnicamente immediata.

Questa procedura operativa e da validare durante la raccolta dati.

---

# 3. Fonti possibili dei video

## 3.1 Criteri comuni di valutazione

Ogni sorgente viene valutata lungo sette dimensioni:

1. **valore di dominio:** quanto rappresenta gli utenti reali;
2. **varieta:** camere, categorie, luce, campi, eta e stili;
3. **qualita tecnica:** continuita, risoluzione, stabilita, campo visibile;
4. **costo:** acquisizione, trasferimento, annotazione e revisione;
5. **chiarezza dei diritti:** possibilita di dimostrare le finalita consentite;
6. **rischio:** minori, terze parti, broadcast, revoche e metadati incompleti;
7. **priorita:** ordine raccomandato per B2.

## 3.2 Partite GS Arco

**Vantaggi**

- accesso diretto del founder;
- conoscenza del contesto;
- possibilita di ricostruire partita, formazione e situazioni;
- dominio dilettantistico reale;
- feedback tecnico disponibile;
- utile per avviare il processo senza coordinare molti clienti.

**Limiti**

- rischio di sovrarappresentare un solo club;
- stesse divise, campo, camera e stile;
- possibile presenza frequente degli stessi giocatori;
- rischio che chi annota conosca gia l'azione;
- campione non sufficiente a dimostrare generalizzazione.

**Valore**

Molto alto per:

- validare il manuale;
- misurare tempi di annotazione;
- trovare failure operativi;
- costruire il primo nucleo di hard negative.

Non sufficiente da solo per benchmark robusto.

**Qualita**

Dipende dalla modalita di ripresa. La distribuzione tra smartphone, camera
fissa e ripresa da tribuna e da validare durante la raccolta dati.

**Costi**

Bassi per accesso; medi per ordinamento, verifica diritti e annotazione.

**Diritti**

Non devono essere presunti. Servono:

- conferma del titolare della registrazione;
- autorizzazione coerente con le finalita;
- policy specifica in presenza di minori;
- verifica di eventuali avversari e organizzatori;
- limiti per uso interno, benchmark, training e demo.

**Priorita**

Priorita 1, soltanto dopo verifica documentale.

## 3.3 Partite dei clienti

**Vantaggi**

- massima aderenza al prodotto;
- varieta crescente;
- dati generati nel workflow reale;
- feedback naturale da coach e match analyst;
- valore per misurare utilita e tempo di review.

**Limiti**

- un upload per usare il servizio non equivale a opt-in per benchmark/training;
- metadati spesso incompleti;
- qualita molto variabile;
- possibili duplicati;
- revoca e cancellazione account;
- rischio di bias verso clienti piu attivi.

**Valore**

Potenzialmente il piu alto nel lungo periodo, perche unisce dominio reale e
feedback operativo.

**Qualita**

Molto variabile. Deve essere misurata, non assunta.

**Costi**

Bassi per acquisizione marginale, ma alti se servono:

- verifica dei diritti;
- normalizzazione dei metadati;
- assistenza al cliente;
- revisione delle annotazioni.

**Diritti**

Richiede opt-in separato e comprensibile per le finalita ulteriori rispetto
all'erogazione del servizio. Il rifiuto non deve impedire l'uso normale del
prodotto.

**Priorita**

Priorita 2 dopo il pilota founder e dopo la definizione del flusso di consenso.

## 3.4 Partite autorizzate tramite accordo diretto

Include accordi con:

- club;
- academy;
- tornei;
- scuole calcio;
- federazioni o organizzatori;
- videomaker titolari dei diritti.

**Vantaggi**

- finalita negoziabili;
- catalogo pianificabile;
- metadati migliori;
- possibilita di bilanciare domini mancanti;
- rapporto stabile.

**Limiti**

- negoziazione lenta;
- necessita di verificare la catena dei diritti;
- possibili restrizioni territoriali o temporali;
- obblighi di cancellazione e reporting.

**Valore**

Molto alto per benchmark e crescita controllata.

**Qualita**

Da media ad alta; dipende dal partner.

**Costi**

Medi o alti per contratti, trasferimenti, storage e relazione.

**Diritti**

Devono specificare almeno:

- soggetto autorizzante;
- materiale coperto;
- finalita;
- durata;
- territorio;
- accesso degli annotatori;
- derivati consentiti;
- revoca;
- uso in benchmark;
- uso in training;
- presenza di minori;
- pubblicazione di esempi.

**Priorita**

Priorita 2 per colmare domini assenti; priorita 3 per acquisizione su scala.

## 3.5 Video caricati dagli allenatori

**Vantaggi**

- rilevanza altissima;
- problemi reali;
- annotazioni e obiettivi gia contestualizzati;
- forte potenziale di feedback.

**Limiti**

- l'allenatore potrebbe non essere titolare di tutti i diritti;
- il video puo provenire da terzi;
- file ritagliati o ricodificati;
- metadati incompleti;
- alto rischio di usare materiale non autorizzato.

**Valore**

Alto per prodotto; condizionale per dataset.

**Qualita**

Variabile.

**Costi**

Bassi per ricezione, medi per verifica e curatela.

**Diritti**

Il caricamento deve essere considerato `service-only` per impostazione
predefinita. Il passaggio a benchmark o training richiede:

- dichiarazione di titolarita/autorizzazione;
- opt-in specifico;
- validazione minima;
- possibilita di revoca.

**Priorita**

Priorita alta per osservare il dominio; priorita subordinata per il dataset
finche i diritti non sono verificati.

## 3.6 Video smartphone

**Vantaggi**

- rappresentano il dilettantismo reale;
- ampia disponibilita;
- grande varieta di angoli, zoom, stabilita e luce;
- ottimi per misurare robustezza;
- generano hard negative realistici.

**Limiti**

- campo spesso parziale;
- movimento camera;
- occlusioni;
- rotazione e aspect ratio variabili;
- compressione;
- interruzioni;
- audio e conversazioni potenzialmente sensibili;
- persone fuori dal terreno di gioco.

**Valore**

Molto alto per la robustezza del dominio MatchIQ.

**Qualita**

Bassa o media in termini editoriali, ma strategicamente preziosa.

**Costi**

Bassi per registrazione, medi/alti per pulizia e annotazione.

**Diritti**

Servono policy su:

- titolare della ripresa;
- persone riprese;
- minori;
- audio;
- pubblico;
- aree non pertinenti;
- condivisione da parte dell'utente.

**Priorita**

Priorita 1 nel pilota, in quota controllata e non esclusiva.

## 3.7 Camere fisse

**Vantaggi**

- continuita;
- maggiore porzione di campo;
- meno cambi di regia;
- migliore comparabilita temporale;
- utili in futuro per tracking e calibrazione.

**Limiti**

- risoluzione apparente dei giocatori ridotta;
- occlusioni;
- prospettiva distante;
- un unico angolo;
- possibili aree morte;
- dipendenza dall'installazione.

**Valore**

Molto alto per momenti tattici collettivi e tracking futuro.

**Qualita**

Da media ad alta, con stabilita generalmente elevata.

**Costi**

Medi: accesso, trasferimento di file lunghi, storage e gestione.

**Diritti**

Spesso piu chiari se la camera appartiene al club, ma devono comunque coprire:

- squadre ospiti;
- competizione;
- minori;
- finalita AI;
- accesso dei revisori.

**Priorita**

Priorita 1-2. Deve essere presente gia nel nucleo iniziale per evitare un
dataset dominato da broadcast o smartphone.

## 3.8 Broadcast

**Vantaggi**

- qualita visiva alta;
- scoreboard;
- molti contesti;
- replay e primi piani utili come negativi;
- ampia varieta tattica apparente.

**Limiti**

- regia non progettata per analisi;
- tagli frequenti;
- replay;
- grafiche;
- primi piani;
- forte domain gap rispetto al dilettantismo;
- diritti complessi.

**Valore**

Alto come sorgente di negativi e test di robustezza; limitato come nucleo del
dataset MatchIQ.

**Qualita**

Alta tecnicamente, discontinua tatticamente.

**Costi**

Potenzialmente alti per licenze.

**Diritti**

Non usare contenuti broadcast commerciali senza licenza esplicita per la
finalita prevista. Accessibilita pubblica, abbonamento o registrazione privata
non equivalgono a diritto di training.

**Priorita**

Priorita bassa per acquisizione. Ammissibile soltanto con licenza chiara e come
quota minoritaria controllata.

## 3.9 Altre sorgenti

### Dataset pubblici o accademici

**Vantaggi:** baseline, confronto, metadati talvolta strutturati.

**Limiti:** dominio diverso, tassonomie incompatibili, licenze restrittive.

**Priorita:** media per ricerca e confronto; condizionale per training.

### Tornei e academy partner

**Vantaggi:** molte partite omogenee, metadati, camere ripetibili.

**Limiti:** forte rischio minori e concentrazione su pochi contesti.

**Priorita:** alta solo con governance legale e consenso adeguati.

### Videomaker e servizi di ripresa

**Vantaggi:** qualita e cataloghi.

**Limiti:** il videomaker potrebbe non possedere tutti i diritti secondari.

**Priorita:** media.

### Materiale sintetico o ricostruito

**Vantaggi:** controllo, assenza di alcune restrizioni personali.

**Limiti:** domain gap, dinamiche non autentiche, rischio di metriche
fuorvianti.

**Priorita:** bassa; non deve sostituire partite reali.

### Social media e piattaforme video

**Vantaggi:** disponibilita apparente.

**Limiti:** provenienza, licenze, montaggi, compressione e privacy.

**Priorita:** esclusa per default salvo accordo/licenza esplicita.

## 3.10 Matrice di priorita iniziale

| Sorgente | Valore dominio | Chiarezza diritti potenziale | Costo curatela | Priorita B2 |
|---|---:|---:|---:|---:|
| GS Arco verificato | molto alto | alta dopo verifica | medio | 1 |
| Camera fissa di club partner | molto alto | medio-alta | medio | 1 |
| Smartphone autorizzato | molto alto | media | medio-alto | 1 |
| Accordo diretto club/academy | molto alto | alta | medio-alto | 2 |
| Opt-in clienti | molto alto | media | alto | 2 |
| Upload ordinario allenatore | alto | bassa senza verifica | alto | quarantena |
| Dataset accademico compatibile | medio | variabile | medio | 3 |
| Broadcast licenziato | medio | alta se licenziato | alto | 4 |
| Broadcast non licenziato | nessuno utilizzabile | insufficiente | irrilevante | escluso |
| Social/video web non autorizzato | nessuno utilizzabile | insufficiente | irrilevante | escluso |

La priorita effettiva e da validare durante la raccolta dati.

---

# 4. Strategia dei diritti

## 4.1 Principio

Nessun asset entra nel dataset proprietario soltanto perche e tecnicamente
disponibile.

L'idoneita richiede due verifiche separate:

1. **idoneita legale e contrattuale**;
2. **idoneita tecnica e scientifica**.

Un video puo essere tecnicamente eccellente ma non utilizzabile. Un video
autorizzato puo essere troppo povero per il benchmark ma utile come hard
negative.

## 4.2 Classi di utilizzo

Ogni video deve avere una classe esplicita:

| Classe | Uso consentito |
|---|---|
| R0 - Quarantena | nessun uso oltre verifica e sicurezza |
| R1 - Servizio | elaborazione necessaria a fornire il servizio all'utente |
| R2 - Miglioramento prodotto | analisi interna di errori, nei limiti autorizzati |
| R3 - Benchmark | valutazione interna congelata, senza training |
| R4 - Training | addestramento/adattamento autorizzato |
| R5 - Demo/pubblicazione | esempi visibili a terzi, espressamente autorizzati |

Le classi sono cumulative solo se il documento di autorizzazione lo prevede.
R1 non implica R2-R5. R4 non implica R5.

## 4.3 Cosa conservare

Quando consentito, conservare:

- file sorgente o riferimento verificabile;
- fingerprint del file;
- metadati minimi;
- autorizzazione e versione;
- classe di utilizzo;
- limitazioni;
- annotazioni;
- audit trail;
- derivati prodotti;
- collegamento tra revoca e derivati.

Non conservare dati accessori privi di valore per la finalita dichiarata.

## 4.4 Cosa anonimizzare o pseudonimizzare

Quando l'identita non e necessaria:

- sostituire nomi personali con identificatori;
- separare contatti e metadati tecnici;
- evitare nomi nei nomi file;
- rimuovere note libere non pertinenti;
- limitare accesso a roster e informazioni personali;
- oscurare o eliminare audio non necessario, se tecnicamente e legalmente
  appropriato;
- evitare di usare il riconoscimento facciale come scorciatoia.

L'anonimizzazione visiva reale di una partita puo essere difficile: volti,
numero, divisa, voce e contesto possono rendere una persona re-identificabile.
Non deve essere dichiarato "anonimo" un dato solo perche il nome e stato
rimosso.

La procedura concreta e da validare durante la raccolta dati.

## 4.5 Cosa non usare

Escludere per default:

- video senza provenienza;
- download da piattaforme senza licenza compatibile;
- broadcast non licenziati;
- video per cui il fornitore non puo dichiarare l'autorizzazione;
- materiale soggetto a revoca non gestibile;
- contenuti con minori senza processo approvato;
- clip ricevute informalmente senza tracciamento;
- materiale promozionale con diritti limitati al marketing;
- asset per cui non e possibile separare servizio e training;
- video ottenuti violando termini o controlli di accesso.

## 4.6 Consenso e autorizzazione

Il processo deve:

- usare linguaggio comprensibile;
- separare finalita necessarie e facoltative;
- evitare caselle preselezionate;
- registrare versione, data e soggetto;
- consentire il rifiuto delle finalita facoltative;
- spiegare conservazione e revoca;
- indicare chi puo vedere il materiale;
- distinguere video, annotazioni e feedback.

Il meccanismo giuridico corretto dipende dal contesto e deve essere validato
prima della raccolta.

## 4.7 Minori

Il dilettantismo include frequentemente minori. Serve una policy dedicata,
non una nota generica.

Prima di includere materiale con minori devono essere definiti:

- soggetto autorizzato a concedere l'uso;
- documentazione richiesta;
- finalita consentite;
- accesso degli annotatori;
- localizzazione dello storage;
- minimizzazione;
- pubblicazione vietata per default;
- durata;
- revoca;
- gestione di squadre avversarie;
- escalation per casi dubbi.

Fino all'approvazione della policy, il materiale con minori resta R0 o R1 e non
entra in benchmark/training.

## 4.8 Revoca

Ogni asset deve poter passare a stato:

- attivo;
- limitato;
- revocato;
- in verifica;
- scaduto.

La revoca deve attivare:

1. blocco di nuove elaborazioni non necessarie;
2. esclusione dalle nuove versioni del dataset;
3. identificazione dei derivati;
4. cancellazione o limitazione secondo l'impegno applicabile;
5. registro dell'azione;
6. valutazione dei modelli gia addestrati;
7. conferma al soggetto interessato quando prevista.

Tempi e modalita sono da validare durante la raccolta dati.

## 4.9 Retention

La retention non deve essere unica per tutto.

Definire finestre separate per:

- file upload temporaneo;
- progetto attivo;
- archivio cliente;
- materiale in quarantena;
- benchmark congelato;
- training set;
- annotazioni;
- log di consenso;
- backup;
- dati revocati.

La durata deve derivare dalla finalita e dagli obblighi applicabili. Il
principio e: conservare il minimo necessario, con scadenze verificabili.

## 4.10 Accesso

Applicare il minimo privilegio:

- cliente: propri video e derivati;
- annotatore: soli asset assegnati, senza dati personali non necessari;
- revisore: campioni e contesto necessario;
- data steward: diritti, versioni e revoche;
- sviluppatore: preferibilmente dati pseudonimizzati o campioni autorizzati;
- partner esterno: solo tramite accordo e perimetro esplicito.

## 4.11 Registro dei diritti

Per B2 serve concettualmente un registro con:

- `asset_id`;
- titolare dichiarato;
- fornitore;
- base documentale;
- classi R0-R5;
- data inizio/fine;
- presenza minori;
- restrizioni geografiche;
- annotatori ammessi;
- condivisione esterna;
- revoca;
- note;
- responsabile della verifica.

Questo documento non ne implementa la struttura tecnica.

---

# 5. Ordine di raccolta

## 5.1 Non partire da tutto

La prima raccolta deve massimizzare:

- chiarezza delle regole;
- velocita di annotazione;
- possibilita di accordo;
- valore per i filtri;
- diversita tecnica controllata.

Non deve inseguire contemporaneamente tutte le tattiche.

## 5.2 Primo blocco: scene non tattiche e replay

Raccogliere prima:

- replay;
- esultanze;
- primi piani;
- panchina;
- pubblico;
- grafiche televisive;
- campo insufficiente;
- pochi giocatori;
- scene tecniche non utili;
- video nero/corrotto.

Motivi:

- sono failure evidenti della pipeline corrente;
- riducono il rumore prima della classificazione tattica;
- producono hard negative importanti;
- hanno criteri relativamente osservabili;
- migliorano subito la review.

## 5.3 Secondo blocco: palle inattive

Ordine consigliato:

1. calcio d'angolo;
2. rimessa laterale;
3. punizione;
4. palla inattiva generica;
5. casi ambigui/non determinabili.

Motivi:

- inizio e ripresa del gioco sono osservabili in sequenza;
- corner e rimesse hanno segnali spaziali piu chiari;
- il valore per allenatori e match analyst e concreto;
- consentono di misurare specificita e astensione;
- aiutano a costruire una gerarchia categoria padre/figlia.

## 5.4 Terzo blocco: casi difficili delle prime classi

Prima di espandere la tassonomia, raccogliere:

- corner che sembrano rimesse;
- punizioni rapidamente battute;
- replay senza grafica;
- primi piani con campo sullo sfondo;
- campo largo senza struttura;
- palla inattiva interrotta;
- cambi camera;
- situazioni con palla non visibile;
- falsi positivi prodotti dalla baseline.

Questi casi sono piu informativi dei duplicati facili.

## 5.5 Quarto blocco: costruzione dal basso

La costruzione dal basso puo entrare come categoria pilota dopo che:

- il protocollo temporale e stabile;
- gli annotatori distinguono ripresa e possesso aperto;
- la copertura del portiere e sufficiente;
- i cambi camera sono gestiti;
- l'accordo e misurabile.

La priorita precisa e da validare durante la raccolta dati.

## 5.6 Quinto blocco: pressing, blocchi e transizioni

Queste categorie arrivano dopo perche richiedono:

- sequenze piu lunghe;
- relazione tra squadre;
- identificazione del possesso;
- velocita e direzione;
- contesto prima/dopo;
- maggiore competenza tattica;
- piu disaccordi;
- tracking e calibrazione per misure solide.

Raccoglierle troppo presto produrrebbe etichette rumorose e confidence
ingannevoli.

## 5.7 Regola di espansione

Una categoria nuova entra nel piano soltanto quando:

- definizione e confini sono operativi;
- esistono positivi, negativi e hard negative;
- il set di calibrazione e aggiornato;
- l'accordo annotatori e accettabile;
- il costo non e sproporzionato;
- non sottrae qualita alle categorie gia aperte.

---

# 6. Strategia MVP

## 6.1 Obiettivo dell'MVP dati

Il dataset minimo utile non serve ad addestrare "l'AI definitiva". Serve a:

- testare B2 e B3;
- misurare l'annotabilita;
- eseguire la baseline corrente;
- quantificare failure;
- congelare un primo benchmark;
- decidere cosa costruire dopo.

## 6.2 Range di video

Un intervallo iniziale ragionevole e:

- **pilota operativo:** ordine di grandezza di una o poche decine di partite;
- **benchmark minimo:** alcune decine di partite, se la varieta e sufficiente;
- **benchmark intermedio:** decine alte o prime centinaia, soltanto dopo
  deduplica e governance.

Il numero esatto non e un criterio di qualita ed e da validare durante la
raccolta dati.

## 6.3 Range di momenti

L'obiettivo iniziale e un ordine di grandezza di:

- centinaia di scene non tattiche;
- centinaia di momenti di palla inattiva;
- decine o centinaia di hard negative per confusione critica;
- un sottoinsieme piu piccolo con doppia revisione completa.

Non e utile fissare migliaia di clip prima di conoscere:

- frequenza reale delle classi;
- tempo medio di annotazione;
- tasso di disaccordo;
- qualita delle sorgenti;
- tasso di esclusione per diritti.

I range per categoria sono da validare durante la raccolta dati.

## 6.4 Composizione minima

L'MVP deve includere piu di:

- un club;
- un campo;
- una camera;
- una condizione di luce;
- una fascia di qualita;
- una categoria/competizione;
- una sorgente.

Deve includere:

- camera fissa;
- camera mobile/smartphone;
- almeno una sorgente con regia o cambi camera, se autorizzata;
- dilettantismo come quota dominante;
- partite complete o sequenze continue;
- scene facili e difficili;
- negativi chiari e hard negative.

## 6.5 Quote consigliate

Non fissare percentuali definitive prima del pilota. Usare fasce operative:

- dominio dilettantistico: maggioranza netta;
- camere fisse e mobili: entrambe sostanziali;
- scene non tattiche: quota sufficiente a misurare leakage;
- palle inattive specifiche: nessuna classe deve essere solo simbolica;
- hard negative: quota intenzionale, non residua;
- materiale broadcast: minoritario e soltanto autorizzato.

Le quote sono da validare durante la raccolta dati.

## 6.6 Gate di sufficienza

L'MVP e pronto non quando raggiunge un contatore, ma quando:

- tutti i video hanno diritti verificati;
- i metadati obbligatori sono completi;
- gli split provvisori sono per partita/sorgente;
- i duplicati noti sono identificati;
- il manuale viene applicato in modo coerente;
- le principali confusioni sono rappresentate;
- il benchmark non dipende da un solo club;
- almeno una quota critica ha doppia revisione;
- esiste un registro dei failure mode;
- la baseline puo essere eseguita e interpretata.

## 6.7 Cosa non fare nell'MVP

- addestrare su tutto cio che e disponibile;
- usare clip dello stesso match in train e test;
- confondere output AI e label;
- bilanciare duplicando gli stessi momenti;
- usare soltanto i frame piu belli;
- usare video non autorizzati "solo per provare";
- includere minori senza policy approvata;
- congelare benchmark prima del pilota.

---

# 7. Strategia di crescita

## 7.1 Fase 1 - Founder

**Obiettivo:** dimostrare che il processo e praticabile.

Fonti:

- GS Arco verificato;
- altre partite direttamente controllabili;
- combinazione di camera fissa e smartphone, se disponibile.

Attivita:

- inventario;
- verifica dei diritti;
- metadati;
- campionamento delle sorgenti;
- annotazione pilota;
- stima dei costi;
- raccolta dei primi hard negative.

Uscita:

- manuale corretto;
- prime metriche operative;
- elenco dei domini mancanti;
- decisione su cosa chiedere ai primi clienti.

Rischio:

- founder bias.

Contromisura:

- non congelare un benchmark rappresentativo usando un solo club.

## 7.2 Fase 2 - Primi clienti

**Obiettivo:** introdurre varieta reale senza perdere controllo.

Fonti:

- clienti opt-in;
- club partner;
- video caricati con diritti verificati.

Attivita:

- consenso granulare;
- catalogo separato tra service-only e dataset-eligible;
- monitoraggio della qualita;
- feedback staff;
- campionamento stratificato;
- prima analisi dei costi per sorgente.

Uscita:

- benchmark minimo piu rappresentativo;
- primi dati di review nel prodotto;
- distribuzione reale delle classi;
- confronto tra camere.

## 7.3 Fase 3 - Community

**Obiettivo:** ampliare la coda lunga del dilettantismo.

La community non deve diventare upload indiscriminato. Deve operare con:

- programma esplicito;
- requisiti di provenienza;
- checklist dei diritti;
- incentivi non legati alla quantita grezza;
- controllo campioni;
- reputazione del contributore;
- quarantena automatica per metadati incompleti.

Possibili incentivi:

- analisi aggiuntive;
- accesso anticipato a strumenti;
- report aggregati;
- riconoscimento del contributo;
- supporto di annotazione.

Gli incentivi e la sostenibilita sono da validare durante la raccolta dati.

## 7.4 Fase 4 - Club

**Obiettivo:** costruire partnership ricorrenti.

Un club partner puo contribuire con:

- partite complete;
- metadati;
- formazioni;
- feedback tecnico;
- camera stabile;
- revisori interni;
- casi d'uso prioritari.

MatchIQ deve offrire in cambio:

- confini contrattuali chiari;
- isolamento;
- controlli di revoca;
- risultati utili;
- report sulla qualita;
- nessun riuso inatteso.

## 7.5 Fase 5 - Professionismo

**Obiettivo:** ampliare robustezza e complessita senza cambiare il centro del
prodotto.

Il professionismo puo portare:

- qualita video;
- metadati;
- piu camere;
- maggior densita tattica;
- revisori qualificati.

Non deve:

- sostituire il dilettantismo;
- alterare le metriche globali nascondendo i domini difficili;
- essere usato come prova automatica di qualita nel prodotto principale.

## 7.6 Regola di passaggio tra fasi

Si passa alla fase successiva solo se:

- diritti gestibili;
- costi misurati;
- qualita controllata;
- annotatori calibrati;
- failure mode precedenti non ignorati;
- benchmark protetto;
- capacita operativa sufficiente.

---

# 8. Feedback come vantaggio competitivo

## 8.1 Principio

Il feedback non e un log di click. E una decisione tecnica contestualizzata.

Per diventare patrimonio proprietario deve mantenere:

- chi ha agito;
- ruolo;
- asset;
- timestamp;
- versione della predizione;
- valore precedente;
- valore corretto;
- motivazione, quando necessaria;
- finalita consentita;
- stato di review.

## 8.2 `Corretto`

Segnala che l'utente accetta:

- delimitazione;
- categoria;
- frame;
- descrizione;
- oppure una parte specifica.

Non deve essere interpretato come approvazione totale se il controllo riguarda
solo un componente.

Valore futuro:

- positivo confermato;
- misura della precisione;
- preferenza editoriale;
- esempio per calibrazione.

## 8.3 `Scarta`

Deve registrare un motivo:

- non tattico;
- replay;
- esultanza;
- primo piano;
- campo insufficiente;
- duplicato;
- momento sbagliato;
- qualita insufficiente;
- descrizione errata;
- altro.

Valore futuro:

- hard negative;
- failure del candidate discovery;
- failure editoriale;
- misura del tempo perso.

## 8.4 `Categoria`

Conservare:

- categoria proposta;
- categoria scelta;
- gerarchia;
- alternative;
- livello di certezza;
- eventuale `non determinabile`.

Valore futuro:

- matrice di confusione;
- dataset di classificazione;
- revisione della tassonomia;
- calibrazione dell'astensione.

## 8.5 `Frame`

Conservare:

- frame proposto;
- frame scelto;
- distanza temporale;
- ragione della sostituzione;
- alternative viste;
- eventuale assenza di frame idoneo.

Valore futuro:

- ranking editoriale;
- rappresentativita;
- confronto tra qualita estetica e tattica.

## 8.6 `Linee`

Le linee manuali possono rappresentare:

- linea difensiva;
- reparto;
- distanza;
- ampiezza;
- zona;
- relazione tra giocatori;
- ombra o copertura, se definita dal protocollo futuro.

Devono mantenere:

- coordinate;
- frame;
- tipo;
- squadra;
- revisore;
- versione;
- eventuale cancellazione.

Non devono essere assunte come ground truth geometrica senza calibrazione del
campo e protocollo specifico.

## 8.7 `Descrizione`

Conservare:

- testo AI;
- testo corretto;
- porzioni rimosse;
- fatti aggiunti;
- motivi;
- evidenze disponibili;
- affermazioni non supportate.

Valore futuro:

- valutazione delle allucinazioni;
- lessico dello staff;
- descrizioni prudenti;
- separazione tra osservazione e interpretazione.

## 8.8 Dal feedback alla ground truth

Pipeline raccomandata:

```text
interazione utente
    ↓
evento grezzo versionato
    ↓
controlli di validita e diritti
    ↓
campionamento per revisione
    ↓
conferma/correzione
    ↓
label candidata
    ↓
ground truth solo dopo protocollo previsto
```

## 8.9 Prevenzione del bias

Il feedback spontaneo tende a sovrarappresentare:

- errori evidenti;
- utenti esperti;
- club molto attivi;
- momenti visualmente interessanti;
- categorie gia disponibili.

Per compensare servono:

- campionamento casuale;
- review di casi non cliccati;
- confronto tra utenti;
- quote per dominio;
- audit dei "corretto" veloci;
- separazione tra comportamento e verita.

---

# 9. Strategia di annotazione

## 9.1 Quando usare un singolo annotatore

Un annotatore calibrato puo bastare per:

- negativi chiari;
- replay evidenti;
- video nero/corrotto;
- scene con pubblico o panchina senza azione;
- corner chiari;
- rimesse chiare;
- metadati tecnici osservabili;
- pre-etichettatura non congelata;
- catalogazione B2.

Condizioni:

- manuale applicabile;
- controllo campionario;
- nessun conflitto;
- label non destinata da sola al benchmark definitivo.

## 9.2 Quando usare doppia revisione

Richiedere almeno due persone per:

- benchmark/test;
- positivi difficili;
- hard negative;
- confini temporali ambigui;
- punizioni confuse con gioco aperto;
- palla inattiva generica;
- costruzione dal basso;
- pressing;
- blocchi;
- transizioni;
- valore tattico `ottimo`;
- descrizioni con inferenze;
- linee geometriche usate come riferimento.

## 9.3 Quando usare un revisore senior

Il revisore senior interviene quando:

- gli annotatori non convergono;
- la tassonomia non copre il caso;
- l'etichetta influenza una decisione di prodotto;
- il caso espone un nuovo failure mode;
- esiste rischio di specificita eccessiva;
- serve congelare la ground truth;
- la qualita del feedback di un contributore e incerta.

La verifica dei diritti resta responsabilita di un ruolo di governance dati,
non dell'annotatore tattico.

## 9.4 Ridurre il costo senza ridurre la qualita

Strategie:

- annotare prima scene non tattiche;
- usare sequenze candidate invece di rivedere sempre l'intera partita;
- raggruppare task simili;
- separare metadati, temporale, categoria e descrizione;
- doppia review solo dove serve;
- campionare i casi facili;
- usare revisione senior per eccezioni;
- costruire un set di calibrazione;
- misurare tempo per classe;
- fermare categorie troppo ambigue;
- usare il feedback prodotto come coda di priorita, non come label automatica.

## 9.5 Modello di staffing progressivo

### Founder

- annotazione e revisione concentrate;
- alto rischio di bias;
- utile per definire il protocollo.

### Piccolo team

- un annotatore primario;
- un secondo revisore part-time;
- un senior responsabile di tassonomia e campioni.

### Scala

- pool calibrato;
- assegnazione per competenza;
- quality sampling;
- monitoraggio per annotatore;
- ricalibrazione;
- data steward separato.

Dimensione e costo sono da validare durante la raccolta dati.

## 9.6 Metriche annotatore

Monitorare:

- tempo per momento;
- accordo categoria;
- accordo confini;
- tasso di astensione;
- correzioni senior;
- errori critici;
- uso improprio di `non determinabile`;
- stabilita nel tempo;
- accuratezza sui set di calibrazione.

Le metriche non devono essere usate per incentivare velocita a scapito della
qualita.

---

# 10. Strategia contro dataset rumorosi

## 10.1 Fonti di rumore

- video duplicati;
- stessa partita ricodificata;
- timestamp errati;
- label copiate dall'AI;
- categorie troppo specifiche;
- confini incoerenti;
- feedback superficiale;
- metadati inventati;
- camera e dominio non dichiarati;
- diritti incerti;
- annotatori non calibrati;
- leakage tra split.

## 10.2 Controllo qualita a livelli

### Livello 1 - Ingest

- provenienza;
- file leggibile;
- fingerprint;
- metadati;
- diritti;
- minori;
- classe R0-R5.

### Livello 2 - Pre-annotazione

- continuita;
- porzioni corrotte;
- duplicati;
- cambi camera;
- scene non valutabili.

### Livello 3 - Annotazione

- confini;
- categoria;
- utilita;
- frame;
- evidenze;
- alternative.

### Livello 4 - Review

- accordo;
- motivazioni;
- errori critici;
- revisione senior.

### Livello 5 - Dataset

- split;
- bilanciamento;
- leakage;
- versioni;
- revoche;
- freeze.

## 10.3 Versionamento

Versionare separatamente:

- video catalog;
- rights manifest;
- annotation schema;
- taxonomy;
- labels;
- benchmark;
- training set futuro;
- modelli;
- feedback.

Una modifica alla label non deve cancellare la versione precedente.

## 10.4 Auditing

Ogni release dati deve poter rispondere:

- quali asset contiene;
- da dove arrivano;
- quali diritti hanno;
- chi li ha annotati;
- quale manuale e stato usato;
- quali correzioni sono state applicate;
- quali split sono coinvolti;
- quali revoche sono pendenti;
- quali failure mode restano.

## 10.5 Casi dubbi

I casi dubbi devono:

- restare visibili;
- avere stato esplicito;
- non essere forzati nella classe maggioritaria;
- essere inclusi in un registro;
- alimentare revisione del manuale;
- entrare nel benchmark solo con trattamento documentato.

## 10.6 Hard negative

Un hard negative e un caso che:

- assomiglia a una categoria;
- induce errore sistematico;
- e legittimamente ambiguo o negativo;
- ha una spiegazione verificata.

Esempi:

- giocatori schierati per un corner non ancora battuto ma immagine da replay;
- portiere in possesso senza costruzione;
- densita locale senza pressing;
- campo largo senza struttura tattica leggibile;
- primo piano con molti giocatori sullo sfondo;
- rimessa confusa con punizione laterale.

Gli hard negative devono essere curati intenzionalmente e non trattati come
scarti.

## 10.7 Deduplica e leakage

Lo split deve avvenire a livello di:

- partita;
- sorgente;
- club;
- periodo;
- configurazione camera;

secondo il rischio valutato.

Non e sufficiente separare clip casualmente. Frame o sequenze della stessa
partita possono rendere il test artificialmente facile.

La strategia esatta di split e da validare durante la raccolta dati.

## 10.8 Freeze

Un benchmark congelato:

- non riceve feedback di produzione automaticamente;
- non viene usato per training;
- cambia soltanto con nuova versione;
- mantiene changelog;
- conserva le metriche storiche;
- viene controllato per revoche.

---

# 11. Categorie iniziali

## 11.1 Replay

Viene prima perche:

- e un failure evidente della regia;
- genera duplicati temporali;
- puo sembrare tatticamente utile in un frame;
- contamina candidate discovery, frame selection e report;
- e relativamente annotabile.

## 11.2 Non tattico

Viene prima perche:

- riduce il carico umano;
- costruisce negativi;
- impedisce all'AI di spiegare immagini non pertinenti;
- misura il leakage;
- protegge le categorie tattiche.

La classe deve mantenere sottotipi, evitando un contenitore opaco.

## 11.3 Palla inattiva generica

Serve come classe padre quando:

- la ripresa del gioco e visibile;
- il tipo specifico non e dimostrabile;
- la camera cambia;
- l'inizio e incompleto.

Permette astensione controllata senza inventare corner o punizione.

## 11.4 Calcio d'angolo

Viene prima perche:

- zona di battuta e area sono spesso visibili;
- struttura offensiva/difensiva e utile allo staff;
- sequenza ha confini pratici;
- produce esempi positivi e hard negative chiari.

## 11.5 Punizione

Viene prima delle categorie dinamiche, ma dopo corner/rimessa, perche:

- e utile;
- puo essere diretta, indiretta, laterale o rapida;
- presenta maggiore ambiguita;
- richiede contesto temporale.

## 11.6 Rimessa laterale

Viene prima perche:

- ripresa dalla linea laterale spesso osservabile;
- frequenza elevata;
- valore tattico concreto;
- confusione utile con gioco aperto e punizioni laterali.

## 11.7 Perche pressing arriva dopo

Il pressing non e "molti giocatori vicini". Richiede:

- trigger;
- portatore;
- avversari;
- intensita;
- direzione;
- coordinamento;
- durata;
- esito.

Senza tracking e sequenza, le label rischiano di codificare impressioni.

## 11.8 Perche blocchi e linee arrivano dopo

Richiedono:

- porzione ampia del campo;
- riconoscimento squadre;
- coordinate;
- calibrazione;
- stabilita temporale;
- distinzione tra fase e transizione.

Un frame largo non dimostra da solo un blocco.

## 11.9 Perche transizioni arrivano dopo

Richiedono:

- cambio possesso;
- istante iniziale;
- reazione delle squadre;
- direzione;
- velocita;
- esito;
- continuita camera.

Sono importanti, ma costose da annotare con precisione.

## 11.10 Politica iniziale

Baseline:

- replay;
- non tattico;
- palla inattiva generica;
- corner;
- punizione;
- rimessa;
- non determinabile.

Pilota successivo:

- costruzione dal basso.

Esplorazione controllata:

- pressing;
- linea/blocco;
- transizione positiva;
- transizione negativa.

L'ordine puo cambiare sulla base delle frequenze e dell'accordo, da validare
durante la raccolta dati.

---

# 12. Roadmap dati

## 12.1 Primi 24 mesi

### Mesi 0-2 - Governance e inventario

- definire classi R0-R5;
- approvare policy diritti e minori;
- inventariare fonti founder;
- definire metadati minimi;
- creare catalogo concettuale;
- selezionare un set di calibrazione;
- identificare domini mancanti.

**Gate:** nessuna annotazione benchmark senza diritti verificati.

### Mesi 2-4 - Pilota founder

- selezionare una o poche decine di partite candidate;
- garantire varieta camera;
- annotare scene non tattiche;
- annotare prime palle inattive;
- misurare tempi e disaccordi;
- aggiornare il manuale.

**Gate:** protocollo applicabile e costi osservabili.

### Mesi 4-6 - B3 e benchmark minimo candidato

- doppia review su campione critico;
- hard negative;
- deduplica;
- split provvisorio;
- baseline corrente;
- failure mode;
- decisione sulle categorie pilota.

**Gate:** non congelare finche diritti, accordo e leakage non sono controllati.

### Mesi 6-12 - Primi clienti

- opt-in granulare;
- acquisizione multi-club;
- camera fissa e smartphone;
- feedback verificato;
- benchmark minimo congelato;
- report per dominio;
- costi per momento accettato.

**Gate:** il benchmark non deve essere dominato dal founder.

### Mesi 13-18 - Community controllata

- programma contributori;
- quarantena;
- reputazione;
- campionamento;
- incremento hard negative;
- prima categoria pilota dinamica;
- revisione della copertura.

**Gate:** la quantita non deve degradare i KPI di qualita.

### Mesi 19-24 - Partnership club

- accordi ricorrenti;
- metadati migliori;
- piu camere fisse;
- revisori qualificati;
- benchmark intermedio;
- preparazione dei dati per esperimenti futuri;
- policy di revoca provata.

**Gate:** training soltanto con dataset e benchmark separati e con diritti
espliciti.

## 12.2 Anno 1

Patrimonio atteso:

- catalogo autorizzato;
- baseline di dominio;
- benchmark minimo;
- prime classi stabili;
- hard negative;
- annotatori calibrati;
- costi noti;
- pipeline di feedback definita.

La misura non e il numero di ore, ma la possibilita di ripetere una valutazione.

## 12.3 Anno 2

Patrimonio atteso:

- fonti multi-club;
- maggiore varieta geografica e tecnica;
- camera fissa e mobile ben rappresentate;
- benchmark intermedio;
- feedback prodotto versionato;
- prime geometrie utili;
- categorie dinamiche pilota;
- processi di revoca e auditing verificati.

## 12.4 Anno 3

L'anno 3 e un'estensione oltre l'orizzonte operativo di questo documento.

Obiettivi possibili:

- consolidare partnership;
- ampliare professionismo senza perdere dominio;
- multi-camera;
- tracking e calibrazione;
- benchmark cross-domain;
- dataset longitudinali;
- valutazione di adattamento per categoria.

Priorita e scala sono da validare durante la raccolta dati.

## 12.5 Dipendenze tra le fasi

```text
diritti e inventario
    ↓
annotazione pilota
    ↓
manuale corretto
    ↓
benchmark minimo
    ↓
baseline e failure
    ↓
acquisizione mirata
    ↓
feedback verificato
    ↓
benchmark intermedio
    ↓
training futuro separato
```

---

# 13. KPI

## 13.1 KPI di qualita

- quota di asset con metadati completi;
- quota di momenti accettati dopo review;
- tasso di annotazioni corrette dal senior;
- quota di `non determinabile`;
- tasso di frame senza evidenza sufficiente;
- duplicati rilevati;
- leakage tra split;
- quota di hard negative documentati;
- valid moment suppression rate;
- non-tactical leakage rate.

## 13.2 KPI di varieta

- numero di club/squadre rappresentati;
- distribuzione per categoria/eta;
- camera fissa/mobile/broadcast autorizzato;
- giorno/notte e luce;
- qualita video;
- orientamento e risoluzione;
- campi diversi;
- geografie;
- sorgenti;
- distribuzione dilettantismo/professionismo.

Nessuna metrica di varieta deve esporre dati personali non necessari.

## 13.3 KPI di annotazione

- tempo mediano per video;
- tempo mediano per momento;
- momenti per ora;
- accordo sulla categoria;
- accordo sui confini;
- accordo sull'utilita;
- tasso di escalation;
- ricalibrazioni;
- errori critici per annotatore;
- quota di task completati senza dati mancanti.

## 13.4 KPI di revisione

- quota a singola/doppia review;
- tempo revisore;
- tasso di conferma;
- tasso di correzione;
- tasso di scarto;
- motivi di scarto;
- decisioni senior;
- tempo fino al freeze;
- errori approvati accidentalmente.

## 13.5 KPI di costo

- costo per video idoneo;
- costo per ora acquisita;
- costo per momento candidato;
- costo per momento accettato;
- costo per hard negative;
- costo della doppia review;
- costo per sorgente;
- storage per asset idoneo;
- costo legale/operativo per partnership;
- costo marginale del feedback prodotto.

## 13.6 KPI di copertura

- categorie con positivi sufficientemente vari;
- categorie con hard negative;
- failure mode coperti;
- domini camera coperti;
- distribuzione per sorgente;
- classi con doppia review;
- classi con benchmark congelato;
- gap di copertura aperti.

## 13.7 KPI di crescita

- nuovi asset idonei per periodo;
- nuovi momenti accettati;
- nuovi contributori qualificati;
- nuovi club autorizzati;
- feedback utile per sessione;
- tasso di conversione da R1 a R3/R4 con opt-in;
- tasso di revoca;
- quota di crescita proveniente da sorgenti sottorappresentate.

## 13.8 KPI diritti e governance

- asset in quarantena;
- tempo medio di verifica;
- autorizzazioni scadute;
- revoche aperte;
- derivati non riconciliati;
- quota con minori;
- accessi non necessari;
- audit completati;
- incidenti.

## 13.9 KPI da non usare da soli

- ore totali;
- terabyte;
- numero di frame;
- numero di upload;
- numero di annotazioni;
- percentuale AI non calibrata.

## 13.10 Soglie

Le soglie di accettazione non devono essere inventate nel presente documento.
Devono essere definite dopo il pilota e sono da validare durante la raccolta
dati.

---

# 14. Rischi

## 14.1 Dataset sbilanciato

**Rischio**

Troppi esempi da:

- un club;
- un campo;
- una camera;
- una classe frequente;
- utenti molto attivi.

**Effetto**

Metriche globali buone e generalizzazione debole.

**Mitigazione**

- quote di acquisizione;
- report stratificati;
- stop temporaneo a fonti dominanti;
- acquisizione mirata dei gap.

## 14.2 Overfitting

**Rischio**

Il sistema apprende:

- divise;
- scoreboard;
- stadio;
- angolo camera;
- pattern del broadcaster;
- annotatore.

**Mitigazione**

- split per partita/club/sorgente;
- test cross-domain;
- holdout temporale;
- hard negative;
- audit delle feature spurie.

## 14.3 Leakage

**Rischio**

Stessa partita o replay in split diversi.

**Mitigazione**

- fingerprint;
- deduplica;
- grouping per partita;
- registro delle versioni;
- audit prima del freeze.

## 14.4 Diritti

**Rischio**

Uso oltre finalita, revoca non propagata, titolarita non verificata.

**Mitigazione**

- R0-R5;
- registro;
- opt-in;
- revisione legale;
- accesso minimo;
- procedura di revoca.

## 14.5 Minori

**Rischio**

Raccolta o condivisione senza processo adeguato.

**Mitigazione**

- policy dedicata;
- esclusione per default da R3-R5 fino ad approvazione;
- minimizzazione;
- accesso ristretto;
- niente demo/pubblicazione senza autorizzazione specifica.

## 14.6 Pochi clienti

**Rischio**

Varieta insufficiente e dipendenza dal founder.

**Mitigazione**

- partnership mirate;
- community controllata;
- acquisizione per gap;
- benchmark dichiarato come limitato;
- nessuna pretesa di generalizzazione.

## 14.7 Annotazioni rumorose

**Rischio**

Categorie soggettive, annotatori non calibrati, velocita incentivata.

**Mitigazione**

- manuale;
- set calibrazione;
- doppia review;
- senior;
- `non determinabile`;
- audit e versionamento.

## 14.8 Feedback non rappresentativo

**Rischio**

Solo gli errori vistosi vengono corretti.

**Mitigazione**

- campionamento casuale;
- review dei "corretto";
- confronto tra utenti;
- KPI per dominio.

## 14.9 Costi fuori controllo

**Rischio**

File lunghi, doppia review estesa, storage e trasferimento.

**Mitigazione**

- candidate moments;
- tier di review;
- misurazione per categoria;
- retention;
- acquisizione guidata dai gap.

## 14.10 Tassonomia prematura

**Rischio**

Aprire pressing, blocchi e transizioni prima che siano annotabili.

**Mitigazione**

- gate di espansione;
- pilota;
- categorie padre;
- astensione;
- revisione del manuale.

## 14.11 Domain shift

**Rischio**

Il prodotto cambia clienti, camere o competizioni.

**Mitigazione**

- monitoraggio drift;
- holdout recenti;
- acquisizione continua;
- versioni benchmark;
- report per dominio.

## 14.12 Sicurezza

**Rischio**

Accesso improprio a video, roster o note.

**Mitigazione**

- minimo privilegio;
- pseudonimizzazione;
- logging;
- ambienti separati;
- revisione dei partner;
- risposta agli incidenti.

## 14.13 Rischio reputazionale

**Rischio**

Percezione che MatchIQ usi automaticamente ogni upload per addestrare l'AI.

**Mitigazione**

- comunicazione chiara;
- scelta reale;
- service-only di default;
- tracciamento delle finalita;
- nessun dark pattern.

---

# 15. Visione finale a 5 anni

## 15.1 Patrimonio possibile

Fra cinque anni, il patrimonio MatchIQ potrebbe essere composto da:

- partite autorizzate multi-club;
- forte rappresentanza del dilettantismo;
- sequenze da camere fisse e mobili;
- momenti tattici temporalmente delimitati;
- tassonomia versionata;
- scene non tattiche e hard negative;
- frame rappresentativi;
- annotazioni geometriche;
- descrizioni corrette dallo staff;
- feedback contestualizzato;
- benchmark congelati per dominio;
- dati longitudinali;
- registri dei failure mode;
- metriche di costo e utilita.

## 15.2 Vantaggio concreto

Questo patrimonio consentirebbe a MatchIQ di:

- scegliere modelli sulla base di metriche proprie;
- misurare il valore nel dilettantismo;
- rilevare regressioni nascoste;
- migliorare le categorie piu utili allo staff;
- ridurre scene inutili;
- calibrare le confidence;
- adattare il sistema a camere difficili;
- confrontare versioni in modo ripetibile;
- spiegare perche una decisione e stata proposta;
- offrire workflow piu efficienti.

## 15.3 Perche sarebbe difficile da replicare

Un concorrente puo:

- usare lo stesso modello;
- creare un'interfaccia simile;
- integrare un LLM;
- acquistare infrastruttura.

E piu difficile replicare:

- anni di autorizzazioni e relazioni;
- varieta dilettantistica;
- protocollo di annotazione maturato;
- benchmark storici;
- hard negative reali;
- correzioni di allenatori e analyst;
- collegamento tra evidenze e decisioni;
- governance delle revoche;
- conoscenza dei failure mode.

## 15.4 Condizione necessaria

Il vantaggio esiste soltanto se il patrimonio rimane:

- legittimo;
- documentato;
- rappresentativo;
- verificato;
- separato per finalita;
- aggiornabile;
- revocabile;
- misurabile.

Accumulo disordinato di video non crea un moat. Crea costo e rischio.

---

# Appendice A - Ordine operativo raccomandato per B2

1. Approvare policy diritti e minori.
2. Definire classi R0-R5.
3. Inventariare GS Arco e fonti founder.
4. Registrare provenienza e limitazioni.
5. Scartare o mettere in quarantena asset dubbi.
6. Selezionare varieta minima di camera e luce.
7. Preparare split soltanto provvisori.
8. Evitare estrazione massiva.
9. Costruire il set pilota B3.
10. Misurare annotazione e disaccordo.
11. Correggere manuale e categorie.
12. Congelare il benchmark solo dopo deduplica e review.

---

# Appendice B - Scheda concettuale di acquisizione

## Identita

- asset ID;
- partita ID;
- fornitore;
- titolare dichiarato;
- club/squadra, se consentito;
- data;
- luogo, se necessario;
- categoria;
- presenza minori.

## File

- formato;
- durata;
- risoluzione;
- frame rate;
- fingerprint;
- camera fissa/mobile/broadcast;
- orientamento;
- audio;
- continuita;
- ricodifiche note.

## Diritti

- classe R0-R5;
- riferimento autorizzazione;
- data inizio/fine;
- finalita;
- restrizioni;
- annotatori ammessi;
- pubblicazione;
- training;
- revoca;
- responsabile verifica.

## Dominio

- dilettantistico/professionistico;
- camera;
- luce;
- meteo;
- campo;
- grafica;
- qualita;
- zoom;
- stabilita.

## Dataset

- idoneo/non idoneo;
- motivo;
- split provvisorio;
- duplicati;
- versione;
- stato annotazione;
- stato review;
- benchmark;
- training futuro.

---

# Appendice C - Decisioni da validare

Le seguenti decisioni non devono essere congelate senza dati:

- range effettivo di partite per l'MVP;
- quota di smartphone e camera fissa;
- tempo medio di annotazione;
- costo per momento accettato;
- soglia di accordo;
- quota di doppia revisione;
- composizione degli hard negative;
- priorita tra punizioni e rimesse;
- ingresso della costruzione dal basso;
- incentivi alla community;
- retention specifica;
- percentuali di split;
- soglie KPI.

Per tutte vale:

> da validare durante la raccolta dati

---

# Criteri di completamento della strategia B2

La progettazione B2 e pronta per la fase operativa quando:

- le sorgenti sono prioritarizzate;
- il dominio dilettantistico e protetto;
- esiste una classificazione degli usi;
- diritti e minori hanno un processo approvato;
- l'inventario minimo e definito;
- l'ordine delle categorie e condiviso;
- l'MVP usa range e gate, non numeri arbitrari;
- feedback e annotazione sono distinti;
- KPI e rischi sono tracciati;
- la selezione dei video precede l'estrazione massiva;
- gli split restano provvisori prima della deduplica;
- nessun asset dubbio entra nel benchmark congelato.

Questo documento completa la progettazione della strategia di acquisizione. Non
certifica che i video B2 siano stati raccolti, autorizzati o selezionati.
