# Environment Reproducibility Audit

Data verifica: 26 luglio 2026

## Ambito

L'intervento riguarda esclusivamente versione Python, dipendenze,
configurazione locale, setup Windows, documentazione e verifica
dell'ambiente. Non sono state modificate logica applicativa, API, database,
AI, frontend, PWA o configurazione Railway.

Commit di partenza:

- `ebf5edd` - `chore: clean repository and document local setup`

## Situazione iniziale

- `runtime.txt` dichiarava gia Python `3.11`.
- Sul computer erano disponibili Python 3.14 e 3.12, ma non Python 3.11.
- `requirements.txt` conteneva dipendenze senza versioni bloccate.
- Runtime web, test e ricerca Vision non avevano lock separati.
- `passlib[bcrypt]` e `bcrypt` erano dichiarati ma non importati dal codice.
- Il progetto usa PBKDF2 dalla libreria standard in `security.py`.
- NumPy e OpenCV erano richiesti dai test e dallo spike Vision, non dal
  runtime web.
- RF-DETR, Torch e TorchVision erano confinati alla ricerca Vision.
- Non erano presenti `pyproject.toml`, `setup.py`, `setup.cfg`, `Procfile`,
  `railway.json` o `Dockerfile`.
- La suite esistente era basata su `unittest`.

## Python adottato

- Versione ufficiale: Python 3.11.
- Versione locale verificata: Python 3.11.9 x64.
- Ambiente pulito: `.venv`, creato con l'interprete 3.11 installato per
  l'utente.
- Versione minima supportata in questa fase: Python 3.11.
- Versione consigliata su Windows: Python 3.11.9, ultimo installer Windows
  pubblicato per la serie 3.11.
- Python 3.12, 3.13 e 3.14 non sono dichiarati supportati finche non vengono
  eseguiti gli stessi controlli.
- Railway puo usare una patch 3.11 successiva disponibile nel runtime, dato
  che `runtime.txt` resta intenzionalmente impostato sulla serie `3.11`.

Python 3.11 e stato scelto per mantenere coerenza con il deploy esistente,
evitare modifiche a Railway e usare una versione verificata con tutte le
dipendenze e i 450 test del repository.

## Strategia delle dipendenze

E stata scelta una struttura `requirements.in` + lock esatti, senza
introdurre Poetry, uv o una dipendenza runtime da pip-tools:

- `requirements.in`: dipendenze runtime dirette e leggibili.
- `requirements.txt`: lock runtime completo e installabile.
- `requirements-dev.in`: sole aggiunte necessarie ai test e allo spike
  Vision leggero.
- `requirements-dev.txt`: runtime bloccato piu NumPy/OpenCV.
- `requirements-vision.in`: ambiente opzionale RF-DETR.
- `requirements-vision.txt`: runtime piu stack Vision pesante.

I file sotto `research/vision_spike/` rimandano ora ai lock canonici nella
root, evitando versioni duplicate e divergenti.

## Dipendenze runtime dirette

| Pacchetto | Versione | Motivo |
| --- | ---: | --- |
| fastapi | 0.140.0 | applicazione e router HTTP |
| uvicorn | 0.51.0 | server ASGI |
| requests | 2.34.2 | integrazioni HTTP |
| python-dotenv | 1.2.2 | caricamento configurazione locale |
| pydantic | 2.13.4 | validazione e schemi |
| stripe | 15.3.1 | pagamenti opzionali |
| reportlab | 5.0.0 | generazione PDF |
| python-jose | 3.5.0 | token JWT |
| python-multipart | 0.0.32 | upload e form FastAPI |
| email-validator | 2.3.0 | validazione indirizzi email |
| psycopg2-binary | 2.9.12 | PostgreSQL |

Le dipendenze transitive sono bloccate in `requirements.txt`. L'installazione
pulita e `pip check` non hanno rilevato conflitti.

## Dipendenze sviluppo e test

- `numpy==2.4.1`
- `opencv-python-headless==4.13.0.92`

Sono necessarie alla suite completa e allo spike Vision leggero. `pytest` e
`psutil` non sono usati dalla suite corrente e non sono stati aggiunti.

## Dipendenze Vision opzionali

- `numpy==2.4.1`
- `rfdetr==1.8.3`
- `torch==2.13.0`
- `torchvision==0.28.0`

Questo ambiente non viene installato per impostazione predefinita. La
risoluzione con pip e stata verificata in modalita `--dry-run`. RF-DETR porta
le proprie dipendenze transitive, incluso lo stack OpenCV richiesto dalla
ricerca, senza contaminare il runtime web.

## Dipendenze aggiunte o rimosse

Non sono state introdotte nuove dipendenze funzionali nel runtime. Sono state
rese esplicite e bloccate le dipendenze gia richieste dal codice.

Rimosse dal runtime:

- `passlib[bcrypt]`
- `bcrypt`

La rimozione e motivata dall'assenza di import, caricamenti dinamici e uso nei
test o all'avvio. L'autenticazione corrente usa PBKDF2 dalla libreria standard.

Separate dal runtime:

- NumPy e OpenCV: sviluppo/test.
- RF-DETR, Torch e TorchVision: ricerca Vision opzionale.

## Variabili di ambiente individuate

Le variabili realmente lette dal codice sono state organizzate in
`.env.example`, senza segreti:

- applicazione e database: `APP_PUBLIC_URL`, `APP_BASE_URL`,
  `CORS_ORIGINS`, `DATABASE_URL`, `PORT`;
- autenticazione e sicurezza: `JWT_SECRET_KEY`, `JWT_SECRET_FILE`,
  `SECRET_KEY`, `OWNER_EMAILS`, `ADMIN_EMAILS`,
  `PASSWORD_RESET_TOKEN_MINUTES`, `EMAIL_VERIFICATION_TOKEN_MINUTES`,
  `PASSWORD_RESET_EXPOSE_LINK`, `EMAIL_VERIFICATION_EXPOSE_LINK`,
  `EMAIL_VERIFICATION_LOGIN_BLOCK`, `TRUST_PROXY_HEADERS`,
  `ADMIN_API_TOKEN`;
- email: `BREVO_API_KEY`, `EMAIL_FROM`, `EMAIL_FROM_NAME`;
- AI: `OPENAI_API_KEY`, `OPENAI_API_URL`, `OPENAI_VIDEO_MODEL`,
  `OPENAI_TACTICAL_ASSISTANT_MODEL`;
- dati calcio: `API_FOOTBALL_KEY`;
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_YEARLY`;
- runtime: `BACKGROUND_REFRESH_MAX_WORKERS`, `SCOUT_PUBLIC_BETA`,
  `PDF_PUBLIC_BETA`;
- Video AI: `VIDEO_REPORT_MAX_FRAMES`, `VIDEO_SELECTION_MAX_FRAMES`,
  `VIDEO_REPORT_MAX_FRAME_CHARS`, `VIDEO_LIBRARY_DIR`,
  `VIDEO_STORAGE_BACKEND`, `VIDEO_LIBRARY_MAX_UPLOAD_MB`,
  `VIDEO_IMPORT_TIMEOUT_SECONDS`, `VIDEO_IMPORT_MAX_REDIRECTS`,
  `VIDEO_HALFTIME_BETA_ENABLED`, `VIDEO_HALFTIME_BETA_USER_IDS`,
  `VIDEO_HALFTIME_BETA_EMAILS`;
- cloud opzionale: credenziali Google Drive, Dropbox, OneDrive e AWS;
- ricerca Vision: `MATCHIQ_V3_DATASET`.

`DATABASE_URL` puo essere vuota in locale per SQLite, ma deve puntare a
PostgreSQL in produzione. `JWT_SECRET_KEY` deve essere stabile e di almeno 32
caratteri in produzione.

## File creati

- `requirements.in`
- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements-vision.in`
- `requirements-vision.txt`
- `scripts/check_environment.py`
- `scripts/setup_windows.ps1`
- `README.md`
- `docs/environment-reproducibility-audit.md`

## File modificati

- `requirements.txt`
- `.env.example`
- `research/vision_spike/requirements.txt`
- `research/vision_spike/requirements-rfdetr.txt`

## Comandi principali eseguiti

```powershell
py -3.11 -m venv .venv
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -Dev
.\.venv\Scripts\python.exe .\scripts\check_environment.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip install --use-feature=truststore --dry-run -r requirements-vision.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8793
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

L'installazione pip su questo computer usa il certificate store di Windows
tramite `--use-feature=truststore`. Non e stata disabilitata la verifica TLS.

## Risultati

### Setup pulito

- `.venv` creata da zero con Python 3.11.9.
- Installate esclusivamente le dipendenze dichiarate in
  `requirements-dev.txt`.
- `pip check`: `No broken requirements found`.
- Lock Vision: risoluzione simulata completata senza conflitti.

### Check ambiente

- Python, directory, percorsi e import runtime: validi.
- Import FastAPI: riuscito senza inizializzare database o servizi.
- Esito: 0 errori.
- Warning: integrazioni Vision pesanti non installate, `JWT_SECRET_KEY` e
  `DATABASE_URL` non configurate nel processo locale.

Questi warning sono previsti: RF-DETR e Torch sono opzionali; segreti e
database di produzione non devono essere inseriti nel repository.

### Avvio e health check

- Backend avviato realmente con Uvicorn su `127.0.0.1:8793`.
- `GET /api/health`: HTTP valido, risposta `status: healthy`.
- Database: `online`.
- Processo arrestato al termine.
- Database SQLite e segreto locali generati durante i controlli: rimossi.

### Suite automatica

Prima esecuzione:

- 450 test eseguiti.
- 450 superati.
- 0 fallimenti.
- 0 errori.
- durata: 45.415 secondi.

Seconda esecuzione:

- 450 test eseguiti.
- 450 superati.
- 0 fallimenti.
- 0 errori.
- durata: 23.176 secondi.

Nessun test e stato disabilitato o saltato per ottenere il risultato.

## Warning residui

- I test esercitano intenzionalmente errori Stripe, argomenti CLI Vision
  mancanti e file video MP4 non valido; i messaggi compaiono nei log ma la
  suite termina correttamente.
- Alcuni test modificano temporaneamente le variabili JWT per verificare il
  fallback locale e producono il relativo warning di sicurezza.
- RF-DETR/Torch/TorchVision non sono stati installati, per evitare diversi GB
  non necessari al runtime. La loro risoluzione e stata verificata senza
  installazione.
- Su Windows pip ha richiesto il trust store di sistema per la catena TLS.

## Differenze rispetto a Railway

- Locale: Python 3.11.9 e SQLite quando `DATABASE_URL` e vuota.
- Railway: serie Python 3.11 dichiarata da `runtime.txt`, PostgreSQL tramite
  `DATABASE_URL`, segreti e integrazioni configurati nelle variabili Railway.
- Nessuna variabile Railway e stata letta o modificata.
- Nessuna configurazione di deploy funzionante e stata alterata.

## Conferme finali

- Nessuna logica funzionale e stata modificata.
- Nessun endpoint o contratto API e stato modificato.
- Nessuno schema o contenuto database e stato modificato.
- Nessuna logica AI, pagina frontend o PWA e stata modificata.
- Nessun test e stato saltato.
- Nessun commit e stato creato.
- Nessun push e stato eseguito.
- `social-assets/` e rimasta intatta.
