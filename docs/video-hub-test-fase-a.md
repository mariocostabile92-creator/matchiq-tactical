# MatchIQ Video Hub - Test Fase A

Data: 2026-07-11

## Obiettivo

Verificare il primo flusso operativo della Libreria Video dopo i blocchi principali:

1. Carico video.
2. Salvataggio sessione.
3. Riapertura sessione.
4. Modifica metadati/sessione.
5. Archivio e ripristino.
6. Apertura in Video AI.

## Stato del test

Risultato codice: PASS

Risultato controlli statici: PASS

Test API live locale: NON ESEGUITO

Motivo: nell'ambiente locale non e presente una virtualenv del progetto e il Python globale non ha FastAPI installato. Il controllo live completo va quindi ripetuto su Railway o su una macchina con dipendenze installate.

## Controlli eseguiti

### Compilazione Python

Eseguito controllo di compilazione su:

- `database.py`
- `app/routers/video.py`
- `app/services/video_hub.py`
- `app/services/cloud_providers.py`
- `app/services/video_library.py`
- `main.py`

Esito: PASS

### Sintassi JavaScript Video AI

Estratto e verificato lo script principale di `frontend/video.html` con `node --check`.

Esito: PASS

### Controllo whitespace/diff

Eseguito `git diff --check` sui file coinvolti dal flusso Video Hub e dal report finale.

Esito: PASS

## Mappatura flusso Fase A

### 1. Carico video

Frontend:

- `uploadLibraryVideoWithProgress(form)`
- `saveCurrentVideoToLibrary()`

Backend atteso:

- Upload asset video.
- Creazione metadati iniziali.
- Creazione job iniziale.
- Aggiornamento attivita sessione.

Stato: coperto dal codice.

### 2. Salvataggio sessione

Frontend:

- `createDraftVideoSession()`
- `saveSessionMetadata(assetId)`

Backend:

- `create_video_session(user_id, data)`
- `patch_video_session(user_id, asset_id, data)`

Stato: coperto dal codice.

### 3. Riapertura sessione

Frontend:

- Lista sessioni dalla libreria.
- Modale/session card.
- `openSessionFromUrl()`

Backend:

- Lettura sessioni Video Hub.
- Lettura singola sessione per asset.

Stato: coperto dal codice.

### 4. Modifica sessione

Frontend:

- Modifica titolo, squadra, tag, stato lavorazione e note dalla scheda sessione.
- Salvataggio tramite `saveSessionMetadata(assetId)`.

Backend:

- `patch_video_session(user_id, asset_id, data)`
- Aggiornamento metadati e attivita.

Stato: coperto dal codice.

### 5. Archivio e ripristino

Frontend:

- `archiveVideoSession(assetId, archived)`

Backend:

- `archive_video_session(user_id, asset_id, archived)`

Stato: coperto dal codice.

### 6. Apertura in Video AI

Frontend:

- `openLibraryVideo(assetId)`
- Ripristino sorgente video.
- Compilazione form Video AI dai metadati sessione.
- `restoreLatestSessionReport(item, options={})`

Backend:

- Stream video da asset caricato.
- Touch della sessione tramite `touch_video_session(user_id, asset_id)`.
- Recupero report piu recente quando disponibile.

Stato: coperto dal codice.

## Test manuale da fare dopo deploy

1. Aprire Video AI e fare refresh completo della PWA.
2. Caricare un MP4 breve con checkbox diritti attiva.
3. Verificare che la card compaia in Libreria Video.
4. Aprire la scheda sessione.
5. Modificare titolo, squadra, tag, note e stato lavorazione.
6. Salvare e ricaricare la pagina.
7. Verificare che i dati modificati restino salvati.
8. Archiviare la sessione.
9. Filtrare le archiviate e ripristinare la sessione.
10. Cliccare "Apri nel Video AI".
11. Verificare video caricato, form precompilato e sessione collegata.
12. Estrarre frame e generare report.
13. Riaprire la stessa sessione e verificare il recupero report.

## Limiti noti

- Non e stato eseguito un test browser/API locale per assenza dipendenze FastAPI nell'ambiente corrente.
- Non e stato caricato un video reale dal sandbox locale.
- Il collaudo production/PWA resta da fare dopo deploy.
- I provider cloud restano collegati come astrazione iniziale, non come integrazione completa definitiva.

## Esito Fase A

La Fase A e pronta per deploy e test manuale in produzione. Il codice copre il flusso principale richiesto: carico video, salvataggio sessione, riapertura, modifica, archivio/ripristino e apertura in Video AI.

Prossimo blocco consigliato: Test Fase B, cioe smoke test production/PWA con upload reale, console pulita, refresh PWA e verifica del recupero sessione/report.
