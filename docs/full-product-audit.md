# MatchIQ Tactical - Hardening 1 Full Product Audit

Data audit: 2026-07-13

Scope: repository `backend`, frontend attivo `backend/frontend`

Principi: MatchIQ non inventa, MatchIQ motiva. L'allenatore decide sempre, l'AI suggerisce sempre.

## 1. Stato iniziale e confini

- Worktree iniziale non pulito: `app/routers/coach_tracking.py` modificato e `social-assets/` non tracciata.
- I due elementi preesistenti sono stati esclusi da modifiche, staging e commit Hardening 1.
- Nessuna macro-feature, modifica prezzi, redesign o integrazione esterna aggiunta.
- Il frontend esterno non e stato toccato.

## 2. Inventario verificato

| Area | Evidenza |
|---|---:|
| OpenAPI | 161 path, 179 operazioni |
| Metodi API | 96 GET, 61 POST, 12 PATCH, 6 DELETE, 4 PUT |
| Router applicativi | 20 file router inclusi `__init__.py` |
| File Python in `app` | 114 |
| Tabelle SQLite inizializzate | 57 |
| Indici SQLite | 69 |
| Pagine HTML frontend | 27 |
| JavaScript frontend | 107 |
| CSS frontend | 24 |
| Test automatici dopo Hardening 2 | 89 |

Moduli mappati: Home, Auth, Account, Admin, Coach, Match Day, Voice Coach, Video AI/Hub, Scout, Live/Match, Weekly Briefing, Pattern Intelligence, Training Planner, Knowledge Foundation/Intelligence, Tactical Assistant, Tactical Identity, Decision Engine, Club Intelligence, pagamenti, PDF/export e PWA.

## 3. Avvio, import e deploy

| Controllo | Risultato |
|---|---|
| Python 3.11 | verificato |
| Compilazione Python | passata |
| Import `main.app` | passato |
| Generazione OpenAPI | passata; 179 operation ID univoci |
| Avvio Uvicorn locale | passato |
| Health check | HTTP 200 |
| 23 route/asset core | 23/23 HTTP 200 |
| Tempo HTTP massimo nel controllo locale | 1833 ms |
| Start command Railway | `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}` |

La duplicazione di `GET /api/scout-live` e stata rimossa in Hardening 2. Il contratto OpenAPI mantiene 161 path e 179 operazioni, tutte con operation ID univoco.

Variabili sensibili attese: database, OpenAI, Stripe, email, admin e JWT. I nomi sono stati verificati senza leggere o pubblicare valori. Per Railway e obbligatorio configurare un `JWT_SECRET_KEY` stabile di almeno 32 caratteri.

## 4. Database e persistenza

- Inizializzazione SQLite completata: 57 tabelle e 69 indici.
- 53 tabelle dichiarano almeno una foreign key.
- Senza foreign key dichiarata: `users`, `training_exercises`, `marketing_events`, `club_intelligence_clubs`; sono entita radice o cataloghi, ma resta consigliato un riesame P2 delle relazioni applicative.
- Le suite verificano persistenza, idempotenza, ownership e versioning per Knowledge, Weekly, Pattern, Training, Tactical Assistant, Tactical Identity, Decision Engine e Club Intelligence.
- Il runtime PostgreSQL/Railway non era disponibile nel test locale. La compatibilita PostgreSQL e stata analizzata staticamente e coperta in parte dai test schema, ma non dichiarata come E2E superata.

Tabelle principali: `users`, `subscriptions`, `saved_matches`, `saved_players`, `scout_reports`, `video_assets`, `video_reports`, `video_frame_feedback`, `weekly_ai_briefings`, `pattern_intelligence_*`, `training_plans`, `knowledge_*`, `tactical_assistant_*`, `tactical_identity_*`, `decision_engine_*`, `club_intelligence_*`, `voice_coach_*`.

## 5. Autenticazione e sicurezza

Contratto OpenAPI finale: 161 path, 179 operazioni e 179 operation ID univoci. La route Live duplicata e stata rimossa, lasciando un solo endpoint canonico.

Correzioni applicate:

1. Webhook Stripe fail-closed: senza secret risponde 503; senza firma o con firma non valida risponde 400; nessun payload unsigned viene elaborato.
2. Rimosso il secret JWT hardcoded. Priorita: `JWT_SECRET_KEY`, poi `SECRET_KEY`, poi secret locale forte persistito e ignorato da Git.
3. Link di reset password e verifica email non vengono piu esposti per default nelle risposte API.
4. Logout e cambio account eliminano tutte le chiavi `matchiq_*` e le chiavi auth generiche da localStorage e sessionStorage.
5. `GET /api/cache-status` e `POST /api/clear-cache` richiedono ora autorizzazione admin.
6. Rimosso il prefisso della chiave Stripe dalla risposta pubblica di stato.

Secret scan sui file tracciati: nessun `sk_live_`, `sk_test_`, `whsec_`, chiave OpenAI assegnata o vecchio secret JWT trovato. `.env`, database e secret locali non sono tracciati.

CORS: lista esplicita di origini, non wildcard. CSRF non applicabile ai flussi principali basati su Bearer token. Hardening 2 aggiunge rate limit IP+identita ad auth/reset/verifica, Video AI, Tactical Assistant, Decision Engine e azioni Admin sensibili. Il limiter e locale al processo: per piu repliche Railway e raccomandato un backend condiviso.

## 6. Permessi e tenant isolation

| Ambito | Enforcement verificato | Test automatico |
|---|---|---|
| Utente e sessione | token, utente attivo, ownership | si |
| Knowledge | `user_id`/workspace e ownership | si |
| Weekly | ownership briefing | si |
| Pattern | ownership, deduplica, fonti | si |
| Training Planner | ownership e storia | si |
| Tactical Assistant | conversazioni/fonti isolate | si |
| Tactical Identity | profilo/versioni isolate | si |
| Decision Engine | casi persistenti e owned | si |
| Club Intelligence | membership, ruolo, team visibility | si |
| Video Hub | directory, asset, report e feedback user-scoped | test cross-user, parent e cancellazione |
| Admin | dependency admin/backend | statico + HTTP negativo |

Non sono emerse letture cross-tenant P0 nelle suite. Le scritture report/feedback Video validano ora asset e report owner-scoped e rifiutano parent incoerenti.

## 7. Audit moduli prodotto

| Modulo | Route/pagina | Persistenza/API | Copertura | Stato |
|---|---|---|---|---|
| Home | `/index.html`, `/api/home/*` | aggregazione moduli | HTTP + statico | operativo |
| Coach/Match Day | `/coach.html`, coach APIs | match/eventi/report | suite Voice + statico | operativo, E2E browser manuale |
| Voice Coach | `/api/coach-voice/*` | osservazioni/temi | 7 test | operativo |
| Video AI/Hub | `/video.html`, `/api/video-*` | asset/frame/report | HTTP + security statico | operativo, upload reale manuale |
| Scout | `/scout.html`, Scout APIs | saved players/report | HTTP + statico | operativo |
| Live/Match | `/match.html`, `/api/live*`, `/api/match*` | cache/provider | route/OpenAPI + statico | operativo |
| Weekly | `/weekly-briefing.html` | briefing/fingerprint | 4 test | operativo |
| Pattern | `/pattern-intelligence.html` | pattern/evidence/run | 7 test | operativo |
| Training | `/training-planner.html` | piano/storia/libreria | 6 test | operativo |
| Knowledge | `/knowledge.html` | nodi/edge/versioni | 9 test complessivi | operativo |
| Tactical Assistant | `/tactical-assistant.html` | conversazioni/fonti | 7 test | operativo |
| Tactical Identity | `/tactical-identity.html` | dimensioni/versioni | 7 test | operativo |
| Decision Engine | `/decision-engine.html` | casi/opzioni/esiti | 5 test | operativo |
| Club Intelligence | `/club-intelligence.html` | club/team/membership | 11 test | operativo |
| Auth/Account/Admin | pagine dedicate | utenti/piani/admin | auth + HTTP | operativo |

Le suite confermano: Weekly non rigenera senza cambi, Pattern deduplica, Training persiste proposta originale e modifiche, Knowledge e idempotente, Tactical Assistant usa retrieval e non inventa senza dati, Identity separa dichiarato/osservato, Decision Engine non esegue azioni automatiche, Club Intelligence applica membership e visibilita team.

## 8. Video, file e upload

- Estensioni e dimensioni sono validate.
- Percorsi asset sono user-scoped e protetti da traversal.
- Import URL blocca localhost, reti private, redirect non sicuri, contenuti non video e download oltre limite.
- Stream, dettaglio e cancellazione filtrano per proprietario.
- Report e feedback verificano ownership prima della scrittura; un asset e un report collegati devono appartenere alla stessa sessione.
- Retry dello stesso report usa una chiave idempotente persistita; feedback identici vengono deduplicati.
- La cancellazione di report/asset rimuove i feedback figli e scollega in modo esplicito i report dall'asset eliminato.
- Mancano test E2E locali con file video grande, rete interrotta e provider storage remoto; checklist manuale allegata.

## 9. PWA

- Manifest valido, scope `/`, display standalone e start URL aggiornato a `10515`.
- Cache aggiornata a `matchiq-pwa-v115`.
- API non vengono salvate nell'app shell.
- Il service worker elimina cache storiche e usa network-first per navigazioni/asset same-origin.
- Logout/cambio utente puliscono cache applicativa sensibile lato storage browser.
- Nessun asset locale mancante nella scansione statica.
- Installazione, offline/online, background, microfono e cambio utente in due tab richiedono test manuale su dispositivo reale.

## 10. Frontend globale

- Tutti i 107 file JavaScript hanno superato `node --check`.
- Nessun riferimento locale statico letterale mancante nella scansione. Quattro riferimenti `${...}` sono template JavaScript dinamici e non asset filesystem.
- Dieci chiamate API letterali frontend verificate senza endpoint orfani; le URL dinamiche non sono completamente dimostrabili con sola analisi statica.
- `match.html` non contiene piu ID duplicati; il controllo e coperto da test.
- `frontend/auth.js` top-level appare legacy e non referenziato; non eliminato in questo hardening.
- Hardening 2 introduce `frontend/js/safe-render.js`, URL allowlist e rendering DOM/testuale nei flussi dinamici Tactical Assistant, API error e Coach report. Resta consigliato continuare la migrazione dei sink legacy non inclusi nel perimetro ad alto rischio.

## 11. PDF, export e performance

PDF/export sono presenti in Coach, Video, Scout e Training. I test locali verificano logica e persistenza, non la resa visiva di ogni PDF su browser/mobile. Nessun flusso P1 rotto e stato riprodotto.

Misure locali:

- startup Uvicorn completato;
- 23/23 route core HTTP 200;
- massimo 1833 ms nel giro locale iniziale, inclusa inizializzazione lazy;
- nessun profiling PostgreSQL/provider esterno disponibile;
- `video.html` e router Video sono grandi e ad alto costo di manutenzione: P2, nessun refactoring generale in Hardening 1.

## 12. Test eseguiti

- `python -m unittest discover -s tests -v`: 97 test, tutti passati.
- Test nuovi Hardening 2: 14, tutti passati.
- Test nuovi Hardening 3: 8, tutti passati.
- `python -m compileall`: passato.
- Import FastAPI e OpenAPI: passati.
- Uvicorn + health + 23 pagine/asset core: passati.
- `node --check` su JavaScript: passato.
- Controllo asset HTML, ID duplicati, secret e Git diff: eseguito.
- `pytest`: non disponibile nell'ambiente; la suite usa `unittest`.

## 13. Limitazioni dichiarate

Non verificati come E2E reali in questo runtime: PostgreSQL Railway, deploy Railway, Stripe reale, OpenAI reale, API-Football reale, email reale, microfono, video grande, installazione PWA e console browser multipiattaforma. Questi controlli sono nella checklist manuale e non vengono dichiarati superati.

## 14. Esito

P0 trovati e corretti: 2. P1 trovati e corretti: 3. Hardening 2 chiude inoltre route duplicate, ownership Video in scrittura, rate limiting applicativo, errori pubblici grezzi, ID Match duplicati e i sink XSS ad alto rischio inclusi nel perimetro. I residui P2/P3 e i limiti di staging/dispositivo restano registrati nel backlog.

## 15. Hardening 3 - UX, PWA, PDF e demo readiness

- Release frontend unica portata a `10515`; cache PWA portata a `matchiq-pwa-v115`.
- Navigazione condivisa estesa al riconoscimento di tutti i moduli operativi.
- Stati offline, errore recuperabile e retry centralizzati senza cambiare API o logica prodotto.
- Focus, touch target, tabelle, dialog, safe-area, tastiera virtuale e reduced motion consolidati nel layer CSS condiviso.
- Immagini impostate lazy e video su metadata; PDF, video, audio e CSV esclusi dalla cache runtime PWA.
- Contratti PDF esistenti di Coach, Video e Match preservati e coperti da test statici.
- Inventario di 27 pagine, checklist visuale/device e scaletta demo aggiunti in `docs/`.
- Stato browser/dispositivo reale: `manual_verification_required`; nessun esito visivo non eseguito viene dichiarato passato.
