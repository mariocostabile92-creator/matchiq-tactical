# Hardening 1 - API, permessi e checklist E2E

Contratto misurato: 161 path OpenAPI, 179 operazioni. Route registrate per enforcement: 45 pubbliche, 110 utente, 9 optional/guest-limited, 16 admin. La route Live duplicata spiega la differenza di una operazione.

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
| `/api/video/*`, `/api/video-*` | GET/POST/PATCH/DELETE | user/optional limitato | asset, URL, frame, feedback | job/asset/report/frame | Video AI/Hub | statico + hardening |
| `/api/scout*` | GET/POST | user/entitlement | ricerca/filtri/player | match/player/report | Scout | statico/manuale |
| `/api/live*`, `/api/match*` | GET/POST | user/optional | match ID/filtri | feed/dettaglio/cache | Match/Home/Scout | HTTP; duplicato P2 |
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
| Video | `user_id`, asset/report ID e directory | path, URL, stream/delete | statico; gap scrittura P2 |

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
- [ ] Ritorno online e aggiornamento service worker v113.
- [ ] Logout e cambio utente: nessun dato del precedente account.
- [ ] Microfono/video in PWA e safe-area portrait/landscape.

## Comandi di verifica manuale

```powershell
cd C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8793
```

Aprire poi `http://127.0.0.1:8793/index.html?v=10513`, DevTools Console/Application e completare le checklist dispositivo/provider sopra.
