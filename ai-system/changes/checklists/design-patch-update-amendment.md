# Amendment — PUT `/update` Patch-only (2026-05-27)

**Decision:** D8 — `handle_update` es **patch-only** (sin replace). Supersede la fila #4 de `design.md` que decía "full replace body".

## Contrato HTTP

| Campo | Requerido | Regla |
|-------|-----------|--------|
| `eventId` | Sí | string no vacío |
| `checklistId` o `id` | Sí | string no vacío |
| `title` | No | Si la key está presente → valor no vacío tras trim |
| `description` | No | Si la key está presente → actualizar (permite `""`) |
| `photoUrl` | No | Si la key está presente → `normalize_optional_url` (permite `null` para limpiar) |
| `visibilityMode` | No | Si presente → `participants` \| `eventDates` |
| `items` | No | Si presente → array; `id` recomendado. **Si un elemento no trae `id`, se ignora (no-op)**. Si `id` empieza con **`client-`**, se trata como “nuevo local” y se ignora (no-op). |
| `participants` | No | Si presente → array; **no toca progreso**. `id` recomendado. **Si un elemento no trae `id`, se ignora (no-op)** |

**400** si:
- Body inválido o faltan `eventId` / `checklistId`
- No hay ningún campo actualizable (ni checklist ni `items`)
- `items` con `id` duplicado/vacío (solo se valida `id` cuando viene)
- `participants` con `id` duplicado/vacío (solo se valida `id` cuando viene)
- `assignedParticipantIds` en body (deprecated)
- `visibilityMode` inválido cuando se envía
- `name` presente en item y vacío tras trim
- `isRequired: true` + `participantIds` no vacío en el mismo item (misma regla que create)
- `participantIds` referencia UID que no existe en `events/{eventId}/participants`
- `participants[]` intenta tocar campos de progreso (prohibido): `itemProgress`, `isCompleted`, `lastUpdateDate`, `assignedAt`

**404** si checklist o algún `items[].id` / `participants[].id` **enviado** no existe.

## Patch de checklist (raíz)

Solo incluir en `update_document` las keys **presentes** en el body + `updatedAt`.

## Patch de items

Por cada `{ "id": "item-1", ... }`:
- Construir payload solo con keys presentes entre: `name`, `description`, `photoUrl`, `latitude`, `longitude`, `isRequired`, `participantIds`, `order`
- `update_document` en `events/{eventId}/checklists/{checklistId}/items/{itemId}`
- **Prohibido:** `delete_all_subcollection_docs`, `persist_template_items`, crear items sin `id`
- **No-op tolerante:** si un entry no trae `id` o `id` empieza con `client-`, se ignora y **no** debe disparar 400/404.
- **404 solo** cuando se envía un `id` “real” (no vacío y no `client-*`) con campos actualizables y el doc no existe.

## Patch de participants (subcolección `checklists/.../participants/`)

- `participants[]` es opcional y se interpreta como patch parcial por participante **existente**.
- **No-op tolerante:** entries sin `id` se ignoran (no disparan 400/404).
- Campos permitidos (solo si vienen): `participantName`, `pilotNumber`, `email`.
- Campos prohibidos (si vienen → 400): `itemProgress`, `isCompleted`, `lastUpdateDate`, `assignedAt`.
- 404 solo cuando se envía `id` + algún campo permitdo, y el doc no existe.

## Sync `participants/`

Ejecutar `sync_all_event_participants` **solo si**:
- Se actualizó `visibilityMode`, o
- Algún patch de item incluyó `isRequired` y/o `participantIds`

**No** sync si el patch solo toca metadata del checklist (`title`, `description`, `photoUrl`) o geodata/fotos de items (`latitude`, `longitude`, `photoUrl`, `name`, `description`, `order`).

Tras sync (o sin sync), responder `build_checklist_detail` (200 JSON).

## Referencia de implementación

Seguir el estilo de `update_checklist_photos.py` (`_parse_body`, early return, `FirestoreHelper.update_document` merge).

## Tests obligatorios

- Patch solo `latitude`/`longitude` en un item → `update_document` del item; **no** borrar otros campos; **no** llamar sync
- Patch solo `title` en checklist → items intactos
- Patch `isRequired` o `participantIds` → sync llamado una vez
- Entries sin `id` en `items[]` / `participants[]` → se ignoran (no 400)
- Item id inexistente → 404
- Múltiples llamadas PATCH seguidas estables
- `participants[]` con campos de progreso → 400
