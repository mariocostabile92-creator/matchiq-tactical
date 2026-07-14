# MatchIQ Hardening 1 - Bug Backlog

Ordinamento: P0, P1, P2, P3. Gli elementi non critici non sono stati corretti nello sprint.

## H1-001 - Webhook Stripe accettava payload non firmati

- Modulo: Payments
- Severita: P0
- Descrizione/riproduzione: rimuovere `STRIPE_WEBHOOK_SECRET` e inviare JSON a `/api/payments/webhook`; prima veniva costruito un evento senza verifica firma.
- Impatto: un attaccante poteva simulare eventi economici.
- Causa: fallback permissivo quando il secret mancava.
- File: `payments.py`
- Fix: fail-closed 503, firma obbligatoria, errore generico.
- Test: tre casi webhook in `tests/test_hardening_security.py`.
- Stato: `fixed_in_hardening_1`

## H1-002 - Cache amministrativa pubblica

- Modulo: System/Admin
- Severita: P0
- Descrizione/riproduzione: chiamare `POST /api/clear-cache` senza credenziali.
- Impatto: operazione distruttiva/cache invalidation non autorizzata.
- Causa: route senza dependency admin.
- File: `app/routers/system.py`, `main.py`
- Fix: dependency `require_admin_token` su status e clear.
- Test: dependency inspection e HTTP negativo.
- Stato: `fixed_in_hardening_1`

## H1-003 - Secret JWT hardcoded

- Modulo: Auth/Security
- Severita: P1
- Descrizione/riproduzione: leggere la costante condivisa in `security.py`.
- Impatto: token falsificabili conoscendo il sorgente.
- Causa: secret di sviluppo rimasto in produzione.
- File: `security.py`, `.gitignore`
- Fix: secret da ambiente o fallback locale forte persistito.
- Test: priorita ambiente, robustezza e persistenza.
- Stato: `fixed_in_hardening_1`

## H1-004 - Link sensibili esposti per default

- Modulo: Auth/Admin Users
- Severita: P1
- Descrizione/riproduzione: richiedere reset/verifica senza configurare le flag di esposizione.
- Impatto: token monouso potevano comparire nella risposta client.
- Causa: default di sviluppo impostato a `1`.
- File: `auth.py`, `app/routers/admin_users.py`
- Fix: default fail-closed `0`.
- Test: controllo delle configurazioni di default.
- Stato: `fixed_in_hardening_1`

## H1-005 - Stato browser sensibile sopravviveva a logout/cambio account

- Modulo: Auth/PWA
- Severita: P1
- Descrizione/riproduzione: salvare dati `matchiq_*`, fare logout o login con altro account e ispezionare storage.
- Impatto: dati del precedente utente potevano restare nel dispositivo.
- Causa: logout cancellava solo cinque chiavi auth.
- File: `frontend/js/auth.js`, pagine login/register/account e PWA.
- Fix: pulizia centralizzata localStorage/sessionStorage per chiavi MatchIQ e auth generiche.
- Test: source contract + test login/sessione + cache release corrente 10520.
- Stato: `fixed_in_hardening_1`

## H1-006 - Route Live e operation ID duplicati

- Modulo: Live/OpenAPI
- Severita: P2
- Riproduzione: generare OpenAPI; compare warning per `api_scout_live_alias` e `GET /api/scout-live` risulta registrata due volte.
- Impatto: client generation ambigua e manutenzione fragile; runtime non bloccato.
- Causa: alias definito in `main.py` e `app/routers/live.py`.
- File: `main.py`, `app/routers/live.py`
- Fix: mantenuta la sola route canonica del router Live; rimosso l'alias duplicato in `main.py`.
- Test: contratto OpenAPI con singolo GET e 179 operation ID univoci.
- Stato: `fixed_in_hardening_2`

## H1-007 - Ownership asset Video non validata esplicitamente in tutte le scritture

- Modulo: Video AI/Hub
- Severita: P2
- Riproduzione: inviare un `video_asset_id` altrui in payload feedback/report.
- Impatto: possibile collegamento di metadati incoerente; le letture restano filtrate per utente, nessuna esposizione confermata.
- Causa: alcuni flussi validano ownership in lettura ma non prima di ogni insert correlato.
- File: `app/routers/video.py`, `app/services/video_hub.py`, repository video.
- Fix: lookup owner-scoped obbligatorio per analisi/report/feedback, verifica parent asset-report e pulizia figli in cancellazione.
- Test: utente A/B, parent incoerente, delete asset/report e deduplica feedback.
- Stato: `fixed_in_hardening_2`

## H1-008 - Login/reset senza rate limit dedicato

- Modulo: Auth
- Severita: P2
- Riproduzione: inviare richieste ripetute a login/reset.
- Impatto: brute force, abuso email e carico.
- Causa: nessun limiter persistente rilevato.
- File: `auth.py`, configurazione proxy/Railway.
- Fix: limiter IP+identita su auth/reset/verifica e sugli endpoint costosi/sensibili; `Retry-After` e proxy header opt-in validato.
- Test: soglia, identita separata, reset finestra, proxy header valido/non valido.
- Stato: `fixed_in_hardening_2` (limiter condiviso tra repliche consigliato)

## H1-009 - Dettagli eccezione esposti in alcune API

- Modulo: Payments/Admin
- Severita: P2
- Riproduzione: provocare errori Stripe/DB autenticati e leggere `detail`.
- Impatto: possibili informazioni interne/provider esposte.
- Causa: `detail=str(e)` e messaggi Stripe interpolati.
- File: `payments.py`, `app/routers/admin_analytics.py`, `app/routers/admin_users.py`.
- Fix: messaggi pubblici generici; dettagli tecnici conservati solo nei log server.
- Test: source contract su Payments e router Admin.
- Stato: `fixed_in_hardening_2`

## H1-010 - Audit XSS da completare sulle renderizzazioni HTML dinamiche

- Modulo: Frontend globale
- Severita: P2
- Riproduzione: inserire payload HTML nei campi provenienti da API/user input e aprire viste che usano `innerHTML`.
- Impatto: XSS se un nuovo campo bypassa le funzioni escape.
- Causa: ampio uso storico di template HTML; molte aree usano escape, copertura non completa.
- File: `frontend/video.html`, Admin, Coach render, render moduli AI.
- Fix: utility condivisa escape/sanitize/safe URL e conversione dei sink dinamici ad alto rischio in Tactical Assistant, API error e Coach report.
- Test: payload script, URL `javascript:`/`data:` e contratto renderer.
- Stato: `fixed_in_hardening_2_core` (migrazione sink legacy continua)

## H1-011 - Router/pagina Video ad alta complessita

- Modulo: Video AI/Hub
- Severita: P2
- Riproduzione: manutenzione o profiling di `video.html` e router Video.
- Impatto: regressioni, parsing/avvio frontend piu costoso e test difficili.
- Causa: evoluzione incrementale in file molto grandi.
- File: `frontend/video.html`, `app/routers/video.py`.
- Fix consigliato: hardening successivo con estrazione per responsabilita e test prima di ogni spostamento.
- Test richiesto: snapshot DOM, contratti API e upload/report E2E.
- Stato: `open`

## H1-012 - PostgreSQL/Railway e provider esterni non verificati E2E localmente

- Modulo: Deploy/DB/Provider
- Severita: P2
- Riproduzione: non disponibile senza ambiente staging e credenziali.
- Impatto: differenze dialect, timeout o configurazione possono emergere solo in staging.
- Causa: limite runtime audit locale.
- File: configurazione Railway, `database.py`, provider.
- Fix consigliato: staging con PostgreSQL, smoke test post-deploy e test webhook/provider sandbox.
- Test richiesto: checklist E2E documentata.
- Stato: `open`

## H1-013 - ID HTML duplicati in Match

- Modulo: Match frontend
- Severita: P3
- Riproduzione: scansione DOM di `match.html`.
- Impatto: selettori possono aggiornare il nodo sbagliato.
- Causa: toolbar nuova e azioni legacy convivono.
- File: `frontend/match.html`
- Fix: rinominati gli ID del template legacy senza alterare il blocco visibile.
- Test: parser HTML verifica unicita ID.
- Stato: `fixed_in_hardening_2`

## H1-014 - File auth frontend legacy non referenziato

- Modulo: Frontend/Auth
- Severita: P3
- Riproduzione: cercare riferimenti a `frontend/auth.js`; le pagine usano `frontend/js/auth.js`.
- Impatto: confusione e rischio di correggere il file sbagliato.
- Causa: migrazione incompleta.
- File: `frontend/auth.js`.
- Fix consigliato: confermare con access log/build e rimuovere in commit dedicato.
- Test richiesto: navigazione auth completa e scansione asset.
- Stato: `open`

## H1-015 - Contratti auth non descritti nello schema OpenAPI

- Modulo: API/OpenAPI
- Severita: P3
- Riproduzione: ispezionare `security` in `/openapi.json`.
- Impatto: documentazione/client generation non mostrano chiaramente i requisiti Bearer.
- Causa: header/dependency custom senza security scheme OpenAPI uniforme.
- File: auth dependencies e router.
- Fix consigliato: `HTTPBearer` centralizzato mantenendo compatibilita.
- Test richiesto: schema security per route user/admin.
- Stato: `open`

## H1-016 - Test browser/PWA/dispositivo ancora manuali

- Modulo: Frontend/PWA/Voice/Video/PDF
- Severita: P3
- Riproduzione: richiede browser e dispositivo reale.
- Impatto: regressioni visuali, permessi microfono e offline non rilevate da unittest.
- Causa: assenza di suite Playwright/device farm nel runtime.
- File: checklist `docs/hardening-1-api-contract-matrix.md`.
- Fix consigliato: Playwright smoke test e matrice dispositivo minima.
- Test richiesto: desktop/tablet/mobile/PWA, console senza errori bloccanti.
- Stato: `open`

## H1-017 - Uso di `datetime.utcnow()` deprecato

- Modulo: Auth/tempo
- Severita: P3
- Riproduzione: eseguire la suite con Python 3.11; compare un `DeprecationWarning` durante la creazione token.
- Impatto: nessun blocco attuale, ma incompatibilita futura e date naive.
- Causa: API datetime legacy.
- File: `security.py` e altri punti data/ora da censire.
- Fix consigliato: migrare in blocco dedicato a datetime UTC timezone-aware, verificando serializzazione e PostgreSQL.
- Test richiesto: scadenza token e confronti timestamp SQLite/PostgreSQL.
- Stato: `open`

## H3-001 - Navigazione e versione non uniformi tra moduli

- Modulo: Frontend globale/PWA
- Severita: P1
- Impatto: orientamento incoerente e cache di release diverse.
- Fix: riconoscimento moduli centralizzato, release `10520`, cache `v120`.
- Test: versione unica, asset esistenti e configurazione moduli.
- Stato: `fixed_in_hardening_3`

## H3-002 - Stati offline ed errori non omogenei

- Modulo: Frontend globale
- Severita: P1
- Impatto: pagina apparentemente bloccata e nessun recupero chiaro.
- Fix: banner condiviso, ultimo aggiornamento, retry e messaggio runtime recuperabile.
- Test: contratto statico piu checklist offline/online.
- Stato: `fixed_in_hardening_3`

## H3-003 - Tabelle, dialog e touch target fragili su schermi piccoli

- Modulo: Frontend responsive
- Severita: P2
- Impatto: dati tagliati o comandi difficili da usare su tablet/PWA.
- Fix: wrapper tabelle, dialog viewport-safe, focus e touch target condivisi.
- Test: parser/statico; verifica visuale device ancora necessaria.
- Stato: `manual_verification_required`

## H3-004 - Cache PWA poteva includere export e media grandi

- Modulo: PWA/Storage browser
- Severita: P1
- Impatto: spazio occupato, dati non necessari offline e aggiornamenti fragili.
- Fix: allowlist asset statici; esclusi PDF, video, audio e CSV.
- Test: contratto service worker.
- Stato: `fixed_in_hardening_3`

## H3-005 - Copertura visuale automatica assente

- Modulo: QA frontend
- Severita: P2
- Impatto: regressioni layout rilevabili solo manualmente.
- Fix consigliato: Playwright con screenshot desktop/tablet/mobile e PWA smoke.
- Test richiesto: matrice in `docs/hardening-3-manual-visual-checklist.md`.
- Stato: `open`
