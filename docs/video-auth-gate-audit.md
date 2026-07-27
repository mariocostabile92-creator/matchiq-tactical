# Video AI authentication gate audit

## Scope

This audit covers the Video AI entry page, its bootstrap scripts, the shared
authentication helper, login/registration/verification return flow, protected
Video APIs, and the PWA cache. Coach, Home, Vision Engine, RF-DETR, database
schemas, and video analysis logic are outside this change.

## Previous anonymous path

An anonymous visitor could open `video.html` and see the complete workspace.
The browser could also initialize private archive and project restores before
authentication had been established. Video Intelligence loaded its halftime
configuration automatically. Upload controls and project configuration were
therefore visible even though protected operations eventually returned `401`.

This was a presentation and bootstrap defect, not an authorization bypass:
server-side report, library, project, evidence, and PDF operations were already
protected, and the two older optional-user routes explicitly returned `401`
without a user.

## Protected surfaces found

### Initial browser bootstrap

- `video.html` rendered the app markup before checking the session.
- `video-intelligence.js` could request the protected halftime configuration.
- inline Video code could load cloud reports, refresh Video Hub sessions, and
  restore private project state.
- `video-experience.js` mounted the interactive workspace independently.

### Protected Video APIs

- analysis and AI frame selection;
- Video Library list, upload, import, stream, update, and delete;
- Video Hub sessions and providers;
- cloud reports and frame feedback;
- Video Intelligence projects, pipeline, evidence, review, reports, PDF, and
  halftime analysis.

All remain protected by the existing backend user and ownership checks.

## Implemented state model

### Anonymous

`video.html` starts in its existing neutral boot shell. Shared session
validation runs before any Video module mounts. With no token, validation does
not call `/api/auth/me`; it immediately selects the anonymous gate.

The gate exposes only:

- `Accedi`;
- `Crea account`;
- a concise explanation of saved projects and reports;
- four product-value points.

Upload, configuration, Library, archive, private reports, and Video actions are
neither visible nor initialized.

### Authenticated

After a valid session, the existing Video bootstrap, archive restore, project
restore, Library, upload, frame review, report, and PDF flows continue in their
previous order. No video analysis behavior or backend contract was changed.

### Expired during work

A `401` or `403` from a protected Video Intelligence or PDF request:

1. clears only authentication credentials;
2. keeps the selected `File`, project context, frames, and current workspace in
   browser memory;
3. stops the failed operation without automatic retries;
4. shows one dominant action, `Accedi e riprendi`;
5. opens authentication in a separate window when available, preserving the
   in-memory file;
6. detects the restored token through storage/focus events;
7. requires an explicit `Riprendi analisi` action before retrying.

There is no timer, retry loop, or anonymous fallback request.

## Safe return flow

The shared auth helper accepts only same-origin paths beginning with `/`.
External origins, protocol-relative values, control characters, and
login/register loops fall back to Home.

The safe relative destination is stored in session storage and carried through:

`Video AI -> Login/Register -> Email verification when required -> Login -> Video AI`

The return value is consumed only after successful authentication.

## PWA and cache

- Video AI release: `10543`.
- PWA cache: `matchiq-pwa-v144`.
- Video, login, registration, verification, shared auth, and Video experience
  assets are included in the application shell.
- Anonymous and authenticated layouts include responsive gate rules for
  desktop, tablet, smartphone, safe-area, and installed PWA dimensions.

## Security notes

- Backend authorization and ownership checks were not weakened or moved to the
  client.
- Client-side hiding is only a user-experience gate; the backend remains the
  security boundary.
- Transient network/server errors during `/api/auth/me` do not destroy a
  locally held token. Protected operations still require successful server
  authorization.
- No video file, frame, or workspace data is written into the return URL.

## Regression risks and controls

| Risk | Control |
| --- | --- |
| Anonymous API requests during bootstrap | All three Video bootstrap branches await the same session promise |
| Open redirect | Same-origin relative URL normalization |
| Lost uploaded file after token expiry | Popup reauthentication and selective credential clearing |
| Retry storm | No interval and no automatic retry |
| Stale PWA shell | New cache name and scoped Video/auth asset versions |
| Coach/Home behavior changes | No Coach/Home code changes |
| Ownership regression | Existing backend ownership helpers remain unchanged |

## Test mapping

`tests/test_video_auth_gate.py` covers the anonymous gate, hidden workspace,
bootstrap ordering, absence of anonymous startup calls, safe return URL,
verification continuation, selective auth cleanup, expiry recovery, explicit
resume, protected backend contracts, ownership helpers, PWA cache, and Coach
isolation. Existing Video bootstrap, auth, experience, library, intelligence,
hardening, and PWA tests remain active.
