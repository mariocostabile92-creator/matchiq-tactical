# MatchIQ Video Hub - Report finale

Data blocco: 2026-07-11

## 1. Architettura precedente trovata

Il modulo Video AI era centrato sulla pagina `frontend/video.html`, con archivio report locale/cloud e caricamento video diretto per generare report PDF. La vecchia "libreria partite" non era ancora un ambiente completo per organizzare sessioni video, stati di lavorazione, provider cloud e collegamento stabile tra archivio e analisi.

## 2. File analizzati

- `frontend/video.html`
- `frontend/index.html`
- `frontend/mobile.html`
- `frontend/manifest.json`
- `frontend/service-worker.js`
- `app/routers/video.py`
- `app/services/video_hub.py`
- `app/services/cloud_providers.py`
- `app/services/video_library.py`
- logica import URL presente in `app/routers/video.py`
- `database.py`
- `usage_guard.py`

## 3. File modificati nel rollout Video Hub

- `app/routers/video.py`
- `app/services/video_hub.py`
- `app/services/cloud_providers.py`
- `frontend/video.html`
- `frontend/index.html`
- `frontend/mobile.html`
- `frontend/manifest.json`
- `frontend/service-worker.js`

## 4. Nuovi file creati

- `app/services/video_hub.py`
- `app/services/cloud_providers.py`
- `docs/video-hub-final-report.md`

## 5. Responsabilita dei nuovi moduli

`app/services/video_hub.py`

Gestisce il concetto di Sessione Video: normalizzazione dati, stati, archiviazione, apertura nel Video AI, storico attivita, ultimo report collegato e filtri.

`app/services/cloud_providers.py`

Espone un registry modulare dei provider cloud. I provider non configurati non fingono connessioni attive: mostrano stato sicuro e messaggi chiari.

`frontend/video.html`

Contiene l'interfaccia Video Hub integrata nel Video AI: archivio sessioni, filtri, upload, import URL autorizzato, provider cloud, modale sessione, resume report e collegamento con il player/analisi.

## 6. Modello Sessione Video

La Sessione Video supporta:

- titolo
- tipo sessione
- stagione
- data
- squadra
- squadra casa
- squadra trasferta
- avversario
- competizione
- categoria
- risultato
- campo
- durata
- sorgente
- provider
- file originale
- MIME type
- dimensione
- thumbnail
- stato lavoro
- progresso
- note
- tag
- archivio attivo/archiviato
- ultimo utilizzo
- ultimo report collegato
- storico attivita

Tipi sessione centralizzati:

- `official_match`
- `friendly_match`
- `training`
- `exercise`
- `opponent_analysis`
- `individual_analysis`
- `goalkeeper`
- `youth`
- `other`

Stati principali:

- `draft`
- `uploading`
- `importing`
- `processing`
- `ready`
- `failed`
- `archived`

Stati workflow:

- `to_analyze`
- `in_analysis`
- `report_ready`
- `needs_review`
- `approved`

## 7. Endpoint aggiunti o consolidati

Sessioni Video Hub:

- `GET /api/video/hub/sessions`
- `POST /api/video/hub/sessions`
- `GET /api/video/hub/sessions/{asset_id}`
- `PATCH /api/video/hub/sessions/{asset_id}`
- `POST /api/video/hub/sessions/{asset_id}/archive`
- `POST /api/video/hub/sessions/{asset_id}/open`

Provider cloud:

- `GET /api/video/hub/providers`
- `GET /api/video/hub/providers/{provider_id}/status`
- `POST /api/video/hub/providers/{provider_id}/import`

Upload e import:

- `POST /api/video/library/upload`
- `POST /api/video/library/import-url`
- `GET /api/video/library/{asset_id}/status`
- `POST /api/video/library/{asset_id}/status`
- `GET /api/video/library/{asset_id}/stream`
- `DELETE /api/video/library/{asset_id}`

Report:

- `GET /api/video/reports`
- `POST /api/video/reports`
- `DELETE /api/video/reports/{report_id}`

## 8. Struttura Archivio MatchIQ

L'Archivio MatchIQ ora mostra sessioni video reali con:

- card responsive
- thumbnail o placeholder
- tipo sessione
- squadre/soggetto
- stagione
- competizione
- risultato
- durata
- tag
- stato tecnico
- stato workflow
- ultimo utilizzo
- azioni principali

Azioni disponibili:

- apri nel Video AI
- analizza
- apri scheda
- salva dati
- archivia/ripristina
- elimina con conferma

Filtri disponibili:

- ricerca testuale
- squadra
- stagione
- competizione
- tipo sessione
- stato workflow
- focus
- tag
- provider
- archivio

## 9. Collegamento con Video AI

Quando una sessione viene aperta nel Video AI:

- mantiene `video_asset_id`
- precompila titolo, squadre, categoria, focus, competizione, tag e note
- aggiorna `last_used_at`
- registra storico "Aperta nel Video AI"
- associa i report generati alla sessione
- salva ultimo report collegato nella metadata della sessione
- permette di riprendere il report dalla scheda sessione
- recupera report cloud, PDF, slide e dati leggeri di frame/linee quando disponibili

Scelta prudente: le immagini frame non vengono duplicate dentro la sessione. Il sistema conserva tempi e metadati; se servono nuove anteprime, l'utente riestrae i frame dal video aperto.

## 10. Struttura provider cloud

Provider predisposti:

- Google Drive
- Dropbox
- Microsoft OneDrive
- Amazon S3

Ogni provider espone:

- id
- nome
- stato
- configurazione richiesta
- messaggio utente
- azioni future abilitate o disabilitate

I provider non configurati restituiscono stato non configurato. Non vengono salvati token finti e non viene mostrato successo senza OAuth reale.

## 11. Provider configurabili

Provider consigliati per prossimi step:

1. Amazon S3
2. Google Drive
3. OneDrive
4. Dropbox

Consiglio: partire da Amazon S3 perche e piu controllabile lato backend e utile per storage video proprietario. Dopo S3, Google Drive e il provider piu appetibile per societa e staff.

## 12. Variabili ambiente future

Per integrazioni reali serviranno variabili come:

- `VIDEO_STORAGE_PROVIDER`
- `VIDEO_STORAGE_BUCKET`
- `VIDEO_STORAGE_REGION`
- `VIDEO_STORAGE_ACCESS_KEY_ID`
- `VIDEO_STORAGE_SECRET_ACCESS_KEY`
- `GOOGLE_DRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET`
- `GOOGLE_DRIVE_REDIRECT_URI`
- `DROPBOX_CLIENT_ID`
- `DROPBOX_CLIENT_SECRET`
- `ONEDRIVE_CLIENT_ID`
- `ONEDRIVE_CLIENT_SECRET`

Nota: non sono state modificate `.env` o `.env.local`.

## 13. Modifiche PWA

Durante i blocchi frontend la PWA e stata aggiornata con version bump progressivi. L'ultima versione asset e:

- `APP_VERSION = 10486`
- cache service worker `matchiq-pwa-v86`

I file video non sono stati inseriti nella cache statica del service worker.

## 14. Test eseguiti

Controlli eseguiti durante il rollout:

- compilazione Python su router e servizi video
- controllo sintassi dello script estratto da `frontend/video.html`
- `git diff --check`
- verifica versioni PWA
- verifica che i file fuori scope non entrassero nei commit
- verifica dei path endpoint e riferimenti frontend

## 15. Risultati

Il Video Hub ora copre:

- Sessione Video reale
- Archivio MatchIQ
- upload MP4 dentro sessione
- import URL autorizzato dentro sessione
- provider cloud visibili e sicuri
- modale sessione avanzata
- stati workflow
- filtri e ricerca
- storico attivita sessione
- collegamento stabile con Video AI
- resume dell'ultimo report
- PWA aggiornata

## 16. Limitazioni note

- OAuth cloud reale non e ancora implementato.
- Lo storage cloud proprietario non e ancora attivo.
- I frame non vengono duplicati in metadata sessione per evitare payload pesanti.
- Il resume report dipende dal report cloud o dai dati leggeri salvati nell'ultimo report.
- Test browser/PWA manuali completi vanno ripetuti dopo deploy Railway.
- La separazione frontend in piu file JS dedicati e solo predisposta a livello architetturale: `video.html` resta ancora il contenitore principale della UI Video AI.

## 17. Prossimo provider consigliato

Integrare prima Amazon S3 come storage video proprietario.

Motivo:

- riduce dipendenza da file locali Railway
- prepara video grandi e archivio persistente
- consente URL firmati sicuri
- e piu semplice da controllare rispetto a OAuth consumer

Dopo S3, integrare Google Drive come primo provider utente.

## 18. Stato finale

Il blocco Video Hub e pronto come base architetturale del futuro ecosistema Video AI. Il prossimo lavoro ad alto valore e trasformare il riconoscimento tattico in pipeline piu robusta: classificazione frame, palle inattive distinte, costruzione dal basso, linee suggerite e salvataggio strutturato delle clip/frame selezionate.
