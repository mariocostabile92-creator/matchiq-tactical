# Hardening 1 - API, permessi e checklist E2E

Contratto rimisurato dopo Hardening 2: 161 path OpenAPI, 179 operazioni e 179 operation ID univoci. Route registrate per enforcement: 45 pubbliche, 110 utente, 9 optional/guest-limited, 16 admin.

## Matrice API per famiglia

| Endpoint/famiglia | Metodi | Auth/ruolo | Input principale | Output principale | Consumer | Test/stato |
|---|---|---|---|---|---|---|
| `/api/auth/*` | GET/POST | pubblico o user | credenziali, token, email | token/user/stato | login, register, account | auth test, operativo |
| `/api/payments/*` | GET/POST | user; webhook pubblico firmato | checkout/portal/evento Stripe | URL/stato/ack | account, Stripe | webhook hardening test |
| `/api/health` | GET | pubblico | nessuno | stato servizi | Railway/monitor | HTTP 200 |
| `/api/cache-status`, `/api/clear-cache` | GET/POST | admin | nessuno | stato/ack | admin operativo | test dependency + HTTP negativo |
| `/api/home/*` | GET | user/optional | sessione | riepilogo moduli | Home | HTTP/statico |
| `/api/coach/*`, `/api/coach-track` | GET/POST/PATCH/DELETE | user o guest-limited | match, eventi, report | stato Coach | Coach | suite moduli + manuale |
| `/api/coach-voice/*` | GET/POST | user/optional limitato | testo e contesto match | proposta/tema/ack | Voice Coach | 7 test |
| `/api/video/*`, `/api/video-*` | GET/POST/PATCH/DELETE | user/optional limitato | asset, URL, frame, feedback | job/asset/report/frame | Video AI/Hub | ownership + integrita H2 |
| `/api/scout*` | GET/POST | user/entitlement | ricerca/filtri/player | match/player/report | Scout | statico/manuale |
| `/api/live*`, `/api/match*` | GET/POST | user/optional | match ID/filtri | feed/dettaglio/cache | Match/Home/Scout | route e operation ID univoci |
| `/api/weekly-briefing/*` | GET/POST/PATCH | user | periodo/fonti | briefing/stato | Weekly/Home | 4 test |
| `/api/pattern-intelligence/*` | GET/POST/PATCH | user | fonti/soglie/stato | pattern/evidenze | Pattern/Coach | 7 test |
| `/api/training-planner/*` | GET/POST/PATCH | user | priorita/vincoli | piano/esercizi/storia | Training | 6 test |
| `/api/knowledge/*` | GET/POST/PATCH/DELETE | user | profili/rosa/note | memoria foundation | Knowledge | 2 test |
| `/api/knowledge-intelligence/*` | GET/POST/PATCH | user | sync/query/tag | nodi/edge/versioni | Knowledge/AI | 7 test |
| `/api/tactical-assistant/*` | GET/POST/PATCH/DELETE | user | domanda/conversazione | risposta/fonti/feedback | Assistant | 7 test |
| `/api/tactical-identity/*` | GET/POST/PATCH | user | scope/fonti/feedback | profilo/dimensioni/versioni | Identity | 7 test |
| `/api/decision-engine/*` | GET/POST/PATCH | user | caso/contesto/decisione | opzioni/fonti/esito | Decision | 5 test |
| `/api/club-intelligence/*` | GET/POST/PATCH/DELETE | member/manager/director | club/team/member/resource | overview/snapshot/audit | Club/Account | 11 test |
| `/api/admin/*` | GET/POST/PATCH | admin/owner | filtri e azioni utenti | analytics/utenti/beta | pagine Admin | statico + HTTP auth |
| `/api/beta-request`, `/api/marketing-event` | POST | pubblico | lead/evento | ack | funnel pubblico | statico |

Il dettaglio route-level autorevole resta `/openapi.json`. La maggior parte dell'autorizzazione usa header Bearer gestiti nelle dependency/handler e non viene descritta automaticamente come `security` nello schema OpenAPI: miglioramento P3 consigliato.

## Matrice permessi

| Risorsa | Guest | Free | Pro/Scout | Owner/Admin | Club role |
|---|---|---|---|---|---|
| Home pubblica/parziale | limitata | si | si | si | n/a |
| Coach e Voice | limiti prodotto | si con limiti | entitlement | completo | team context |
| Video AI/Hub | esempio/limite | limite report | entitlement | completo | asset owner |
| Scout/Live | limitato | piano dipendente | Scout/Owner | completo | n/a |
| Knowledge e moduli AI | no | piano dipendente | si | completo | workspace/team |
| Club Intelligence | no | no membership | membro assegnato | admin globale | viewer/staff/manager/director |
| Admin analytics/users/beta | no | no | no | si | n/a |
| Cache amministrativa | no | no | no | si | n/a |

Il frontend nasconde o disabilita le funzioni in base al piano, ma la decisione di sicurezza deve restare backend. Le suite Club verificano revoca, assegnazioni e visibilita squadra.

## Matrice tenant isolation

| Risorsa | Chiave isolamento | Manipolazioni considerate | Evidenza |
|---|---|---|---|
| Profili Knowledge | `user_id`, workspace | ID sequenziale, user B | test ownership |
| Nodi/edge/versioni | workspace/source ownership | query/body alterato | test sync/ownership |
| Pattern | `user_id`, fingerprint | retry/doppio invio | test idempotenza |
| Training | `user_id`, plan ID | open/edit altro utente | test ownership |
| Assistant | `user_id`, conversation ID | rename/archive/delete | test lifecycle |
| Identity | `user_id`, scope | version/feedback altrui | test repository |
| Decision | `user_id`, case ID | direct route | test ownership |
| Club | membership, role, team IDs | hidden team, demotion owner | 11 test |
| Video | `user_id`, asset/report ID e directory | path, URL, stream/delete/write/retry | test ownership, parent consistency e idempotenza |

## Matrice scritture Video Hardening 2

| Operazione | Endpoint | Ownership | Integrita/retry | Stato e test |
|---|---|---|---|---|
| Analisi e report AI | `POST /api/video/analyze` | asset opzionale verificato su `user_id` | chiave idempotenza persistita; UI blocca doppio click | test source + repository |
| Salvataggio report cloud | `POST /api/video/reports` | asset verificato prima dell'insert | replay restituisce lo stesso report | test DB dedicato |
| Feedback frame | `POST /api/video/frame-feedback` | asset e report verificati; parent coerenti | feedback identico deduplicato | test cross-user e deduplica |
| Cancellazione report | `DELETE /api/video/reports/{id}` | delete owner-scoped | elimina i feedback figli dello stesso utente | test cascata applicativa |
| Cancellazione asset | `DELETE /api/video/library/{id}` | lookup e delete owner-scoped | elimina feedback asset e scollega i report | test consistenza riferimenti |
| Upload/import | `POST /api/video/library/upload`, `POST /api/video/library/import` | utente richiesto | limite anti-abuso e controlli URL/file esistenti | test statico + checklist E2E |
| Clip/playlist/collegamenti Pattern | nessuna API di scrittura dedicata rilevata | n/a | nessuna duplicazione possibile nel contratto attuale | non applicabile |

Il limiter applicativo e in memoria per processo. In produzione con piu repliche resta consigliato un rate limiter condiviso al proxy/Redis; la chiave idempotenza dei report resta persistita nel database.

## Checklist E2E ripetibile

### Allenatore

- [ ] Login e refresh pagina interna.
- [ ] Crea partita, salva setup, formazione e panchina.
- [ ] Avvia Match Day, timer, periodo e punteggio.
- [ ] Registra evento e cambio; verifica minuto e nessun doppio invio.
- [ ] Usa Voice Coach con microfono concesso, negato e fallback testo.
- [ ] Pausa/background/ritorno; verifica stato persistente.
- [ ] Genera sintesi intervallo, pagelle e report PDF.
- [ ] Riapri storico e verifica Pattern, Weekly, Training, Knowledge, Assistant, Identity e Decision.

### Match analyst

- [ ] Login utente A, upload video supportato e metadati.
- [ ] Verifica job pending/processing/ready/error e annullamento.
- [ ] Apri frame, salva feedback/linee/clip e genera report.
- [ ] Riapri sessione dal Video Hub.
- [ ] Prova URL autorizzato; rifiuta localhost/rete privata/formato errato/file grande.
- [ ] Login utente B e verifica che asset/report di A non siano accessibili.

### Club

- [ ] Crea club e squadra; assegna membro a una sola squadra.
- [ ] Verifica viewer/staff/manager/director.
- [ ] Verifica filosofia, risorse, overview e snapshot.
- [ ] Rimuovi membro e conferma revoca immediata.
- [ ] Prova URL/ID di club e team non assegnati.

### PWA

- [ ] Installa su desktop e smartphone; verifica icona/start URL.
- [ ] Login, navigazione moduli, background e ritorno.
- [ ] Offline: app shell disponibile, API non cache sensibile.
- [ ] Ritorno online e aggiornamento service worker v115.
- [ ] Logout e cambio utente: nessun dato del precedente account.
- [ ] Microfono/video in PWA e safe-area portrait/landscape.

## Comandi di verifica manuale

```powershell
cd C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8793
```

Aprire poi `http://127.0.0.1:8793/index.html?v=10523`, DevTools Console/Application e completare le checklist dispositivo/provider sopra.

## Contratti frontend Hardening 3

| Contratto | Evidenza | Stato |
|---|---|---|
| Release unica | tutte le query asset `10523` | `fixed_in_hardening_3` |
| Cache PWA unica | `matchiq-pwa-v123` | `fixed_in_hardening_3` |
| Risorse condivise | `app-meta.js` carica componenti, UX e nav | `fixed_in_hardening_3` |
| Navigazione moduli | config riconosce 8 moduli intelligence | `fixed_in_hardening_3` |
| Stati rete | offline, online, ultimo aggiornamento e retry | `fixed_in_hardening_3` |
| Errori runtime | messaggio recuperabile senza stack pubblico | `fixed_in_hardening_3` |
| File sensibili/grandi | PDF, video, audio e CSV non cache runtime | `fixed_in_hardening_3` |
| PDF Coach | finestra di stampa A4 | `verified_static_contract` |
| PDF Video | Blob `application/pdf` e download | `verified_static_contract` |
| PDF Match | `FileResponse` con filename | `verified_static_contract` |
| Browser/device/PWA reale | checklist dedicata | `manual_verification_required` |
