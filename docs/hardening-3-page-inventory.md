# Hardening 3 - Inventario pagine e sistema UI

Data audit: 13 luglio 2026
Release frontend: `10519`
Cache PWA: `matchiq-pwa-v119`

## Regole condivise applicate

- `frontend/js/app-meta.js` e il punto centrale per versione, footer, disclaimer e caricamento delle risorse condivise.
- `frontend/js/global-nav-config.js` riconosce tutti i moduli operativi senza sovraccaricare la navigazione primaria.
- `frontend/js/ux-hardening.js` gestisce stato offline, errore recuperabile, retry, tabelle responsive, dialog, immagini lazy e semantica live.
- `frontend/css/components.css` contiene focus, touch target, safe-area PWA, dialog, tabelle, responsive dei moduli e reduced motion.
- Tutte le pagine attive usano la stessa release `10519`; la PWA usa una sola cache `v115`.

## Inventario completo

| Pagina | Scopo | Navigazione/footer | Stati e responsive | PWA | Stato |
|---|---|---|---|---|---|
| `index.html` | Dashboard e accesso ai moduli | condivisi | focus, errori, offline, touch | shell | `fixed_in_hardening_3` |
| `account.html` | Profilo, piano e accessi | condivisi | form, dialog, feedback | shell | `fixed_in_hardening_3` |
| `login.html` | Accesso utente | nav minima, footer | form e messaggi recuperabili | shell | `fixed_in_hardening_3` |
| `register.html` | Registrazione | nav minima, footer | form e messaggi recuperabili | shell | `fixed_in_hardening_3` |
| `reset-password.html` | Ripristino password | condivisi | form, focus, errori | shell | `fixed_in_hardening_3` |
| `verify-email.html` | Verifica email | condivisi | stato asincrono e retry | shell | `fixed_in_hardening_3` |
| `coach.html` | Match day e report staff | condivisi | touch, safe-area, dialog, offline | shell | `fixed_in_hardening_3` |
| `match.html` | Analisi live partita | condivisi | tabelle, touch, offline | shell | `fixed_in_hardening_3` |
| `video.html` | Video AI e archivio | condivisi | video responsive, retry, errori | shell; media esclusi cache | `fixed_in_hardening_3` |
| `scout.html` | Scouting live e report | condivisi | griglie, tabelle, touch | shell | `fixed_in_hardening_3` |
| `weekly-briefing.html` | Briefing settimanale | condivisi | larghezza, dialog, stati | dinamica | `fixed_in_hardening_3` |
| `pattern-intelligence.html` | Pattern tattici | condivisi | larghezza, tabelle, stati | dinamica | `fixed_in_hardening_3` |
| `training-planner.html` | Piano allenamento | condivisi | griglie, dialog, stati | dinamica | `fixed_in_hardening_3` |
| `knowledge.html` | Memoria tecnica | condivisi | layout, tabelle, stati | dinamica | `fixed_in_hardening_3` |
| `tactical-assistant.html` | Assistente tattico | condivisi | viewport tastiera e safe-area | dinamica | `fixed_in_hardening_3` |
| `tactical-identity.html` | Identita tattica | condivisi | larghezza, griglie, stati | dinamica | `fixed_in_hardening_3` |
| `decision-engine.html` | Supporto decisionale | condivisi | larghezza, griglie, stati | dinamica | `fixed_in_hardening_3` |
| `club-intelligence.html` | Governance club | condivisi | larghezza, tabelle, dialog | dinamica | `fixed_in_hardening_3` |
| `admin-analytics.html` | Metriche prodotto | condivisi | tabelle scrollabili e retry | shell | `fixed_in_hardening_3` |
| `admin-beta.html` | Richieste beta | condivisi | tabelle scrollabili e retry | shell | `fixed_in_hardening_3` |
| `admin-users.html` | Gestione utenti | condivisi | tabelle scrollabili e retry | shell | `fixed_in_hardening_3` |
| `privacy.html` | Privacy Policy | footer legale | lettura responsive | raggiungibile | `verified` |
| `terms.html` | Termini di utilizzo | footer legale | lettura responsive | raggiungibile | `verified` |
| `cookies.html` | Cookie Policy | footer legale | lettura responsive | raggiungibile | `verified` |
| `mobile.html` | Redirect compatibilita | nessuna nav duplicata | redirect accessibile | shell | `verified` |
| `lp.html` | Landing legacy | autonoma | non inclusa nei flussi autenticati | non core | `manual_verification_required` |
| `video-demo.html` | Demo commerciale legacy | autonoma | non usata dal flusso Video AI | non core | `manual_verification_required` |

## Audit design system

| Area | Decisione |
|---|---|
| Colori e tipografia | invariati; nessun redesign |
| Navigazione | configurazione unica, riconoscimento di tutti i moduli |
| Footer e legali | centralizzati in `app-meta.js` |
| Focus tastiera | anello visibile condiviso |
| Touch target | minimo coerente su tablet/smartphone |
| Tabelle | wrapper orizzontale automatico senza rompere il desktop |
| Dialog | limiti viewport, scroll interno e ripristino focus |
| Stati rete | banner offline con ultimo aggiornamento e pulsante Riprova |
| Errori runtime | messaggio recuperabile senza esporre dettagli tecnici |
| Media | immagini lazy, video `preload=metadata`, file grandi non cache PWA |
| Movimento | rispetto di `prefers-reduced-motion` |

## Verifica manuale residua

La struttura e coperta da test statici e HTTP. La resa finale su Safari iOS, Android PWA, tastiera virtuale, permessi microfono, PDF nativo e orientamento landscape resta da confermare con la checklist visuale dedicata.
