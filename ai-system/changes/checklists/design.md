# design.md — Event Checklists v2 (backend)

**Session:** `event-checklists-v2-backend-22052026130306`  
**Tickets:** SPRTMNTRPP-123 (contract) → 124 (CRUD) → 125 (progress)  
**Date:** 2026-05-22

---

## Decision log

| ID | Decision | Choice |
|----|----------|--------|
| D1 | HTTP path style | **Flat paths** (dart-define / `firebase.json`), **not** nested REST |
| D2 | PATCH mobile (#7) | **Out of scope** this session |
| D3 | Auth CRM | **Owner + staff** via Bearer UID |
| D4 | Region | `us-central1` (events module family) |
| D5 | List response wrapper | `{ "result": [...] }` per Jira 123 |
| D6 | Success body | JSON direct; errors empty body (project standard) |
| D7 | Item assignment (v3) | `participantIds[]` per item; sync all `events/.../participants`; remove checklist `assignedParticipantIds` |

> **Amendment (2026-05-22):** Phase 0 initially chose nested REST (4-A). User requested **flat paths like dart-define**. D1 supersedes nested examples in Jira narrative.
>
> **Amendment v3 (2026-05-22):** Per-item `participantIds`, mandatory rules per pilot, `sync_all_event_participants`. See `functions/checklists/README.md`.
>
> **Amendment patch-only (2026-05-27):** Row #4 (`update`) is **patch-only**, not full replace. See [`design-patch-update-amendment.md`](design-patch-update-amendment.md).

---

## HTTP paths (canonical — flat)

Aligned with SPRTMNTRPP-123 dart-define block and existing `firebase.json` style (`/api/events/detail`).

| # | Action | Method | Public path | `eventId` | `checklistId` | Other |
|---|--------|--------|-------------|-----------|---------------|-------|
| 1 | list | GET | `/api/events/checklists/list` | query `eventId` | — | — |
| 2 | get | GET | `/api/events/checklists/get` | query `eventId` | query `checklistId` | — |
| 3 | create | POST | `/api/events/checklists/create` | body | — | body: title, visibilityMode, items (`participantIds` per item) |
| 4 | update | PUT | `/api/events/checklists/update` | body | body `id` or `checklistId` | full replace body |
| 5 | delete | DELETE | `/api/events/checklists/delete` | query `eventId` | query `checklistId` | 204 |
| 6 | participant-progress | GET | `/api/events/checklists/participant-progress` | query `eventId` | query `checklistId` | query: `limit`, `cursor`, `search` |
| 7 | patch participant | PATCH | `/api/events/checklists/participant-update` | — | — | **Deferred** (mobile) |

### dart-define keys (web — reference only)

```json
{
  "path_list_event_checklists": "/api/events/checklists/list",
  "path_get_event_checklist": "/api/events/checklists/get",
  "path_create_event_checklist": "/api/events/checklists/create",
  "path_update_event_checklist": "/api/events/checklists/update",
  "path_delete_event_checklist": "/api/events/checklists/delete",
  "path_checklist_participant_progress": "/api/events/checklists/participant-progress",
  "path_patch_checklist_participant": "/api/events/checklists/participant-update"
}
```

### `firebase.json` rewrites (one per path → `checklist_route`)

```json
{ "source": "/api/events/checklists/list", "function": "checklist_route", "region": "us-central1" },
{ "source": "/api/events/checklists/get", "function": "checklist_route", "region": "us-central1" },
{ "source": "/api/events/checklists/create", "function": "checklist_route", "region": "us-central1" },
{ "source": "/api/events/checklists/update", "function": "checklist_route", "region": "us-central1" },
{ "source": "/api/events/checklists/delete", "function": "checklist_route", "region": "us-central1" },
{ "source": "/api/events/checklists/participant-progress", "function": "checklist_route", "region": "us-central1" }
```

### Router dispatch (`checklist_route.py`)

`_action_from_path(path, method)` maps exact path segments after `/api/events/checklists/`:

- `list` + GET → `handle_list`
- `get` + GET → `handle_get`
- `create` + POST → `handle_create`
- `update` + PUT → `handle_update`
- `delete` + DELETE → `handle_delete`
- `participant-progress` + GET → `handle_participant_progress`

Auth once in router: `validate_request` + `verify_bearer_token` + `get_bearer_uid` → pass `uid` to handlers.

---

## Authorization

```python
def get_event_if_owner_or_staff(event_id: str, user_id: str) -> Optional[dict]:
    # 1) creator match (existing logic)
    # 2) else doc exists at events/{eventId}/staff_users/{userId}
```

- 403 vs 404: use **404** when event missing or no access (match `get_event_if_owner` behavior).

---

## Firestore model

### v2 (superseded)

Checklist-level `assignedParticipantIds`; `itemProgress` = all `isRequired` items for assigned pilots only.

### v3 (current — 2026-05-22)

```
events/{eventId}/checklists/{checklistId}
  title, visibilityMode, createdAt, updatedAt

  items/{itemId}
    name, description, photoUrl?, latitude?, longitude?
    isRequired, participantIds: string[], order, createdAt, updatedAt

  participants/{userId}   # one doc per event competitor after sync
    itemProgress: { itemId: { check, updateDate } }  # mandatory items FOR this pilot
    isCompleted, lastUpdateDate, assignedAt, updatedAt
    participantName?, pilotNumber?, email?
```

| Item config | Mandatory for |
|-------------|----------------|
| `isRequired: true`, `participantIds: []` | All event competitors |
| `participantIds: [uids]` | Listed UIDs only |
| `isRequired: false`, `participantIds: []` | None (optional) |

Validation: `isRequired: true` + non-empty `participantIds` → 400. Body field `assignedParticipantIds` → 400.

### `FirestoreCollections` additions

```python
EVENT_CHECKLISTS = "checklists"
CHECKLIST_ITEMS = "items"
CHECKLIST_PARTICIPANTS = "participants"  # under checklist, not event root
```

Path builder helpers:

- `_checklist_path(event_id)` → `events/{eventId}/checklists`
- `_items_path(event_id, checklist_id)` → `.../items`
- `_participants_path(event_id, checklist_id)` → `.../participants`

---

## JSON contracts (summary)

See SPRTMNTRPP-123 for full shapes. Backend must return:

- **list:** `{ "result": ChecklistSummary[] }` — include `assignedCount`
- **get/create/update:** ChecklistDetail with `items[]` (each includes `participantIds`); no root `assignedParticipantIds`
- **participant-progress:** `{ "result", "pagination", "summary" }`

---

## File table

| File | Action | Agent / wave |
|------|--------|----------------|
| `models/firestore_collections.py` | edit | functions-cross W1 |
| `utils/event_owner_helper.py` | edit — `get_event_if_owner_or_staff` | functions-cross W1 |
| `checklists/checklist_route.py` | create | functions-endpoint W1 |
| `checklists/list_checklists.py` | create | functions-endpoint W1 |
| `checklists/get_checklist.py` | create | functions-endpoint W1 |
| `checklists/create_checklist.py` | create | functions-endpoint W1 |
| `checklists/update_checklist.py` | create | functions-endpoint W1 |
| `checklists/delete_checklist.py` | create | functions-endpoint W1 |
| `checklists/get_participant_progress.py` | create | functions-endpoint W1 (125) |
| `checklists/checklist_participant_service.py` | create — sync/init/merge | functions-endpoint W1 |
| `checklists/__init__.py` | create | functions-cross W1 |
| `main.py` | edit — import/export | functions-cross W1 |
| `firebase.json` | edit — 6 rewrites | functions-cross W1 |
| `tests/test_checklist_route.py` | create | functions-test W2 |
| `tests/test_checklist_*.py` | create | functions-test W2 |
| `checklists/README.md` | create | functions-docs W3 |

---

## Implementation order (tickets)

1. **SPRTMNTRPP-123** — Mark contract validated in repo (`design.md` + README path table); optional Jira description update.
2. **SPRTMNTRPP-124** — Endpoints 1–5 + participant sync.
3. **SPRTMNTRPP-125** — Endpoint 6 participant-progress.

---

## Open items

- [ ] Update SPRTMNTRPP-123 Jira description: replace nested path examples with flat table above.
- [ ] Confirm web `sport_monitor_web` paths use same strings (126+).
- [x] Backend implementation on `main` (2026-05-22) — see `verify-report.md`
