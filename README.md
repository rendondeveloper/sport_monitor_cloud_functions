# Sport Monitor Cloud Functions

## 📋 Descripción del Proyecto

Este proyecto contiene las **Cloud Functions de Firebase** desarrolladas en Python para el sistema **Sport Monitor**. Estas funciones proporcionan servicios backend para la gestión y control de eventos deportivos, incluyendo:

- **Gestión de Eventos**: Obtención de listados y detalles de eventos deportivos
- **Gestión de Usuarios**: Obtención de perfiles de usuario con eventos asignados
- **Tracking de Competidores**: Seguimiento en tiempo real de competidores durante eventos
- **Gestión de Checkpoints**: Control de puntos de control en eventos deportivos

Las funciones están desplegadas en **Firebase Cloud Functions** y proporcionan APIs REST para ser consumidas desde aplicaciones cliente (Flutter, Web, etc.).

## 🏗️ Arquitectura

### Estructura del Proyecto

```
functions/
├── events/              # Package: Gestión de Eventos
│   ├── events_customer.py          # events
│   └── events_detail_customer.py  # event_detail
├── users/               # Package: Gestión de Usuarios
│   └── user_profile.py            # user_profile
├── checkpoints/         # Package: Gestión de Checkpoints
│   ├── day_of_race_active.py       # day_of_race_active
│   ├── checkpoint.py               # checkpoint
│   ├── competitor_tracking.py      # competitor_tracking
│   └── days_of_race.py         # days_of_race
├── tracking/           # Package: Tracking de Competidores
│   ├── tracking_checkpoint.py     # track_event_checkpoint
│   └── tracking_competitors.py     # track_competitors, track_competitors_off
├── models/             # Modelos de datos
└── utils/              # Utilidades compartidas
```

### Información del Proyecto

- **Project ID**: `system-track-monitor`
- **Región**: `us-central1`
- **Runtime**: Python 3.12
- **Tipo**: Firebase Cloud Functions (2nd Gen)

## 📦 Packages y Funciones

---

## 📦 Package: Events

Funciones relacionadas con la gestión y consulta de eventos deportivos.

### 1. `events`

Obtiene una lista paginada de eventos desde Firestore. Retorna eventos en formato `EventShortDocument` (versión simplificada con campos esenciales).

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://events-xa26lpxdea-uc.a.run.app`

#### Parámetros (Query Parameters)

| Parámetro   | Tipo    | Requerido | Descripción                                                          |
| ----------- | ------- | --------- | -------------------------------------------------------------------- |
| `size`      | integer | No        | Número de eventos por página (default: 50, max: 100)                 |
| `page`      | integer | No        | Número de página (default: 1)                                        |
| `lastDocId` | string  | No        | ID del último documento para cursor-based pagination (más eficiente) |

#### Campos Retornados

- `id`: ID del evento
- `title`: Título del evento
- `subtitle`: Subtítulo (opcional)
- `status`: Estado del evento (draft, published, inProgress, etc.)
- `startDateTime`: Fecha y hora de inicio en formato ISO 8601
- `timezone`: Zona horaria (opcional)
- `locationName`: Nombre de la ubicación
- `imageUrl`: URL de la imagen (opcional)

#### Comandos cURL

**Primera página (sin parámetros):**

```bash
curl -X GET \
  'https://events-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json'
```

**Con paginación (size y page):**

```bash
curl -X GET \
  'https://events-xa26lpxdea-uc.a.run.app?size=20&page=1' \
  -H 'Content-Type: application/json'
```

**Paginación con cursor (recomendado - más eficiente):**

```bash
curl -X GET \
  'https://events-xa26lpxdea-uc.a.run.app?size=20&lastDocId=id-del-ultimo-documento' \
  -H 'Content-Type: application/json'
```

**Con todos los parámetros:**

```bash
curl -X GET \
  'https://events-xa26lpxdea-uc.a.run.app?size=20&page=1&lastDocId=id-del-ultimo-documento' \
  -H 'Content-Type: application/json'
```

#### Respuesta Exitosa (200)

```json
{
  "items": [
    {
      "id": "event-id-1",
      "title": "Evento Deportivo 2025",
      "subtitle": "Subtítulo del evento",
      "status": "published",
      "startDateTime": "2025-01-15T10:00:00",
      "timezone": "America/Mexico_City",
      "locationName": "Estadio Principal",
      "imageUrl": "https://example.com/image.jpg"
    }
  ],
  "pagination": {
    "limit": 20,
    "page": 1,
    "hasMore": true,
    "lastDocId": "event-id-20"
  }
}
```

---

### 2. `event_detail`

Obtiene el detalle completo de un evento específico desde Firestore. Retorna el objeto `EventInfo` completo con todos sus campos.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://event-detail-xa26lpxdea-uc.a.run.app`

#### Parámetros (Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción               |
| --------- | ------ | --------- | ------------------------- |
| `eventId` | string | **Sí**    | ID del evento a consultar |

#### Campos Retornados (EventInfo)

- `name`: Nombre del evento
- `descriptionShort`: Descripción corta
- `description`: Descripción completa
- `photoMain`: URL de la imagen principal
- `photoUrls`: Array de URLs de imágenes adicionales
- `startEvent`: Fecha y hora de inicio
- `endEvent`: Fecha y hora de fin
- `address`: Dirección del evento
- `historia`: Historia del evento
- `website`: Sitio web del evento
- Y cualquier otro campo presente en el documento

#### Comandos cURL

**Obtener detalle de evento:**

```bash
curl -X GET \
  'https://event-detail-xa26lpxdea-uc.a.run.app?eventId=TU_EVENT_ID' \
  -H 'Content-Type: application/json'
```

**Ejemplo con eventId específico:**

```bash
curl -X GET \
  'https://event-detail-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://event-detail-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json'
```

#### Respuestas

**200 OK - Evento encontrado:**

```json
{
  "name": "Nombre del evento",
  "descriptionShort": "Descripción corta",
  "description": "Descripción completa del evento",
  "photoMain": "https://example.com/main.jpg",
  "photoUrls": [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg"
  ],
  "startEvent": "2025-01-15T10:00:00Z",
  "endEvent": "2025-01-16T18:00:00Z",
  "address": "Dirección del evento",
  "historia": "Historia del evento",
  "website": "https://example.com"
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta `eventId`

**404 Not Found** - Sin cuerpo (solo código HTTP) - cuando el evento no existe

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor

---

## 📦 Package: Users

Funciones relacionadas con la gestión y consulta de perfiles de usuario.

### 3. `user_profile`

Obtiene el perfil completo de un usuario desde Firestore. Retorna el objeto `UserProfile` completo con todos sus campos, incluyendo eventos asignados y checkpoints filtrados según las relaciones del usuario.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://user-profile-xa26lpxdea-uc.a.run.app`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado. El parámetro `userId` es en realidad el `authUserId` (ID de autenticación de Firebase), no el ID del documento en Firestore. La búsqueda se realiza usando una query `where('authUserId', '==', authUserId)`.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                                                                        |
| --------- | ------ | --------- | ---------------------------------------------------------------------------------- |
| `userId`  | string | **Sí**    | `authUserId` del usuario (ID de autenticación de Firebase), no el ID del documento |

#### Campos Retornados (UserProfile)

**Campos del Usuario:**

- `id`: ID del documento del usuario en Firestore
- `authUserId`: ID de autenticación de Firebase
- `personalData`: Objeto con:
  - `fullName`: Nombre completo del usuario
  - `email`: Correo electrónico
  - `phone`: Teléfono
- `emergencyContact`: Objeto con:
  - `fullName`: Nombre completo del contacto de emergencia
  - `phone`: Teléfono del contacto de emergencia
- `userData`: Objeto con:
  - `username`: Nombre de usuario
- `eventStaffRelations`: Array de relaciones usuario-evento (estructura original)
- `assignedEvents`: Array de eventos asignados con checkpoints filtrados
- `createdAt`: Fecha de creación en formato ISO 8601
- `updatedAt`: Fecha de actualización en formato ISO 8601
- `avatarUrl`: URL del avatar del usuario (opcional, puede ser null)
- `isActive`: Estado activo del usuario (boolean)
- `deletedAt`: Fecha de eliminación en formato ISO 8601 (opcional, puede ser null)
- `disableAt`: Fecha de deshabilitación en formato ISO 8601 (opcional, puede ser null)
- `appVersion`: Versión de la app (default: "2.0.0")

**Estructura de `assignedEvents`:**
Cada evento en `assignedEvents` incluye:

- Todos los campos del evento desde Firestore
- `checkpoints`: Array de checkpoints filtrados según `checkpointIds` de la relación

#### Comandos cURL

**Obtener perfil de usuario (con token Bearer y authUserId):**

```bash
curl -X GET \
  'https://user-profile-xa26lpxdea-uc.a.run.app?userId=TU_AUTH_USER_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con authUserId específico:**

```bash
curl -X GET \
  'https://user-profile-xa26lpxdea-uc.a.run.app?userId=firebase-auth-uid-123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Nota**: El parámetro `userId` debe ser el `authUserId` (ID de autenticación de Firebase), no el ID del documento en Firestore.

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://user-profile-xa26lpxdea-uc.a.run.app?userId=firebase-auth-uid-123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin authUserId):**

```bash
curl -X GET \
  'https://user-profile-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://user-profile-xa26lpxdea-uc.a.run.app?userId=firebase-auth-uid-123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 404 (usuario no existente con ese authUserId):**

```bash
curl -X GET \
  'https://user-profile-xa26lpxdea-uc.a.run.app?userId=auth-uid-que-no-existe' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Usuario encontrado:**

```json
{
  "id": "user-id",
  "authUserId": "firebase-auth-uid",
  "personalData": {
    "fullName": "Nombre Completo",
    "email": "email@example.com",
    "phone": "+1234567890"
  },
  "emergencyContact": {
    "fullName": "Contacto Emergencia",
    "phone": "+1234567890"
  },
  "userData": {
    "username": "username"
  },
  "eventStaffRelations": [
    {
      "eventId": "event-id",
      "checkpointIds": ["cp1", "cp2"]
    }
  ],
  "assignedEvents": [
    {
      "id": "event-id",
      "name": "Nombre del Evento",
      "rallySystemId": "rally-id",
      "status": "EN_CURSO",
      "checkpoints": [
        {
          "id": "cp1",
          "name": "Inicio",
          "type": "start",
          "status": "active"
        }
      ]
    }
  ],
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z",
  "avatarUrl": "https://example.com/avatar.jpg",
  "isActive": true,
  "deletedAt": null,
  "disableAt": null,
  "appVersion": "2.0.0"
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta el parámetro `userId` (authUserId) o está vacío

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**404 Not Found** - Sin cuerpo (solo código HTTP) - cuando no se encuentra ningún usuario con el `authUserId` proporcionado en Firestore

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token para buscar el usuario.
- **Parámetro userId**: El parámetro `userId` es en realidad el `authUserId` (ID de autenticación de Firebase), **NO** el ID del documento en Firestore. La búsqueda se realiza usando `where('authUserId', '==', authUserId).limit(1)`.
- **Búsqueda por authUserId**: La función busca el usuario en la colección `users` usando el campo `authUserId`, no el ID del documento. Esto coincide con cómo se consulta en la app Flutter.
- **Eventos Asignados**: Los eventos se obtienen desde `eventStaffRelations` del usuario. Solo se incluyen los checkpoints cuyo ID esté en el array `checkpointIds` de cada relación.
- **Campos Opcionales**: Los campos `avatarUrl`, `deletedAt`, y `disableAt` pueden ser `null` si no están definidos en el documento.
- **Compatibilidad**: La respuesta JSON es compatible con `UserProfile.fromMap()` o `UserProfile.fromJson()` en Flutter.

---

## 📦 Package: Checkpoints

Funciones relacionadas con la gestión de checkpoints y días de carrera en eventos deportivos.

### 4. `day_of_race_active`

Obtiene el día de carrera activo para un evento específico desde Firestore. Retorna el primer documento de la subcolección `dayOfRaces` que tenga `isActivate: true`.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://day-of-race-active-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/checkpoint/dayofrace/active/{eventId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                                    |
| --------- | ------ | --------- | ---------------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento (puede venir en path o query)   |

**Nota**: El `eventId` puede venir en el path de la URL (`/api/checkpoint/dayofrace/active/{eventId}`) o como query parameter (`?eventId=xxx`).

#### Campos Retornados (DayOfRace)

- `id`: ID del documento del día de carrera
- `createdAt`: Fecha de creación en formato ISO 8601
- `updatedAt`: Fecha de actualización en formato ISO 8601
- `day`: Nombre/descripción del día de carrera (ej: "Día 1")
- `isActivate`: Estado activo del día (siempre `true` ya que se filtra por este campo)
- Cualquier otro campo presente en el documento

#### Consulta Firestore

- **Ruta de colección**: `events/{eventId}/dayOfRaces`
- **Filtro**: `where('isActivate', '==', True)`
- **Límite**: 1 documento (el primero que cumpla la condición)
- **Retorno**: El primer documento que cumpla, o `404` si no existe

#### Comandos cURL

**Obtener día de carrera activo (con token Bearer y eventId en query):**

```bash
curl -X GET \
  'https://day-of-race-active-xa26lpxdea-uc.a.run.app?eventId=TU_EVENT_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con eventId específico:**

```bash
curl -X GET \
  'https://day-of-race-active-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Usando el endpoint con Hosting (eventId en path):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/checkpoint/dayofrace/active/abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://day-of-race-active-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin eventId):**

```bash
curl -X GET \
  'https://day-of-race-active-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://day-of-race-active-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 404 (día activo no encontrado):**

```bash
curl -X GET \
  'https://day-of-race-active-xa26lpxdea-uc.a.run.app?eventId=evento-sin-dia-activo' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Día de carrera activo encontrado:**

```json
{
  "id": "FM7eNdNOQfZGhQdDNgSE",
  "createdAt": "2025-11-13T19:48:01.459Z",
  "updatedAt": "2025-11-13T19:48:01.459Z",
  "day": "Día 1",
  "isActivate": true
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta el parámetro `eventId` o está vacío

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**404 Not Found** - Sin cuerpo (solo código HTTP) - cuando no se encuentra ningún día de carrera con `isActivate: true` para el evento proporcionado

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta la subcolección `events/{eventId}/dayOfRaces` y filtra por `isActivate: true`, retornando el primer documento que cumpla la condición.
- **Retorno**: Si no existe ningún día de carrera activo, la función retorna `404 Not Found`.
- **Timestamps**: Los campos `createdAt` y `updatedAt` se convierten automáticamente de Timestamps de Firestore a formato ISO 8601.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen estos campos.

---

### 5. `get_checkpoint`

Obtiene un checkpoint específico de un evento desde Firestore. Retorna el documento completo del checkpoint con todos sus campos.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-checkpoint-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/checkpoint/{checkpointId}/event/{eventId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro     | Tipo   | Requerido | Descripción                                    |
| ------------- | ------ | --------- | ---------------------------------------------- |
| `checkpointId` | string | **Sí**    | ID del checkpoint (puede venir en path o query) |
| `eventId`     | string | **Sí**    | ID del evento (puede venir en path o query)   |

**Nota**: Los parámetros pueden venir en el path de la URL (`/api/checkpoint/{checkpointId}/event/{eventId}`) o como query parameters (`?checkpointId=xxx&eventId=yyy`).

#### Campos Retornados (Checkpoint)

- `id`: ID del documento del checkpoint
- `name`: Nombre del checkpoint
- `order`: Orden del checkpoint
- `type`: Tipo del checkpoint (ej: "pass", "start", "finish")
- `status`: Estado del checkpoint (ej: "active", "inactive")
- `assignedStaffIds`: Array de IDs del staff asignado
- `coordinates`: Coordenadas del checkpoint (formato: "lat,lng")
- `logoUrl`: URL del logo del checkpoint (opcional, puede ser null)
- `createdAt`: Fecha de creación en formato ISO 8601
- `updatedAt`: Fecha de actualización en formato ISO 8601
- `eventRouteId`: Array de IDs de rutas del evento (opcional)
- `dayOfRaceId`: Array de IDs de días de carrera (opcional)
- Cualquier otro campo presente en el documento

#### Consulta Firestore

- **Ruta de colección**: `events/{eventId}/checkpoints/{checkpointId}`
- **Método**: Obtener documento por ID
- **Retorno**: El documento del checkpoint, o `404` si no existe

#### Comandos cURL

**Obtener checkpoint (con token Bearer y parámetros en query):**

```bash
curl -X GET \
  'https://get-checkpoint-xa26lpxdea-uc.a.run.app?checkpointId=TU_CHECKPOINT_ID&eventId=TU_EVENT_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con IDs específicos:**

```bash
curl -X GET \
  'https://get-checkpoint-xa26lpxdea-uc.a.run.app?checkpointId=7110Mif2Xx3AnmiN73HZ&eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Usando el endpoint con Hosting (parámetros en path):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/checkpoint/7110Mif2Xx3AnmiN73HZ/event/abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://get-checkpoint-xa26lpxdea-uc.a.run.app?checkpointId=7110Mif2Xx3AnmiN73HZ&eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin parámetros):**

```bash
curl -X GET \
  'https://get-checkpoint-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://get-checkpoint-xa26lpxdea-uc.a.run.app?checkpointId=7110Mif2Xx3AnmiN73HZ&eventId=abc123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 404 (checkpoint no encontrado):**

```bash
curl -X GET \
  'https://get-checkpoint-xa26lpxdea-uc.a.run.app?checkpointId=checkpoint-inexistente&eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Checkpoint encontrado:**

```json
{
  "id": "7110Mif2Xx3AnmiN73HZ",
  "name": "CP 10 GASOLINA ENTRADA A PEÑON",
  "order": 10,
  "type": "pass",
  "status": "active",
  "assignedStaffIds": ["85WfvOCFRVIusHHAFLYY"],
  "coordinates": "19.0423226,-100.0936652",
  "logoUrl": null,
  "createdAt": "2025-11-13T19:48:01.459Z",
  "updatedAt": "2025-11-13T19:48:01.459Z",
  "eventRouteId": [],
  "dayOfRaceId": []
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta alguno de los parámetros (`checkpointId` o `eventId`) o están vacíos

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**404 Not Found** - Sin cuerpo (solo código HTTP) - cuando no se encuentra el checkpoint con el ID proporcionado en el evento especificado

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta directamente el documento `events/{eventId}/checkpoints/{checkpointId}` en Firestore.
- **Retorno**: Si el checkpoint no existe, la función retorna `404 Not Found`.
- **Timestamps**: Los campos `createdAt` y `updatedAt` se convierten automáticamente de Timestamps de Firestore a formato ISO 8601.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen estos campos.
- **Parámetros flexibles**: Los parámetros pueden venir en el path de la URL o como query parameters, facilitando su uso desde diferentes clientes.

---

### 6. `competitor_tracking`

Obtiene la lista de competidores con su checkpoint específico y el nombre de la ruta asociada. Retorna un JSON mapeable a la clase `CompetitorTrackingWithRoute`, filtrando competidores visibles según su status y el tipo de checkpoint.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://competitor-tracking-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro      | Tipo   | Requerido | Descripción                                    |
| -------------- | ------ | --------- | ---------------------------------------------- |
| `eventId`      | string | **Sí**    | ID del evento (puede venir en path o query)   |
| `dayOfRaceId`  | string | **Sí**    | ID del día de carrera (puede venir en path o query) |
| `checkpointId` | string | **Sí**    | ID del checkpoint para filtrar (puede venir en path o query) |

**Nota**: Los parámetros pueden venir en el path de la URL (`/api/competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}`) o como query parameters (`?eventId=xxx&dayOfRaceId=yyy&checkpointId=zzz`).

#### Campos Retornados (CompetitorTrackingWithRoute)

**Estructura de respuesta:**

```json
{
  "success": true,
  "data": {
    "competitors": [...],
    "routeName": "Nombre de la Ruta"
  }
}
```

**Campos de `competitors` (array de CompetitorTracking):**

- `id`: ID del competidor
- `name`: Nombre del competidor
- `order`: Orden del competidor
- `category`: Categoría del competidor
- `number`: Número del competidor (string)
- `timeToStart`: Fecha y hora de inicio en formato ISO 8601 (puede ser null)
- `createdAt`: Fecha de creación en formato ISO 8601
- `updatedAt`: Fecha de actualización en formato ISO 8601
- `trackingCheckpoints`: Array con un solo elemento - el checkpoint específico solicitado:
  - `id`: ID del checkpoint
  - `name`: Nombre del checkpoint
  - `order`: Orden del checkpoint
  - `checkpointType`: Tipo de checkpoint (start, pass, timer, startTimer, endTimer, finish)
  - `statusCompetitor`: Status del competidor (none, check, out, outStart, outLast, disqualified)
  - `checkpointDisable`: ID del checkpoint deshabilitado (string vacío si no hay)
  - `checkpointDisableName`: Nombre del checkpoint deshabilitado (string vacío si no hay)
  - `passTime`: Fecha y hora de paso en formato ISO 8601
  - `note`: Nota opcional (puede ser null)

**Campo `routeName`:**

- `routeName`: Nombre de la ruta que contiene el `checkpointId` (puede ser null si no se encuentra)

#### Consultas Firestore

- **Competidores**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors`
- **Checkpoint por competidor**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints/{checkpointId}`
- **Rutas**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/routes`

#### Lógica de Filtrado: isCompetitorVisible

La función filtra competidores visibles según estas reglas:

| Status | Checkpoint Type | Visible |
|--------|----------------|---------|
| `out` | Cualquiera | ✅ Sí |
| `outStart` | `start` o `finish` | ✅ Sí |
| `outStart` | Otros | ❌ No |
| Otros | Cualquiera | ✅ Sí |

#### Comandos cURL

**Obtener tracking de competidores (con token Bearer y parámetros en query):**

```bash
curl -X GET \
  'https://competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=TU_EVENT_ID&dayOfRaceId=TU_DAY_ID&checkpointId=TU_CHECKPOINT_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con IDs específicos:**

```bash
curl -X GET \
  'https://competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=abc123&dayOfRaceId=day1&checkpointId=cp123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Usando el endpoint con Hosting (parámetros en path):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitor-tracking/abc123/day1/cp123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=abc123&dayOfRaceId=day1&checkpointId=cp123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin parámetros):**

```bash
curl -X GET \
  'https://competitor-tracking-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=abc123&dayOfRaceId=day1&checkpointId=cp123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Tracking de competidores encontrado:**

```json
{
  "success": true,
  "data": {
    "competitors": [
      {
        "id": "competitor_id",
        "name": "Nombre del Competidor",
        "order": 1,
        "category": "Categoría",
        "number": "123",
        "timeToStart": "2025-11-13T10:00:00.000Z",
        "createdAt": "2025-11-13T19:48:01.459Z",
        "updatedAt": "2025-11-13T19:48:01.459Z",
        "trackingCheckpoints": [
          {
            "id": "checkpoint_id",
            "name": "CP 10 GASOLINA ENTRADA A PEÑON",
            "order": 10,
            "checkpointType": "pass",
            "statusCompetitor": "check",
            "checkpointDisable": "",
            "checkpointDisableName": "",
            "passTime": "2025-11-13T19:48:01.459Z",
            "note": null
          }
        ]
      }
    ],
    "routeName": "Nombre de la Ruta"
  }
}
```

**200 OK - Sin competidores (lista vacía):**

```json
{
  "success": true,
  "data": {
    "competitors": [],
    "routeName": null
  }
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta alguno de los parámetros (`eventId`, `dayOfRaceId` o `checkpointId`) o están vacíos

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors` y para cada competidor obtiene su checkpoint específico.
- **Filtrado**: Solo se incluyen competidores que tienen el checkpoint específico solicitado y que pasan el filtro de visibilidad `isCompetitorVisible`.
- **Ruta**: La función busca la ruta cuyo array `checkpointIds` contiene el `checkpointId` solicitado. Si no se encuentra, `routeName` será `null`.
- **Timestamps**: Los campos de fecha se convierten automáticamente de Timestamps de Firestore a formato ISO 8601.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura `CompetitorTrackingWithRoute`.
- **Parámetros flexibles**: Los parámetros pueden venir en el path de la URL o como query parameters, facilitando su uso desde diferentes clientes.

---

### 7. `days_of_race`

Obtiene todos los días de carrera de un evento específico desde Firestore. Retorna un array directo de días de carrera mapeable a `List<DayOfRaces>`, sin aplicar filtros.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-days-of-race-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/days-of-race/{eventId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                                    |
| --------- | ------ | --------- | ---------------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento (puede venir en path o query)   |

**Nota**: El parámetro puede venir en el path de la URL (`/api/days-of-race/{eventId}`) o como query parameter (`?eventId=xxx`).

#### Campos Retornados (Array de DayOfRace)

Cada elemento del array contiene:

- `id`: ID del documento del día de carrera
- `day`: Fecha del día de carrera (formato: "YYYY-MM-DD")
- `isActivate`: Estado activo del día (boolean)
- `createdAt`: Fecha de creación en formato ISO 8601
- `updatedAt`: Fecha de actualización en formato ISO 8601
- Cualquier otro campo presente en el documento

#### Consulta Firestore

- **Ruta de colección**: `events/{eventId}/dayOfRaces`
- **Método**: Obtener todos los documentos sin filtros
- **Retorno**: Array de todos los días de carrera del evento (activos e inactivos)

#### Comandos cURL

**Obtener días de carrera (con token Bearer y eventId en query):**

```bash
curl -X GET \
  'https://get-days-of-race-xa26lpxdea-uc.a.run.app?eventId=TU_EVENT_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con eventId específico:**

```bash
curl -X GET \
  'https://get-days-of-race-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Usando el endpoint con Hosting (eventId en path):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/days-of-race/abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://get-days-of-race-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin eventId):**

```bash
curl -X GET \
  'https://get-days-of-race-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://get-days-of-race-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Días de carrera encontrados (array directo):**

```json
[
  {
    "id": "day_of_race_id_1",
    "day": "2025-11-13",
    "isActivate": true,
    "createdAt": "2025-11-13T19:48:01.459Z",
    "updatedAt": "2025-11-13T19:48:01.459Z"
  },
  {
    "id": "day_of_race_id_2",
    "day": "2025-11-14",
    "isActivate": false,
    "createdAt": "2025-11-13T19:48:01.459Z",
    "updatedAt": "2025-11-13T19:48:01.459Z"
  }
]
```

**200 OK - Sin días de carrera (array vacío):**

```json
[]
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta el parámetro `eventId` o está vacío

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta la subcolección `events/{eventId}/dayOfRaces` sin aplicar filtros. Retorna todos los días de carrera, activos e inactivos.
- **Formato de respuesta**: Retorna un array directo (sin wrapper) para facilitar el mapeo a `List<DayOfRaces>` en Flutter.
- **Array vacío**: Si no hay días de carrera, retorna `[]` (array vacío) con código 200 OK.
- **Timestamps**: Los campos `createdAt` y `updatedAt` se convierten automáticamente de Timestamps de Firestore a formato ISO 8601.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura `DayOfRaces`.
- **Parámetros flexibles**: El parámetro puede venir en el path de la URL o como query parameter, facilitando su uso desde diferentes clientes.
- **Sin filtros**: Esta API no aplica filtros (por ejemplo, por `isActivate`). Si se necesita filtrar, debe hacerse en el cliente.

---

## 📦 Package: Tracking

Funciones relacionadas con el tracking y seguimiento de competidores durante eventos deportivos.

### 8. `track_event_checkpoint`

Crea la colección `tracking_checkpoint` para un evento cuando el status es `inProgress`. Inicializa la estructura de tracking de checkpoints.

**Tipo**: Callable Function (POST)  
**Endpoint**: `https://us-central1-system-track-monitor.cloudfunctions.net/track_event_checkpoint`

#### Parámetros (Body JSON)

| Parámetro | Tipo   | Requerido | Descripción                               |
| --------- | ------ | --------- | ----------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento                             |
| `status`  | string | **Sí**    | Estado del evento (debe ser "inProgress") |
| `day`     | string | **Sí**    | Identificador del día (ej: "day1")        |

#### Comandos cURL

```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/track_event_checkpoint' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_ID_TOKEN' \
  -d '{
    "data": {
      "eventId": "tu-event-id-aqui",
      "status": "inProgress",
      "day": "day1"
    }
  }'
```

#### Respuesta Exitosa (200)

```json
{
  "success": true,
  "message": "Colección '\''tracking_checkpoint'\'' creada para el evento '\''Nombre del Evento'\'' (event-id)",
  "event_id": "event-id",
  "event_name": "Nombre del Evento",
  "event_status": "inProgress",
  "status": "inProgress",
  "tracking_data": {
    "checkpoints_count": 2,
    "competitors_count": 0,
    "checkpoints": [...]
  }
}
```

---

### 9. `track_competitors`

Crea la estructura de tracking de competidores para un evento y día específico. Inicializa el sistema de seguimiento de competidores.

**Tipo**: Callable Function (POST)  
**Endpoint**: `https://us-central1-system-track-monitor.cloudfunctions.net/track_competitors`

#### Parámetros (Body JSON)

| Parámetro | Tipo   | Requerido | Descripción                               |
| --------- | ------ | --------- | ----------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento                             |
| `dayId`   | string | **Sí**    | ID del día del evento                     |
| `status`  | string | **Sí**    | Estado del evento (debe ser "inProgress") |
| `dayName` | string | **Sí**    | Nombre del día (ej: "Día 1")              |

#### Comandos cURL

```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/track_competitors' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_ID_TOKEN' \
  -d '{
    "data": {
      "eventId": "tu-event-id-aqui",
      "dayId": "tu-day-id-aqui",
      "status": "inProgress",
      "dayName": "Día 1"
    }
  }'
```

#### Respuesta Exitosa (200)

```json
{
  "success": true,
  "message": "Tracking de competidores creado para el evento '\''Nombre del Evento'\'' día day-id",
  "event_id": "event-id",
  "day_id": "day-id",
  "event_name": "Nombre del Evento",
  "competitors_count": 10,
  "routes_count": 2,
  "tracking_id": "event-id_day-id",
  "structure_type": "optimized_granular",
  "competitors": [...],
  "routes": [...]
}
```

---

### 10. `track_competitors_off`

Desactiva el tracking de competidores para un evento y día específico. Detiene el seguimiento activo.

**Tipo**: Callable Function (POST)  
**Endpoint**: `https://us-central1-system-track-monitor.cloudfunctions.net/track_competitors_off`

#### Parámetros (Body JSON)

| Parámetro | Tipo   | Requerido | Descripción           |
| --------- | ------ | --------- | --------------------- |
| `eventId` | string | **Sí**    | ID del evento         |
| `dayId`   | string | **Sí**    | ID del día del evento |

#### Comandos cURL

```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/track_competitors_off' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_ID_TOKEN' \
  -d '{
    "data": {
      "eventId": "tu-event-id-aqui",
      "dayId": "tu-day-id-aqui"
    }
  }'
```

#### Respuesta Exitosa (200)

```json
{
  "success": true,
  "message": "Tracking de competidores desactivado para el evento event-id día day-id",
  "event_id": "event-id",
  "day_id": "day-id",
  "tracking_id": "event-id_day-id",
  "is_active": false,
  "previous_status": true
}
```

---

## 🔐 Autenticación

### Funciones Públicas (sin autenticación)

Las siguientes funciones pueden ser públicas y no requieren autenticación:

- `events` - Solo lectura de datos públicos
- `event_detail` - Solo lectura de datos públicos

### Funciones que Requieren Autenticación

Las siguientes funciones requieren autenticación Bearer token:

- `user_profile` - Obtiene perfil de usuario (requiere token para identificar usuario)
- `day_of_race_active` - Obtiene día de carrera activo (requiere token para autenticación)
- `checkpoint` - Obtiene checkpoint específico (requiere token para autenticación)
- `competitor_tracking` - Obtiene tracking de competidores (requiere token para autenticación)
- `days_of_race` - Obtiene todos los días de carrera (requiere token para autenticación)
- `track_event_checkpoint` - Modifica datos de tracking
- `track_competitors` - Modifica datos de tracking
- `track_competitors_off` - Modifica datos de tracking

### Cómo Obtener el Token de Autenticación

#### Desde Flutter

```dart
String? token = await FirebaseAuth.instance.currentUser?.getIdToken();
```

#### Desde JavaScript/Web

```javascript
const token = await firebase.auth().currentUser.getIdToken();
```

#### Autenticación Anónima (para pruebas)

```bash
curl -X POST \
  'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=TU_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"returnSecureToken": true}'
```

Usa el `idToken` de la respuesta en el header:

```
Authorization: Bearer {idToken}
```

**Nota**: Primero debes habilitar "Anonymous" en Firebase Console → Authentication → Sign-in method.

### Hacer Funciones Públicas

Para hacer una función pública (solo lectura), usa gcloud:

```bash
gcloud functions add-iam-policy-binding NOMBRE_FUNCION \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/cloudfunctions.invoker" \
  --project=system-track-monitor
```

O desde Firebase Console:

1. Ve a Firebase Console → Tu proyecto → **Functions**
2. Busca la función y haz clic en los **tres puntos** (⋮)
3. Selecciona **"Edit"** o **"Configurar"**
4. Ve a **"Permissions"** → **"Invoker"**
5. Selecciona **"allUsers"** y guarda

---

## 🚀 Despliegue

### Desplegar todas las funciones

```bash
firebase deploy --only functions
```

### Desplegar una función específica

```bash
firebase deploy --only functions:NOMBRE_FUNCION
```

### Ejemplos

```bash
# Desplegar solo events
firebase deploy --only functions:events

# Desplegar solo event_detail
firebase deploy --only functions:event_detail

# Desplegar solo user_profile
firebase deploy --only functions:user_profile

# Desplegar solo day_of_race_active
firebase deploy --only functions:day_of_race_active

# Desplegar solo get_checkpoint
firebase deploy --only functions:get_checkpoint

# Desplegar solo competitor_tracking
firebase deploy --only functions:competitor_tracking

# Desplegar solo days_of_race
firebase deploy --only functions:days_of_race

# Desplegar funciones de tracking
firebase deploy --only functions:track_event_checkpoint,functions:track_competitors,functions:track_competitors_off
```

---

## 🧪 Pruebas Locales

Para probar las funciones localmente, consulta el archivo [README_TESTING.md](./README_TESTING.md).

### Iniciar emulador

```bash
firebase emulators:start
```

---

## 📝 Notas Importantes

1. **Paginación**: Para `events`, se recomienda usar `lastDocId` en lugar de `page` para mejor rendimiento con grandes volúmenes de datos.

2. **Códigos HTTP**: Las funciones de eventos (`events`, `event_detail`), usuarios (`user_profile`) y checkpoints (`day_of_race_active`, `checkpoint`, `competitor_tracking`, `days_of_race`) retornan códigos HTTP estándar. Las funciones de tracking retornan objetos JSON con `success` y `message`.

3. **Errores**: Las funciones de eventos, usuarios y checkpoints retornan solo códigos HTTP en caso de error (400, 401, 404, 500) sin cuerpo JSON, excepto `competitor_tracking` que retorna JSON con `success: false` en caso de error. Las funciones de tracking retornan objetos JSON con información del error.

4. **Autenticación**: Las funciones `user_profile`, `day_of_race_active`, `checkpoint`, `competitor_tracking` y `days_of_race` requieren Bearer token válido de Firebase Auth solo para autenticación. Los parámetros se reciben como parámetros query o path, no se extraen del token. El token solo valida que el usuario esté autenticado.

5. **CORS**: Todas las funciones HTTP incluyen headers CORS para permitir llamadas desde aplicaciones web.

---

## 📚 Documentación Adicional

- [Comandos cURL Detallados](./POSTMAN_CURL_COMMANDS.md) - Guía completa de comandos cURL para Postman
- [Guía de Pruebas Locales](./README_TESTING.md) - Cómo probar funciones localmente

---

## 🔧 Tecnologías Utilizadas

- **Python 3.12**
- **Firebase Cloud Functions (2nd Gen)**
- **Firebase Admin SDK**
- **Firestore**

---

## 📄 Licencia

Este proyecto es parte del sistema Sport Monitor.
