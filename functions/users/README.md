# Package Users

Este package expone una sola Cloud Function: `user_route`.

`user_route` valida CORS, método HTTP y Bearer token una sola vez, y después despacha por path a handlers internos de usuarios.

## Endpoints servidos por `user_route`

- `GET /api/users/read`
- `GET /api/users/profile` (compatibilidad de `read`)
- `GET /api/users/personalData`
- `GET /api/users/healthData`
- `GET /api/users/emergencyContacts`
- `GET /api/users/membership`
- `GET /api/users/subscribedEvents`
- `POST /api/users/create`
- `PUT /api/users/update`
- `DELETE /api/users/emergencyContacts`
- `DELETE /api/users/vehicles` (legacy)
- `POST /api/users/my-routes`
- `GET /api/users/my-routes`
- `PUT /api/users/my-routes/{routeId}/notes`
- `DELETE /api/users/my-routes/{routeId}`
- `DELETE /api/users/my-routes/{routeId}/notes`

## `my-routes`

Gestiona rutas personales del usuario con subcolecciones para puntos y notas.

**URLs base para los cURL de esta sección:**

- **Hosting:** `https://system-track-monitor.web.app`
- **Cloud Function `user_route` (2nd gen):** `https://user-route-xa26lpxdea-uc.a.run.app` — misma ruta bajo `/api/users/...`; si el deploy cambia la URL, revisar Firebase Console → Functions.

### Estructura Firestore

- `users/{userId}/myRoutes/{routeId}`
- `users/{userId}/myRoutes/{routeId}/points/{pointId}`
- `users/{userId}/myRoutes/{routeId}/notes/{identifier}`
- `users/{userId}/myRoutes/{routeId}/trackStyles/{styleId}`

IDs autogenerados por Firebase:

- Rutas: auto ID (ej. `aBcD123...`)
- Points: auto ID (ej. `xYz987...`)
- Notes: ID = `identifier` enviado por frontend (ej. `7`, `8`)
- Track styles: auto ID (ej. `sTy123...`)

### POST `/api/users/my-routes`

Crea una ruta y, en la misma operación, crea los subdocumentos de `points`, `notes` y `trackStyles`.

#### Documento de ruta (Firestore)

El documento `users/{userId}/myRoutes/{routeId}` incluye el campo:

- `distance`: float en **kilómetros** calculado desde `points` (suma de distancias entre puntos consecutivos válidos en el orden recibido). El resultado se **redondea hacia arriba a 1 decimal (###.#)**. Si `points` es `null` o no hay suficientes puntos válidos, se guarda `0.0`.

#### Reglas del payload

- `userId` requerido.
- `identifier` requerido (int, ID local del dispositivo). Antes de crear, se consultan las rutas existentes del usuario en `myRoutes`. Si ya existe una ruta con el mismo `identifier` (campo persistido, tipo entero), el nuevo documento se guarda con `max(identifiers existentes) + 1`. Si no hay colisión, se guarda el valor recibido.
- `name` requerido.
- `description` opcional. Si no viene, viene `null`, vacío o solo whitespace, se guarda `""`.
- `eventId` puede ser `null`.
- `points` puede ser `null` o array.
- `notes` puede ser `null` o array.
- `notes[].identifier` requerido (int). Se usa como ID del documento en Firestore.
- `notes[].photos` es opcional (si no viene, se normaliza a `[]`).
  Si llegan dos notas con el mismo `identifier`, la ultima sobrescribe la anterior (`set`).
- `trackStyles` puede ser `null`, omitido o array vacío (sin subdocumentos).
- Cada elemento de `trackStyles` debe ser objeto; se persiste tal como llega del cliente (p. ej. `startPointIndex`, `colorHex`). Los no-objeto se ignoran.

#### Ejemplo request

```json
{
  "userId": "USER_DOC_ID",
  "identifier": 16,
  "name": "test fotos",
  "eventId": null,
  "points": [
    {
      "altitudeMeters": 2348.500244140625,
      "date": "2026-04-16T16:06:03.393809Z",
      "identifierParent": 16,
      "isUploaded": false,
      "latitude": 19.2435863,
      "longitude": -99.0167349,
      "source": "LocationAccuracy.high",
      "speedKmh": 1.8004602670669556,
      "timeCurrent": "00:01:51"
    }
  ],
  "notes": [
    {
      "identifier": 7,
      "trackId": 16,
      "latitude": 19.2435642,
      "longitude": -99.0168343,
      "message": "primer check",
      "photos": [
        "http://gggg.jpg"
      ],
      "timestamp": "2026-04-16T16:06:42.510681Z"
    }
  ],
  "trackStyles": [
    {"startPointIndex": 0, "colorHex": "#FF0000"},
    {"startPointIndex": 150, "colorHex": "#00FF00"}
  ]
}
```

#### Respuesta exitosa

- `id`: ID autogenerado de Firestore del documento de ruta.
- `distance`: float en kilómetros, mismo valor calculado y persistido en el documento (desde `points` del body; ver reglas del campo en el doc de ruta).
- `identifierLocal` e `identifierNew`: en caso de **colisión** de `identifier` con una ruta previa del mismo usuario, `identifierLocal` es el valor enviado en el body y `identifierNew` el valor persistido (`max + 1`). Si **no** hubo colisión, ambos vienen en `null`.

```json
{
  "id": "AUTO_ROUTE_ID_FIREBASE",
  "distance": 1.2,
  "identifierLocal": null,
  "identifierNew": null
}
```

Ejemplo tras colisión (llegó `16`, ya existía `16` entre las rutas del usuario; máximo en colección `99` → se guarda `100`):

```json
{
  "id": "AUTO_ROUTE_ID_FIREBASE",
  "distance": 0.0,
  "identifierLocal": 16,
  "identifierNew": 100
}
```

### GET `/api/users/my-routes`

Un solo endpoint con dos modos:

- **Detalle**: `GET /api/users/my-routes?userId=USER_DOC_ID&routeId=AUTO_ROUTE_ID_FIREBASE` — incluye `points`, `notes` y `trackStyles` (ordenados por `startPointIndex` ascendente), más campos de la ruta (`description`, `distance`, etc.).
- **Lista (compatibilidad legacy + paginación opcional)**: `GET /api/users/my-routes?userId=USER_DOC_ID`

#### Query params

- `userId`: string (**requerido**)
- `routeId`: string (opcional) — activa modo detalle (sin cambios de contrato)

**Paginación (solo modo lista):**

- `limit`: int (opcional)
  - Default: `50`
  - Máximo: `100`
- `startAfterDocId`: string (opcional) — cursor basado en **docId** del último elemento retornado

#### Respuesta 200 (compatibilidad)

Para mantener compatibilidad con clientes legacy:

- **Sin `limit` y sin `startAfterDocId`** → retorna **array JSON** (legacy).
- **Con `limit` o con `startAfterDocId`** → retorna **objeto JSON** con `result` y `pagination`.

En **modo lista**, cada item incluye:

- `distance`: float en kilómetros de esa ruta (ya calculado y redondeado a 1 decimal).
- `distanceTotal`: float en kilómetros con **la suma de `distance` de todas las rutas del usuario**, **redondeada hacia arriba a 1 decimal (###.#)**.

**Legacy (array):**

```json
[
  {
    "id": "ROUTE_ID",
    "identifier": 16,
    "name": "Ruta 1",
    "eventId": null,
    "distance": 0.0,
    "distanceTotal": 12.3,
    "pointsCount": 0,
    "notesCount": 0
  }
]
```

**Paginada (objeto):**

```json
{
  "result": [
    {
      "id": "ROUTE_ID",
      "identifier": 16,
      "name": "Ruta 1",
      "eventId": null,
      "distance": 0.0,
      "distanceTotal": 12.3,
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

### PUT `/api/users/my-routes/{routeId}/notes`

Reemplaza **por completo** las notas de una ruta: borra todos los documentos actuales en `users/{userId}/myRoutes/{routeId}/notes` y escribe los del body. No es un merge parcial.

#### Path y query

- **Path**: `routeId` — ID de documento de la ruta en Firestore (el mismo `id` que devuelve el POST o el listado).
- **Query**: `userId` — string (**requerido**), ID del documento de usuario.

#### Headers

- `Authorization: Bearer {token Firebase}` (**requerido**)
- `Content-Type: application/json` (body JSON)

#### Body

- Objeto JSON con clave **`notes`**: array (**requerido**). Puede ser `[]` para dejar la ruta sin notas.
- Cada elemento de `notes` debe ser un objeto con **`identifier`** (int, **requerido**); se usa como ID del documento en la subcolección `notes` (misma regla que en el POST).
- **`photos`**: opcional; si falta o no es un array, se guarda `[]`. El resto de campos de cada nota se guardan tal cual lleguen (p. ej. `trackId`, `latitude`, `longitude`, `message`, `timestamp`, etc.).
- Si hay dos entradas con el mismo `identifier`, la última en el array es la que queda (mismo docId).

#### Efecto en el documento de la ruta

Tras un PUT exitoso se actualizan en `users/{userId}/myRoutes/{routeId}`:

- `notesCount`: número de notas escritas.
- `updatedAt`: timestamp ISO (UTC) actual.

#### Respuesta exitosa

- **200**: cuerpo vacío (sin JSON).

#### Errores

- **400**: `userId` faltante o vacío; body inválido; `notes` no es lista; alguna nota no es objeto o sin `identifier` int.
- **404**: usuario no existe o la ruta no existe para ese `userId`.
- **401**: token (validado en `user_route` antes del handler).
- **500**: error interno.

### DELETE `/api/users/my-routes/{routeId}`

Elimina la ruta completa: borra todos los documentos de `notes`, luego todos los de `points`, luego todos los de `trackStyles`, y finalmente el documento `users/{userId}/myRoutes/{routeId}`.

#### Path y query

- **Path**: `routeId` — ID del documento de la ruta en Firestore.
- **Query**: `userId` — string (**requerido**), ID del documento de usuario.

#### Headers

- `Authorization: Bearer {token Firebase}` (**requerido**)

#### Respuesta exitosa

- **200**: cuerpo vacío (sin JSON).

#### Errores

- **400**: `userId` faltante o vacío.
- **404**: usuario no existe o la ruta no existe para ese `userId`.
- **401**: token (validado en `user_route` antes del handler).
- **500**: error interno.

#### Ejemplo cURL

```bash
# Con Hosting (recomendado)
curl -X DELETE \
  'https://system-track-monitor.web.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# URL directa de la Cloud Function `user_route` (2nd gen, us-central1; ver consola Firebase si cambia)
curl -X DELETE \
  'https://user-route-xa26lpxdea-uc.a.run.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

### DELETE `/api/users/my-routes/{routeId}/notes`

Elimina **solo** las notas: borra todos los documentos en `users/{userId}/myRoutes/{routeId}/notes` y actualiza el documento de la ruta con `notesCount: 0` y `updatedAt` actual (misma idea que un PUT con `notes: []` sin reescribir notas nuevas).

#### Path y query

- **Path**: `routeId` — ID del documento de la ruta en Firestore.
- **Query**: `userId` — string (**requerido**), ID del documento de usuario.

#### Headers

- `Authorization: Bearer {token Firebase}` (**requerido**)

#### Respuesta exitosa

- **200**: cuerpo vacío (sin JSON).

#### Errores

- **400**: `userId` faltante o vacío.
- **404**: usuario no existe o la ruta no existe para ese `userId`.
- **401**: token (validado en `user_route` antes del handler).
- **500**: error interno.

#### Ejemplo cURL

```bash
# Con Hosting (recomendado)
curl -X DELETE \
  'https://system-track-monitor.web.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE/notes?userId=USER_DOC_ID' uj
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# URL directa de la Cloud Function `user_route` (2nd gen, us-central1; ver consola Firebase si cambia)
curl -X DELETE \
  'https://user-route-xa26lpxdea-uc.a.run.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE/notes?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

### cURL

```bash
# Crear ruta
curl -X POST \
  'https://system-track-monitor.web.app/api/users/my-routes' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{
    "userId": "USER_DOC_ID",
    "identifier": 16,
    "name": "test fotos",
    "eventId": null,
    "points": [
      {
        "altitudeMeters": 2348.500244140625,
        "date": "2026-04-16T16:06:03.393809Z",
        "identifierParent": 16,
        "isUploaded": false,
        "latitude": 19.2435863,
        "longitude": -99.0167349,
        "source": "LocationAccuracy.high",
        "speedKmh": 1.8004602670669556,
        "timeCurrent": "00:01:51"
      },
      {
        "altitudeMeters": 2351.10009765625,
        "date": "2026-04-16T16:07:03.393809Z",
        "identifierParent": 16,
        "isUploaded": false,
        "latitude": 19.2436123,
        "longitude": -99.0167122,
        "source": "LocationAccuracy.high",
        "speedKmh": 8.245000839233398,
        "timeCurrent": "00:02:51"
      }
    ],
    "notes": [
      {
        "identifier": 7,
        "trackId": 16,
        "latitude": 19.2435642,
        "longitude": -99.0168343,
        "message": "primer check",
        "photos": [
          "http://gggg.jpg",
          "http://gggg2.jpg"
        ],
        "timestamp": "2026-04-16T16:06:42.510681Z"
      },
      {
        "identifier": 8,
        "trackId": 16,
        "latitude": 19.2434215,
        "longitude": -99.0168844,
        "message": "segunda nota sin fotos",
        "photos": [],
        "timestamp": "2026-04-16T16:08:42.510681Z"
      }
    ]
  }'

# Listar rutas
curl -X GET \
  'https://system-track-monitor.web.app/api/users/my-routes?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Listar rutas (paginado) — primera página
curl -X GET \
  'https://system-track-monitor.web.app/api/users/my-routes?userId=USER_DOC_ID&limit=50' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Listar rutas (paginado) — segunda página usando cursor (startAfterDocId = pagination.lastDocId)
curl -X GET \
  'https://system-track-monitor.web.app/api/users/my-routes?userId=USER_DOC_ID&limit=50&startAfterDocId=ROUTE_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Detalle de ruta
curl -X GET \
  'https://system-track-monitor.web.app/api/users/my-routes?userId=USER_DOC_ID&routeId=AUTO_ROUTE_ID_FIREBASE' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Reemplazar todas las notas de una ruta (notes=[] borra todas las notas)
curl -X PUT \
  'https://system-track-monitor.web.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE/notes?userId=USER_DOC_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{
    "notes": [
      {
        "identifier": 7,
        "trackId": 16,
        "latitude": 19.2435642,
        "longitude": -99.0168343,
        "message": "primer check actualizado",
        "photos": [
          "https://example.com/photo_1.jpg"
        ],
        "timestamp": "2026-04-16T16:06:42.510681Z"
      }
    ]
  }'

# Eliminar solo las notas de una ruta (Hosting)
curl -X DELETE \
  'https://system-track-monitor.web.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE/notes?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Eliminar solo las notas (URL directa user_route en Cloud Run)
curl -X DELETE \
  'https://user-route-xa26lpxdea-uc.a.run.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE/notes?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Eliminar la ruta completa: notas, puntos y documento de ruta (Hosting)
curl -X DELETE \
  'https://system-track-monitor.web.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'

# Eliminar la ruta completa (URL directa user_route en Cloud Run)
curl -X DELETE \
  'https://user-route-xa26lpxdea-uc.a.run.app/api/users/my-routes/AUTO_ROUTE_ID_FIREBASE?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

## Códigos de respuesta (my-routes)

- `201`: creación exitosa (POST)
- `200`: consulta exitosa (GET); actualización de notas exitosa (PUT, sin cuerpo); borrado de ruta o solo notas (DELETE, sin cuerpo)
- `400`: request inválido
- `401`: token inválido/faltante
- `404`: usuario o ruta no encontrada
- `500`: error interno

## Changelog

- 2026-05-16: `POST /api/users/my-routes` incluye `distance` en la respuesta 201 (mismo valor guardado en Firestore).
- 2026-05-15: `POST /api/users/my-routes` resuelve colisiones de `identifier` por usuario (`max+1`) y amplía la respuesta 201 con `identifierLocal` / `identifierNew` (`null` si no hubo colisión).
- 2026-05-12: cURL de DELETE duplicados bajo cada subsección DELETE, bloque consolidado con variantes Hosting + Cloud Run, y URLs base en intro de `my-routes`.
- 2026-05-12: `DELETE /api/users/my-routes/{routeId}` y `DELETE /api/users/my-routes/{routeId}/notes` (cURLs en esta sección).
- 2026-05-12: Documentación ampliada de `PUT /api/users/my-routes/{routeId}/notes` (reemplazo completo, `notesCount`/`updatedAt`, reglas de body y errores; ejemplo cURL alineado con `photos`).
- 2026-05-06: `GET /api/users/my-routes` agrega paginación opcional en modo lista (`limit`, `startAfterDocId`) manteniendo compatibilidad legacy (sin params retorna array; con params retorna `{result, pagination}`).
- 2026-05-16: Subcolección `trackStyles` en POST create y GET detalle; cascada en DELETE ruta.
