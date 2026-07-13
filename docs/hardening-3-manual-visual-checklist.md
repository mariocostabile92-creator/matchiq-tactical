# Hardening 3 - Checklist visuale e PWA

Release da verificare: `10516`

## Viewport

| Dispositivo | Viewport | Home | Coach | Video | Scout | Moduli AI | Admin | Esito |
|---|---:|---|---|---|---|---|---|---|
| Desktop largo | 1920x1080 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | manuale |
| Desktop | 1366x768 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | manuale |
| Tablet landscape | 1024x768 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | manuale |
| Tablet portrait | 768x1024 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | manuale |
| Smartphone grande | 430x932 | [ ] | [ ] | [ ] | [ ] | [ ] | n/a | manuale |
| Smartphone | 390x844 | [ ] | [ ] | [ ] | [ ] | [ ] | n/a | manuale |
| Smartphone compatto | 360x800 | [ ] | [ ] | [ ] | [ ] | [ ] | n/a | manuale |
| PWA installata | dispositivo reale | [ ] | [ ] | [ ] | [ ] | [ ] | n/a | manuale |

## Controlli per ogni pagina

- [ ] Nessuna sovrapposizione o testo tagliato.
- [ ] Header e navigazione restano utilizzabili.
- [ ] Footer raggiungibile e link legali funzionanti.
- [ ] Focus tastiera visibile.
- [ ] Pulsanti disabilitati non eseguono azioni.
- [ ] Tabelle scorrono orizzontalmente solo quando necessario.
- [ ] Dialog dentro il viewport, chiusura da tastiera e focus ripristinato.
- [ ] Loading, empty, errore e retry sono comprensibili.
- [ ] Offline mostra il banner senza nascondere i contenuti.
- [ ] Ritorno online aggiorna lo stato e permette il retry.
- [ ] Nessun errore bloccante in console.

## PWA e dispositivo reale

- [ ] Installazione e avvio dalla home screen.
- [ ] Safe-area corretta su dispositivi con notch.
- [ ] Portrait/landscape senza perdita di controlli.
- [ ] Tastiera virtuale non copre AI Voice Coach o Tactical Assistant.
- [ ] Microfono con permesso concesso, negato e revocato.
- [ ] Background e ritorno preservano timer/stato atteso.
- [ ] Logout e cambio account non mostrano dati del precedente utente.
- [ ] PDF, video, audio e CSV non vengono salvati nella cache PWA.
- [ ] Aggiornamento dalla cache `v114` alla `v115` senza pagina bianca.

## Registrazione esito

Per ogni anomalia annotare: pagina, viewport, browser, passaggi, screenshot, console, severita P0-P3 e stato `open`, `fixed` o `cannot_reproduce`.
