# Handoff: align-subscribed-events-to-events-list

| Campo | Estado |
|-------|--------|
| **Feature / path** | `ai-system/changes/align-subscribed-events-to-events-list/` |
| **Objective** | Ítems de `GET /api/users/subscribedEvents` con el mismo shape que `GET /api/events` (EventShortDocument + overrides desde `event_content`). |
| **Current phase** | Implementado en repo (2026-04-15). |
| **Completed** | `subscribed_events.py` usa `EventShortDocument` + overrides; tests; README 4.1.1 + deploy user_route+hosting. |
| **Next** | Deploy: `firebase deploy --only functions:user_route,hosting` desde raíz del proyecto. |
| **Blockers** | Ninguno. |
| **Key files** | `design.md`, `functions/users/subscribed_events.py`, `functions/events/event_short_document.py`, `functions/events/events_customer.py`, `functions/tests/test_subscribed_events.py`, `README.md`. |

## Instrucciones para implementación (copiar checklist)

1. En `subscribed_events.py`, sustituir `_build_event_item` por lógica equivalente a la del bucle en `events_customer.py` (líneas ~177–198): `EventShortDocument.from_firestore_data(event_doc, event_id).to_dict()` → `event_dict["isEnrolled"] = True` → si hay `event_content`, `photoMain` → `imageUrl`, `address` → `locationName`.
2. Asegurar que `event_doc` sea un `dict` compatible con `from_firestore_value` si FirestoreHelper devuelve tipos crudos; si hace falta, usar `convert_firestore_value` solo donde el modelo falle (probar primero sin conversión global, como `events_customer` con `to_dict()`).
3. Actualizar docstring del handler describiendo el nuevo shape.
4. Tests: reemplazar expectativas `name`/`description`/`endEvent` por `title`/`subtitle`/`locationName`/`isEnrolled`; `startDateTime` debe alinearse con el modelo (campo `date` en doc de evento, no `startEvent` de content).
5. README: tabla de campos retornados igual que lista de events (versión corta).
