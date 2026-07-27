# Video AI Final Polish Audit

## Perimetro

Audit esclusivamente UX del Video AI e della Libreria Video AI. Backend, API,
database, autenticazione, pagamenti, pipeline AI, Vision Engine, RF-DETR, Coach,
Home e Account restano fuori perimetro.

## Classificazione

| Area | Elemento | Classe | Valutazione |
| --- | --- | --- | --- |
| Hero | Titolo, promessa e accesso ai progetti | Importante | Utile per orientare l'ingresso, ma deve cedere rapidamente il centro al workflow. |
| Workflow | Carica, Prepara, Analizza, Revisiona, Consegna | Essenziale | Deve restare visibile e spiegare il contesto corrente, non essere solo un indicatore colorato. |
| Upload | Dropzone e selezione modalita | Essenziale | Prima azione del progetto; una sola CTA dominante. |
| Preparazione | Titolo, focus e squadra osservata | Essenziale | Dati minimi per avviare un'analisi coerente. |
| Preparazione | Formazioni, metadati e opzioni report | Secondario | Correttamente raccolti nelle impostazioni avanzate. |
| Analisi | Stato, avanzamento, tempo ed evidenze | Essenziale | Deve comunicare che il sistema sta lavorando e che il progetto rimane recuperabile. |
| Review | Player | Essenziale | Elemento dominante dell'intero workspace. |
| Review | Evidenza selezionata e decisioni | Essenziale | Conferma, Correggi e Scarta sono le azioni principali. |
| Review | Coda evidenze | Importante | Serve per navigare senza perdere il contesto del video. |
| Review | Filtri | Secondario | Necessari in sessioni lunghe, ma non devono occupare spazio in modo permanente. |
| Review | Note, classificazione e provenienza | Secondario | Disponibili su richiesta per una correzione approfondita. |
| Review | Regolazioni frame e clip | Secondario | Strumenti specialistici da espandere volontariamente. |
| Review | Frame, diapositive e strumenti tecnici | Secondario | Materiale di supporto gia raccolto in una sezione collassabile. |
| Timeline | Video, momento, frame e clip | Importante | Devono essere percepiti come un unico blocco di lavoro. |
| Report | Apri report e PDF | Essenziale | Conclusione naturale del workflow. |
| Report | Ritorno alla review e pendenti | Importante | Mantengono continuita senza trasformare il report in una pagina isolata. |
| Libreria | Partita, stato, revisione, report e continua | Essenziale | Memoria tecnica dello staff, non semplice elenco di file. |
| Libreria | Filtri e ordinamento | Importante | Utili con archivio ampio; gerarchia inferiore rispetto a Continua. |
| Libreria | Metadati completi e azioni amministrative | Secondario | Devono restare disponibili senza dominare la card. |
| Messaggi | Errori recuperabili | Essenziale | Devono preservare il lavoro e offrire retry o ritorno ai progetti. |
| Stati vuoti | Primo progetto, nessun filtro, nessuna evidenza | Importante | Devono indicare un passo successivo chiaro. |

## Problemi rilevati

1. Il workflow comunicava soprattutto lo stato tramite colore e numero.
2. Il player condivideva troppo peso visivo con la sidebar.
3. Filtri, campi editoriali, metadati e regolazioni frame/clip erano sempre
   visibili durante la review.
4. La fase di elaborazione mostrava numeri corretti ma poca continuita narrativa.
5. Le CTA finali del report non seguivano l'ordine naturale apertura, PDF,
   eventuale ritorno alla review.
6. Il titolo della Libreria descriveva un insieme di progetti, non la memoria
   tecnica dello staff.

## Gerarchia applicata

### Carica

1. Video.
2. Modalita di analisi.
3. Ripresa di un progetto esistente.

### Prepara

1. Contesto essenziale.
2. Avvio analisi.
3. Impostazioni avanzate su apertura volontaria.

### Analizza

1. Stato corrente.
2. Attivita completate e in corso.
3. Avanzamento, tempo ed evidenze.

### Revisiona

1. Player.
2. Evidenza corrente.
3. Conferma, Correggi, Scarta.
4. Coda.
5. Filtri, note e regolazioni su apertura volontaria.

### Consegna

1. Apri report.
2. Scarica PDF.
3. Torna alla review.
4. Completa eventuali evidenze pendenti.

## Responsive

- Desktop 1366/1440/1920: player con colonna fluida e sidebar limitata.
- Tablet: workspace in una colonna, senza overflow orizzontale.
- Sotto 700 px: contesti secondari degli step nascosti, controlli e statistiche
  impilati, safe area preservata.

## Vincoli rispettati

- Nessuna funzione aggiunta.
- Nessuna chiamata o payload modificato.
- Nessuna modifica a backend, API, database o autenticazione.
- Nessuna modifica a Coach, Home o Account.
- Nessuna modifica alla pipeline AI o al Vision Engine.
