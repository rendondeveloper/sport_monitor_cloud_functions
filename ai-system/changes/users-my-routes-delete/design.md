# Diseño — DELETE ruta myRoutes y DELETE notas

## Objetivo

Dos operaciones nuevas bajo el router `user_route`, cada una en su propio módulo:

1. **Eliminar una ruta completa** del track en `myRoutes`: borra subcolección `points`, subcolección `notes` y el documento `users/{userId}/myRoutes/{routeId}`.
2. **Eliminar solo las notas** de esa ruta: borra todos los docs en `users/{userId}/myRoutes/{routeId}/notes` y actualiza el doc de ruta (`notesCount: 0`, `updatedAt` con `get_current_timestamp()`), alineado con el reemplazo vacío de `update_my_route_notes`.

## Contrato HTTP

| Método | Path | Query | Respuesta éxito | Errores |
|--------|------|-------|-----------------|--------|
| DELETE | `/api/users/my-routes/{routeId}` | `userId` requerido | 200, body vacío, CORS como el resto del módulo | 400 userId; 401 router; 404 user o ruta; 500 |
| DELETE | `/api/users/my-routes/{routeId}/notes` | `userId` requerido | 200, body vacío | igual |

Headers de éxito: coherentes con `update_my_route_notes` (`Access-Control-Allow-Origin`, `Allow`/`Methods` si aplica).

## Router (`user_route.py`)

- Extender `validate_request` si hace falta (ya incluye DELETE).
- Resolver path **antes** que el branch genérico `my-routes` (GET/POST): prioridad `.../my-routes/{routeId}/notes` + DELETE → handler notas; luego `.../my-routes/{routeId}` + DELETE → handler ruta.
- PUT `.../notes` se mantiene sin cambios de comportamiento.

## Implementación

- `functions/users/delete_my_route.py` — `handle(req, route_id)`.
- `functions/users/delete_my_route_notes.py` — `handle(req, route_id)`.
- Sin nuevas constantes Firestore si ya existen `USER_MY_ROUTES`, `MY_ROUTE_POINTS`, `MY_ROUTE_NOTES`.
- `FirestoreHelper`: `list_document_ids` + `delete_document`; mismo patrón que `update_my_route_notes` para notas.

## Tests

- `functions/tests/test_delete_my_route.py` y `functions/tests/test_delete_my_route_notes.py` (o un solo archivo con dos clases si el proyecto prefiere menos archivos — preferible **un archivo por función** como pidió el usuario: dos archivos de test).
- Casos: happy path con mocks, userId faltante 400, user/route 404, token vía tests de router en `test_user_route.py` para los nuevos paths DELETE.
- Cobertura ≥ 90 % en el código nuevo.

## Documentación

- `functions/users/README.md`: secciones nuevas con cURL (hosting `system-track-monitor.web.app`).
- `README.md` raíz: sección users/my-routes si existe tabla índice.

## Deploy

- Solo `user_route` + `hosting` si `firebase.json` ya reescribe `/api/users/my-routes/**` (no suele requerir nuevas rewrites).
