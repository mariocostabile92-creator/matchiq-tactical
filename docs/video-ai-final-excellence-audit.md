# Video AI Final Excellence - Audit iniziale

Data audit: 2026-07-15

## Confini verificati

- Frontend attivo: `frontend/video.html`, `frontend/js/video-intelligence.js`, `frontend/css/video-intelligence.css`.
- API: `app/routers/video_intelligence.py`.
- Pipeline: `app/services/video_intelligence_engine.py`.
- Segmentazione e classificazione prudente: `app/services/video_segmentation_service.py`.
- Ranking frame: `app/services/video_frame_ranking_service.py`.
- Clip: `app/services/video_clip_service.py`.
- Evidenze e review: `app/services/video_evidence_service.py`.
- Report verificabile: `app/services/video_report_service.py`.
- Persistenza e ownership: `app/repositories/video_intelligence_repository.py` e archivio Video Hub esistente.
- Test principali: `tests/test_video_intelligence.py`.

## Capacita reali trovate

- I timestamp arrivano da fotogrammi realmente estratti nel browser dal video caricato.
- La selezione iniziale combina metriche visuali leggere nel browser e, quando disponibile, una selezione AI remota.
- La pipeline backend e idempotente rispetto alla stessa richiesta.
- Le fasi sono proposte in modo prudente a partire da metadati dichiarati; non esiste tracking giocatori o pallone.
- Le clip sono finestre temporali sul video sorgente, non file video generati.
- Frame e intervalli clip possono essere corretti dallo staff.
- Il report usa soltanto evidenze confermate o corrette ed esclude quelle scartate.
- I progetti vengono caricati e salvati con `user_id`, mantenendo l'ownership nel repository.
- Coach Mode e Analysis Mode sono gia separati; i collegamenti Coach restano suggerimenti finche lo staff non li conferma.

## Limiti precedenti allo sprint

- Il ranking frame usa un punteggio semplice e non espone pesi centralizzati, penalita di bordo, esposizione, contrasto o duplicazione.
- Ogni evidenza ha un solo frame rappresentativo; le alternative non sono persistite come gruppo ordinato.
- Il backend riceve soprattutto i frame finali selezionati e perde buona parte del pool di candidati gia estratti nel browser.
- La motivazione del ranking non distingue in modo strutturato contributi positivi e penalita.
- Le clip non conservano separatamente intervallo suggerito e intervallo corretto, quindi manca il ripristino rapido.
- Non esiste una deduplicazione esplicita delle finestre clip quasi identiche.
- La review mostra tutte le schede complete in sequenza e non ha selezione/progresso/scorciatoie controllate.
- Gli errori di frame e clip non espongono ancora uno stato locale con retry mirato.

## Rischi tecnici

- Le metriche visuali del browser sono euristiche: non dimostrano presenza di pallone, giocatori o una fase tattica certa.
- Un pool di soli 4-8 frame limita la qualita delle alternative; occorre inoltrare anche i candidati reali gia campionati.
- Il video resta locale durante l'analisi browser in alcuni flussi; il backend puo validare timestamp e metadati, ma non sempre ricalcolare i pixel.
- OpenCV non e una dipendenza corrente. Lo sprint deve funzionare senza aggiungere una dipendenza pesante obbligatoria.
- Il file `frontend/video.html` contiene ancora parte della logica legacy ed e molto esteso: le modifiche devono restare ancorate e limitate.

## Strategia di consolidamento

1. Inoltrare alla pipeline il pool reale di frame primari e alternativi.
2. Centralizzare metriche, pesi e soglie del ranking deterministico.
3. Persistire 5-9 candidati ordinati quando il pool lo consente, con fallback manuale esplicito.
4. Conservare suggerimento clip, correzione e ripristino senza generare file fittizi.
5. Rendere la review desktop piu rapida mantenendo il workflow e la pagina esistenti.
6. Rafforzare la tracciabilita report-evidenza-frame-clip-timestamp-video.
7. Mantenere PWA di supporto, senza cache di video utente.

## Baseline test

`python -m unittest tests.test_video_intelligence -v`: 23 test superati prima delle modifiche.
