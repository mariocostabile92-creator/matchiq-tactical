# MatchIQ - Demo readiness checklist

Release demo: `10518`

## Preparazione prima della chiamata

- [ ] Railway mostra deployment riuscito e health online.
- [ ] Hard refresh eseguito; PWA aggiornata a cache `v115`.
- [ ] Account demo verificato con piano e dati coerenti.
- [ ] Una partita Coach completa gia disponibile.
- [ ] Un video breve, autorizzato e gia analizzato disponibile.
- [ ] Uno scout report e una sessione club disponibili.
- [ ] PDF Coach, Video e Scout aperti almeno una volta.
- [ ] Microfono verificato; fallback testo pronto.
- [ ] Nessun errore bloccante in console.
- [ ] Connessione secondaria disponibile.

## Percorso demo consigliato

| Ordine | Pagina | Messaggio da dimostrare | Azione breve |
|---:|---|---|---|
| 1 | Home | Un solo ecosistema per staff dilettantistico | mostra moduli e piano |
| 2 | Coach | Meno inserimenti, piu memoria e decisioni | evento, Voice Coach, sintesi |
| 3 | Video AI | Dal video a frame, linee e report | apri sessione gia pronta |
| 4 | Scout | Osservazione live e shortlist | apri player e PDF |
| 5 | Weekly/Pattern | I dati diventano conoscenza ricorrente | apri briefing e pattern |
| 6 | Training | L'analisi diventa lavoro sul campo | apri piano salvato |
| 7 | Assistant/Decision | Supporto motivato, non automazione cieca | mostra fonti e opzioni |
| 8 | Club | Visione aggregata per societa | overview, squadra, ruoli |
| 9 | Account | Piano, accessi e controllo utente | mostra stato account |

## Test cinque minuti prima

- [ ] Login e refresh su una pagina interna.
- [ ] Home, Coach, Video, Scout e Account rispondono.
- [ ] Archivio Video e storico Coach si aprono.
- [ ] Un PDF viene generato o scaricato.
- [ ] Offline banner compare staccando la rete e sparisce al ritorno.
- [ ] Navigazione mobile apribile a 390 px.

## Piano B

- Video AI lento: aprire una sessione gia pronta e il PDF salvato.
- Microfono negato: usare il comando testuale nello stesso pannello.
- Provider live non disponibile: usare dati salvati e dichiararlo.
- Railway instabile: usare PWA/app shell e PDF locali, senza simulare dati nuovi.
- Connessione assente: mostrare le viste gia caricate; non promettere chiamate API offline.
- PDF popup bloccato: consentire popup o usare il file gia preparato.

## Chiusura demo

- [ ] Ribadire che l'AI e supporto decisionale verificato dallo staff.
- [ ] Chiedere quale flusso fa perdere piu tempo oggi.
- [ ] Concordare prova pilota, squadra, referente e prossima verifica.
