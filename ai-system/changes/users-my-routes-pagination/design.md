# Diseño — paginación en GET /api/users/my-routes (modo lista)

## Objetivo

Agregar paginación al modo **lista** de `GET /api/users/my-routes` para controlar la cantidad de documentos retornados y reducir costo/latencia en clientes con muchas rutas.

## Contexto actual (baseline)

- El endpoint público es `user_route` y despacha a `users/get_my_routes.py` para `GET /api/users/my-routes`.
- `get_my_routes.py` tiene 2 modos:
  - **Lista**: `GET /api/users/my-routes?userId=...` → retorna **array JSON** de rutas (sin `description`, `createdAt`, `updatedAt`).
  - **Detalle**: `GET /api/users/my-routes?userId=...&routeId=...` → retorna **objeto JSON** (ruta + `points` + `notes`).
- La query de lista actualmente no aplica `limit`, no ordena y no soporta cursor.

## Contrato HTTP (nuevo)

### Endpoint

`GET /api/users/my-routes`

### Headers requeridos

- `Authorization: Bearer {Firebase Auth Token}` (validado en `user_route`)

### Query parameters

- `userId`: string (requerido)
- `routeId`: string (opcional) — si viene, activa modo detalle (sin cambios de contrato)

#### Parámetros de paginación (solo modo lista)

- `limit`: int (opcional)
  - Default: `50`
  - Máximo: `100`
  - Si es inválido (no int / < 1) ⇒ usar default `50`
- `startAfterDocId`: string (opcional)
  - Cursor basado en **docId**. Si viene vacío/whitespace ⇒ se ignora.

### Ordenamiento (modo lista paginada)

- `createdAt` **descendente**.
- Si un documento no tiene `createdAt`, Firestore podría fallar al ordenar; se asume que los documentos creados por `POST /api/users/my-routes` incluyen `createdAt`.

## Respuesta HTTP (compatibilidad)

### Modo detalle (sin cambios)

- `200`: objeto JSON de la ruta, incluyendo `points` y `notes`.

### Modo lista — compatibilidad hacia atrás

Para evitar romper clientes que esperan **array**:

- Si **NO** se envían `limit` **ni** `startAfterDocId`:
  - Respuesta `200`: **array JSON** (igual que hoy).

### Modo lista — paginada (nuevo)

- Si se envía `limit` **o** `startAfterDocId`:
  - Respuesta `200`: JSON con forma:

```json
{
  "result": [
    {
      "id": "ROUTE_ID",
      "identifier": 16,
      "name": "Ruta 1",
      "eventId": null,
      "distance": 0.0,
      "pointsCount": 0,
      "notesCount": 0
    }
  ],
  "pagination": {
    "limit": 50,
    "page": 1,
    "hasMore": true,
    "count": 1,
    "lastDocId": "ROUTE_ID"
  }
}
```

Notas:

- Se reutiliza `models.paginated_response.PaginatedResponse` para generar `result` + `pagination`.
- `page` se fija en `1` (no se usa page-based en este endpoint; el cursor es `startAfterDocId`).
- `hasMore`: `True` si se retornó exactamente `limit` elementos (o alternativamente, si se obtuvo `limit + 1` y se recorta; a decisión de implementación).
- `lastDocId`: ID del último documento retornado cuando `hasMore` sea `True`; en caso contrario `null`.

## Validaciones y errores (sin cambios)

- `400`: `userId` faltante o vacío.
- `404`: `users/{userId}` no existe.
- `404`: si `routeId` viene y la ruta no existe.
- `500`: error interno.

Errores retornan body vacío, con CORS.

## Firestore

- Colección: `users/{userId}/myRoutes` (`FirestoreCollections.USER_MY_ROUTES`)
- Modo lista:
  - Query con `order_by=[("createdAt","desc")]`
  - `limit` (si aplica)
  - `start_after_doc_id=startAfterDocId` (si aplica)

## Testing (criterios de salida)

Agregar/actualizar `functions/tests/test_users_get_my_routes.py` con, mínimo:

- Lista legacy (sin params de paginación) retorna **array** 200.
- Lista paginada (con `limit`) retorna objeto con `result` y `pagination`.
- Cursor: request con `startAfterDocId` llama `query_documents(..., start_after_doc_id=...)`.
- `limit` inválido cae a default.
- `userId` faltante ⇒ 400.
- `userId` no existe ⇒ 404.
- `routeId` detalle ⇒ contrato sin cambios (200 con objeto; 404 si no existe).
- Múltiples llamadas seguidas: 2 páginas estables (primera retorna `lastDocId`, segunda usa ese cursor).

Cobertura >= 90% para el scope del módulo bajo test.

## Docs (criterios de salida)

Actualizar:

- `functions/users/README.md`:
  - Documentar `limit` y `startAfterDocId` para GET lista.
  - Explicar compatibilidad: array legacy vs response paginada.
  - Ejemplos cURL para ambos modos.
- `README.md` raíz, sección `4.1.2 my-routes`:
  - Actualizar `GET /api/users/my-routes` con paginación y ejemplos.

