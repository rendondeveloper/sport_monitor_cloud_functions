# Module: routes

Router central para la gestión de rutas de evento (tracks y waypoints).

La función `route_route` actúa como dispatcher: recibe todas las solicitudes bajo
`/api/routes/` y las delega al handler correspondiente según el método HTTP y el path final.

**Región**: `us-central1`

**Paths soportados**

| Método | Path | Acción |
|--------|------|--------|
| POST | `/api/routes/{userId}/create` | Crear ruta con waypoints |
| PUT | `/api/routes/{userId}/update` | Actualizar ruta |
| GET | `/api/routes/{userId}/get` | Obtener ruta por ID |
| GET | `/api/routes/{userId}/list` | Listar rutas de un evento |
| DELETE | `/api/routes/{userId}/delete` | Eliminar ruta |
| GET | `/api/routes/{userId}/event-categories` | Categorías del evento |
| GET | `/api/routes/{userId}/event-days` | Días de carrera del evento |

---

## Autorización — cómo funciona el {userId}

> **Importante**: este módulo usa un esquema de autorización en dos capas.

**Capa 1 — Autenticación (token)**
El Bearer token se valida una sola vez en el router (`route_route`). Sirve para confirmar que el request viene de un usuario autenticado en Firebase. El UID del token **no se usa** para determinar permisos.

**Capa 2 — Ownership (userId en el path)**
El `{userId}` que va en la URL es el UID del propietario del evento. Cada handler verifica que el documento del evento en Firestore tenga el campo `creator` igual a ese `userId`:

```
events/{eventId}  →  { "creator": "{userId}", ... }
```

Si `creator != userId`, la respuesta es **404** (no 403) — el evento no se expone como existente a quien no es el dueño.

**Causa frecuente de 404 inesperado:**
- El `{userId}` en la URL no coincide con el campo `creator` del evento en Firestore.
- El evento existe pero su campo se llama `creatorId`, `ownerId` u otro nombre en lugar de `creator`.

---

## POST /api/routes/{userId}/create

Crea una ruta de evento con sus waypoints (checkpoints) en una sola operación atómica.

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Body (JSON)**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `name` | string | Sí | Nombre de la ruta |
| `eventId` | string | Sí | ID del evento padre |
| `colorTrack` | number (int) | Sí | Color ARGB como entero. Ej: `4293000015` (= `0xFFD9534F`) |
| `width` | number (double) | Sí | Ancho del track. Ej: `3.0` |
| `routeUrl` | string | No | URL del archivo GPX en Storage |
| `categoryIds` | array[string] | No | IDs de categorías. Default `[]` |
| `dayOfRaceIds` | array[string] | No | IDs de días de carrera. Default `[]` |
| `visibleForPilots` | boolean | No | Visibilidad para pilotos en app móvil |
| `trackPoints` | array[object] | No | Puntos inline del track: `{lat, lng, ele?}` |
| `waypoints` | array[object] | No | Waypoints → se guardan como checkpoints de la ruta |

**Campos de cada waypoint**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `name` | string | Sí | Nombre del waypoint |
| `order` | int | Sí | Índice de posición (para ordenar al recuperar) |
| `coordinates` | string | Sí | `"lat,lng"` Ej: `"40.123,-74.456"` |
| `checkpointTypeId` | string | No | ID del tipo de checkpoint |
| `iconCustom` | string | No | Ícono personalizado |
| `assignedStaffIds` | array[string] | No | IDs de staff asignado. Default `[]` |

**Respuesta exitosa — 200**

```json
{
  "id": "newRouteId",
  "name": "Ruta Etapa 1",
  "createdAt": "2026-04-30T12:00:00+00:00",
  "updatedAt": "2026-04-30T12:00:00+00:00"
}
```

**Errores**

| Código | Causa |
|---|---|
| 400 | Body inválido, campo requerido faltante o vacío |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado, o `{userId}` no coincide con el campo `creator` del evento |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X POST "https://system-track-monitor.web.app/api/routes/{userId}/create" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ruta Etapa 1",
    "eventId": "evt_abc123",
    "colorTrack": 4293000015,
    "width": 3.0,
    "routeUrl": "https://storage.example.com/routes/route.gpx",
    "categoryIds": ["cat_id_1", "cat_id_2"],
    "dayOfRaceIds": ["day_id_1"],
    "visibleForPilots": true,
    "trackPoints": [
      { "lat": 40.123, "lng": -74.456, "ele": 100.0 }
    ],
    "waypoints": [
      {
        "name": "Waypoint 1",
        "order": 0,
        "coordinates": "40.123,-74.456",
        "checkpointTypeId": "type_id_1",
        "iconCustom": "",
        "assignedStaffIds": []
      }
    ]
  }'
```

**Notas**
- La ruta y todos sus waypoints se crean en un único batch atómico.
- Si `waypoints` está vacío o ausente, solo se crea el documento de ruta.
- Los waypoints se guardan en `events/{eventId}/routes/{routeId}/checkpoints/`.

---

## PUT /api/routes/{userId}/update

Actualiza una ruta de evento. Si se incluye `waypoints`, reemplaza todos los checkpoints existentes.

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Body (JSON)**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `eventId` | string | Sí | ID del evento |
| `routeId` | string | Sí | ID de la ruta a actualizar |
| `name` | string | No | Nuevo nombre |
| `colorTrack` | number | No | Nuevo color ARGB |
| `width` | number | No | Nuevo ancho |
| `routeUrl` | string | No | Nueva URL GPX |
| `categoryIds` | array[string] | No | Reemplaza categorías |
| `dayOfRaceIds` | array[string] | No | Reemplaza días de carrera |
| `visibleForPilots` | boolean | No | Nueva visibilidad |
| `trackPoints` | array[object] | No | Nuevos puntos del track |
| `waypoints` | array[object] | No | Si está presente, reemplaza todos los checkpoints existentes |

**Respuesta exitosa — 200** (sin cuerpo)

**Errores**

| Código | Causa |
|---|---|
| 400 | Body inválido, `eventId` o `routeId` faltante |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado, `{userId}` no coincide con `creator`, o ruta no existe |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X PUT "https://system-track-monitor.web.app/api/routes/{userId}/update" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": "evt_abc123",
    "routeId": "route_xyz",
    "name": "Ruta Etapa 1 — actualizada",
    "colorTrack": 4278222848,
    "waypoints": [
      { "name": "WP1", "order": 0, "coordinates": "40.123,-74.456" }
    ]
  }'
```

---

## GET /api/routes/{userId}/get

Retorna una ruta de evento por ID, incluyendo sus checkpoints.

**Handler**: `routes/get_event_route.py`

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `eventId` | string | Sí | ID del evento |
| `routeId` | string | Sí | ID de la ruta |

**Respuesta exitosa — 200**

```json
{
  "id": "routeId",
  "name": "Ruta Etapa 1",
  "colorTrack": 4293000015,
  "width": 3.0,
  "checkpoints": [
    { "id": "cp1", "name": "WP1", "order": 0, "coordinates": "40.123,-74.456" }
  ]
}
```

**Errores**

| Código | Causa |
|---|---|
| 400 | `{userId}`, `eventId` o `routeId` faltante o vacío |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado, `{userId}` no coincide con `creator`, o ruta no existe |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X GET "https://system-track-monitor.web.app/api/routes/{userId}/get?eventId=evt_abc123&routeId=route_xyz" \
  -H "Authorization: Bearer {token}"
```

---

## GET /api/routes/{userId}/list

Lista todas las rutas de un evento. Retorna `[]` si no hay rutas.

**Handler**: `routes/list_event_route.py`

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `eventId` | string | Sí | ID del evento |

**Respuesta exitosa — 200**

```json
[
  { "id": "route1", "name": "Etapa 1", "colorTrack": 4293000015 },
  { "id": "route2", "name": "Etapa 2", "colorTrack": 4278222848 }
]
```

**Errores**

| Código | Causa |
|---|---|
| 400 | `{userId}` o `eventId` faltante o vacío |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado o `{userId}` no coincide con el campo `creator` del evento |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X GET "https://system-track-monitor.web.app/api/routes/{userId}/list?eventId=evt_abc123" \
  -H "Authorization: Bearer {token}"
```

---

## DELETE /api/routes/{userId}/delete

Elimina una ruta y todos sus checkpoints.

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `eventId` | string | Sí | ID del evento |
| `routeId` | string | Sí | ID de la ruta a eliminar |

**Respuesta exitosa — 200** (sin cuerpo)

**Errores**

| Código | Causa |
|---|---|
| 400 | `eventId` o `routeId` faltante o vacío |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado, `{userId}` no coincide con `creator`, o ruta no existe |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X DELETE "https://system-track-monitor.web.app/api/routes/{userId}/delete?eventId=evt_abc123&routeId=route_xyz" \
  -H "Authorization: Bearer {token}"
```

**Notas**
- Se eliminan en cascada todos los checkpoints bajo `routes/{routeId}/checkpoints/`.

---

## GET /api/routes/{userId}/event-categories

Retorna las categorías del evento.

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `eventId` | string | Sí | ID del evento |

**Respuesta exitosa — 200**

```json
["Categoría A", "Categoría B"]
```

**Errores**

| Código | Causa |
|---|---|
| 400 | `eventId` faltante o vacío |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado o `{userId}` no coincide con `creator` |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X GET "https://system-track-monitor.web.app/api/routes/{userId}/event-categories?eventId=evt_abc123" \
  -H "Authorization: Bearer {token}"
```

---

## GET /api/routes/{userId}/event-days

Retorna los días de carrera del evento.

**Headers**
- `Authorization: Bearer {token}` (requerido)

**Path params**
- `{userId}`: UID del creador del evento. Debe coincidir con el campo `creator` del evento en Firestore.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `eventId` | string | Sí | ID del evento |

**Respuesta exitosa — 200**

```json
[
  { "id": "day1", "name": "Día 1", "date": "2026-05-10" },
  { "id": "day2", "name": "Día 2", "date": "2026-05-11" }
]
```

**Errores**

| Código | Causa |
|---|---|
| 400 | `eventId` faltante o vacío |
| 401 | Token inválido o faltante |
| 404 | Evento no encontrado o `{userId}` no coincide con `creator` |
| 500 | Error interno |

**Ejemplo curl**

```bash
curl -X GET "https://system-track-monitor.web.app/api/routes/{userId}/event-days?eventId=evt_abc123" \
  -H "Authorization: Bearer {token}"
```
