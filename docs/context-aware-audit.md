# Coach Context-Aware Audit

## Scope

This audit covers the active Coach frontend in `frontend/coach.html` and the
presentation orchestration in `frontend/js/coach-render.js`.

The sprint changes presentation only. Data contracts, persistence, reports,
Voice Coach, AI integrations, API calls, authentication and backend behavior
remain unchanged.

## Element inventory

| Surface | Current content | Priority | Correct context |
| --- | --- | --- | --- |
| Product hero | Product explanation, KPI summary, active-match overview | Secondary | Hidden from the operational flow; the phase status replaces it |
| Phase navigation | Pre-match, Match Day, Post-match | Essential | Always visible; extended with History |
| Phase status | Current phase, short situation summary, main action | Essential | Always visible |
| Match setup | Teams, category, date, venue, formations, notes | Essential | Pre-match only |
| Pre-match checklist | Objective, risks, observations, opponent, training focus | Essential | Pre-match only |
| Formation and bench | Players, pitch positions, formation selector, bench | Essential | Pre-match only |
| Plan limits | Ratings, history, PDF and WhatsApp limits | Secondary | Kept available in Pre-match without visual priority |
| Match Day board | Clock, period, start/pause, critical controls | Essential | Match Day only |
| Team events | Goals, chances, cards and match events | Essential | Match Day only |
| Tactical observations | Structure, phases, review bookmark, manual note | Essential | Match Day only |
| Voice Coach | Recording, review and tactical observations | Essential | Match Day only |
| Live assistant | Last event, insights, halftime summary, questions, reminders | Useful | Match Day only, collapsed by default |
| Event timeline | Recorded events and notes | Useful | Match Day only, compact and always reachable |
| Post-match summary | Result, event count, ratings, report, archive and Voice themes | Essential | Post-match only |
| Technical report | Generate/update, PDF, TXT, WhatsApp and team summary | Essential | Post-match only |
| Save to history | Save completed match | Essential | Post-match only |
| Player ratings | Manual and assisted ratings | Useful | Post-match only, collapsible |
| Tactical patterns | Recurring themes and weekly priorities | Useful | Post-match only, collapsible |
| AI Training Planner | Training priorities linked to available evidence | Useful | Post-match only, collapsible |
| Player performance archive | Aggregated player ratings | Secondary | History only |
| Saved matches | Reopen and copy previous reports | Essential | History only |
| Pattern impact | Historical recurrence impact | Useful | History only |
| Knowledge entry | Technical memory link | Useful | History only |

## Context model

### Pre-match

Goal: prepare the match.

Visible:

- setup;
- checklist;
- formation;
- bench;
- one dominant action: `Vai al Match Day` after a match exists.

Not visible:

- Match Day board;
- event timeline;
- report and exports;
- ratings;
- patterns;
- archives.

### Match Day

Goal: operate with one hand and very little time.

Visible:

- timer and match phase;
- event controls;
- Voice Coach;
- tactical observations;
- match situation;
- compact timeline.

The live assistant remains available behind a native disclosure so it does not
compete with the timer and event controls.

Dominant action:

- `Termina partita`.

### Post-match

Goal: close and deliver the staff work.

Visible first:

- result and completion summary;
- technical report;
- PDF and WhatsApp delivery;
- save to history.

Visible afterwards through disclosures:

- ratings;
- patterns and weekly priorities;
- training planner.

Dominant action:

- `Genera report`, or `Salva nello storico` when the report is ready.

### History

Goal: consult previous work.

Visible:

- saved matches;
- reopen match;
- copy report;
- player performance archive;
- linked technical memory and historical pattern impact when available.

Not visible:

- setup;
- timer;
- event controls;
- Voice Coach;
- current Match Day workspace.

Dominant action:

- `Aggiorna archivio`.

## PWA requirements

- Four phase tabs remain reachable without a long vertical navigation block.
- Touch targets remain at least 48 px on coarse pointers.
- The phase bar uses the measured sticky header offset.
- The active context is represented by text and `aria-selected`, not color only.
- Secondary content uses native `details`/`summary` controls.
- Safe-area padding remains active in standalone mode.
- No horizontal scrolling is introduced at 390 px or 430 px.

## Explicitly unchanged

- backend;
- database;
- API;
- authentication;
- payment flows;
- report generation;
- Coach event contracts;
- Voice Coach processing;
- AI models and integrations;
- Video AI and Vision Engine.
