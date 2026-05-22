# Checklists — Event CRM API (v2)

Paths **planos** (dart-define). Progreso en `events/{eventId}/checklists/{checklistId}/participants/{userId}`.

## Auth

`Authorization: Bearer {Firebase ID token}` — acceso si el UID es **creador del evento** o está en `events/{eventId}/staff_users/{uid}`.

## Endpoints

| Método | Path | Parámetros |
|--------|------|------------|
| GET | `/api/events/checklists/list` | query `eventId` |
| GET | `/api/events/checklists/get` | query `eventId`, `checklistId` |
| POST | `/api/events/checklists/create` | body JSON |
| PUT | `/api/events/checklists/update` | body JSON (`checklistId` o `id`) |
| DELETE | `/api/events/checklists/delete` | query `eventId`, `checklistId` |
| GET | `/api/events/checklists/participant-progress` | query `eventId`, `checklistId`, `limit`, `cursor`, `search` |

## Ejemplos curl

```bash
# List
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/list?eventId=EVENT_ID"

# Get
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/get?eventId=EVENT_ID&checklistId=CHK_ID"

# Create
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","title":"Technical","visibilityMode":"participants","items":[{"name":"License","isRequired":true,"order":0}],"assignedParticipantIds":["USER_1"]}' \
  "$BASE/api/events/checklists/create"

# Update
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","checklistId":"CHK_ID","title":"Technical","visibilityMode":"participants","items":[{"name":"License","isRequired":true,"order":0}],"assignedParticipantIds":["USER_1","USER_2"]}' \
  "$BASE/api/events/checklists/update"

# Delete
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/delete?eventId=EVENT_ID&checklistId=CHK_ID"

# Participant progress
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/participant-progress?eventId=EVENT_ID&checklistId=CHK_ID&limit=20"
```

## Reglas v2

- Solo IDs en `assignedParticipantIds` tienen doc en `participants/`.
- `itemProgress` solo incluye ítems de plantilla con `isRequired: true`.
- Sin sync en `users/.../membership`.
- PATCH móvil (`participant-update`) — pendiente otra subtarea.
