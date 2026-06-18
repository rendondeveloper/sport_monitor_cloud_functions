# Sport Monitor Cloud Functions

## Project identity

- **Project**: Firebase Cloud Functions (2nd Gen), Python 3.12, Firestore + Realtime DB
- **Project ID**: `system-track-monitor`
- **Entrypoint**: `functions/main.py` — imports every function by name
- **Region**: functions in `us-central1` by default; competitors/catalogs/tracking/vehicles/checkpoints use `us-east4`

## Dev commands

Run from repo root unless noted:

| Command | Purpose |
|---------|---------|
| `npm run emulators` | Start Firebase emulators (functions+hosting) — needs `functions/venv/` active |
| `pytest functions/tests/` | Run all tests (from within `functions/` or with `PYTHONPATH=functions`) |
| `pytest functions/tests/test_FOO.py -v --cov=functions/competitors --cov-fail-under=90` | Single module with coverage |
| `firebase deploy --only functions:FUNC_NAME` | Deploy a single function |
| `firebase deploy --only functions:FUNC_NAME,hosting` | Deploy function + hosting rewrites |

## Architecture

### Router pattern
Several modules expose a **single HTTP function** that validates CORS + token once, then dispatches by path:
- `user_route.py` → `/api/users/{read,profile,create,update,personalData,...}`
- `vehicle_route.py` → `/api/vehicles/...`
- `checklist_route.py` → `/api/events/checklists/{list,get,create,update,...}`
- `competitor_api_route.py` → `/api/competitors/*`
- `catalog_route.py` → `/api/catalogs/{vehicle,year,color,relationship-type,checkpoint-type}`
- `event_route.py` → `/api/events{/create,/update,/list,/get-info,/save-info,...}`
- `event_management_route.py` → `/api/event-management/*`
- `route_route.py` → `/api/routes/{create,update,get,list,delete,...}`
- `checkpoint_route.py` → `/api/checkpoint/*`
- `tracking_route.py` → `/api/tracking/*`
- `staff_route.py` → `/api/create_staff_user`

Internal handlers in these routers **do not** call `validate_request`/`verify_bearer_token` — they assume the request is already validated.

### Non-router functions
Standalone functions live in their own `.py` file (e.g. `get_competitor_by_email.py`, `track_competitors.py`). These follow the standard template with `validate_request` + `verify_bearer_token` inline.

## Hard rules (all verified against existing code)

1. **Every function** calls `validate_request(req, [...], "fn_name", return_json_error=False)` then `verify_bearer_token(req, "fn_name")` — in that order, no exceptions.
2. **Success responses**: JSON direct, **never** wrapped in `success`/`data`/`message`.
3. **Error responses**: HTTP status code **only** — no JSON body. Only exceptions: 409 for duplicate competitor, 422 for field-level validation errors.
4. **Early return**: never nest `if/else` for validation — validate and `return` immediately.
5. **FirestoreCollections**: use constants from `models/firestore_collections.py` — never raw strings like `"events"`.
6. **FirestoreHelper**: use `FirestoreHelper` class for CRUD in endpoints — never call `firestore.client()` directly in endpoint files.
7. **One function per file**, **one test file per function**, **max ~200 lines** per endpoint file.

## Firestore shortcuts

Collection constants live in `models/firestore_collections.py`. Notable subcollection paths:

| Path pattern | Constant prefix |
|---|---|
| `events/{eventId}/participants/{uid}` | `EVENTS` → `EVENT_PARTICIPANTS` |
| `events/{eventId}/event_content/{docId}` | `EVENTS` → `EVENT_CONTENT` |
| `events/{eventId}/routes/{rid}/checkpoints/{cid}` | `EVENTS` → `EVENT_ROUTES` |
| `users/{uid}/personalData/{docId}` | `USERS` → `USER_PERSONAL_DATA` |
| `users/{uid}/emergencyContacts/{cid}` | `USERS` → `USER_EMERGENCY_CONTACT` |
| `users/{uid}/membership/{eventId}` | `USERS` → `USER_MEMBERSHIP` |
| `events/{eventId}/participants/{uid}/vehicle/{vid}` | `EVENTS` → `PARTICIPANT_VEHICLE` |
| `catalogs/default/{type}/{id}` | `CATALOGS` + `CATALOGS_DEFAULT_DOC_ID` |

## Testing conventions

- Tests in `functions/tests/test_<module>_<function>.py`
- Fixture pattern: `mock_validate_request`, `mock_verify_bearer_token`, `mock_firestore_helper` (all via `unittest.mock.patch`)
- Helper: `_make_request(method, args, body, path)` returns a `MagicMock` request
- Coverage threshold: **90% minimum**

## Existing instruction files

- `CLAUDE.md` — Architect mode orchestration (always-on architect pattern)
- `.claude/CLAUDE.md` — Python/Firebase template rules and patterns
- `.cursor/rules/structure_project.mdc` — Cursor variant of architect rules
- `ai-system/` — SDD workflow, agent definitions, context docs (architecture.md, coding-standards.md, project-structure.md, workflow.md)

## AI orchestration notes

- **Trigger word**: `work backend` activates full Architect Action plan mode
- **Confirmation word**: `ok` bypasses the plan-approval gate
- Always read `ai-system/context/architecture.md` and coding-standards.md at session start
- Architect must **not** write application code — delegate to specialist agents. Orchestration files under `ai-system/` are the only exception.
