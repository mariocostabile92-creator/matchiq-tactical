# MatchIQ Video Hub - Test Fase B

Data: 2026-07-11

## Obiettivo

Validare il flusso Video Hub in scenario production/PWA dopo il completamento dei blocchi principali e del Test Fase A.

La Fase B serve a verificare che l'utente possa usare il sistema come piattaforma reale:

1. Aprire la PWA aggiornata.
2. Caricare o importare una sessione video.
3. Salvare metadati e stato lavorazione.
4. Riaprire la sessione dopo refresh.
5. Archiviare e ripristinare.
6. Aprire la sessione nel Video AI.
7. Estrarre fotogrammi.
8. Generare report.
9. Riaprire report/sessione senza perdere dati.

## Stato del test

Risultato codice: PASS

Risultato PWA/statico: PASS

Test production browser reale: DA ESEGUIRE DOPO DEPLOY

Motivo: da questo ambiente posso verificare codice, asset PWA e sintassi, ma non posso simulare in modo affidabile una sessione Railway reale con upload video, cache browser/PWA e credenziali utente production.

## Controlli eseguiti

### Backend

Eseguito controllo di compilazione su:

- `database.py`
- `app/routers/video.py`
- `app/services/video_hub.py`
- `app/services/cloud_providers.py`
- `app/services/video_library.py`
- `main.py`

Esito: PASS

### Frontend Video AI

Estratto lo script principale da `frontend/video.html` e verificato con `node --check`.

Esito: PASS

### PWA e cache

Verificati riferimenti PWA principali:

- `frontend/service-worker.js`
- `frontend/manifest.json`
- `frontend/index.html`
- `frontend/mobile.html`
- `frontend/video.html`

Stato trovato:

- cache PWA: `matchiq-pwa-v86`
- app shell aggiornata con `v=10486`
- `manifest.json` punta a `/index.html?v=10486`
- `mobile.html` rimanda a `/index.html?v=10486`
- `index.html` apre Video AI con `video.html?v=10486`

Esito: PASS

## Checklist production/PWA

Questa e la checklist da eseguire sul dominio production dopo deploy.

### 1. Refresh PWA

1. Aprire la pagina production.
2. Fare refresh completo del browser.
3. Se usata come PWA installata, chiuderla e riaprirla.
4. Verificare che la pagina carichi asset aggiornati e non vecchie versioni.

Risultato atteso:

- Home, Coach, Video AI e Account si aprono.
- Video AI mostra la UI aggiornata del Video Hub.
- Nessun blocco evidente da cache vecchia.

### 2. Carico video

1. Aprire Video AI.
2. Compilare titolo, societa/squadra, categoria, focus e note.
3. Caricare un MP4 breve.
4. Usare il consenso diritti quando richiesto.

Risultato atteso:

- Il video compare nel player.
- La sessione viene creata/aggiornata.
- Il Video Hub mostra la sessione nella lista.

### 3. Salvataggio sessione

1. Aprire la scheda della sessione dal Video Hub.
2. Cambiare titolo, squadra, tag, note e stato lavorazione.
3. Salvare.

Risultato atteso:

- Messaggio di salvataggio positivo.
- I dati modificati restano visibili.

### 4. Riapertura dopo refresh

1. Fare refresh della pagina.
2. Tornare su Video AI.
3. Riaprire la sessione dal Video Hub.

Risultato atteso:

- La sessione e ancora presente.
- I metadati modificati sono conservati.
- Il pulsante "Apri nel Video AI" carica la sessione corretta.

### 5. Archivio e ripristino

1. Archiviare una sessione.
2. Usare filtro archiviate.
3. Ripristinare la sessione.

Risultato atteso:

- La sessione sparisce dalla lista attiva dopo archivio.
- Compare nel filtro archiviate.
- Dopo ripristino torna nella lista attiva.

### 6. Apertura in Video AI

1. Cliccare "Apri nel Video AI".
2. Verificare player, metadati e form.

Risultato atteso:

- Il video viene caricato nel player.
- Titolo, squadra, focus e note sono coerenti con la sessione.
- La sessione viene marcata come usata/riaperta.

### 7. Estrazione fotogrammi

1. Estrarre fotogrammi dal video.
2. Cambiare focus tattico se necessario.
3. Verificare le card frame generate.

Risultato atteso:

- I frame vengono mostrati sotto il player.
- Ogni frame ha timestamp leggibile.
- Lo storyboard/diapositive tattiche non rompe il layout.

### 8. Generazione report

1. Generare report AI.
2. Scaricare PDF.
3. Riaprire la stessa sessione.

Risultato atteso:

- Il report compare nel pannello di destra.
- Il PDF e scaricabile.
- Il report rimane collegato alla sessione.

### 9. Console e rete

Durante il test aprire DevTools e controllare:

- nessun errore 500
- nessun errore 404 su asset PWA principali
- nessun loop di refresh
- nessun blocco service worker
- eventuali 401 solo se utente non autenticato o token scaduto

## Esito Fase B

La Fase B e pronta per essere eseguita in produzione dopo deploy. I controlli locali su codice, sintassi frontend e asset PWA sono passati.

Il test production vero resta manuale perche richiede browser/PWA reale, sessione utente, dominio Railway/custom domain e upload video effettivo.

## Prossimo blocco

Dopo il test production, il prossimo step consigliato e un log di esito Fase B:

- esito upload
- esito riapertura sessione
- esito archivio/ripristino
- esito apertura in Video AI
- esito report/PDF
- eventuali errori console

Se tutto passa, il Video Hub puo essere considerato pronto come base stabile per la successiva evoluzione: riconoscimento tattico piu intelligente, libreria pro e workflow da match analyst.
