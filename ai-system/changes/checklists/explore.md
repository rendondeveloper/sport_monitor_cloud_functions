# explore.md — Event Checklists v2 (backend)

**Session:** `event-checklists-v2-backend-22052026130306`  
**Jira:** [SPRTMNTRPP-120](https://softwarecosta.atlassian.net/browse/SPRTMNTRPP-120) → 123, 124, 125  
**Date:** 2026-05-22

---

## Current inventory

| Area | Status |
|------|--------|
| `functions/checklists/` | **Does not exist** — greenfield module |
| `FirestoreCollections` | No `EVENT_CHECKLISTS`, `CHECKLIST_ITEMS`, `CHECKLIST_PARTICIPANTS` |
| `firebase.json` | No rewrites for `/api/events/checklists/**` |
| `main.py` | No `checklist_route` export |
| Legacy `users/.../membership` checklist sync | **Not present** — v2 avoids it by design |

## Reference patterns in repo

| Pattern | Reference file |
|---------|----------------|
| Flat path router + dispatch | `events/event_route.py`, `routes/route_route.py` |
| `firebase.json` one rewrite per path | `/api/events/detail`, `/api/routes/**` |
| Owner auth | `utils/event_owner_helper.py` → `get_event_if_owner` |
| UID from Bearer | `utils/helper_http.py` → `get_bearer_uid` |
| Subcollections under event | `routes/create_event_route.py` → `events/{eventId}/routes` |
| Event participants denorm | `competitors/create_competitor_user.py` → `events/{eventId}/participants` |

## Dependencies

- **Firestore:** `events/{eventId}/checklists/{checklistId}/items/{itemId}` + `participants/{userId}`
- **Auth (decided):** owner **or** staff (`events/{eventId}/staff_users/{uid}`) — **new helper required** (staff not used elsewhere yet)
- **Web client:** `sport_monitor_web` dart-define paths (flat) — must match backend rewrites
- **Mobile:** PATCH endpoint **out of scope** this session

## Risks

| Risk | Mitigation |
|------|------------|
| Jira SPRTMNTRPP-123 still documents nested REST examples | Update ticket + align `design.md` (paths planos) |
| Staff auth helper missing | Add `get_event_if_owner_or_staff` in `event_owner_helper.py` |
| PUT participant sync complexity | Dedicated `_sync_participants_subcollection` in shared checklist service module |
| Large handler files | Split: router + handlers + `checklist_participant_service.py` (<200 lines each) |

## Deviations from SPRTMNTRPP-123 draft

- **Paths:** implementation uses **flat paths** (dart-define), not `/api/events/{eventId}/checklists/...` — see `design.md § HTTP paths`.
