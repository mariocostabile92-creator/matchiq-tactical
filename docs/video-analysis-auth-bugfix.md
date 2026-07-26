# Video AI authentication bugfix

Data verifica: 27 luglio 2026

## Perimetro

Correzione mirata del blocco che impediva l'avvio dell'analisi Video AI su
`POST /api/video/select-frames`. Coach, Home, Account, database, Vision Engine,
RF-DETR e algoritmo di selezione dei frame non sono stati modificati.

## Causa radice

`frontend/video.html` manteneva una copia locale della gestione autenticazione
invece di caricare il client condiviso `frontend/js/auth.js`.

Il metodo locale `getAuthToken()` eliminava silenziosamente dal browser un token
scaduto. La successiva chiamata diretta a `/api/video/select-frames` partiva
quindi senza un Bearer token valido e il backend, correttamente, rispondeva 401.

L'errore veniva poi assorbito in due punti:

- `extractFrames()` convertiva il fallimento in un semplice risultato negativo;
- `startAnalysis()` riportava la UI allo step di configurazione.

Il risultato visibile era un ritorno indietro senza spiegazione e con retry
potenzialmente ripetuti. Il service worker non era la causa: le richieste
`/api/` sono escluse dalla cache.

## Endpoint e protezione

Endpoint coinvolto:

`POST /api/video/select-frames`

L'endpoint continua a richiedere `get_current_user`. Non è stato reso pubblico
e non è stato aggiunto alcun token hardcoded.

Quando è presente `video_asset_id`, il backend verifica inoltre che l'asset
appartenga all'utente autenticato. Un asset di un altro utente viene rifiutato
senza esporne i dati. Le analisi locali che non hanno ancora un asset persistito
restano supportate con `video_asset_id` assente.

## Richiesta prima della correzione

- chiamata eseguita con `fetch` locale;
- nessun uso garantito dell'helper autenticato condiviso;
- token scaduto cancellato prima della richiesta;
- `Authorization` assente o non valido;
- `credentials` non dichiarato;
- payload privo di `video_asset_id`;
- risposta backend: `401 Unauthorized`;
- errore nascosto e ritorno allo step precedente.

## Richiesta dopo la correzione

- helper condiviso `MatchIQAuth.authHeaders()` usato per gli header;
- `Authorization: Bearer <token>` aggiunto nello stesso modo degli altri
  endpoint autenticati;
- `credentials: "same-origin"`;
- payload con `video_asset_id` quando disponibile;
- una sola richiesta attiva grazie al single-flight guard;
- 401 trasformato in uno stato di recupero esplicito;
- nessun reset di video, configurazione o frame già disponibili.

## Transizione e recupero

### Successo

Il flusso passa da `Prepara` ad `Analizza`, completa la selezione dei frame e
apre il workspace di revisione. Il player, il video e il contesto restano
associati alla stessa sessione.

### Sessione assente o scaduta

La UI mostra:

> Sessione non attiva. Accedi di nuovo in un'altra scheda, poi premi Riprova
> analisi.

Il video resta in memoria, il contesto non viene cancellato e viene mostrato un
solo comando `Riprova analisi`. Un ulteriore tentativo senza sessione resta
nello stesso stato di recupero e non crea loop o duplicazioni.

## Warning Canvas2D

Il canvas usato per estrarre i frame esegue letture ripetute. Il contesto è ora
creato localmente con:

`getContext("2d", { willReadFrequently: true })`

La modifica non cambia pixel, frame scelti o algoritmo.

## File modificati

- `app/routers/video.py`
- `frontend/video.html`
- `frontend/js/video-experience.js`
- `frontend/service-worker.js`
- `tests/test_video_analysis_auth_bugfix.py`
- test di release aggiornati alla versione Video AI `10542` e PWA `v143`

## Test aggiunti

La nuova suite mirata copre:

1. utente non autenticato: 401;
2. Bearer token risolto dall'helper condiviso;
3. proprietario dell'asset: successo;
4. utente non proprietario: rifiuto;
5. analisi locale senza asset persistito;
6. header condivisi, credenziali e payload;
7. una sola richiesta concorrente;
8. conservazione del workspace in errore;
9. retry controllato;
10. transizione `Prepara` -> `Analizza`;
11. uso locale di `willReadFrequently`.

Test mirati:

`121 test`, esito `OK`.

## Suite completa

Prima esecuzione:

`469 test`, `24.441 s`, esito `OK`.

Seconda esecuzione:

`469 test`, `23.658 s`, esito `OK`.

Controlli aggiuntivi:

- sintassi JavaScript `video-experience.js`: OK;
- compilazione Python `app/routers/video.py`: OK;
- dipendenze installate (`pip check`): OK.

## Verifica reale nel browser

Flusso autenticato realmente eseguito:

1. login con account locale temporaneo;
2. apertura Video AI;
3. upload di un MP4 locale di prova;
4. configurazione mantenuta;
5. click su `Avvia analisi`;
6. nessun 401;
7. step `Carica`, `Prepara` e `Analizza` completati;
8. workspace `Revisiona` aperto;
9. player e frame visibili;
10. nessun ritorno allo step precedente;
11. nessun errore o warning bloccante in console.

Flusso senza sessione realmente eseguito:

1. logout;
2. nuovo upload;
3. click su `Avvia analisi`;
4. stato di recupero esplicito;
5. video conservato;
6. retry unico e senza loop.

Verifica responsive reale, tramite viewport isolati:

- `1366x768`: nessun overflow orizzontale;
- `1920x1080`: nessun overflow orizzontale;
- tablet `834x1112`: nessun overflow, upload entro il viewport;
- step bar e footer presenti in tutti i viewport.

## Rischi residui

- un token realmente scaduto richiede comunque un nuovo login: non è presente
  un refresh token automatico;
- un video molto lungo resta soggetto ai normali tempi di upload/elaborazione;
- l'analisi locale senza asset persistito non può applicare un controllo di
  ownership su un ID che non esiste, ma resta protetta dall'autenticazione.

## Conferme

- endpoint ancora protetto;
- ownership e isolamento utenti attivi;
- nessuna modifica a Coach, Home o Account;
- nessuna modifica allo schema database;
- nessuna modifica a Vision Engine o RF-DETR;
- nessun commit creato;
- nessun push eseguito.
