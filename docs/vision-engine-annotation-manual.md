# MatchIQ Vision Engine V3.1

## Manuale operativo di annotazione - Milestone B1

**Stato:** bozza operativa da calibrare  
**Dipende da:** Benchmark Specification B0 e Tactical Moment Selection Design  
**Finalita:** produrre annotazioni umane ripetibili, confrontabili e auditabili  
**Ambito:** video calcistici, momenti tattici, scene non tattiche e materiale di review  

Questo manuale traduce la specifica del benchmark in decisioni operative. Non
descrive l'interfaccia attuale, non presume che la pipeline sia corretta e non
autorizza l'uso di categorie oltre il livello sostenuto dalle immagini.

Ogni regola indicata come provvisoria e **da validare durante l'annotazione
pilota**.

---

## 1. Scopo del manuale

### 1.1 Chi deve usarlo

Il manuale e destinato a:

- annotatori che costruiscono la ground truth;
- match analyst e allenatori che revisionano i casi tattici;
- revisori senior che risolvono disaccordi;
- curatori che controllano qualita, versioni, diritti e split;
- persone esterne al prodotto incaricate di ripetere la valutazione.

### 1.2 Competenze minime

Un annotatore primario deve:

- conoscere le regole del calcio;
- distinguere gioco live, replay e interruzioni;
- comprendere possesso, perdita, recupero, ripresa del gioco e comportamento
  collettivo;
- saper usare una timeline video senza alterare il contenuto;
- aver letto integralmente questo manuale;
- aver completato il set di calibrazione previsto nella sezione 16;
- saper spiegare una decisione usando evidenze osservabili.

Le categorie esplorative richiedono competenza aggiuntiva da allenatore,
match analyst o revisore formato specificamente.

### 1.3 Che cosa significa annotare

Annotare significa registrare in modo strutturato:

- dove si trova una scena o un momento nel video;
- che cosa e osservabile;
- che cosa non e osservabile;
- quale categoria e sostenuta;
- quale squadra e coinvolta, se determinabile;
- quanto il momento e utile;
- quale frame lo rappresenta;
- quali limiti o alternative esistono;
- chi ha preso la decisione e con quale versione del manuale.

Annotare non significa raccontare la partita, giudicare la qualita generale
delle squadre o prevedere intenzioni non visibili.

### 1.4 Osservazione e interpretazione

**Osservazione**

Descrive fatti verificabili nel video.

Esempio:

> Dopo la perdita, tre giocatori vicini avanzano verso il nuovo portatore.

**Interpretazione**

Attribuisce un significato tattico ai fatti.

Esempio:

> La squadra tenta una riaggressione immediata.

L'interpretazione e ammessa soltanto quando e collegata alle osservazioni. Se
esistono spiegazioni alternative plausibili, devono essere registrate.

### 1.5 Ground truth e output della pipeline

La **ground truth** e il riferimento umano congelato secondo questo manuale.
L'**output della pipeline** e una predizione da valutare.

La ground truth non deve:

- copiare la categoria proposta dal sistema;
- adattare i confini per far coincidere una predizione;
- promuovere un caso per migliorare una metrica;
- usare una confidence AI come prova;
- essere riscritta senza conservare la versione precedente.

### 1.6 Annotazione cieca iniziale

Nel primo passaggio l'annotatore non deve vedere:

- categoria AI;
- confidence;
- descrizione generata;
- frame suggerito;
- linee automatiche;
- decisioni di altri annotatori.

Questo riduce l'ancoraggio. Le predizioni possono essere mostrate solo in una
fase successiva dedicata alla valutazione della pipeline.

### 1.7 Quando usare `non determinabile`

Usare `non determinabile` quando:

- esiste un possibile momento utile ma l'evidenza non sostiene una categoria;
- palla, trigger, squadra o continuita non sono sufficienti;
- due categorie restano ugualmente plausibili;
- il video inizia o termina nel mezzo dell'azione;
- il cambio camera impedisce di collegare le fasi;
- l'annotatore non puo giustificare una scelta piu specifica.

Non usarlo per evitare una decisione semplice e visibile. Non usarlo al posto
di `non tattico`.

---

## 2. Principi obbligatori

1. **Annotare cio che e visibile, non cio che probabilmente e accaduto.**
   Il risultato noto o la conoscenza delle squadre non sostituiscono il video.
2. **Non forzare una categoria specifica.**
   Una palla inattiva generica corretta vale piu di un corner inventato.
3. **Il momento e una sequenza, non un frame.**
   Un'immagine puo suggerire una forma, ma non dimostra origine e sviluppo.
4. **Trigger, sviluppo ed esito sono distinti.**
   Devono essere marcati separatamente oppure dichiarati assenti.
5. **Non tattico non equivale a non determinabile.**
   Il primo e contenuto non utile; il secondo e evidenza insufficiente.
6. **Una scena visivamente bella puo essere tatticamente inutile.**
   Nitidezza ed estetica non determinano valore tattico.
7. **La mancanza di palla, campo o giocatori deve essere registrata.**
   Non deve essere compensata con supposizioni.
8. **Le correzioni non cancellano le decisioni precedenti.**
   Ogni cambiamento conserva autore, valore, motivo e data.
9. **In caso di dubbio motivato, astenersi.**
   L'astensione e un output valido, non un errore.
10. **La finalita e la ripetibilita, non dimostrare che MatchIQ funziona.**
    Un risultato negativo ben annotato e piu utile di un positivo forzato.

### 2.1 Regole di comportamento

L'annotatore deve:

- guardare la sequenza a velocita normale prima di usare rallentamenti;
- riesaminare i secondi precedenti e successivi;
- motivare eccezioni;
- evitare terminologia assoluta come "perfetto" o "sempre";
- registrare il limite anche quando la categoria e corretta;
- interrompere la sessione se stanchezza o problemi tecnici compromettono la
  coerenza.

L'annotatore non deve:

- cercare conferme alla propria prima impressione;
- usare solo scoreboard o commento audio come prova principale;
- unire azioni distinte per creare un momento piu completo;
- assegnare la squadra sulla base del nome del file;
- inferire il possesso da una singola postura.

---

## 3. Workflow operativo di annotazione

L'ordine seguente e obbligatorio. Cambiarlo aumenta il rischio di classificare
prima di aver compreso la sequenza.

### Passo 1 - Apertura e identificazione

Registrare:

- video ID;
- nome tecnico o fingerprint disponibile;
- durata;
- formato;
- sorgente;
- partita associata, se documentata;
- versione del file.

Non usare il titolo come evidenza tattica.

### Passo 2 - Diritti e metadati

Verificare:

- autorizzazione all'uso;
- eventuali limiti;
- presenza di minori;
- competizione e livello, se documentati;
- tipo di camera;
- data e fonte.

Se i diritti non sono verificati, il video non entra nel benchmark congelato.

### Passo 3 - Continuita e qualita tecnica

Guardare l'inizio, alcuni punti intermedi e la fine. Registrare:

- discontinuita;
- montaggi;
- frame rate anomalo;
- audio fuori sincrono, se rilevante;
- porzioni corrotte;
- variazioni marcate di risoluzione o camera.

### Passo 4 - Porzioni non valutabili

Marcare prima:

- video nero;
- file corrotto;
- freeze prolungato;
- immagine assente;
- salto temporale non ricostruibile;
- porzione in cui non e possibile capire se il contenuto e live.

Una porzione non valutabile non e automaticamente `non tattico`.

### Passo 5 - Scene non tattiche

Marcare replay, esultanze, primi piani, panchina, pubblico, grafiche e altri casi
della sezione 7. Le scene possono sovrapporsi a un momento originale soltanto
come materiale editoriale collegato, non come nuovo evento live.

### Passo 6 - Ricerca dei momenti

Guardare il gioco live cercando:

- un'origine osservabile;
- un comportamento collettivo;
- cambiamenti in palla, spazi o relazioni;
- una conseguenza immediata.

Non ritagliare clip a intervalli regolari per il solo fatto che mostrano campo.

### Passo 7 - Delimitazione temporale

Segnare nell'ordine:

1. trigger;
2. inizio necessario a comprenderlo;
3. esito, se visibile;
4. fine;
5. centro rappresentativo.

La categoria non deve ancora essere scelta.

### Passo 8 - Categoria

Applicare la decision tree della sezione 9 alla sequenza completa. Se il tipo
specifico non e sostenuto, scegliere il livello generico. Se neppure quello e
sostenuto, usare `non determinabile`.

### Passo 9 - Squadra

Assegnare:

- squadra osservata;
- squadra avversaria, se prevista;
- `non determinabile` se divise, direzione o contesto non bastano.

Non dedurre la squadra dal colore dichiarato in metadati non verificati.

### Passo 10 - Utilita

Valutare il momento come `ottimo`, `buono`, `mediocre` o `inutile` secondo la
sezione 10. La valutazione riguarda il lavoro dello staff, non la bellezza del
video.

### Passo 11 - Frame rappresentativo

Sceglierlo solo dentro l'intervallo gia delimitato. Se nessun frame rappresenta
adeguatamente la sequenza, registrare `nessun frame idoneo`.

### Passo 12 - Evidenze e ambiguita

Separare:

- visibile;
- inferibile;
- mancante;
- segnali contrari;
- alternative;
- motivazione dell'astensione.

### Passo 13 - Salvataggio

Prima del salvataggio eseguire la checklist della sezione 15. Il record deve
contenere annotatore, versione manuale e versione tassonomia.

### Passo 14 - Seconda revisione

Inviare i casi che richiedono doppia revisione senza mostrare la prima decisione
finche la revisione indipendente non e conclusa.

### 3.1 Perche delimitare prima di classificare

Classificare prima induce a:

- scegliere soltanto i frame che confermano l'etichetta;
- ignorare il vero trigger;
- includere replay o conseguenze estranee;
- trasformare possesso ordinario in costruzione;
- scambiare densita temporanea per pressing;
- perdere il cambio di fase.

La sequenza deve stabilire che cosa e accaduto; la categoria deve riassumerlo.

---

## 4. Unita di annotazione

### 4.1 Video completo

**Definizione:** file audiovisivo trattato come sorgente.

**Valido:** partita continua con identita e durata registrate.  
**Invalido:** file senza provenienza o con diritti non verificabili per il
benchmark congelato.  
**Caso limite:** montaggio di clip; puo essere usato in sviluppo se dichiarato,
ma non come partita continua.

### 4.2 Intervallo

**Definizione:** porzione temporale delimitata per stato tecnico, scena non
tattica o candidato tattico.

**Valido:** `[inizio, fine]` con motivo esplicito.  
**Invalido:** finestra arbitraria generata ogni N minuti.  
**Caso limite:** cambio camera breve; resta nello stesso intervallo solo se la
continuita e dimostrabile.

### 4.3 Momento tattico

**Definizione:** sequenza continua con origine osservabile e comportamento
collettivo pertinente.

**Valido:** perdita, reazione coordinata ed esito immediato visibili.  
**Invalido:** un frame largo con giocatori disposti.  
**Caso limite:** comportamento utile senza trigger visibile; annotabile come
momento incompleto e potenzialmente `non determinabile`.

### 4.4 Scena non tattica

**Definizione:** intervallo non utile alla valutazione tattica primaria.

**Valido:** replay, esultanza, pubblico o grafica a schermo intero.  
**Invalido:** azione di gioco poco spettacolare ma tatticamente leggibile.  
**Caso limite:** replay utile editorialmente; resta non live e viene collegato
al momento originale.

### 4.5 Frame rappresentativo

**Definizione:** immagine interna al momento che ne mostra la configurazione
piu informativa.

**Valido:** palla, relazioni e spazio necessari sono leggibili.  
**Invalido:** primo piano nitido del marcatore.  
**Caso limite:** due frame equivalenti; registrare il preferito e l'alternativa.

### 4.6 Categoria

**Definizione:** etichetta operativa assegnata al livello massimo supportato.

**Valido:** `palla inattiva generica` quando il restart e visibile ma non il
punto di battuta.  
**Invalido:** `calcio d'angolo offensivo` senza angolo, battitore o contesto
coerente.  
**Caso limite:** due categorie dinamiche sovrapposte; scegliere primaria e
secondaria solo se entrambe osservabili.

### 4.7 Descrizione

**Definizione:** sintesi delle evidenze e dei limiti.

**Valido:** "Dopo la perdita, tre giocatori accorciano; l'esito non e visibile."  
**Invalido:** "Pressing perfetto che obbliga l'avversario all'errore" senza esito.  
**Caso limite:** intenzione plausibile ma non verificabile; riportarla come
interpretazione alternativa, non come fatto.

### 4.8 Annotazione geometrica

**Definizione:** linea, punto, area o relazione disegnata su un frame idoneo.

**Valido:** linea tra difensori chiaramente visibili nello stesso istante.  
**Invalido:** prolungare una linea verso giocatori fuori campo.  
**Caso limite:** prospettiva distorta; registrare che la geometria e illustrativa,
non una misura metrica.

### 4.9 Sessione di review

**Definizione:** insieme tracciato di decisioni prese da una persona in un
periodo di lavoro.

**Valido:** sessione con annotatore, orari, manuale e record modificati.  
**Invalido:** modifiche anonime sul dato congelato.  
**Caso limite:** interruzione lunga; chiudere la sessione e aprirne una nuova.

---

## 5. Come riconoscere un momento tattico

### 5.1 Struttura attesa

Quando applicabile, cercare:

- **contesto precedente:** posizione minima necessaria;
- **trigger:** evento che attiva il comportamento;
- **organizzazione:** disposizione o reazione collettiva;
- **sviluppo:** evoluzione di palla, spazi e relazioni;
- **esito immediato:** prima conseguenza osservabile.

Una componente assente non invalida automaticamente il caso, ma deve essere
registrata.

### 5.2 Vero momento

Ha continuita, almeno un'origine o conseguenza osservabile e relazioni tra piu
giocatori pertinenti al principio analizzato.

### 5.3 Configurazione statica

Mostra una forma in un istante, ma non consente di sapere:

- come si e formata;
- che cosa la attiva;
- come reagisce;
- quale effetto produce.

Puo fornire un frame editoriale, non necessariamente una ground truth tattica.

### 5.4 Azione incompleta

Manca inizio, esito o continuita. Annotarla solo se:

- la parte visibile e comunque utile;
- il limite e dichiarato;
- la categoria non richiede la parte mancante;
- non viene presentata come sequenza completa.

### 5.5 Evento tecnico individuale

Un dribbling, tiro o errore individuale non e automaticamente un momento
tattico. Diventa pertinente quando la sequenza mostra relazioni o conseguenze
collettive utili al focus.

### 5.6 Momento utile non classificabile

E una sequenza che merita review ma non sostiene una categoria disponibile.
Usare `non determinabile`, descrivere l'evidenza e proporre eventuali alternative.

### 5.7 Clip arbitraria

E una finestra scelta per timestamp, estetica o durata, senza trigger e senza
logica temporale. Non deve entrare tra i momenti positivi.

### 5.8 Checklist si/no

Rispondere prima di creare un momento:

- [ ] Il contenuto e live o chiaramente collegato al live?
- [ ] La porzione e tecnicamente valutabile?
- [ ] Esiste un contesto minimo?
- [ ] Esiste un trigger o un esito osservabile?
- [ ] Sono visibili relazioni tra piu giocatori?
- [ ] La sequenza evolve nel tempo?
- [ ] Palla o stato della palla sono osservabili quando necessari?
- [ ] Il campo visibile e sufficiente per la categoria ipotizzata?
- [ ] Le squadre sono distinguibili?
- [ ] Il caso sarebbe utile a uno staff anche senza descrizione AI?
- [ ] Posso spiegare perche inizia e perche finisce?
- [ ] Posso indicare che cosa manca senza inventarlo?

Se molte risposte essenziali sono `no`, non forzare il momento. Se il contenuto
e potenzialmente utile ma ambiguo, usare `non determinabile`.

---

## 6. Annotazione temporale

### 6.1 Punti da segnare

- **Inizio:** primo istante necessario per capire il contesto.
- **Trigger:** evento che avvia il comportamento.
- **Centro:** istante piu informativo, non la meta matematica.
- **Esito:** prima conseguenza tatticamente rilevante.
- **Fine:** dissoluzione del comportamento o passaggio a una fase distinta.

### 6.2 Intervallo minimo e massimo

L'intervallo minimo deve contenere abbastanza contesto da interpretare trigger
e risposta. L'intervallo massimo deve terminare prima che inizi una fase distinta.

Non esiste ancora una durata numerica definitiva: e **da validare durante
l'annotazione pilota** per categoria.

### 6.3 Calcio d'angolo

- **Inizio:** organizzazione immediatamente precedente.
- **Trigger:** rincorsa o battuta.
- **Centro:** configurazione piu informativa tra battitore, area e marcature.
- **Esito:** primo contatto, respinta, tiro o uscita.
- **Fine:** possesso stabilizzato, palla fuori o nuova fase.

Non includere l'esultanza. Se la battuta non e visibile, non forzare `corner`.

### 6.4 Punizione

- **Inizio:** palla ferma e organizzazione.
- **Trigger:** battuta.
- **Centro:** struttura coerente con la domanda tattica.
- **Esito:** ricezione, duello, tiro o respinta.
- **Fine:** seconda fase stabilizzata o interruzione.

### 6.5 Rimessa laterale

- **Inizio:** battitore e riceventi si preparano.
- **Trigger:** rilascio della palla.
- **Centro:** relazioni tra battitore, riceventi e pressione.
- **Esito:** controllo, perdita, restituzione o palla contesa.
- **Fine:** possesso stabilizzato o nuova interruzione.

### 6.6 Costruzione dal basso

- **Inizio:** controllo o restart che avvia l'uscita bassa.
- **Trigger:** prima scelta che attiva lo sviluppo contro la pressione.
- **Centro:** configurazione piu informativa delle linee di passaggio.
- **Esito:** superamento della prima pressione, rinvio, perdita o riciclo.
- **Fine:** ingresso stabile in una nuova zona/fase.

Se il video inizia a sviluppo avanzato, registrare origine assente.

### 6.7 Pressing

- **Inizio:** contesto che precede l'attivazione.
- **Trigger:** passaggio, ricezione, postura o zona che avvia l'uscita.
- **Centro:** coordinazione e orientamento osservabili.
- **Esito:** recupero, forzatura, superamento o interruzione.
- **Fine:** pressing dissolto o nuova organizzazione.

La densita in un frame non e un trigger.

### 6.8 Transizione positiva

- **Inizio/trigger:** recupero osservabile.
- **Centro:** prima risposta offensiva collettiva.
- **Esito:** avanzamento, occasione, perdita o stabilizzazione.
- **Fine:** possesso organizzato o azione conclusa.

### 6.9 Transizione negativa

- **Inizio/trigger:** perdita osservabile.
- **Centro:** reazione immediata senza palla.
- **Esito:** recupero, rallentamento, superamento o blocco stabilizzato.
- **Fine:** termina la prima reazione.

### 6.10 Linea o blocco difensivo

- **Inizio:** azione avversaria che rende leggibile la struttura.
- **Trigger:** movimento della palla o avversario che richiede adattamento.
- **Centro:** maggioranza del reparto e riferimenti visibili.
- **Esito:** avanzamento, arretramento, rottura, recupero o nuova fase.
- **Fine:** struttura dissolta o camera non piu utile.

### 6.11 Confini graduali

Quando non esiste un singolo frame certo:

- scegliere il primo/ultimo istante ragionevole;
- registrare un confine alternativo;
- spiegare il motivo;
- non cercare precisione fittizia.

### 6.12 Azioni senza esito

Se il video termina, cambia camera o perde il campo:

- lasciare `esito non osservabile`;
- terminare all'ultimo istante affidabile;
- non dedurre l'esito dal punteggio successivo.

### 6.13 Momenti consecutivi

Separare quando:

- cambia stabilmente il possesso;
- compare un nuovo trigger;
- cambia il principio osservato;
- la struttura precedente si dissolve.

Un esito puo coincidere con il trigger del momento successivo.

### 6.14 Momenti sovrapposti

Consentire sovrapposizione solo se:

- due comportamenti distinti sono entrambi osservabili;
- una categoria primaria e una secondaria descrivono dimensioni diverse;
- la motivazione e registrata.

Non duplicare lo stesso momento con etichette alternative.

### 6.15 Cambi camera e replay

Un cambio camera live puo restare nello stesso momento se palla, tempo e azione
sono collegabili. Un replay interrompe la timeline live e va separato.

### 6.16 Interruzioni ed eventi fuori campo

Se trigger o esito avvengono fuori campo:

- non ricostruirli dal solo movimento successivo;
- registrare la componente mancante;
- ridurre specificita o astenersi;
- mantenere il caso solo se la parte visibile ha utilita autonoma.

---

## 7. Scene non tattiche

Una scena non tattica puo essere tecnicamente valida e utile editorialmente, ma
non deve essere presentata allo staff come evidenza di un comportamento
collettivo. Per ogni scena registrare classe, intervallo, segnali, decisione ed
eventuale collegamento a un momento live.

### 7.1 Replay

**Definizione**

Riproduzione non live di un evento gia avvenuto.

**Segnali osservabili**

- logo o transizione dedicata;
- discontinuita del cronometro;
- ripetizione di un'azione;
- slow motion;
- angolazione incompatibile con la ripresa principale;
- dissolvenza o grafica di replay.

**Escludere**

Dal candidate discovery live e dal conteggio dei momenti.

**Penalizzare**

Quando il replay occupa solo una parte dell'intervallo: dividere la sequenza o
marcare la contaminazione.

**Utilita editoriale**

Puo accompagnare il momento originale, se etichettato e collegato.

**Confusioni**

Cambio camera live, montaggio, ritardo della trasmissione.

**Caso limite**

Se non e possibile stabilire la natura live, usare evidenza insufficiente e non
inventare un secondo evento.

### 7.2 Esultanza

**Definizione**

Reazione celebrativa successiva a gol o evento favorevole.

**Segnali**

Abbracci, corsa celebrativa, palla assente, pubblico/staff, interruzione.

**Escludere**

Da tutte le categorie tattiche collettive.

**Penalizzare**

Se pochi frame celebrativi contaminano la fine: accorciare il momento alla
conseguenza tattica immediata.

**Utilita editoriale**

Solo narrativa.

**Confusioni**

Raggruppamento dopo fallo, protesta, ritorno alle posizioni.

**Caso limite**

Il gol puo essere esito del momento; l'esultanza non ne prolunga i confini.

### 7.3 Primo piano

**Definizione**

Una persona o una porzione ridotta domina l'immagine, impedendo relazioni
collettive.

**Segnali**

Campo ridotto, pochi giocatori, palla assente, volti o busti dominanti.

**Escludere**

Per pressing, costruzione, blocco, linea, ampiezza e piazzati.

**Penalizzare**

Per analisi individuale se il contesto precedente resta collegabile.

**Utilita editoriale**

Identificazione del soggetto o storytelling, non struttura.

**Confusioni**

Zoom su battitore con area ancora visibile.

**Caso limite**

Un battitore in primo piano non dimostra il tipo di restart senza riferimenti.

### 7.4 Panchina e area tecnica

**Definizione**

Staff, riserve o area tecnica dominano l'inquadratura.

**Segnali**

Sedute, pettorine, bordo campo, persone non coinvolte, terreno insufficiente.

**Escludere**

Dalla pipeline tattica di gioco.

**Penalizzare**

Non applicabile come momento tattico.

**Utilita editoriale**

Reazione staff, sostituzioni o comunicazione, se il benchmark futuro lo prevede.

**Confusioni**

Rimessa laterale vicina alla panchina.

**Caso limite**

Se la rimessa e interamente visibile, annotare la sequenza utile senza includere
il primo piano della panchina.

### 7.5 Pubblico

**Definizione**

Tribune o spettatori dominano senza evidenza di gioco.

**Segnali**

Assenza del campo, della palla e delle squadre.

**Escludere**

Sempre dal benchmark tattico.

**Penalizzare**

Una presenza marginale del pubblico non penalizza se campo e azione restano
leggibili; penalizzare quando riduce la porzione utile.

**Utilita editoriale**

Solo narrativa.

**Confusioni**

Ripresa molto larga con tribune ma campo ancora sufficiente.

**Caso limite**

Valutare la porzione di campo richiesta dalla categoria, non la percentuale
assoluta di tribuna.

### 7.6 Grafica televisiva

**Definizione**

Elemento grafico che sostituisce o copre il contenuto.

**Segnali**

Formazioni, tabellino, pubblicita fullscreen, lower third, split screen.

**Escludere**

Grafica a schermo intero.

**Penalizzare**

Overlay che copre palla, giocatori o linee necessarie.

**Utilita editoriale**

Metadati di partita, mai sostituto della scena.

**Confusioni**

Scoreboard piccolo e stabile, che normalmente non invalida la sequenza.

**Caso limite**

Una formazione grafica non e evidenza della disposizione reale.

### 7.7 Intervista

**Definizione**

Persona che parla fuori dal gioco live.

**Segnali**

Microfono, sfondo statico, inquadratura volto/busto, assenza di azione.

**Escludere**

Sempre dal benchmark tattico.

**Penalizzare**

Non applicabile se l'intervista sostituisce il gioco; dividere l'intervallo se
compare brevemente sopra una ripresa ancora utilizzabile.

**Utilita editoriale**

Contesto esterno, fuori dallo scopo B1.

**Confusioni**

Commentatore a bordocampo mentre l'azione resta visibile; segmentare le parti.

**Caso limite**

Split screen con intervista e partita: la porzione di gioco e valutabile solo se
conserva i riferimenti necessari.

### 7.8 Pubblicita

**Definizione**

Contenuto commerciale che sostituisce la partita.

**Segnali**

Cambio audio/immagine, logo prodotto, assenza di timeline sportiva.

**Escludere**

Sempre.

**Penalizzare**

Overlay pubblicitario solo se copre evidenze necessarie; la pubblicita fullscreen
e esclusione, non penalizzazione.

**Utilita editoriale**

Nessuna per il benchmark.

**Confusioni**

Cartelloni a bordo campo e sponsor sulle maglie non sono scene pubblicitarie.

**Caso limite**

Inserto commerciale che occupa una parte dello schermo: valutare se palla,
giocatori e campo richiesti restano visibili.

### 7.9 Campo insufficiente

**Definizione**

La superficie visibile non consente di osservare le relazioni richieste.

**Segnali**

Scala troppo ravvicinata, reparti fuori campo, linee non riconoscibili.

**Escludere**

Quando la categoria e collettiva e mancano i riferimenti minimi.

**Penalizzare**

Quando la sequenza resta utile localmente ma non per affermazioni globali.

**Utilita editoriale**

Possibile per evento individuale, non per struttura.

**Confusioni**

Campo ridotto ma sufficiente per una rimessa locale.

**Caso limite**

La sufficienza dipende dalla categoria ed e **da validare durante l'annotazione
pilota**.

### 7.10 Pochi giocatori

**Definizione**

Numero o distribuzione dei giocatori insufficiente per il comportamento
ipotizzato.

**Segnali**

Uno o due soggetti per una categoria collettiva, reparto incompleto, avversari
assenti.

**Escludere**

Per linee, blocchi e pressing quando non si osservano relazioni collettive.

**Penalizzare**

Per categorie locali quando il trigger resta visibile.

**Utilita editoriale**

Possibile per duelli, fuori dalla tassonomia iniziale.

**Confusioni**

Camera larga con giocatori piccoli ma presenti.

**Caso limite**

Una categoria locale puo restare annotabile con pochi giocatori, mentre una
categoria di reparto no.

### 7.11 Scena tecnica non utile

**Definizione**

Evento tecnico individuale senza contesto collettivo utile.

**Segnali**

Controllo, passaggio, tiro o dribbling isolato senza origine e conseguenza.

**Escludere**

Come momento tattico positivo.

**Penalizzare**

Se fa parte di una sequenza valida ma il ritaglio e troppo stretto.

**Utilita editoriale**

Highlight individuale.

**Confusioni**

Il primo passaggio dopo un recupero puo essere parte di una transizione.

**Caso limite**

Un gesto individuale che attiva una risposta collettiva va incluso nel momento,
ma non classificato da solo.

### 7.12 Video nero o corrotto

**Definizione**

Contenuto non decodificabile o privo di immagine utile.

**Segnali**

Frame neri, blocchi, artefatti totali, freeze prolungato.

**Escludere**

Marcare come porzione non valutabile, non come non tattico.

**Penalizzare**

La continuita dei momenti adiacenti.

**Utilita editoriale**

Nessuna.

**Confusioni**

Transizione televisiva scura, dissolvenza o fotogramma nero isolato.

**Caso limite**

Un singolo frame corrotto non invalida una sequenza continua se prima e dopo
sono collegabili.

---

## 8. Tassonomia iniziale

### 8.1 Non tattico

**Definizione semplice**

Scena senza comportamento collettivo utile per il benchmark.

**Segnali minimi obbligatori**

Contenuto escluso dominante oppure assenza chiara di azione tattica.

**Segnali utili**

Palla assente, campo assente, interruzione, soggetti non coinvolti.

**Esclusioni**

Non usare se esiste un momento utile ma non classificabile.

**Confusioni**

`non determinabile`, configurazione statica, evento individuale.

**Specificita massima**

Sottotipo della scena non tattica solo se visibile.

**Esempio positivo**

Primo piano dell'allenatore durante gioco fermo.

**Hard negative**

Zoom moderato che mantiene visibili battitore, area e marcature.

**Restare generici**

Quando e certa l'inutilita ma non il sottotipo.

**Scegliere non determinabile**

Quando il valore tattico non puo essere escluso.

### 8.2 Replay

**Definizione semplice**

Riproduzione non live di una sequenza precedente.

**Segnali obbligatori**

Almeno un segnale forte verificabile: transizione, ripetizione, cronometro
discontinuo o grafica.

**Segnali utili**

Slow motion, camera speciale, dissolvenza.

**Esclusioni**

Non confondere con cambio camera live.

**Confusioni**

Montaggio, ritardo di trasmissione.

**Specificita massima**

`replay`; il contenuto tattico resta collegato al live originale.

**Esempio positivo**

Stessa azione ripetuta con logo replay.

**Hard negative**

Cambio istantaneo dalla camera centrale a quella laterale durante l'azione.

**Restare generici**

Usare non tattico se e certo che non e live ma non dimostrabile come replay.

**Scegliere non determinabile**

Timeline montata senza riferimenti sufficienti.

### 8.3 Palla inattiva generica

**Definizione semplice**

Ripresa organizzata del gioco il cui tipo non e sostenuto con certezza.

**Segnali obbligatori**

Gioco fermo, organizzazione, palla preparata o restart osservabile.

**Segnali utili**

Distanze, barriera, zona, gesto del battitore.

**Esclusioni**

Pausa senza ripresa, rinvio lungo non contestualizzato, calcio d'inizio se non
previsto dalla tassonomia.

**Confusioni**

Corner, punizione, rimessa, costruzione dal portiere.

**Specificita massima**

Non aggiungere lato, zona o orientamento senza evidenza.

**Esempio positivo**

Giocatori organizzati e battuta visibile, ma punto esatto fuori campo.

**Hard negative**

Palla ferma durante un'interruzione senza restart.

**Restare generici**

Ogni volta che il restart e certo ma il tipo no.

**Scegliere non determinabile**

Quando non e certo che si tratti di una ripresa.

### 8.4 Calcio d'angolo

**Definizione semplice**

Ripresa dall'arco d'angolo con organizzazione in area.

**Segnali obbligatori**

Zona d'angolo o battitore coerente, area e battuta/preparazione osservabili.

**Segnali utili**

Bandierina, arco, marcature, portiere, traiettoria.

**Esclusioni**

Cross in open play, punizione laterale, rimessa profonda.

**Confusioni**

Punizione laterale e rimessa.

**Specificita massima**

`calcio d'angolo`; offensivo/difensivo solo rispetto alla squadra osservata
correttamente identificata.

**Esempio positivo**

Battitore all'arco, area visibile e pallone calciato.

**Hard negative**

Cross dalla stessa fascia iniziato con palla in movimento.

**Restare generici**

Se si vede un piazzato laterale ma non la zona di battuta.

**Scegliere non determinabile**

Se il video parte dopo la battuta e i riferimenti non bastano.

### 8.5 Punizione

**Definizione semplice**

Ripresa conseguente a fallo con palla ferma e battuta.

**Segnali obbligatori**

Palla ferma, organizzazione coerente e battuta.

**Segnali utili**

Barriera, arbitro, distanza, postura, area bersaglio.

**Esclusioni**

Corner, rinvio, calcio d'inizio, pausa.

**Confusioni**

Corner e palla inattiva generica.

**Specificita massima**

`punizione`; laterale/diretta/indiretta solo se realmente osservabile.

**Esempio positivo**

Palla ferma, barriera e battuta visibili.

**Hard negative**

Portiere che rimette il pallone dopo un'uscita.

**Restare generici**

Se la palla inattiva e certa ma il fallo o punto non sono osservabili.

**Scegliere non determinabile**

Se manca la battuta e l'organizzazione ha spiegazioni alternative.

### 8.6 Rimessa laterale

**Definizione semplice**

Ripresa mediante lancio da oltre la linea laterale.

**Segnali obbligatori**

Battitore fuori/dietro la linea e gesto o rilascio osservabile.

**Segnali utili**

Mani sopra la testa, riceventi, pressione locale.

**Esclusioni**

Palla raccolta senza esecuzione, punizione laterale.

**Confusioni**

Primo piano bordocampo e restart non visibile.

**Specificita massima**

`rimessa laterale`; zona profonda o lato solo con campo leggibile.

**Esempio positivo**

Gesto completo e ricezione visibili.

**Hard negative**

Giocatore sul bordo campo che tiene la palla ma non la rimette.

**Restare generici**

Se e certo un restart laterale ma il gesto e parzialmente coperto.

**Scegliere non determinabile**

Se linea e palla non sono osservabili.

### 8.7 Non determinabile

**Definizione semplice**

Momento potenzialmente utile con evidenza insufficiente o conflittuale.

**Segnali obbligatori**

Almeno un limite concreto e una motivazione.

**Segnali utili**

Alternative plausibili, componente mancante, confine incerto.

**Esclusioni**

Non usarlo per scene chiaramente non tattiche.

**Confusioni**

Categoria rara, annotatore indeciso senza riesame.

**Specificita massima**

Nessuna categoria primaria piu specifica.

**Esempio positivo**

Sequenza collettiva leggibile ma recupero/perdita avviene fuori campo.

**Hard negative**

Corner evidente lasciato non determinabile per eccessiva prudenza.

**Restare generici**

Se almeno una famiglia e sostenuta, preferire quella generica.

**Scegliere non determinabile**

Quando le famiglie restano equivalenti o manca l'evidenza minima.

### 8.8 Costruzione dal basso - categoria pilota

**Definizione semplice**

Possesso originato in zona bassa che tenta di superare la prima pressione.

**Segnali obbligatori**

Origine bassa, possesso controllato, relazioni tra portiere/prima linea e sviluppo.

**Segnali utili**

Prima pressione, linee di passaggio, terzo uomo, uscita da zona.

**Esclusioni**

Rinvio lungo isolato, possesso statico, clip iniziata troppo tardi.

**Confusioni**

Rimessa dal fondo, ricircolo basso, recupero difensivo.

**Specificita massima**

Non qualificare il tipo di costruzione senza sequenza sufficiente.

**Esempio positivo**

Portiere serve un difensore e la squadra supera la prima linea avversaria.

**Hard negative**

Passaggio laterale del portiere seguito da taglio camera.

**Restare generici**

`possesso in zona bassa` come nota, se lo schema non e dimostrabile.

**Scegliere non determinabile**

Se origine o esito non sono osservabili.

### 8.9 Transizione positiva - categoria pilota

**Definizione semplice**

Risposta offensiva immediatamente successiva al recupero.

**Segnali obbligatori**

Recupero e cambio di possesso osservabili, risposta nei secondi successivi.

**Segnali utili**

Corse, primo passaggio, attacco dello spazio, superiorita.

**Esclusioni**

Contropiede gia iniziato, possesso ordinario, seconda palla non risolta.

**Confusioni**

Recupero senza sviluppo e possesso stabilizzato.

**Specificita massima**

Non dichiarare efficacia o principio specifico senza esito.

**Esempio positivo**

Intercetto seguito da avanzamento coordinato.

**Hard negative**

Passaggio verticale durante possesso gia consolidato.

**Restare generici**

`cambio di possesso` se direzione o squadra non sono certe.

**Scegliere non determinabile**

Se il recupero e fuori campo.

### 8.10 Transizione negativa - categoria pilota

**Definizione semplice**

Risposta difensiva immediatamente successiva alla perdita.

**Segnali obbligatori**

Perdita e cambio di possesso osservabili, reazione immediata.

**Segnali utili**

Riaggressione, protezione profondita, fallo tattico, arretramento.

**Esclusioni**

Blocco gia organizzato, pressing posizionale, errore senza conseguenza.

**Confusioni**

Pressing e seconda palla.

**Specificita massima**

Non qualificare la transizione come efficace senza esito.

**Esempio positivo**

Perdita centrale seguita da accorciamento di piu giocatori.

**Hard negative**

Un solo giocatore insegue il portatore dopo un duello.

**Restare generici**

`reazione dopo perdita` se la coordinazione non e pienamente leggibile.

**Scegliere non determinabile**

Se la perdita avviene fuori campo.

### 8.11 Pressing - categoria esplorativa

**Definizione semplice**

Comportamento coordinato senza palla per ridurre tempo, spazio e linee.

**Segnali obbligatori**

Trigger, azione di piu giocatori/reparto, orientamento e risposta avversaria.

**Segnali utili**

Coperture, ombre, uscita su passaggio, forzatura.

**Esclusioni**

Densita statica, duello individuale, riaggressione non distinta.

**Confusioni**

Transizione negativa e blocco.

**Specificita massima**

`pressione coordinata` finche altezza, orientamento e schema non sono validati.

**Esempio positivo**

Passaggio laterale attiva uscite coordinate e chiusura di linee.

**Hard negative**

Quattro giocatori vicini in un frame senza movimento precedente.

**Restare generici**

`pressione` se la coordinazione e incompleta.

**Scegliere non determinabile**

Se mancano i secondi prima/dopo.

### 8.12 Linea o blocco difensivo - categoria esplorativa

**Definizione semplice**

Organizzazione collettiva senza palla osservata durante una sequenza.

**Segnali obbligatori**

Maggioranza del reparto, riferimenti avversari, palla/direzione e adattamento.

**Segnali utili**

Distanze, salita, scivolamento, copertura, profondita.

**Esclusioni**

Frame statico senza sviluppo, palla inattiva, reparto parziale.

**Confusioni**

Transizione, pressing, campo largo generico.

**Specificita massima**

`blocco difensivo`; non attribuire altezza o efficacia senza calibrazione/evidenza.

**Esempio positivo**

Linea visibile che adatta posizione durante lo sviluppo avversario.

**Hard negative**

Quattro difensori allineati durante pausa.

**Restare generici**

`organizzazione difensiva` se il movimento non e completo.

**Scegliere non determinabile**

Se mancano palla, reparto o riferimenti.

---

## 9. Decision tree

Seguire l'albero dall'alto. Non saltare direttamente alla categoria desiderata.

```text
1. La porzione e tecnicamente valutabile?
   -> NO: porzione non valutabile; registrare il motivo; STOP.
   -> SI: continua.

2. La scena appartiene alla timeline live?
   -> NO CERTO: replay oppure altra scena non tattica; STOP.
   -> NON DETERMINABILE: registrare evidenza insufficiente; non creare evento live.
   -> SI: continua.

3. Una classe non tattica domina la scena?
   -> SI: non tattico + sottotipo osservabile; STOP.
   -> NO: continua.

4. Esiste una sequenza con contesto e cambiamento osservabile?
   -> NO: configurazione statica o evento individuale.
          Se inutile -> non tattico.
          Se potenzialmente utile -> non determinabile.
   -> SI: continua.

5. Esiste un comportamento collettivo osservabile?
   -> NO: non tattico o non determinabile, secondo l'evidenza.
   -> SI: continua.

6. Il gioco e fermo e una ripresa e osservabile?
   -> SI: il tipo e certo?
          -> angolo e battuta visibili: calcio d'angolo.
          -> fallo/palla ferma/battuta: punizione.
          -> gesto dalla laterale: rimessa laterale.
          -> restart certo, tipo incerto: palla inattiva generica.
   -> NO: continua.

7. Sono visibili origine bassa, possesso e tentativo di uscita?
   -> SI: costruzione dal basso (pilota).
   -> NO: continua.

8. E visibile un recupero con risposta offensiva immediata?
   -> SI: transizione positiva (pilota).
   -> NO: continua.

9. E visibile una perdita con risposta difensiva immediata?
   -> SI: transizione negativa (pilota).
   -> NO: continua.

10. E visibile un trigger con pressione coordinata?
    -> SI: pressing (esplorativa).
    -> NO: continua.

11. E visibile un reparto che adatta la struttura senza palla?
    -> SI: linea o blocco difensivo (esplorativa).
    -> NO: non determinabile oppure non tattico.
```

`Open play` non e una categoria e non deve diventare un fallback. Se il sistema
di categorie non descrive il caso, scegliere `non determinabile` e documentare
l'evidenza.

---

## 10. Livello di utilita

Utilita tattica e qualita visiva devono essere assegnate separatamente.

### 10.1 Ottimo

**Requisiti**

- sequenza completa o quasi completa;
- comportamento collettivo chiaro;
- trigger e conseguenza utili;
- campo e soggetti adeguati;
- materiale direttamente utilizzabile in review o presentazione;
- limiti non decisivi.

**Esempio**

Costruzione dal portiere fino al superamento della prima pressione, con entrambe
le squadre leggibili.

**Errore frequente**

Promuovere un frame spettacolare senza sequenza.

**In dubbio**

Scendere a `buono` se manca una componente importante.

### 10.2 Buono

**Requisiti**

- principio leggibile;
- sequenza utile;
- uno o piu limiti gestibili;
- richiede correzione o contesto minore prima dell'uso.

**Esempio**

Transizione con recupero e sviluppo visibili ma esito perso nel cambio camera.

**Errore frequente**

Confondere utilita con confidence della categoria.

**In dubbio**

Usare `mediocre` se lo staff deve ricostruire gran parte del significato.

### 10.3 Mediocre

**Requisiti**

- spunto parziale;
- contesto insufficiente;
- frame o sequenza poco leggibili;
- valore limitato senza revisione sostanziale.

**Esempio**

Blocco difensivo visibile per pochi secondi senza trigger.

**Errore frequente**

Scartare tutto cio che non e pronto per una presentazione.

**In dubbio**

Usare `inutile` se non esiste una domanda concreta a cui il materiale risponde.

### 10.4 Inutile

**Requisiti**

Almeno uno:

- nessun comportamento rilevante;
- scena esclusa;
- evidenza troppo povera;
- duplicato senza valore aggiunto;
- costo di review superiore al beneficio.

**Esempio**

Primo piano durante esultanza proposto come linea difensiva.

**Errore frequente**

Confondere scarsa qualita tecnica con inutilita tattica.

**In dubbio**

Se esiste valore potenziale specifico e motivabile, preferire `mediocre`.

### 10.5 Separazione obbligatoria

- Un frame nitido puo appartenere a un momento inutile.
- Un momento ottimo puo avere qualita editoriale mediocre.
- Un momento classificato `non determinabile` puo essere `buono`.
- Un corner certo puo essere tatticamente inutile se mostra solo la battuta in
  primo piano.

Le soglie tra livelli sono **da validare durante l'annotazione pilota**.

---

## 11. Frame rappresentativo

### 11.1 Procedura

1. Delimitare il momento.
2. Guardarlo a velocita normale.
3. Identificare trigger, configurazione ed esito.
4. Esaminare i frame candidati interni.
5. Scegliere quello con piu relazioni utili.
6. Registrare alternative equivalenti.
7. Dichiarare `nessun frame idoneo` se necessario.

### 11.2 Criteri obbligatori

Il frame:

- appartiene all'intervallo;
- rappresenta trigger, configurazione o esito;
- mostra relazioni utili;
- mostra campo sufficiente;
- mostra la palla quando necessaria;
- evita primi piani;
- consente annotazioni;
- non e scelto soltanto per nitidezza.

### 11.3 Frame preferito

Soddisfa tutti i criteri essenziali e massimizza utilita tattica.

### 11.4 Frame accettabile

Soddisfa i criteri minimi ma presenta un limite dichiarato: overlay, occlusione
parziale o prospettiva.

### 11.5 Nessun frame idoneo

Usare quando la sequenza e utile ma nessun istante singolo comunica la struttura.
Non scegliere un frame fuorviante per riempire il campo.

### 11.6 Piu frame equivalenti

Registrare:

- frame preferito;
- frame alternativi;
- motivo dell'equivalenza;
- eventuale differenza editoriale.

La regola di scelta tra equivalenti e **da validare durante l'annotazione
pilota**.

---

## 12. Qualita tecnica

Valutare ogni dimensione separatamente con una rubric semplice:

- `adeguata`;
- `limitata`;
- `insufficiente`;
- `non applicabile`.

Non calcolare uno score tattico dalla somma.

### 12.1 Nitidezza

- **Adeguata:** palla e soggetti necessari distinguibili.
- **Limitata:** dettagli ridotti ma relazioni leggibili.
- **Insufficiente:** movimento/sfocatura impediscono la decisione.

### 12.2 Esposizione

- **Adeguata:** aree chiare e scure conservano i soggetti.
- **Limitata:** alcune zone perse, evento ancora leggibile.
- **Insufficiente:** squadra o palla scompaiono nelle ombre/luci.

### 12.3 Contrasto

- **Adeguato:** squadre, campo e palla distinguibili.
- **Limitato:** colori simili richiedono riesame.
- **Insufficiente:** attribuzione affidabile impossibile.

### 12.4 Stabilita

- **Adeguata:** camera consente di seguire l'azione.
- **Limitata:** pan/zoom bruschi ma continuita recuperabile.
- **Insufficiente:** movimento impedisce tracking umano.

### 12.5 Compressione

- **Adeguata:** artefatti non compromettono i soggetti.
- **Limitata:** blocchi o scie presenti.
- **Insufficiente:** identita/posizione non leggibili.

### 12.6 Porzione di campo

- **Adeguata:** include i riferimenti richiesti dalla categoria.
- **Limitata:** una relazione importante e fuori campo.
- **Insufficiente:** comportamento collettivo non valutabile.

### 12.7 Occlusione

- **Adeguata:** soggetti essenziali visibili.
- **Limitata:** occlusione temporanea o parziale.
- **Insufficiente:** trigger, palla o reparto coperti.

### 12.8 Overlay

- **Adeguato:** scoreboard non copre evidenze.
- **Limitato:** grafica copre una zona secondaria.
- **Insufficiente:** grafica nasconde palla o soggetti necessari.

### 12.9 Continuita della camera

- **Adeguata:** l'azione resta collegabile.
- **Limitata:** un cambio crea incertezza ma non spezza il momento.
- **Insufficiente:** non e possibile collegare prima e dopo.

Le soglie concrete di questa rubric sono **da validare durante l'annotazione
pilota**.

---

## 13. Evidenze e limiti

Ogni momento deve contenere quattro blocchi distinti.

### 13.1 Visibile

Fatti direttamente osservabili.

Corretto:

> Tre giocatori avanzano verso il portatore dopo una ricezione laterale.

Scorretto:

> La squadra vuole obbligare il passaggio all'indietro.

### 13.2 Inferibile

Interpretazione plausibile, dichiarata come tale.

Corretto:

> Il movimento puo essere coerente con una pressione orientata verso la fascia.

Scorretto:

> Il pressing e organizzato perfettamente.

### 13.3 Mancante

Elencare esplicitamente:

- palla;
- trigger;
- esito;
- giocatori/reparto;
- zona;
- continuita;
- squadra;
- tipo di restart.

### 13.4 Alternative

Corretto:

> La sequenza puo rappresentare una transizione negativa oppure una pressione
> successiva a una seconda palla; il primo cambio di possesso non e visibile.

Scorretto:

> E sicuramente una transizione negativa.

### 13.5 Motivo della categoria

Collegare etichetta e segnali.

Corretto:

> Rimessa laterale: battitore dietro la linea, gesto sopra la testa e ricezione
> visibili.

Scorretto:

> Rimessa laterale perche la palla e vicino alla fascia.

### 13.6 Motivo dell'astensione

Corretto:

> Non determinabile: il video inizia dopo la ripresa e non mostra il punto di
> battuta.

Scorretto:

> Non determinabile perche non sono sicuro.

### 13.7 Motivo dell'utilita

Corretto:

> Buono: mostra recupero e prima risposta, ma perde l'esito nel cambio camera.

Scorretto:

> Buono perche il frame e nitido.

### 13.8 Segnali contrari

Registrare fatti che indeboliscono la scelta:

- movimento non coordinato;
- palla gia in gioco;
- cronometro discontinuo;
- avversari fuori campo;
- possesso ambiguo;
- confine alternativo.

Un'annotazione senza segnali contrari quando il caso e ambiguo e incompleta.

---

## 14. Disaccordi

### 14.1 Stati

**Accordo pieno**

Gli annotatori concordano su:

- validita del momento;
- categoria primaria;
- squadra;
- utilita;
- confini entro la tolleranza prevista;
- frame o frame equivalente.

**Accordo parziale**

Concordano sul momento e sulla famiglia, ma differiscono su:

- confine;
- specificita;
- categoria secondaria;
- utilita adiacente;
- frame equivalente.

**Disaccordo**

Divergono su almeno uno:

- momento valido/non valido;
- categoria primaria;
- scena tattica/non tattica;
- squadra;
- utilita con distanza superiore a una classe.

**Evidenza insufficiente**

Il materiale non consente una decisione affidabile neppure dopo riesame.

**Decisione senior**

Il revisore senior risolve il conflitto applicando il manuale oppure conferma
`non determinabile`.

### 14.2 Processo obbligatorio

1. **Annotazioni indipendenti.**
   Nessuno vede la decisione dell'altro.
2. **Confronto delle sole dimensioni divergenti.**
   Il sistema o curatore evidenzia campi diversi, non suggerisce il vincitore.
3. **Riesame della sequenza.**
   Guardare velocita normale, poi punti critici.
4. **Applicazione del manuale.**
   Citare regola e segnali osservabili.
5. **Decisione o astensione.**
   Se il manuale non risolve, usare decisione senior o evidenza insufficiente.
6. **Registrazione della motivazione.**
   Conservare entrambe le versioni e l'esito.

### 14.3 Divieti

E vietato:

- sovrascrivere silenziosamente l'annotazione iniziale;
- mediare categorie incompatibili;
- scegliere la decisione della persona piu esperta senza motivazione;
- usare la predizione AI come arbitro;
- cambiare manuale durante il confronto senza nuova versione;
- trasformare automaticamente ogni disaccordo in `non determinabile`.

### 14.4 Registro del disaccordo

Deve contenere:

- ID campione;
- annotatori;
- campi divergenti;
- valori originali;
- evidenze citate;
- regola applicata;
- decisione finale;
- decisore;
- motivazione;
- versione manuale;
- eventuale proposta di modifica del manuale.

### 14.5 Quando aggiornare il manuale

Aprire una proposta quando lo stesso conflitto:

- ricorre in piu campioni;
- non e risolvibile con una regola esistente;
- produce decisioni senior incoerenti;
- rivela una categoria non annotabile.

La regola nuova vale solo dalla versione successiva. Le annotazioni congelate
non cambiano senza una migrazione tracciata.

### 14.6 Quando basta un annotatore

Un annotatore puo essere sufficiente per:

- screening tecnico preliminare;
- video nero o corrotto evidente;
- grafica fullscreen;
- pubblicita fullscreen;
- replay con segnale inequivocabile;
- negativi chiari nel development set non congelato.

Una quota di questi casi deve comunque essere sottoposta ad audit.

### 14.7 Quando servono almeno due annotatori

La revisione indipendente e obbligatoria per:

- momenti tattici positivi del benchmark;
- confini temporali usati nelle metriche;
- categorie primarie;
- utilita `ottimo` o `buono`;
- hard negative;
- casi `non determinabile`;
- categorie pilota o esplorative;
- campioni usati per calibrare score;
- test set congelato.

La quota definitiva e **da validare durante l'annotazione pilota**.

---

## 15. Controllo qualita

### 15.1 Checklist del singolo momento

- [ ] Video ID e versione presenti.
- [ ] Diritti verificati.
- [ ] Timestamp nell'intervallo del video.
- [ ] Ordine `inizio <= trigger <= centro <= esito <= fine`, con assenze motivate.
- [ ] Trigger presente oppure dichiarato non osservabile.
- [ ] Esito presente oppure dichiarato non osservabile.
- [ ] Confini spiegabili guardando la sequenza.
- [ ] Categoria compatibile con i segnali minimi.
- [ ] Specificita non superiore all'evidenza.
- [ ] Squadra corretta oppure non determinabile.
- [ ] Utilita assegnata con motivazione.
- [ ] Frame selezionato oppure nessun frame idoneo.
- [ ] Scena non tattica registrata quando presente.
- [ ] Qualita tecnica compilata separatamente.
- [ ] Evidenze visibili presenti.
- [ ] Limiti presenti nei casi incompleti.
- [ ] Interpretazioni alternative presenti nei casi ambigui.
- [ ] Segnali contrari registrati.
- [ ] Stato di accordo presente.
- [ ] Annotatore e revisore identificati.
- [ ] Versione manuale e tassonomia presenti.

### 15.2 Checklist del video

- [ ] Metadati minimi completi.
- [ ] Diritti e policy minori verificati.
- [ ] Porzioni corrotte/non valutabili marcate.
- [ ] Replay e scene non tattiche controllati.
- [ ] Timeline senza intervalli impossibili.
- [ ] Duplicati interni identificati.
- [ ] Replay collegati al live originale quando possibile.
- [ ] Split assegnato.
- [ ] Nessun duplicato o stessa partita in split incompatibili.
- [ ] Distribuzione categorie plausibile ma non forzata.
- [ ] Audit casuale completato.

### 15.3 Controlli automatici futuri concettuali

Senza progettare software, un futuro strumento dovrebbe segnalare:

- timestamp fuori durata;
- ordine temporale invalido;
- campi obbligatori vuoti;
- categoria specifica senza segnali minimi;
- frame fuori intervallo;
- annotazione congelata modificata;
- duplicati;
- versioni mancanti;
- diritti non verificati.

Questi controlli non sostituiscono la revisione tattica.

### 15.4 Campionamento di qualita

Anche negativi chiari e scene tecniche devono essere riesaminati a campione.
Frequenza e dimensione del campione sono **da validare durante l'annotazione
pilota**.

---

## 16. Set di calibrazione degli annotatori

Il set di calibrazione e concettuale: questa sezione non crea video, dataset o
soglie di superamento.

### 16.1 Composizione

| Tipo | Che cosa deve verificare |
|---|---|
| Caso facile | applicazione lineare di confini, categoria e utilita |
| Hard negative | capacita di rifiutare un caso visivamente simile |
| Replay | distinzione timeline live/non live |
| Esultanza | separazione tra esito del gol e celebrazione |
| Primo piano | riconoscimento del campo insufficiente |
| Palla inattiva generica | prudenza quando il tipo non e visibile |
| Calcio d'angolo | prova della zona, organizzazione e battuta |
| Punizione | distinzione da corner, pausa e rinvio |
| Rimessa laterale | prova del gesto e della linea |
| Non determinabile | astensione motivata, non pigrizia |
| Costruzione dal basso | sequenza dall'origine al primo esito |
| Transizione positiva | recupero osservabile e risposta offensiva |
| Transizione negativa | perdita osservabile e risposta difensiva |
| Pressing ambiguo | distinzione tra densita e coordinazione |
| Blocco ambiguo | distinzione tra struttura dinamica e frame statico |

### 16.2 Distribuzione concettuale

Il set deve:

- contenere piu esempi per regola critica;
- alternare positivi e hard negative;
- includere camera fissa e mobile;
- includere professionistico e dilettantistico;
- variare luce, compressione e contrasto;
- evitare che la risposta sia deducibile dall'ordine;
- non essere riutilizzato come benchmark finale.

La numerosita e **da validare durante l'annotazione pilota**.

### 16.3 Quiz teorico

Il quiz deve verificare:

1. differenza tra non tattico e non determinabile;
2. perche un frame non dimostra pressing;
3. quando restare su palla inattiva generica;
4. ordine corretto del workflow;
5. differenza tra trigger ed esito;
6. gestione replay;
7. separazione tra qualita tecnica e utilita;
8. obbligo di conservare le correzioni;
9. uso delle alternative;
10. condizioni per la doppia revisione.

Le domande devono includere motivazione, non solo scelta multipla.

### 16.4 Prova pratica

Procedura:

1. annotazione indipendente di un piccolo set;
2. consegna di intervalli, categorie, utilita e frame;
3. confronto con ground truth formativa;
4. analisi degli errori per dimensione;
5. seconda annotazione dopo feedback;
6. autorizzazione condizionata alle categorie comprese;
7. supervisione iniziale sulle categorie pilota/esplorative.

### 16.5 Valutazione

Misurare separatamente:

- scene non tattiche;
- confini;
- categoria;
- astensione;
- utilita;
- frame;
- motivazione.

Non ridurre la calibrazione a un unico punteggio. La soglia di superamento e
**da validare durante l'annotazione pilota**.

### 16.6 Ricalibrazione

Richiederla quando:

- cambia la tassonomia;
- cambia una regola critica;
- l'accordo cala;
- compaiono nuovi domini;
- l'annotatore resta inattivo a lungo;
- si osservano errori sistematici.

---

## 17. Modulo di annotazione concettuale

Questa sezione descrive dati, non database o UI.

### 17.1 Campi sempre obbligatori

| Campo | Contenuto |
|---|---|
| video ID | identificatore stabile della sorgente |
| diritti | stato e riferimento autorizzazione |
| inizio | primo istante del record |
| fine | ultimo istante del record |
| tipo intervallo | valutabile, non valutabile, non tattico, momento |
| categoria primaria | categoria o non determinabile |
| utilita | ottimo, buono, mediocre, inutile |
| qualita tecnica | rubric per dimensione |
| evidenze | fatti osservabili |
| limiti | elementi mancanti o degradati |
| annotatore | identita/ID |
| stato accordo | stato corrente |
| versione manuale | versione B1 usata |
| versione tassonomia | versione delle categorie |

### 17.2 Campi obbligatori per un momento tattico

| Campo | Regola |
|---|---|
| trigger | timestamp oppure assente con motivo |
| centro | istante piu informativo |
| esito | timestamp oppure assente con motivo |
| squadra | identificata oppure non determinabile |
| frame | ID oppure nessun frame idoneo |
| motivo categoria | segnali che sostengono l'etichetta |
| motivo utilita | valore operativo per lo staff |

### 17.3 Campi condizionali

| Campo | Quando |
|---|---|
| categorie secondarie | altra dimensione osservabile e prevista |
| scena non tattica | intervallo escluso o contaminato |
| frame alternativi | piu frame equivalenti |
| confine alternativo | inizio/fine graduali |
| motivo astensione | categoria non determinabile |
| segnali contrari | caso ambiguo o categoria pilota/esplorativa |
| revisore | seconda revisione richiesta |
| decisione senior | disaccordo non risolto |
| split | campione destinato a dataset |
| duplicato di | replay, duplicato o stessa azione |

### 17.4 Campi opzionali

- note operative;
- interpretazioni alternative;
- annotazione geometrica;
- commento editoriale;
- collegamento al momento precedente/successivo;
- difficolta percepita;
- tempo di annotazione.

Un campo opzionale non deve contenere informazioni necessarie a giustificare una
categoria obbligatoria.

### 17.5 Audit trail

Ogni revisione futura deve conservare:

- valore precedente;
- valore nuovo;
- autore;
- data;
- motivo;
- manuale/tassonomia;
- stato prima/dopo.

---

## 18. Esempi di errori dell'annotatore

### 18.1 Categoria da un solo frame

**Errore:** vedere quattro difensori allineati e assegnare blocco difensivo.  
**Correzione:** guardare origine, adattamento e conseguenza.

### 18.2 Densita scambiata per pressing

**Errore:** molti giocatori vicini equivalgono a pressing.  
**Correzione:** cercare trigger, coordinazione, orientamento e risposta.

### 18.3 Campo largo scambiato per linea di centrocampo

**Errore:** una ripresa ampia viene classificata perche mostra una forma.  
**Correzione:** il campo largo e qualita potenziale, non categoria.

### 18.4 `Open play` usato come fallback

**Errore:** assegnare un'etichetta generica non prevista a ogni azione.  
**Correzione:** non tattico oppure non determinabile secondo l'evidenza.

### 18.5 Esultanza classificata

**Errore:** attribuire struttura difensiva ai giocatori che rientrano dopo un gol.  
**Correzione:** separare esito ed esultanza.

### 18.6 Corner forzato

**Errore:** cross laterale o giocatori in area diventano automaticamente corner.  
**Correzione:** richiedere zona d'angolo, organizzazione e battuta.

### 18.7 Possesso inventato

**Errore:** attribuire possesso da postura o direzione senza palla.  
**Correzione:** registrare palla non osservabile e ridurre specificita.

### 18.8 Cambio camera ignorato

**Errore:** unire prima e dopo anche se il collegamento non e dimostrabile.  
**Correzione:** marcare discontinuita, confine o esito assente.

### 18.9 Frame piu bello invece del piu utile

**Errore:** scegliere il frame piu nitido con pochi soggetti.  
**Correzione:** privilegiare relazioni, palla e campo.

### 18.10 Ambiguita non registrata

**Errore:** scegliere una categoria e omettere l'alternativa plausibile.  
**Correzione:** compilare limiti, segnali contrari e alternative.

### 18.11 Correzione senza versione originale

**Errore:** sovrascrivere categoria o confini durante la review.  
**Correzione:** creare una revisione con audit trail.

### 18.12 Conoscenza futura

**Errore:** usare il gol o il risultato successivo fuori intervallo per giudicare
la scelta precedente.  
**Correzione:** valutare soltanto evidenza disponibile entro il momento.

### 18.13 Score AI usato come prova

**Errore:** accettare un'etichetta perche la confidence e alta.  
**Correzione:** la predizione resta nascosta nel primo passaggio.

### 18.14 Specificita eccessiva

**Errore:** aggiungere lato, altezza o efficacia non osservabili.  
**Correzione:** fermarsi al livello massimo sostenuto.

---

## 19. Glossario

**Momento tattico**  
Sequenza continua con origine osservabile e comportamento collettivo pertinente.

**Trigger**  
Evento osservabile che attiva il comportamento.

**Sviluppo**  
Evoluzione di palla, spazi, posizioni e relazioni dopo il trigger.

**Esito**  
Prima conseguenza tatticamente rilevante osservabile.

**Scena non tattica**  
Intervallo non utile alla valutazione tattica primaria.

**Hard negative**  
Caso negativo visivamente simile a un positivo e quindi difficile da rifiutare.

**Ground truth**  
Riferimento umano revisionato, versionato e congelato.

**Annotazione**  
Record strutturato di intervallo, categorie, evidenze, limiti e decisioni.

**Adjudication**  
Risoluzione formale di un disaccordo tramite regole e revisore senior.

**Astensione**  
Decisione esplicita di non assegnare una categoria non sostenuta.

**Categoria primaria**  
Etichetta principale che descrive il momento.

**Categoria secondaria**  
Etichetta aggiuntiva osservabile che non sostituisce la primaria.

**Livello massimo di specificita**  
Dettaglio piu preciso sostenuto dalle evidenze disponibili.

**Frame rappresentativo**  
Immagine interna al momento che mostra la configurazione piu informativa.

**Qualita tecnica**  
Idoneita visiva e audiovisiva del materiale, separata dal valore tattico.

**Valore tattico**  
Utilita del momento per comprendere, discutere o allenare un comportamento.

**Evidenza insufficiente**  
Stato in cui i dati non consentono una decisione affidabile.

**Confine alternativo**  
Inizio o fine plausibile aggiuntivo registrato nei casi graduali.

**Porzione non valutabile**  
Intervallo tecnicamente impossibile da giudicare; non equivale a non tattico.

**Accordo parziale**  
Convergenza sul momento con differenze limitate su attributi o confini.

**Segnale contrario**  
Osservazione che indebolisce la categoria proposta.

**Specificita eccessiva**  
Categoria o attributo piu dettagliati di quanto consentito dall'evidenza.

---

## 20. Criteri di completamento B1

B1 e completata soltanto se:

1. una persona esterna comprende il workflow senza conoscere il prodotto;
2. le categorie iniziali hanno segnali minimi, esclusioni e hard negative;
3. `non tattico` e `non determinabile` sono distinti operativamente;
4. inizio, trigger, centro, esito e fine sono annotabili;
5. i confini incerti possono essere registrati senza precisione fittizia;
6. i disaccordi seguono un processo e conservano le versioni originali;
7. esiste una checklist di qualita per momento e video;
8. esiste un set di calibrazione concettuale;
9. il modulo concettuale distingue campi obbligatori, condizionali e opzionali;
10. il manuale non dipende dalla UI attuale;
11. nessuna confidence AI viene trattata come ground truth;
12. nessuna soglia non supportata viene presentata come definitiva;
13. pressing e blocco restano esplorativi;
14. costruzione e transizioni restano categorie pilota;
15. il manuale non presuppone che la pipeline sia corretta.

Prima del congelamento B1 devono essere eseguiti:

- walkthrough con almeno una persona esterna;
- annotazione pilota;
- raccolta dei disaccordi;
- revisione delle regole ambigue;
- assegnazione di una versione stabile.

Queste attivita non sono state eseguite durante la redazione del documento.

---

## Appendice A - Decisioni ancora aperte

Le seguenti decisioni sono **da validare durante l'annotazione pilota**:

1. durata minima e massima per categoria;
2. tolleranze temporali per l'accordo;
3. numero di esempi nel set di calibrazione;
4. soglia di superamento della calibrazione;
5. frequenza della ricalibrazione;
6. quota di doppia revisione sui negativi chiari;
7. dimensione dell'audit casuale;
8. sufficienza del campo per categoria;
9. numero minimo di giocatori per categoria;
10. gestione dei cambi camera brevi;
11. regola tra frame equivalenti;
12. soglia tra ottimo, buono, mediocre e inutile;
13. inclusione definitiva di costruzione e transizioni;
14. annotabilita affidabile di pressing e blocco;
15. uso delle categorie secondarie;
16. gestione dei momenti sovrapposti;
17. policy per video montati;
18. gestione dell'audio come evidenza;
19. livello massimo di specificita per i piazzati;
20. processo di adjudication con team composto da una sola persona.

---

## Appendice B - Scheda rapida dell'annotatore

Prima:

1. verifica video, diritti e qualita;
2. marca non valutabile e non tattico;
3. nascondi le predizioni AI.

Per ogni momento:

1. guarda la sequenza;
2. trova trigger e conseguenza;
3. delimita i confini;
4. applica la decision tree;
5. resta generico o astieniti;
6. assegna squadra e utilita;
7. scegli il frame;
8. registra evidenze e limiti;
9. esegui la checklist;
10. conserva ogni revisione.

Regola finale:

> Se non puoi indicare nel video le prove della categoria, non assegnarla.
