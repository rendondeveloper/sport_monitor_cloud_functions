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

## `my-routes`

Gestiona rutas personales del usuario con subcolecciones para puntos y notas.

### Estructura Firestore

- `users/{userId}/myRoutes/{routeId}`
- `users/{userId}/myRoutes/{routeId}/points/{pointId}`
- `users/{userId}/myRoutes/{routeId}/notes/{identifier}`

IDs autogenerados por Firebase:

- Rutas: auto ID (ej. `aBcD123...`)
- Points: auto ID (ej. `xYz987...`)
- Notes: ID = `identifier` enviado por frontend (ej. `7`, `8`)

### POST `/api/users/my-routes`

Crea una ruta y, en la misma operación, crea los subdocumentos de `points` y `notes`.

#### Reglas del payload

- `userId` requerido.
- `identifier` requerido (int, ID local del dispositivo).
- `name` requerido.
- `description` requerido.
- `eventId` puede ser `null`.
- `points` puede ser `null` o array.
- `notes` puede ser `null` o array.
- `notes[].identifier` requerido (int). Se usa como ID del documento en Firestore.
- `notes[].photos` es opcional (si no viene, se normaliza a `[]`).
  Si llegan dos notas con el mismo `identifier`, la ultima sobrescribe la anterior (`set`).

#### Ejemplo request

```json
{
  "userId": "USER_DOC_ID",
  "identifier": 16,
  "name": "test fotos",
  "description": "test fotos",
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
  ]
}
```

#### Respuesta exitosa

```json
{
  "id": "AUTO_ROUTE_ID_FIREBASE"
}
```

### GET `/api/users/my-routes`

Un solo endpoint con dos modos:

- Lista: `GET /api/users/my-routes?userId=USER_DOC_ID`
- Detalle: `GET /api/users/my-routes?userId=USER_DOC_ID&routeId=AUTO_ROUTE_ID_FIREBASE`

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
    "description": "test fotos",
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

# Detalle de ruta
curl -X GET \
  'https://system-track-monitor.web.app/api/users/my-routes?userId=USER_DOC_ID&routeId=AUTO_ROUTE_ID_FIREBASE' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

## Códigos de respuesta (my-routes)

- `201`: creación exitosa (POST)
- `200`: consulta exitosa (GET)
- `400`: request inválido
- `401`: token inválido/faltante
- `404`: usuario o ruta no encontrada
- `500`: error interno
