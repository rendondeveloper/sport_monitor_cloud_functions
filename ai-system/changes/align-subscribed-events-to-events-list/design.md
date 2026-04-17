# Design: Alinear `subscribedEvents` con el shape de evento de `GET /api/events`

## Objetivo

Cada elemento de `result` en `GET /api/users/subscribedEvents` debe usar el **mismo contrato de campos** que `GET /api/events` (lista corta): `id`, `title`, `subtitle`, `status`, `startDateTime`, `locationName`, `imageUrl`, `isEnrolled`.  
No se pide cambiar la semántica de paginación ni el router.

## Fuente de verdad

- Lista pública: `functions/events/events_customer.py` + `functions/events/event_short_document.py` (`EventShortDocument.from_firestore_data`, luego override desde `event_content`: `photoMain` → `imageUrl`, `address` → `locationName`).
- Suscripciones: `functions/users/subscribed_events.py` (reemplazar `_build_event_item`).

## `isEnrolled`

En `subscribedEvents` el usuario **está** en membership de esos eventos; para coincidir con el shape del listado y con el cliente, cada ítem debe llevar **`isEnrolled`: `true`**.

## ADR

- **ADR-1**: Reutilizar `EventShortDocument.from_firestore_data` en lugar de duplicar mapeo (`name`/`description`/`startEvent` de content) para garantizar paridad con `/api/events` (misma `startDateTime` basada en `date` / fallbacks del modelo).

## Archivos a tocar

| Archivo | Cambio |
|---------|--------|
| `functions/users/subscribed_events.py` | Importar `EventShortDocument`; construir dict como en `events_customer`; eliminar campos legacy (`name`, `description`, `endEvent`). |
| `functions/tests/test_subscribed_events.py` | Actualizar aserciones al nuevo shape; ajustar fixtures (`date`, `location`, `subtitle` en event doc; `address` en content si aplica). |
| `README.md` (sección subscribedEvents) | Documentar el nuevo shape de cada ítem en `result`. |

## No incluido

- Refactor extraer helper compartido events ↔ users (opcional, fuera de scope mínimo).
- Cambiar `events` ni `firebase.json`.

## Criterios de salida

- JSON de cada evento en `subscribedEvents` coincide en **claves** y **origen de datos** con `events` para los mismos campos.
- Tests `pytest functions/tests/test_subscribed_events.py` pasan; cobertura del módulo se mantiene ≥ umbral del proyecto.
- README actualizado.
