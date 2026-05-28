# Amendment — update-photos (2026-05-25)

| ID | Decision | Choice |
|----|----------|--------|
| D8 | Event image | `events/{eventId}.photoUrl` (string \| null) |
| D9 | Checklist item photos | `checklists/.../items/{itemId}.photoUrl` by `id` in body |
| D10 | Response | **200** cuerpo vacío (sin JSON) |
| D11 | participant-progress | Incluir `photoUrl` en cada ítem de `items[]` |
| D12 | Web | Solo backend; README documenta request/response |

**Path:** `PUT /api/events/checklists/update-photos`
