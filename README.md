# Sport Monitor Cloud Functions

## 📋 Descripción del Proyecto

Este proyecto contiene las **Cloud Functions de Firebase** desarrolladas en Python para el sistema **Sport Monitor**. Estas funciones proporcionan servicios backend para la gestión y control de eventos deportivos, incluyendo:

- **Gestión de Eventos**: Obtención de listados y detalles de eventos deportivos
- **Gestión de Usuarios**: Obtención de perfiles de usuario con eventos asignados
- **Gestión de Competidores**: Creación de competidores, usuarios competidores y consultas por evento
- **Gestión de Staff**: Creación de usuarios staff con roles (organizador, staff, checkpoint)
- **Tracking de Competidores**: Seguimiento en tiempo real de competidores durante eventos
- **Gestión de Checkpoints**: Control de puntos de control en eventos deportivos

Las funciones están desplegadas en **Firebase Cloud Functions** y proporcionan APIs REST para ser consumidas desde aplicaciones cliente (Flutter, Web, etc.).

## 🏗️ Arquitectura

### Estructura del Proyecto

```
functions/
├── events/              # Package: Gestión de Eventos
│   ├── events_customer.py          # events
│   ├── events_detail_customer.py  # event_detail
│   └── event_categories.py        # event_categories
├── users/               # Package: Gestión de Usuarios (una función: user_route)
│   ├── user_route.py                # user_route (router: read/create/update/delete_section/subscribedEvents por path)
│   ├── create.py                    # create.handle (crear/activar usuario)
│   ├── read.py                      # read.handle (perfil por email/userId/documentId)
│   ├── subscribed_events.py        # subscribed_events.handle (eventos suscritos del usuario, paginado)
│   └── update.py                    # update.handle (actualizar usuario por secciones)
├── vehicles/            # Package: Vehículos de usuarios/competidores
│   ├── get_vehicles.py            # get_vehicles (GET /api/vehicles + POST delega a create_vehicle)
│   ├── create_vehicle.py          # create_vehicle_handler (POST, invocado desde get_vehicles)
│   ├── search_vehicle.py          # search_vehicle (GET busca por branch, model, year)
│   ├── update_vehicle.py          # update_vehicle (PUT /api/vehicles/{id})
│   └── delete_vehicle.py          # delete_vehicle (DELETE /api/vehicles/{id})
├── catalogs/            # Package: Catálogos — una función catalog_route (router por path) SPRTMNTRPP-82
│   ├── color/                     # Catálogo colores
│   │   ├── _common.py
│   │   ├── list_color.py
│   │   ├── create_color.py
│   │   ├── update_color.py
│   │   └── delete_color.py
│   ├── vehicle/                   # Catálogo marcas de motos
│   │   ├── _common.py
│   │   ├── list_vehicle.py
│   │   ├── create_vehicle.py
│   │   ├── update_vehicle.py
│   │   └── delete_vehicle.py
│   └── year/                      # Catálogo años
│       ├── _common.py
│       ├── list_year.py
│       ├── create_year.py
│       ├── update_year.py
│       └── delete_year.py
├── competitors/         # Package: Competidores y rutas
│   ├── competitor_route.py        # competitor_route
│   ├── create_competitor.py       # create_competitor (POST)
│   ├── create_competitor_user.py  # create_competitor_user (POST)
│   ├── delete_competitor.py       # delete_competitor (DELETE, solo participante)
│   ├── delete_competitor_user.py  # delete_competitor_user (DELETE, usuario completo)
│   ├── get_competitor_by_email.py  # get_competitor_by_email (GET)
│   ├── get_competitor_by_id.py    # get_competitor_by_id (GET)
│   ├── get_event_competitor_by_email.py # get_event_competitor_by_email (GET)
│   ├── get_competitors_by_event.py # get_competitors_by_event (GET)
│   └── list_competitors_by_event.py # list_competitors_by_event (GET, paginado)
├── staff/               # Package: Gestión de Staff
│   └── create_staff_user.py       # create_staff_user (POST)
├── checkpoints/         # Package: Gestión de Checkpoints
│   ├── day_of_race_active.py       # day_of_race_active
│   ├── checkpoint.py               # checkpoint
│   ├── competitor_tracking.py      # competitor_tracking
│   ├── all_competitor_tracking.py  # all_competitor_tracking
│   ├── update_competitor_status.py # update_competitor_status
│   ├── change_competitor_status.py # change_competitor_status
│   └── days_of_race.py             # days_of_race
├── tracking/           # Package: Tracking de Competidores
│   ├── track_competitor_position.py # track_competitor_position
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

Obtiene una lista paginada de eventos desde Firestore. Retorna eventos en formato `EventShortDocument` (versión simplificada con campos esenciales). Opcionalmente indica si el usuario ya está inscrito en cada evento.

**Tipo**: HTTP Request (GET)
**Endpoint**: `https://events-xa26lpxdea-uc.a.run.app`

#### Parámetros (Query Parameters)

| Parámetro   | Tipo    | Requerido | Descripción                                                          |
| ----------- | ------- | --------- | -------------------------------------------------------------------- |
| `size`      | integer | No        | Número de eventos por página (default: 50, max: 100)                 |
| `page`      | integer | No        | Número de página (default: 1)                                        |
| `lastDocId` | string  | No        | ID del último documento para cursor-based pagination (más eficiente) |
| `userId`    | string  | No        | ID del usuario para verificar si ya está inscrito en cada evento     |

#### Campos Retornados

- `id`: ID del evento
- `title`: Título del evento
- `subtitle`: Subtítulo (opcional)
- `status`: Estado del evento (draft, published, inProgress, etc.)
- `startDateTime`: Fecha y hora de inicio en formato ISO 8601
- `locationName`: Dirección del evento (viene del campo `address` de `event_content`)
- `imageUrl`: URL de la imagen principal (viene del campo `photoMain` de `event_content`)
- `isEnrolled`: `true` si el usuario está inscrito, `false` si no, `null` si no se envió `userId` o el usuario no existe en Firestore

#### Origen de `imageUrl` y `locationName`

Ambos campos se obtienen del **primer documento** de la subcolección `events/{eventId}/event_content`:

| Campo en respuesta | Campo en Firestore (`event_content`) |
|---|---|
| `imageUrl` | `photoMain` |
| `locationName` | `address` |

Si el evento no tiene documentos en `event_content`, ambos campos retornan `null`.

#### Comportamiento de `isEnrolled`

| Escenario | Valor de `isEnrolled` |
|---|---|
| No se envía `userId` | `null` |
| `userId` no existe en `users` | `null` |
| `userId` válido, inscrito en el evento | `true` |
| `userId` válido, no inscrito en el evento | `false` |

> La verificación usa un batch get sobre `events/{eventId}/participants/{userId}` — una sola operación para toda la página, sin N+1.

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

**Con verificación de inscripción por usuario:**

```bash
curl -X GET \
  'https://events-xa26lpxdea-uc.a.run.app?size=20&userId=uid-del-usuario' \
  -H 'Content-Type: application/json'
```

**Con todos los parámetros:**

```bash
curl -X GET \
  'https://events-xa26lpxdea-uc.a.run.app?size=20&page=1&lastDocId=id-del-ultimo-documento&userId=uid-del-usuario' \
  -H 'Content-Type: application/json'
```

#### Respuesta Exitosa (200)

```json
{
  "result": [
    {
      "id": "event-id-1",
      "title": "Evento Deportivo 2025",
      "subtitle": "Subtítulo del evento",
      "status": "published",
      "startDateTime": "2025-01-15T10:00:00",
      "locationName": "Estadio Principal",
      "imageUrl": "https://example.com/image.jpg",
      "isEnrolled": true
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

### 3. `event_categories`

Obtiene todas las categorías de un evento específico desde Firestore. Retorna un array directo de categorías mapeable a `List<EventCategory>`, sin aplicar filtros.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://event-categories-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/event/event-categories/{eventId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                                 |
| --------- | ------ | --------- | ------------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento (puede venir en path o query) |

**Nota**: El parámetro puede venir en el path de la URL (`/api/event/event-categories/{eventId}`) o como query parameter (`?eventId=xxx`).

#### Campos Retornados (Array de EventCategory)

Cada elemento del array contiene:

- `id`: ID del documento de la categoría
- `name`: Nombre de la categoría
- `createdAt`: Fecha de creación en formato ISO 8601
- `updatedAt`: Fecha de actualización en formato ISO 8601

#### Consulta Firestore

- **Ruta de colección**: `events/{eventId}/eventCategories`
- **Método**: Obtener todos los documentos sin filtros, ordenados por `name` alfabéticamente
- **Retorno**: Array de todas las categorías del evento

#### Comandos cURL

**Obtener categorías de evento (con token Bearer y eventId en query):**

```bash
curl -X GET \
  'https://event-categories-xa26lpxdea-uc.a.run.app?eventId=TU_EVENT_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con eventId específico:**

```bash
curl -X GET \
  'https://event-categories-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Usando el endpoint con Hosting (eventId en path):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/event/event-categories/abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con valores reales:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/event/event-categories/cN6ykYvP5WortNOxr3j6' \
  -H 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ...' \
  -H 'Content-Type: application/json'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://event-categories-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin eventId):**

```bash
curl -X GET \
  'https://event-categories-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://event-categories-xa26lpxdea-uc.a.run.app?eventId=abc123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Categorías encontradas (array directo):**

```json
[
  {
    "id": "category123",
    "name": "Moto A",
    "createdAt": "2024-01-15T10:00:00Z",
    "updatedAt": "2024-01-15T12:00:00Z"
  },
  {
    "id": "category456",
    "name": "Moto B",
    "createdAt": "2024-01-15T10:00:00Z",
    "updatedAt": "2024-01-15T12:00:00Z"
  },
  {
    "id": "category789",
    "name": "Auto",
    "createdAt": "2024-01-15T10:00:00Z",
    "updatedAt": "2024-01-15T12:00:00Z"
  }
]
```

**200 OK - Sin categorías (array vacío):**

```json
[]
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta el parámetro `eventId` o está vacío

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta la subcolección `events/{eventId}/eventCategories` sin aplicar filtros.
- **Ordenamiento**: Las categorías se ordenan alfabéticamente por `name` para facilitar su uso.
- **Formato de respuesta**: Retorna un array directo (sin wrapper) para facilitar el mapeo a `List<EventCategory>` en Flutter.
- **Array vacío**: Si no hay categorías, retorna `[]` (array vacío) con código 200 OK.
- **Timestamps**: Los campos `createdAt` y `updatedAt` se convierten automáticamente de Timestamps de Firestore a formato ISO 8601.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura `EventCategory`.
- **Parámetros flexibles**: El parámetro puede venir en el path de la URL o como query parameter, facilitando su uso desde diferentes clientes.
- **Sin filtros**: Esta API no aplica filtros. Retorna todas las categorías del evento.

---

## 📦 Package: Users

Una sola Cloud Function **`user_route`** atiende todas las operaciones de usuarios. El router valida CORS, método HTTP y Bearer token una vez y despacha por path a la lógica correspondiente (read, create, update, read_sections, subscribed_events, delete_section_item). Paths: `/api/users/read`, `/api/users/profile` (equivalente a read), `/api/users/personalData`, `/api/users/healthData`, `/api/users/emergencyContacts`, `/api/users/vehicles`, `/api/users/membership` (GET; DELETE solo para emergencyContacts y vehicles), `/api/users/subscribedEvents` (GET, eventos suscritos paginados), `/api/users/create`, `/api/users/update`.

### 4. `read` (perfil de usuario)

Obtiene el perfil básico de un usuario desde Firestore (solo datos directos: id, authUserId, avatarUrl, email, username). Servido por **user_route** en GET.

**Tipo**: HTTP Request (GET)  
**Paths**: `/api/users/read`, `/api/users/profile` (compatibilidad)  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/users/read` o `.../api/users/profile`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado. El parámetro `userId` es en realidad el `authUserId` (ID de autenticación de Firebase), no el ID del documento en Firestore. La búsqueda se realiza usando una query `where('authUserId', '==', authUserId)`.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Query Parameters) — uno de los tres requerido

| Parámetro    | Tipo   | Requerido | Descripción                                                                        |
| ------------ | ------ | --------- | ---------------------------------------------------------------------------------- |
| `userId`     | string | Opcional  | `authUserId` del usuario (ID de autenticación de Firebase)                        |
| `documentId` | string | Opcional  | ID del documento en la colección `users` (Firestore)                                |
| `email`      | string | Opcional  | Correo electrónico del usuario (campo `email` en el documento)                     |

#### Campos Retornados (solo datos directos del usuario)

- `id`: ID del documento del usuario en Firestore
- `authUserId`: ID de autenticación de Firebase (puede ser null)
- `avatarUrl`: URL del avatar (puede ser null)
- `email`: Correo electrónico
- `username`: Nombre de usuario

#### Comandos cURL

**Obtener perfil de usuario (con token Bearer y authUserId):**

```bash
# Path recomendado: /api/users/read (también válido: /api/users/profile)
curl -X GET \
  'https://system-track-monitor.web.app/api/users/read?userId=TU_AUTH_USER_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con authUserId específico:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/profile?userId=firebase-auth-uid-123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Nota**: El parámetro `userId` debe ser el `authUserId` (ID de autenticación de Firebase), no el ID del documento en Firestore.

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://system-track-monitor.web.app/api/users/profile?userId=firebase-auth-uid-123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin authUserId):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/profile' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/profile?userId=firebase-auth-uid-123' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 404 (usuario no existente con ese authUserId):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/profile?userId=auth-uid-que-no-existe' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Usuario encontrado:**

```json
{
  "id": "user-doc-id",
  "authUserId": "firebase-auth-uid",
  "avatarUrl": "https://example.com/avatar.jpg",
  "email": "usuario@example.com",
  "username": "usuario@example.com"
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando faltan todos los parámetros (userId, documentId, email) o el formato de email es inválido

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**404 Not Found** - Sin cuerpo (solo código HTTP) - cuando no se encuentra ningún usuario con los parámetros proporcionados

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Notas Importantes (read)

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado.
- **Parámetros**: Se puede buscar por `userId` (authUserId), `documentId` (ID del documento en Firestore) o `email`. Solo se retornan los campos directos: id, authUserId, avatarUrl, email, username.

### 4.1 Lectura por sección del perfil (GET /api/users/{section})

Permite leer una subcolección del usuario en una petición. Servido por **user_route** en GET. El formato de cada documento es el mismo que en `get_event_competitor_by_email` (excluye `createdAt`/`updatedAt`, incluye `id`).

**Paths:**

- `GET /api/users/personalData` — Objeto que combina **email** (del documento `users/{userId}`) con los campos del primer documento de la subcolección (id, fullName, phone, dateOfBirth, address, etc.). Si el usuario existe pero la subcolección está vacía: 200 con **email** informado y el resto de campos en **null**. 404 solo si el usuario no existe.
- `GET /api/users/healthData` — Primer documento de la subcolección (objeto único). 404 si no hay datos.
- `GET /api/users/emergencyContacts` — Lista de documentos (puede ser `[]`).
- `GET /api/users/vehicles` — Lista de documentos (puede ser `[]`).
- `GET /api/users/membership` — Lista de documentos (puede ser `[]`).

**Query params:** `userId` (requerido) — ID del documento en la colección `users`.

**Importante:** La URL debe incluir el prefijo `/api`. Ejemplo: `.../api/users/personalData?userId=USER_DOC_ID`.

**Ejemplo cURL (personalData):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/personalData?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo cURL (vehicles):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/vehicles?userId=USER_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Respuestas:** 200 con JSON. Para personalData: objeto con `email` (del usuario) más campos de la subcolección; si la subcolección está vacía, 200 con email y el resto en null. Para healthData: objeto único (404 si vacía). Para emergencyContacts, vehicles, membership: array. 400 si falta userId o sección inválida. 404 si el usuario no existe o, en healthData, si la subcolección está vacía. 401 si el token es inválido.

### 4.1.1 `subscribedEvents` (eventos suscritos del usuario)

Obtiene los eventos en los que el usuario está suscrito (documentos en `users/{userId}/membership`), con datos del evento y del primer documento de `event_content`. Respuesta paginada. **Solo la respuesta 200 retorna JSON**; los errores retornan cuerpo vacío (solo código HTTP y CORS).

**Tipo**: HTTP Request (GET)  
**Path**: `/api/users/subscribedEvents`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/users/subscribedEvents`

**Nota**: Requiere autenticación Bearer token.

#### Parámetros (Query)

| Parámetro | Tipo    | Requerido | Descripción                                      |
| --------- | ------- | --------- | ------------------------------------------------ |
| `userId`  | string  | **Sí**    | ID del documento del usuario en la colección `users` |
| `limit`   | integer | No        | Items por página (default: 50, máx: 100)         |
| `page`    | integer | No        | Número de página (default: 1)                    |

#### Respuesta 200 (única con JSON)

- `result`: array de objetos, cada uno con: `id` (eventId), `name`, `description`, `status`, `startDateTime`, `endEvent`, `imageUrl` (de `event_content`: `startEvent`, `endEvent`, `photoMain`).
- `pagination`: `limit`, `page`, `hasMore`, `count`, `lastDocId`.

#### Errores (sin cuerpo JSON)

- **400**: `userId` faltante o vacío.
- **404**: Usuario no existe o colección `membership` vacía (sin eventos suscritos).
- **500**: Error interno.

#### Ejemplo cURL

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/users/subscribedEvents?userId=USER_DOC_ID&limit=50&page=1' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Desplegar (incluye user_route con read, create, update, subscribedEvents, lectura por sección y DELETE por sección):**

```bash
firebase deploy --only functions:user_route
```

### 4.2 Eliminar contacto de emergencia o vehículo (DELETE /api/users/{section})

Permite eliminar **un** documento de la subcolección `emergencyContacts` o `vehicles` del usuario. Servido por **user_route** en DELETE. Solo están permitidas las secciones `emergencyContacts` y `vehicles`.

**Paths:**

- `DELETE /api/users/emergencyContacts?userId={userId}&id={documentId}` — Elimina el contacto en `users/{userId}/emergencyContacts/{documentId}`.
- `DELETE /api/users/vehicles?userId={userId}&id={vehicleId}` — Elimina el vehículo en `users/{userId}/vehicles/{vehicleId}`.

**Query params:** `userId` (requerido) — ID del documento del usuario en `users`. `id` (requerido) — ID del documento a eliminar dentro de la subcolección.

**Respuesta exitosa:** 204 No Content (sin cuerpo).

**Errores:** 400 si falta `userId` o `id`; 401 si el token es inválido; 404 si el usuario no existe o el documento no existe en la subcolección; 405 si se usa DELETE en una sección no permitida (p. ej. personalData).

**Ejemplo cURL (eliminar contacto de emergencia):**

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/users/emergencyContacts?userId=USER_DOC_ID&id=DOC_ID_CONTACTO' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo cURL (eliminar vehículo):**

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/users/vehicles?userId=USER_DOC_ID&id=VEHICLE_DOC_ID' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

### 5. `create` (crear usuario)

Crea o activa un usuario en la colección `users` mediante **upsert por email**. Servido por **user_route** en POST.

- Si el email **ya existe** (template creado por `create_competitor_user`): actualiza `authUserId`, `avatarUrl`, `isActive=true`, `updatedAt` y `username` → retorna **200**.
- Si el email **no existe**: crea un documento nuevo con `isActive=true` → retorna **201**.

El campo `username` toma el email como valor por defecto. Solo se guardan los campos raíz limpios (sin embedding de subcolecciones).

**Tipo**: HTTP Request (POST)  
**Path**: `/api/users/create`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/users/create`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                   |
| --------------- | ------ | --------- | ----------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth |
| `Content-Type`  | string | **Sí**    | `application/json`            |

#### Request Body (JSON)

| Campo        | Tipo           | Requerido | Descripción                        |
| ------------ | -------------- | --------- | ---------------------------------- |
| `email`      | string         | **Sí**    | Email del usuario (formato válido) |
| `authUserId` | string         | **Sí**    | UID de Firebase Auth               |
| `avatarUrl`  | string \| null | No        | URL del avatar del usuario         |

#### Documento resultante en `users/{userId}`

```json
{
  "email":      "usuario@example.com",
  "username":   "usuario@example.com",
  "authUserId": "firebase-uid-123",
  "avatarUrl":  "https://example.com/avatar.jpg",
  "isActive":   true,
  "createdAt":  "2026-03-07T12:00:00+00:00",
  "updatedAt":  "2026-03-07T12:00:00+00:00"
}
```

#### Comandos cURL

**Caso CREATE — email nuevo (201):**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/users/create' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{"email":"nuevo@example.com","authUserId":"firebase-uid-abc","avatarUrl":"https://example.com/av.jpg"}'
```

**Caso UPDATE — email ya existe, activa template (200):**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/users/create' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{"email":"piloto_registrado@example.com","authUserId":"firebase-uid-xyz"}'
```

**Probar error 400 (sin authUserId):**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/users/create' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{"email":"test@example.com"}' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/users/create' \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","authUserId":"uid1"}' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**201 Created** — Usuario nuevo creado: `{"id": "<userId>"}`.

**200 OK** — Template existente activado: `{"id": "<userId>"}`.

**400 Bad Request** — Sin cuerpo. Body nulo/vacío, `email` faltante o inválido, `authUserId` faltante.

**401 Unauthorized** — Sin cuerpo. Token Bearer inválido, expirado o faltante.

**500 Internal Server Error** — Sin cuerpo. Error al operar Firestore.

#### Notas

- El upsert es por `email`: si existe un template previo (creado por `create_competitor_user` con `isActive: false`), se activa en lugar de crear un duplicado.
- `username` se asigna automáticamente como el email; si el template ya tenía un `username` válido, se conserva.
- Campos eliminados respecto a la versión anterior: `eventStaffRelations`, `userData`, `personalData` inline, `emergencyContact` inline. Las subcolecciones siguen manejándose por sus propios endpoints.

### 6. `update` (actualizar usuario)

Actualiza datos de un usuario existente **por secciones**. Servido por **user_route** en PUT. Solo las secciones presentes en el body se modifican; las ausentes no se tocan. El campo `competition` se ignora si se envía.

**Tipo**: HTTP Request (PUT)  
**Path**: `/api/users/update`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/users/update`

**Nota**: Esta función requiere autenticación Bearer token.

#### Query Parameters

| Parámetro | Tipo   | Requerido | Descripción                    |
| --------- | ------ | --------- | ------------------------------ |
| `userId`  | string | **Sí**    | ID del usuario a actualizar    |

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                      |
| --------------- | ------ | --------- | -------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth    |
| `Content-Type`  | string | **Sí**    | `application/json`               |

#### Request Body (JSON) — al menos una sección requerida

| Campo               | Tipo   | Descripción                                                                                     |
| ------------------- | ------ | ----------------------------------------------------------------------------------------------- |
| `email`             | string | Nuevo email (formato válido, único entre usuarios)                                              |
| `username`          | string | Nuevo username (mínimo 4 caracteres, único entre usuarios)                                      |
| `personalData`      | object | Campos a actualizar: `fullName`, `phone`, `dateOfBirth`, `address`, `city`, `state`, `country`, `postalCode`. **No incluir `email`** aquí; el email se actualiza con el campo raíz `email`. Si se envía `email` dentro de `personalData`, se ignora. |
| `healthData`        | object | Campos a actualizar: `bloodType`, `socialSecurityNumber`, `medications`, `medicalConditions`, `insuranceProvider`, `insuranceNumber` |
| `emergencyContacts` | array  | **Replace completo**. Cada elemento requiere `fullName` y `phone`; `relationship` es opcional   |
| `vehicleData`       | object | Si incluye `id`: actualiza ese vehículo (o lo crea si no existe). Sin `id`: crea nuevo vehículo |

> `competition` se ignora aunque se envíe.

#### Comportamiento de `vehicleData`

| Caso | Acción |
|------|--------|
| `id` presente y el doc existe | Actualiza el vehículo existente |
| `id` presente pero no existe  | Crea el vehículo con ese id     |
| Sin `id`                      | Crea nuevo vehículo (id autogenerado) |

#### Comandos cURL

**Actualizar email y username:**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/users/update?userId=USER_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{"email":"nuevo@example.com","username":"nuevousuario"}'
```

**Actualizar solo personalData:**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/users/update?userId=USER_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{"personalData":{"fullName":"Juan Pérez","phone":"+521234567890","city":"CDMX"}}'
```

**Reemplazar emergencyContacts:**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/users/update?userId=USER_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{"emergencyContacts":[{"fullName":"Contacto Uno","relationship":"Hermano","phone":"+529876543210"}]}'
```

**Actualizar todas las secciones:**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/users/update?userId=USER_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -d '{
    "email": "nuevo@example.com",
    "username": "nuevousuario",
    "personalData": {"fullName": "Juan Pérez", "phone": "+521234567890"},
    "healthData": {"bloodType": "A+", "medications": "ninguna"},
    "emergencyContacts": [{"fullName": "Contacto", "phone": "+529876543210"}],
    "vehicleData": {"id": "vehicle_id", "branch": "Honda", "model": "CRF", "year": 2022, "color": "Rojo"}
  }'
```

#### Respuestas

**200 OK** — `{"id": "<userId>", "updated": ["email", "personalData", ...]}` con la lista de secciones actualizadas.

**400 Bad Request** — Sin cuerpo. `userId` faltante, body inválido, sin secciones reconocidas, o campo con formato incorrecto.

**401 Unauthorized** — Sin cuerpo. Token Bearer inválido o faltante.

**404 Not Found** — Sin cuerpo. Usuario no encontrado.

**409 Conflict** — Sin cuerpo. Email o username ya en uso por otro usuario.

**500 Internal Server Error** — Sin cuerpo. Error interno del servidor.

#### Notas

- Solo las secciones presentes en el body se procesan; las demás no se modifican.
- `emergencyContacts` realiza un **replace completo**: elimina todos los contactos existentes y crea los nuevos.
- `personalData` y `healthData` actualizan el primer documento existente en su subcolección; si no existe ninguno, lo crean. En el body, **no enviar `email` dentro de `personalData`**; usar el campo raíz `email` para cambiar el correo.
- La validación de email/username solo falla si otro usuario diferente ya los usa.

---

## 📦 Package: Vehicles

Funciones para obtener y gestionar vehículos de usuarios/competidores (subcolección `users/{userId}/vehicles`).

### 1. `get_vehicles` (SPRTMNTRPP-70)

Obtiene todos los vehículos de un usuario desde Firestore. Retorna un array directo de vehículos (sin wrappers). Requiere Bearer token.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-vehicles-....run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/vehicles?userId={userId}`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                   |
| --------------- | ------ | --------- | ----------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth |

#### Parámetros (Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                                    |
| --------- | ------ | --------- | ---------------------------------------------- |
| `userId`  | string | **Sí**    | UUID del usuario (ID del documento en `users`) |

#### Campos retornados (cada elemento del array)

| Campo       | Tipo   | Descripción                       |
| ----------- | ------ | --------------------------------- |
| `id`        | string | ID del documento del vehículo     |
| `branch`    | string | Marca                             |
| `year`      | number | Año                               |
| `model`     | string | Modelo                            |
| `color`     | string | Color                             |
| `createdAt` | string | Fecha de creación (ISO 8601)      |
| `updatedAt` | string | Fecha de actualización (ISO 8601) |

#### Comandos cURL

**Obtener vehículos de un usuario:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/vehicles?userId=UUID_DEL_USUARIO' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (userId faltante):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/vehicles' \
  -H 'Authorization: Bearer TU_TOKEN' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/vehicles?userId=UUID' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK** - Array directo de vehículos: `[{id, branch, year, model, color, createdAt, updatedAt}, ...]`. Si no hay vehículos: `[]`.

**400 Bad Request** - Sin cuerpo. `userId` faltante o vacío.

**401 Unauthorized** - Sin cuerpo. Token inválido o faltante.

**404 Not Found** - Sin cuerpo. Usuario no encontrado (no existe el documento `users/{userId}`).

**500 Internal Server Error** - Sin cuerpo. Error del servidor.

#### Notas

- Ruta en Firestore: `users/{userId}/vehicles`.
- Usa constantes `FirestoreCollections.USERS` y `FirestoreCollections.USER_VEHICLES`.

### 2. Crear vehículo – POST `/api/vehicles` (SPRTMNTRPP-71)

Crea un vehículo para un usuario. Mismo path que GET; método **POST**. Requiere Bearer token, `userId`, `authUserId` y body con `branch`, `year`, `model`, `color`. El usuario debe existir y su campo `authUserId` debe coincidir con el enviado.

**Tipo**: HTTP Request (POST)  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/vehicles?userId={userId}&authUserId={authUserId}`

#### Query Parameters

| Parámetro    | Tipo   | Requerido | Descripción                                                             |
| ------------ | ------ | --------- | ----------------------------------------------------------------------- |
| `userId`     | string | **Sí**    | UUID del usuario (documento en `users`)                                 |
| `authUserId` | string | **Sí**    | UUID de autenticación del usuario (debe coincidir con el del documento) |

#### Request Body (JSON)

| Campo    | Tipo   | Requerido | Descripción            |
| -------- | ------ | --------- | ---------------------- |
| `branch` | string | **Sí**    | Marca                  |
| `year`   | number | **Sí**    | Año (entero 1900-2100) |
| `model`  | string | **Sí**    | Modelo                 |
| `color`  | string | **Sí**    | Color                  |

#### Ejemplo cURL

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/vehicles?userId=UUID_USUARIO&authUserId=AUTH_UID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN' \
  -d '{"branch":"Toyota","year":2024,"model":"Corolla","color":"Blanco"}'
```

#### Respuestas

**201 Created** – Objeto del vehículo creado: `{id, branch, year, model, color, createdAt, updatedAt}` (sin wrapper).

**400** – Parámetros o body inválidos (userId/authUserId faltantes, body mal formado, year no entero).

**401** – Token inválido o faltante.

**404** – Usuario no encontrado o `authUserId` no coincide con el documento.

**500** – Error interno.

### 3. Actualizar vehículo – PUT `/api/vehicles/{vehicleId}` (SPRTMNTRPP-72)

Actualiza un vehículo existente. Requiere Bearer token, `userId`, `authUserId` (query) y body con `branch`, `year`, `model`, `color`. No modifica `createdAt`.

**Tipo**: HTTP Request (PUT)  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/vehicles/{vehicleId}?userId={userId}&authUserId={authUserId}`

#### Path y Query

| Dónde | Parámetro    | Tipo   | Requerido | Descripción                                                |
| ----- | ------------ | ------ | --------- | ---------------------------------------------------------- |
| Path  | `vehicleId`  | string | **Sí**    | UUID del vehículo (documento en `users/{userId}/vehicles`) |
| Query | `userId`     | string | **Sí**    | UUID del usuario                                           |
| Query | `authUserId` | string | **Sí**    | UUID de autenticación (debe coincidir con el del usuario)  |

#### Request Body (JSON)

| Campo    | Tipo   | Requerido | Descripción     |
| -------- | ------ | --------- | --------------- |
| `branch` | string | **Sí**    | Marca           |
| `year`   | number | **Sí**    | Año (1900-2100) |
| `model`  | string | **Sí**    | Modelo          |
| `color`  | string | **Sí**    | Color           |

#### Ejemplo cURL

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/vehicles/VEHICLE_ID?userId=USER_ID&authUserId=AUTH_UID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN' \
  -d '{"branch":"Toyota","year":2025,"model":"Corolla","color":"Negro"}'
```

#### Respuestas

**200 OK** – Vehículo actualizado: `{id, branch, year, model, color, createdAt, updatedAt}` (sin wrapper).

**400** – Parámetros o body inválidos. **401** – Token inválido o faltante. **404** – Usuario no encontrado, authUserId no coincide o vehículo no existe. **500** – Error interno.

### 4. Eliminar vehículo – DELETE `/api/vehicles/{vehicleId}` (SPRTMNTRPP-73)

Elimina un vehículo de un usuario. Requiere Bearer token, `userId` y `authUserId` (query). Respuesta exitosa: 204 No Content (sin cuerpo).

**Tipo**: HTTP Request (DELETE)  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/vehicles/{vehicleId}?userId={userId}&authUserId={authUserId}`

#### Path y Query

| Dónde | Parámetro    | Tipo   | Requerido | Descripción                                               |
| ----- | ------------ | ------ | --------- | --------------------------------------------------------- |
| Path  | `vehicleId`  | string | **Sí**    | UUID del vehículo                                         |
| Query | `userId`     | string | **Sí**    | UUID del usuario                                          |
| Query | `authUserId` | string | **Sí**    | UUID de autenticación (debe coincidir con el del usuario) |

#### Ejemplo cURL

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/vehicles/VEHICLE_ID?userId=USER_ID&authUserId=AUTH_UID' \
  -H 'Authorization: Bearer TU_TOKEN'
```

#### Respuestas

**204 No Content** – Vehículo eliminado (sin cuerpo).

**400** – Parámetros faltantes o inválidos. **401** – Token inválido o faltante. **404** – Usuario no encontrado, authUserId no coincide o vehículo no existe. **500** – Error interno.

### 5. Buscar vehículo – GET `search_vehicle`

Busca un vehículo de un usuario por coincidencia exacta de `branch`, `model` y `year`. Si encuentra coincidencia retorna 200 con los datos del vehículo; si no, retorna 404.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://search-vehicle-....run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/vehicles/search?userId={userId}&branch={branch}&model={model}&year={year}`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                   |
| --------------- | ------ | --------- | ----------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth |

#### Parámetros (Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                                    |
| --------- | ------ | --------- | ---------------------------------------------- |
| `userId`  | string | **Sí**    | UUID del usuario (ID del documento en `users`) |
| `branch`  | string | **Sí**    | Marca del vehículo                             |
| `model`   | string | **Sí**    | Modelo del vehículo                            |
| `year`    | number | **Sí**    | Año del vehículo (entero, 1900-2100)           |

#### Campos retornados

| Campo       | Tipo   | Descripción                       |
| ----------- | ------ | --------------------------------- |
| `id`        | string | ID del documento del vehículo     |
| `branch`    | string | Marca                             |
| `year`      | number | Año                               |
| `model`     | string | Modelo                            |
| `color`     | string | Color                             |
| `createdAt` | string | Fecha de creación (ISO 8601)      |
| `updatedAt` | string | Fecha de actualización (ISO 8601) |

#### Comandos cURL

**Buscar vehículo por branch, model y year:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/vehicles/search?userId=UUID_DEL_USUARIO&branch=Honda&model=CRF450R&year=2024' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (parámetro faltante):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/vehicles/search?userId=UUID' \
  -H 'Authorization: Bearer TU_TOKEN' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/vehicles/search?userId=UUID&branch=Honda&model=CRF450R&year=2024' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK** – Vehículo encontrado: `{id, branch, year, model, color, createdAt, updatedAt}` (sin wrapper).

**400 Bad Request** – Sin cuerpo. Parámetros faltantes, vacíos o `year` inválido (no numérico o fuera de rango).

**401 Unauthorized** – Sin cuerpo. Token inválido o faltante.

**404 Not Found** – Sin cuerpo. Usuario no encontrado o no existe vehículo que coincida en `branch`, `model` y `year`.

**500 Internal Server Error** – Sin cuerpo. Error del servidor.

#### Notas

- Ruta en Firestore: `users/{userId}/vehicles`.
- Usa query con filtros `==` sobre `branch`, `model` y `year` (los tres deben coincidir).
- Usa `FirestoreHelper.query_documents()` y constantes `FirestoreCollections.USERS` / `FirestoreCollections.USER_VEHICLES`.

---

## 📦 Package: Catalogs (SPRTMNTRPP-82)

Una sola Cloud Function **`catalog_route`** atiende todos los catálogos HTTP: valida CORS, método y Bearer token una vez y despacha por path a la misma lógica que antes (`vehicle`, `year`, `color`, `relationship-type`, `checkpoint-type`). Los paths públicos **no cambian** (`/api/catalogs/...`).

CRUD de catálogos en Firestore: **vehicles** (marcas y modelos de motos), **years** (años), **colors** (nombre + hex), **checkpoint_types** (grupos `zones`, `symbols`, `waypoints`, `safety`, `dunes_sand`; cada ítem: `name`, `type`, `icon`, `description`; `abbreviation` opcional o `null`). Operaciones **masivas** (crear/eliminar por lista donde aplica). Rutas en Firestore: `catalogs/default/vehicles`, `catalogs/default/years`, `catalogs/default/colors`, `catalogs/default/checkpoint_types`. Todas requieren Bearer token.

### 1. Catálogo Vehicles – `/api/catalogs/vehicle`

| Método | Descripción                                      | Body                                                                                |
| ------ | ------------------------------------------------ | ----------------------------------------------------------------------------------- |
| GET    | Lista de marcas `[{id, name, models, logoUrl?}]` | —                                                                                   |
| POST   | Creación masiva; retorna array de ids (201)      | Lista directa: `[{"name": "...", "models": ["..."], "logoUrl?": "..."}]`            |
| PUT    | Actualización masiva (200)                       | Lista directa: `[{"id": "...", "name": "...", "models": [...], "logoUrl?": "..."}]` |
| DELETE | Eliminación masiva (204)                         | Lista directa de ids: `["id1", "id2"]`                                              |

**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/catalogs/vehicle`

### 2. Catálogo Years – `/api/catalogs/year`

| Método | Descripción                        | Body                                           |
| ------ | ---------------------------------- | ---------------------------------------------- |
| GET    | Lista `[{id, year}]`               | —                                              |
| POST   | Creación masiva; retorna ids (201) | Lista directa: `[{"year": 2024}]`              |
| PUT    | Actualización masiva (200)         | Lista directa: `[{"id": "...", "year": 2024}]` |
| DELETE | Eliminación masiva (204)           | Lista directa de ids: `["id1", "id2"]`         |

**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/catalogs/year`

### 3. Catálogo Colors – `/api/catalogs/color`

| Método | Descripción                        | Body                                                          |
| ------ | ---------------------------------- | ------------------------------------------------------------- |
| GET    | Lista `[{id, name, hex}]`          | —                                                             |
| POST   | Creación masiva; retorna ids (201) | Lista directa: `[{"name": "...", "hex": "#000000"}]`          |
| PUT    | Actualización masiva (200)         | Lista directa: `[{"id": "...", "name": "...", "hex": "..."}]` |
| DELETE | Eliminación masiva (204)           | Lista directa de ids: `["id1", "id2"]`                        |

**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/catalogs/color`

Errores: 400 (body/items inválido), 401 (token), 404 (documento no encontrado en PUT), 500 (interno). Sin JSON en cuerpos de error.

### 4. Catálogo Relationship Types – `/api/catalogs/relationship-type`

Catálogo de tipos de relación para contactos de emergencia. Solo **lectura** (GET). Ruta en Firestore: `catalogs/default/relationship_types`. Requiere Bearer token.

| Método | Descripción                              | Body |
| ------ | ---------------------------------------- | ---- |
| GET    | Lista `[{id, label, order}]` ordenada   | —    |

**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/catalogs/relationship-type`

**Ejemplo de respuesta GET**:
```json
[
  {"id": "abc1", "label": "Padre", "order": 1},
  {"id": "abc2", "label": "Madre", "order": 2},
  {"id": "abc3", "label": "Cónyuge / Esposo(a)", "order": 3},
  {"id": "abc4", "label": "Hijo", "order": 4},
  {"id": "abc5", "label": "Hija", "order": 5},
  ...
  {"id": "abc20", "label": "Otro", "order": 20}
]
```

**cURL**:
```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/catalogs/relationship-type' \
  -H 'Authorization: Bearer <token>'
```

Errores: 401 (token inválido), 405 (método no permitido), 500 (interno). Sin JSON en cuerpos de error.

**Seed del catálogo** (crear los 20 tipos de relación en Firestore):
```bash
cd sport_monitor_cloud_functions
python scripts/seed_relationship_types.py
```

### 5. Catálogo Checkpoint types – `/api/catalogs/checkpoint-type`

Tipos de checkpoint agrupados por categoría. **GET** devuelve siempre cinco grupos en orden fijo: `zones`, `symbols`, `waypoints`, `safety`, `dunes_sand`. Cada grupo es `{ "type": "<categoría>", "items": [ ... ] }`. Cada ítem incluye `id` (Firestore), `name`, `type` (slug del tipo), `icon`, `description` y `abbreviation` (`null` o string). Los ítems dentro de cada grupo se ordenan por `type`. **POST**: body es un **array de grupos** con la misma forma (sin `id` en los ítems); por cada ítem se crea un documento con campo `category` en Firestore. Campos por ítem obligatorios: `name`, `type`, `icon`, `description` (strings no vacíos). `abbreviation` opcional: string no vacío, `null`, u omitido; string vacío no está permitido. Firestore: `catalogs/default/checkpoint_types`. **Sin PUT**: solo GET, POST y DELETE masivos.

| Método | Descripción                        | Body                                                          |
| ------ | ---------------------------------- | ------------------------------------------------------------- |
| GET    | Lista agrupada (cinco categorías)   | —                                                             |
| POST   | Creación masiva; retorna ids (201) | `[{ "type": "zones", "items": [{ ... }] }, ...]`              |
| DELETE | Eliminación masiva (204)           | Lista directa de ids: `["id1", "id2"]`                        |

**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/catalogs/checkpoint-type`

**Ejemplo de respuesta GET** (fragmento):
```json
[
  {
    "type": "zones",
    "items": [
      {
        "id": "abc123",
        "name": "Speed Limit",
        "type": "speed_limit",
        "icon": "speed_limit",
        "abbreviation": null,
        "description": "Indicates a mandatory maximum speed."
      }
    ]
  },
  { "type": "symbols", "items": [] },
  { "type": "waypoints", "items": [] },
  { "type": "safety", "items": [] },
  { "type": "dunes_sand", "items": [] }
]
```

**cURL** (reemplaza `<token>` por un ID token de Firebase Auth):

```bash
curl -sS -X GET 'https://system-track-monitor.web.app/api/catalogs/checkpoint-type' \
  -H "Authorization: Bearer <TOKEN>"
```

```bash
curl -sS -X POST 'https://system-track-monitor.web.app/api/catalogs/checkpoint-type' \
  -H "Authorization: Bearer <TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '[{"type":"zones","items":[{"name":"Speed Limit","type":"speed_limit","icon":"speed_limit","abbreviation":null,"description":"Indicates a mandatory maximum speed."}]}]'
```

```bash
curl -sS -X DELETE 'https://system-track-monitor.web.app/api/catalogs/checkpoint-type' \
  -H "Authorization: Bearer <TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '["abc123"]'
```

Errores: 400 (body/items inválido), 401 (token), 405 (p. ej. PUT), 500 (interno). Sin JSON en cuerpos de error.

---

## 📦 Package: Competitors

Funciones relacionadas con competidores y sus rutas en eventos (API pública).

### 1. `competitor_route` (SPRTMNTRPP-74)

Obtiene la información del competidor y su ruta para un evento y día de carrera. **API pública**: no requiere Bearer token.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://competitor-route-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/competitor-route/{eventId}/{dayId}/{competitorId}`

**Nota**: Esta función es pública y no requiere autenticación.

#### Parámetros (Path o Query Parameters)

| Parámetro      | Tipo   | Requerido | Descripción                                                                     |
| -------------- | ------ | --------- | ------------------------------------------------------------------------------- |
| `eventId`      | string | **Sí**    | ID del evento                                                                   |
| `dayId`        | string | **Sí**    | ID del día de carrera                                                           |
| `competitorId` | string | **Sí**    | ID del competidor (documento en `events/{eventId}/participants/{competitorId}`) |

Los parámetros pueden ir en el path (`/api/competitors/competitor-route/{eventId}/{dayId}/{competitorId}`) o en query (`?eventId=xxx&dayId=yyy&competitorId=zzz`).

#### Validaciones realizadas

- El participante `events/{eventId}/participants/{competitorId}` debe existir y tener `isAvailable == true`.
- El día de carrera `events/{eventId}/day_of_races/{dayId}` debe existir y tener `isActivate == true`.
- Se obtiene el `categoryId` desde `event_categories` donde `name == competitionCategory.registrationCategory` del participante.
- Se busca en `routes` un documento donde `categoryIds` contenga ese `categoryId` y `dayOfRaceIds` contenga `dayId`.

#### Campos Retornados (200)

- `competitor`: Objeto con:
  - `category`: Valor de `pilotNumber` del participante (ej: "ORO")
  - `nombre`: Valor de `registrationCategory` (ej: "25F")
- `route`: Objeto con:
  - `name`: Nombre de la ruta
  - `route`: URL de la ruta (campo `routeUrl` en Firestore)
  - `version`: Siempre `1`
  - `totalDistance`: Distancia total (numérico)
  - `typedistance`: Unidad (ej: "km/millas")
- `lastUpdate`: Fecha/hora del servidor en formato ISO 8601 (ej: `2026-01-13T12:52:32Z`)

#### Comandos cURL

**Con path:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/competitor-route/{eventId}/{dayId}/{competitorId}'
```

**Con query parameters:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/competitor-route?eventId=EVENT_ID&dayId=DAY_ID&competitorId=COMPETITOR_ID'
```

#### Respuestas

- **200 OK**: JSON con `competitor`, `route` y `lastUpdate`.
- **400 Bad Request**: Parámetros faltantes o vacíos (sin cuerpo).
- **404 Not Found**: Participante no encontrado o no disponible, día no activo, categoría no encontrada o ruta no encontrada (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Ejemplo de respuesta exitosa

```json
{
  "competitor": {
    "category": "ORO",
    "nombre": "25F"
  },
  "route": {
    "name": "Ruta Principal",
    "route": "https://example.com/route.gpx",
    "version": 1,
    "totalDistance": 200,
    "typedistance": "km/millas"
  },
  "lastUpdate": "2026-01-13T12:52:32Z"
}
```

### 2. `create_competitor`

Crea un nuevo competidor básico en un evento. Solo guarda datos de competición (categoría, equipo, score). Los datos personales completos están en la colección `users`.

**Tipo**: HTTP Request (POST)  
**Endpoint**: `https://create-competitor-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/create`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |
| `Content-Type`  | `application/json`                 | Tipo de contenido    |

#### Request Body (JSON)

| Campo                  | Tipo   | Requerido | Descripción                  |
| ---------------------- | ------ | --------- | ---------------------------- |
| `userId`               | string | **Sí**    | ID del usuario en colección users |
| `eventId`              | string | **Sí**    | ID del evento                |
| `competitionCategory`  | object | No        | Categoría de competición     |
| `competitionCategory.pilotNumber` | string | No | Número de piloto       |
| `competitionCategory.registrationCategory` | string | No | Categoría de registro |
| `team`                 | string | No        | Nombre del equipo            |

#### Campos Retornados (201)

| Campo | Tipo   | Descripción               |
| ----- | ------ | ------------------------- |
| `id`  | string | ID del competidor creado  |

#### Comandos cURL

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/competitors/create' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -d '{
    "userId": "USER_ID",
    "eventId": "EVENT_ID",
    "competitionCategory": {
      "pilotNumber": "42",
      "registrationCategory": "Pro"
    },
    "team": "Team Red Bull"
  }'
```

#### Respuestas

- **201 Created**: `{"id": "USER_ID"}` (mismo id que en users)
- **400 Bad Request**: Body inválido o campos faltantes (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Usuario o evento no encontrado (sin cuerpo).
- **409 Conflict**: Usuario ya participante en el evento, o número de piloto duplicado (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Notas

- El documento del participante usa el userId como id (mismo id que en users).
- Se guarda en `events/{eventId}/participants/{userId}`.
- Campos automáticos: `registrationDate` (timestamp actual), `score: 0`, `timesToStart: []`, `createdAt`, `updatedAt`.
- Si `pilotNumber` no está vacío, se verifica que no exista duplicado en el mismo evento.
- También acepta `competition` con campos `number`/`category` (se mapean a `pilotNumber`/`registrationCategory` en Firestore).

---

### 3. `create_competitor_user`

Crea en una sola llamada: template de usuario (sin Firebase Auth), subcolecciones de datos (personalData, healthData, emergencyContact, vehicles), membership y participante en el evento. Flujo: (1) documento en `users` (campos raíz: **email**, **username**, isActive, etc.; sin userData), (2.1) `users/{userId}/personalData` (un documento con **id autogenerado**), (2.2) `users/{userId}/healthData` (un documento con **id autogenerado**), (2.3) `users/{userId}/emergencyContact` (**map**: un documento por contacto, **id autogenerado**), (2.4) si hay vehicleData: `users/{userId}/vehicles` (id autogenerado), (3) `users/{userId}/membership/{eventId}`, (4) participante en `events/{eventId}/participants` con el **mismo id** que en users. Rollback automático si falla cualquier paso (incluye borrado de subcolecciones).

**Tipo**: HTTP Request (POST)  
**Endpoint**: `https://create-competitor-user-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/create-user`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |
| `Content-Type`  | `application/json`                 | Tipo de contenido    |

#### Request Body (JSON)

| Campo                  | Tipo   | Requerido | Descripción                         |
| ---------------------- | ------ | --------- | ----------------------------------- |
| `email`                | string | **Sí**    | Email (formato válido)              |
| `username`             | string | No        | Username (si se envía, mínimo 4 caracteres y único) |
| `personalData`         | object | No        | Datos personales                    |
| `personalData.fullName` | string | No       | Nombre completo                     |
| `personalData.phone`   | string | No        | Teléfono (+52..., 10-15 dígitos). Si se envía, se valida formato |
| `personalData.dateOfBirth` | string/null | No | Fecha nacimiento ISO 8601         |
| `personalData.address` | string | No        | Dirección                           |
| `personalData.city`    | string | No        | Ciudad                              |
| `personalData.state`   | string | No        | Estado                              |
| `personalData.country` | string | No        | País                                |
| `personalData.postalCode` | string | No     | Código postal                       |
| `healthData`           | object | No        | Datos de salud                      |
| `healthData.bloodType` | string | No        | Tipo de sangre                      |
| `healthData.allergies` | string | No        | Alergias                            |
| `healthData.medications` | string | No      | Medicamentos                        |
| `healthData.medicalConditions` | string | No | Condiciones médicas              |
| `healthData.insuranceProvider` | string | No | Proveedor de seguro              |
| `healthData.insuranceNumber` | string | No   | Número de póliza                   |
| `emergencyContacts`    | array  | No        | Lista de contactos de emergencia (puede ser `[]`) |
| `emergencyContacts[].fullName` | string | Condicional | Nombre del contacto (requerido si se envía el contacto) |
| `emergencyContacts[].relationship` | string | No | Relación con el usuario        |
| `emergencyContacts[].phone` | string | Condicional | Teléfono del contacto (requerido si se envía el contacto) |
| `vehicleData`          | object | No        | Si se envía, se crea un documento en `users/{userId}/vehicles` (id autogenerado) |
| `vehicleData.branch`   | string | No        | Marca del vehículo (también se acepta `brand`)                                   |
| `vehicleData.model`    | string | No        | Modelo                                                                           |
| `vehicleData.year`     | int    | No        | Año                                                                              |
| `vehicleData.color`    | string | No        | Color                                                                            |
| `competition`          | object | No        | Datos de competición. Si no se envía, se crea con valores por defecto            |
| `competition.eventId`  | string | **Sí**    | ID del evento                                                                   |
| `competition.number`   | string | **Sí**    | Número de piloto                                                                |
| `competition.category` | string | **Sí**    | Categoría de registro                                                           |
| `competition.team`     | string | No        | Nombre del equipo                                                               |

#### Campos Retornados (201)

| Campo          | Tipo   | Descripción                    |
| -------------- | ------ | ------------------------------ |
| `id`           | string | ID del usuario (mismo id en `users` y en `participants`) |
| `membershipId` | string | ID del evento (= eventId)      |

#### Comandos cURL

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/competitors/create-user' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -d '{
    "email": "piloto@example.com",
    "username": "piloto01",
    "personalData": {
      "fullName": "Luis Enrique",
      "phone": "",
      "dateOfBirth": null,
      "address": "",
      "city": "",
      "state": "",
      "country": "",
      "postalCode": ""
    },
    "healthData": {
      "bloodType": "No especificado",
      "allergies": "",
      "medications": "",
      "medicalConditions": "",
      "insuranceProvider": "",
      "insuranceNumber": ""
    },
    "emergencyContacts": [],
    "vehicleData": {
      "branch": "",
      "model": "",
      "year": 2026,
      "color": ""
    },
    "competition": {
      "eventId": "EVENT_ID",
      "number": "1005",
      "category": "Oro",
      "team": ""
    }
  }'
```

#### Respuestas

- **201 Created**: `{"id": "USER_ID", "membershipId": "EVENT_ID"}`
- **400 Bad Request**: Body inválido o campos faltantes (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Evento no encontrado (sin cuerpo).
- **409 Conflict**: Email o username ya registrado, o número de piloto duplicado en el evento (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Notas

- El `userId` NO se envía en el request; lo genera la función automáticamente al crear el documento en `users`.
- No se crea usuario en Firebase Auth. El documento en `users` tiene `isActive: false` y `authUserId: null`.
- `registrationDate` se asigna automáticamente por la función (timestamp actual); no se envía en el request.
- Los campos `number` y `category` del request se almacenan como `pilotNumber` y `registrationCategory` en Firestore.
- Si `competition` no se envía en el request, se crea con valores por defecto (vacíos) y la validación de sus campos internos aplicará.
- Todos los campos excepto `email` y `competition` (con `eventId`, `number`, `category`) son opcionales. Los valores pueden ser vacíos (`""`) o `null`.
- Estructura Firestore creada:
  - `users/{userId}` - Documento raíz (**email**, **username** a la misma altura, isActive: false, etc.; sin userData)
  - `users/{userId}/personalData/{id}` - Un documento; **id autogenerado** (map)
  - `users/{userId}/healthData/{id}` - Un documento; **id autogenerado** (map)
  - `users/{userId}/emergencyContact/{id}` - Un documento por contacto; **ids autogenerados** (map)
  - `users/{userId}/vehicles/{vehicleId}` - Vehículo (si se envió vehicleData); id autogenerado
  - `users/{userId}/membership/{eventId}` - Relación con evento (solo `createdAt` y `updatedAt`; userId y eventId están implícitos en la ruta)
  - `events/{eventId}/participants/{userId}` - Participante en el evento (mismo id que en users)
- Si cualquier paso falla, se hace rollback automático (subcolecciones y documento users).

---

### 4. `get_competitor_by_id`

Obtiene un competidor específico por su ID desde la subcolección `participants` de un evento.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-competitor-by-id-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/get-competitor-by-id`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |

#### Parámetros (Query o Path Parameters)

| Parámetro       | Tipo   | Requerido | Descripción          |
| --------------- | ------ | --------- | -------------------- |
| `eventId`       | string | **Sí**    | ID del evento        |
| `competitorId`  | string | **Sí**    | ID del competidor    |

Los parámetros pueden ir en query (`?eventId=xxx&competitorId=yyy`) o en path (`/get-competitor-by-id/{eventId}/{competitorId}`).

#### Campos Retornados (200)

| Campo                            | Tipo   | Descripción               |
| -------------------------------- | ------ | ------------------------- |
| `id`                             | string | ID del competidor         |
| `eventId`                        | string | ID del evento             |
| `competitionCategory.pilotNumber` | string | Número de piloto         |
| `competitionCategory.registrationCategory` | string | Categoría       |
| `registrationDate`               | string | Fecha de registro         |
| `team`                           | string | Nombre del equipo         |
| `score`                          | int    | Puntaje                   |
| `timesToStart`                   | array  | Tiempos de salida         |
| `createdAt`                      | string | Fecha de creación         |
| `updatedAt`                      | string | Fecha de actualización    |

#### Comandos cURL

**Con query parameters:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-competitor-by-id?eventId=EVENT_ID&competitorId=COMPETITOR_ID' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

**Con path:**

```bash
curl -X GET \
  'https://get-competitor-by-id-xa26lpxdea-uc.a.run.app/get-competitor-by-id/EVENT_ID/COMPETITOR_ID' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

#### Respuestas

- **200 OK**: Objeto JSON directo con los datos del competidor.
- **400 Bad Request**: Parámetros faltantes (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Competidor no encontrado (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Ejemplo de respuesta exitosa

```json
{
  "id": "COMPETITOR_ID",
  "eventId": "EVENT_ID",
  "competitionCategory": {
    "pilotNumber": "42",
    "registrationCategory": "Pro"
  },
  "registrationDate": "2026-02-15T10:00:00",
  "team": "Team Red Bull",
  "score": 10,
  "timesToStart": [],
  "createdAt": "2026-02-15T08:00:00+00:00",
  "updatedAt": "2026-02-15T09:00:00+00:00"
}
```

---

### 5. `get_competitor_by_email`

Obtiene un usuario competidor buscándolo por email. Busca en la colección `users` y retorna el documento raíz junto con todas sus subcolecciones: `personalData`, `healthData`, `emergencyContacts`, `vehicles` y `membership`.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-competitor-by-email-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/get-competitor-by-email`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |

#### Parámetros (Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                   |
| --------- | ------ | --------- | ----------------------------- |
| `email`   | string | **Sí**    | Email del usuario competidor  |

#### Campos Retornados (200)

| Campo                         | Tipo    | Descripción                              |
| ----------------------------- | ------- | ---------------------------------------- |
| `id`                          | string  | ID del usuario                           |
| `email`                       | string  | Email del usuario                        |
| `username`                    | string  | Nombre de usuario                        |
| `authUserId`                  | string  | ID de Firebase Auth (null si no activado)|
| `avatarUrl`                   | string  | URL del avatar (null si no tiene)        |
| `isActive`                    | boolean | Si el usuario está activo                |
| `createdAt`                   | string  | Fecha de creación                        |
| `updatedAt`                   | string  | Fecha de actualización                   |
| `personalData`                | array   | Datos personales (fullName, phone, etc.) |
| `healthData`                  | array   | Datos de salud (bloodType, allergies, etc.) |
| `emergencyContacts`           | array   | Contactos de emergencia                  |
| `vehicles`                    | array   | Vehículos (branch, year, model, color)   |
| `membership`                  | array   | Membresías a eventos (eventId, userId)   |

#### Comandos cURL

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-competitor-by-email?email=pilot@example.com' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

#### Respuestas

- **200 OK**: Objeto JSON con datos del usuario y todas sus subcolecciones.
- **400 Bad Request**: Email faltante o formato inválido (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Usuario no encontrado con ese email (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Ejemplo de respuesta exitosa

```json
{
  "id": "USER_ID",
  "email": "pilot@example.com",
  "username": "pilot42",
  "authUserId": null,
  "avatarUrl": null,
  "isActive": false,
  "createdAt": "2026-02-15T08:00:00+00:00",
  "updatedAt": "2026-02-15T09:00:00+00:00",
  "personalData": [
    {
      "id": "DOC_ID",
      "fullName": "Juan Pérez",
      "phone": "+521234567890",
      "dateOfBirth": null,
      "address": "",
      "city": "",
      "state": "",
      "country": "",
      "postalCode": "",
      "createdAt": "2026-02-15T08:00:00+00:00",
      "updatedAt": "2026-02-15T08:00:00+00:00"
    }
  ],
  "healthData": [
    {
      "id": "DOC_ID",
      "bloodType": "O+",
      "allergies": "",
      "medications": "",
      "medicalConditions": "",
      "insuranceProvider": "",
      "insuranceNumber": "",
      "createdAt": "2026-02-15T08:00:00+00:00",
      "updatedAt": "2026-02-15T08:00:00+00:00"
    }
  ],
  "emergencyContacts": [
    {
      "id": "DOC_ID",
      "fullName": "María López",
      "phone": "+529876543210",
      "relationship": "Spouse",
      "createdAt": "2026-02-15T08:00:00+00:00",
      "updatedAt": "2026-02-15T08:00:00+00:00"
    }
  ],
  "vehicles": [
    {
      "id": "DOC_ID",
      "branch": "Honda",
      "year": 2024,
      "model": "CRF450R",
      "color": "Red",
      "createdAt": "2026-02-15T08:00:00+00:00",
      "updatedAt": "2026-02-15T08:00:00+00:00"
    }
  ],
  "membership": [
    {
      "id": "EVENT_ID",
      "userId": "USER_ID",
      "eventId": "EVENT_ID",
      "createdAt": "2026-02-15T08:00:00+00:00",
      "updatedAt": "2026-02-15T08:00:00+00:00"
    }
  ]
}
```

---

### 6. `get_event_competitor_by_email`

Obtiene un competidor de un evento buscándolo por email. Busca al usuario por email en `users`, valida que sea participante en `events/{eventId}/participants` y retorna los datos del usuario (con subcolecciones). El objeto `register` con los datos de competición se incluye dentro de la entrada de `membership` que corresponde al evento consultado.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-event-competitor-by-email-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/get-event-competitor-by-email`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |

#### Parámetros (Query Parameters)

| Parámetro | Tipo   | Requerido | Descripción                   |
| --------- | ------ | --------- | ----------------------------- |
| `eventId` | string | **Sí**    | ID del evento                 |
| `email`   | string | **Sí**    | Email del usuario competidor  |

#### Campos Retornados (200)

| Campo                                   | Tipo    | Descripción                               |
| ---------------------------------------- | ------- | ----------------------------------------- |
| `id`                                     | string  | ID del usuario                            |
| `email`                                  | string  | Email del usuario                         |
| `personalData`                           | array   | Datos personales (fullName, phone, etc.)  |
| `healthData`                             | array   | Datos de salud (bloodType, allergies, etc.) |
| `emergencyContacts`                      | array   | Contactos de emergencia                   |
| `vehicles`                               | array   | Vehículos (branch, year, model, color)    |
| `membership`                             | array   | Membresías a eventos (la del evento consultado incluye `register`) |
| `membership[].register.number`           | string  | Número de piloto en el evento             |
| `membership[].register.category`         | string  | Categoría de registro en el evento        |
| `membership[].register.team`             | string  | Nombre del equipo en el evento            |

#### Comandos cURL

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-event-competitor-by-email?eventId=EVENT_ID&email=pilot@example.com' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

#### Respuestas

- **200 OK**: Objeto JSON con datos del usuario y subcolecciones. La membership del evento consultado incluye `register`.
- **400 Bad Request**: Parámetros faltantes o email con formato inválido (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Usuario no encontrado por email o no es participante del evento (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Ejemplo de respuesta exitosa

```json
{
  "id": "USER_ID",
  "email": "pilot@example.com",
  "personalData": [
    {
      "id": "DOC_ID",
      "fullName": "Juan Pérez",
      "phone": "+521234567890",
      "dateOfBirth": "1990-05-15T00:00:00",
      "address": "Calle Principal 123",
      "city": "CDMX",
      "state": "CDMX",
      "country": "México",
      "postalCode": "01000"
    }
  ],
  "healthData": [
    {
      "id": "DOC_ID",
      "bloodType": "O+",
      "allergies": "Ninguna",
      "medications": "Ninguno",
      "medicalConditions": "Ninguna",
      "insuranceProvider": "Seguro XYZ",
      "insuranceNumber": "ABC123456"
    }
  ],
  "emergencyContacts": [
    {
      "id": "DOC_ID",
      "fullName": "María Pérez",
      "phone": "+529876543210",
      "relationship": "Esposa"
    }
  ],
  "vehicles": [
    {
      "id": "DOC_ID",
      "branch": "Toyota",
      "year": 2025,
      "model": "Hilux",
      "color": "Gris"
    }
  ],
  "membership": [
    {
      "id": "EVENT_ID",
      "userId": "USER_ID",
      "eventId": "EVENT_ID",
      "register": {
        "number": "42",
        "category": "Pro",
        "team": "Team Red Bull"
      }
    }
  ]
}
```

---

### 7. `get_event_competitor_by_id`

Obtiene un competidor de un evento buscándolo directamente por su ID. Valida que el competidor sea participante en `events/{eventId}/participants/{competitorId}`, obtiene los datos del usuario en `users/{competitorId}` y retorna los datos del usuario (con subcolecciones). El objeto `register` con los datos de competición se incluye dentro de la entrada de `membership` que corresponde al evento consultado.

**Tipo**: HTTP Request (GET)
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/get-event-competitor-by-id`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |

#### Parámetros (Query Parameters)

| Parámetro      | Tipo   | Requerido | Descripción                        |
| -------------- | ------ | --------- | ---------------------------------- |
| `eventId`      | string | **Sí**    | ID del evento                      |
| `competitorId` | string | **Sí**    | ID del competidor (userId)         |

#### Campos Retornados (200)

| Campo                                   | Tipo    | Descripción                               |
| ---------------------------------------- | ------- | ----------------------------------------- |
| `id`                                     | string  | ID del usuario                            |
| `email`                                  | string  | Email del usuario                         |
| `personalData`                           | array   | Datos personales (fullName, phone, etc.)  |
| `healthData`                             | array   | Datos de salud (bloodType, etc.)          |
| `emergencyContacts`                      | array   | Contactos de emergencia                   |
| `vehicles`                               | array   | Vehículos (branch, year, model, color)    |
| `membership`                             | array   | Membresías a eventos (la del evento consultado incluye `register`) |
| `membership[].register.number`           | string  | Número de piloto en el evento             |
| `membership[].register.category`         | string  | Categoría de registro en el evento        |
| `membership[].register.team`             | string  | Nombre del equipo en el evento            |

#### Comandos cURL

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-event-competitor-by-id?eventId=EVENT_ID&competitorId=COMPETITOR_ID' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

#### Respuestas

- **200 OK**: Objeto JSON con datos del usuario y subcolecciones. La membership del evento consultado incluye `register`.
- **400 Bad Request**: Parámetros faltantes (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Competidor no es participante del evento o usuario no encontrado (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Deploy

```bash
firebase deploy --only functions:get_event_competitor_by_id
```

---

### 8. `get_competitors_by_event`

Obtiene todos los competidores de un evento, ordenados por fecha de registro descendente. Soporta filtros opcionales por categoría y equipo.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://get-competitors-by-event-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/get-competitors-by-event`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |

#### Parámetros (Query Parameters)

| Parámetro   | Tipo   | Requerido | Descripción                       |
| ----------- | ------ | --------- | --------------------------------- |
| `eventId`   | string | **Sí**    | ID del evento                     |
| `category`  | string | No        | Filtrar por categoría de registro |
| `team`      | string | No        | Filtrar por equipo                |

#### Campos Retornados (200) - Array de competidores

| Campo                            | Tipo   | Descripción               |
| -------------------------------- | ------ | ------------------------- |
| `id`                             | string | ID del competidor         |
| `eventId`                        | string | ID del evento             |
| `competitionCategory.pilotNumber` | string | Número de piloto         |
| `competitionCategory.registrationCategory` | string | Categoría       |
| `registrationDate`               | string | Fecha de registro         |
| `team`                           | string | Nombre del equipo         |
| `score`                          | int    | Puntaje                   |
| `timesToStart`                   | array  | Tiempos de salida         |
| `createdAt`                      | string | Fecha de creación         |
| `updatedAt`                      | string | Fecha de actualización    |

#### Comandos cURL

**Todos los competidores del evento:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-competitors-by-event?eventId=EVENT_ID' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

**Filtrar por categoría:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-competitors-by-event?eventId=EVENT_ID&category=Pro' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

**Filtrar por equipo:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-competitors-by-event?eventId=EVENT_ID&team=Team%20Red%20Bull' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

**Filtrar por categoría y equipo:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/get-competitors-by-event?eventId=EVENT_ID&category=Pro&team=Team%20Red%20Bull' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

#### Respuestas

- **200 OK**: Array JSON directo de competidores. Si no hay resultados, retorna `[]`.
- **400 Bad Request**: eventId faltante (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Ejemplo de respuesta exitosa

```json
[
  {
    "id": "COMPETITOR_1_ID",
    "eventId": "EVENT_ID",
    "competitionCategory": {
      "pilotNumber": "42",
      "registrationCategory": "Pro"
    },
    "registrationDate": "2026-02-15T10:00:00",
    "team": "Team Red Bull",
    "score": 10,
    "timesToStart": [],
    "createdAt": "2026-02-15T08:00:00+00:00",
    "updatedAt": "2026-02-15T09:00:00+00:00"
  },
  {
    "id": "COMPETITOR_2_ID",
    "eventId": "EVENT_ID",
    "competitionCategory": {
      "pilotNumber": "7",
      "registrationCategory": "Amateur"
    },
    "registrationDate": "2026-02-14T10:00:00",
    "team": "Solo",
    "score": 5,
    "timesToStart": [],
    "createdAt": "2026-02-14T08:00:00+00:00",
    "updatedAt": "2026-02-14T09:00:00+00:00"
  }
]
```

---

### 6. `list_competitors_by_event`

Lista competidores de un evento con **paginación por cursor**. Devuelve por cada competidor: id (documento), nombre, categoría, número y equipo. Región: us-east4.

**Tipo**: HTTP Request (GET)  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/list-competitors-by-event`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |

#### Parámetros (Query Parameters)

| Parámetro   | Tipo   | Requerido | Descripción                                                                 |
| ----------- | ------ | --------- | --------------------------------------------------------------------------- |
| `eventId`   | string | **Sí**    | ID del evento                                                               |
| `limit`     | int    | No        | Tamaño de página (default 20, máx 100)                                      |
| `cursor`    | string | No        | ID del último documento de la página anterior (`lastDocId`) para siguiente página |

#### Respuesta 200 - Estructura

Array directo de objetos con:
  - **id**: ID del documento del competidor en la colección del evento (para identificarlo).
  - **name**: Nombre completo del competidor (desde datos personales del usuario).
  - **category**: Categoría de registro (`registrationCategory`).
  - **number**: Número de piloto (`pilotNumber`).
  - **team**: Nombre del equipo.

#### Comandos cURL

**Primera página:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/list-competitors-by-event?eventId=EVENT_ID&limit=20' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

**Siguiente página (usar `lastDocId` de la respuesta anterior como `cursor`):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/competitors/list-competitors-by-event?eventId=EVENT_ID&limit=20&cursor=LAST_DOC_ID' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN'
```

#### Respuestas

- **200 OK**: Array directo de competidores (`[{ id, name, category, number, team }, ...]`).
- **400 Bad Request**: eventId faltante o inválido (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Ejemplo de respuesta exitosa

```json
[
  {
    "id": "USER_ID_1",
    "name": "Juan Pérez",
    "category": "Pro",
    "number": "42",
    "team": "Team Red Bull"
  },
  {
    "id": "USER_ID_2",
    "name": "María García",
    "category": "Amateur",
    "number": "7",
    "team": "Solo"
  }
]
```

---

### 7. `delete_competitor_user`

Elimina el usuario competidor creado con `create_competitor_user` y todos sus datos asociados: participante en el evento, membership, subcolecciones (vehicles, emergencyContacts, healthData, personalData) y documento en `users`.

**Tipo**: HTTP Request (DELETE)  
**Endpoint**: `https://delete-competitor-user-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/delete-user`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                          | Descripción          |
| --------------- | ------------------------------ | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}` | Token de autenticación |
| `Content-Type`  | `application/json`             | Body en JSON         |

#### Body (JSON)

El usuario se puede identificar por **userId** o por **email** (debe enviarse al menos uno). `eventId` es siempre requerido.

| Campo     | Tipo   | Requerido | Descripción                                           |
| --------- | ------ | --------- | ----------------------------------------------------- |
| `userId`  | string | No*       | ID del usuario a eliminar (*requerido si no se envía email) |
| `email`   | string | No*       | Email del usuario (*requerido si no se envía userId; se busca el usuario por este campo) |
| `eventId` | string | **Sí**    | ID del evento (membership/participante)               |

También se aceptan `user_id` y `event_id` como nombres de campo.

#### Comandos cURL

**Por userId:**

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/competitors/delete-user' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"userId": "USER_ID", "eventId": "EVENT_ID"}'
```

**Por email:**

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/competitors/delete-user' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"email": "usuario@example.com", "eventId": "EVENT_ID"}'
```

**Directo (Cloud Run):**

```bash
curl -X DELETE \
  'https://delete-competitor-user-xa26lpxdea-uc.a.run.app' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"userId": "USER_ID", "eventId": "EVENT_ID"}'
```

#### Respuestas

- **204 No Content**: Usuario y datos asociados eliminados correctamente (cuerpo vacío).
- **400 Bad Request**: Body inválido, falta `eventId` o no se envió ni `userId` ni `email` (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Usuario no encontrado en `users` (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

---

### 8. `delete_competitor`

Elimina **solo el participante del evento** (y su membership en `users/{userId}/membership/{eventId}`). **No elimina** el documento del usuario en `users` ni sus subcolecciones (vehicles, emergencyContacts, healthData, personalData). Útil para quitar a un competidor de un evento sin borrar su cuenta ni datos.

**Tipo**: HTTP Request (DELETE)  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/competitors/delete-competitor`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                          | Descripción          |
| --------------- | ------------------------------ | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}` | Token de autenticación |
| `Content-Type`  | `application/json`             | Body en JSON         |

#### Body (JSON)

El participante se identifica por **userId** o por **email** (debe enviarse al menos uno). `eventId` es siempre requerido.

| Campo     | Tipo   | Requerido | Descripción                                           |
| --------- | ------ | --------- | ----------------------------------------------------- |
| `userId`  | string | No*       | ID del usuario/participante a eliminar del evento (*requerido si no se envía email) |
| `email`   | string | No*       | Email del usuario (*requerido si no se envía userId)  |
| `eventId` | string | **Sí**    | ID del evento                                         |

También se aceptan `user_id` y `event_id` como nombres de campo.

#### Comandos cURL

**Por userId:**

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/competitors/delete-competitor' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"userId": "USER_ID", "eventId": "EVENT_ID"}'
```

**Por email:**

```bash
curl -X DELETE \
  'https://system-track-monitor.web.app/api/competitors/delete-competitor' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"email": "usuario@example.com", "eventId": "EVENT_ID"}'
```

#### Respuestas

- **204 No Content**: Participante (y membership) eliminados correctamente (cuerpo vacío).
- **400 Bad Request**: Body inválido, falta `eventId` o no se envió ni `userId` ni `email` (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **404 Not Found**: Participante no encontrado en el evento (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

---

## 📦 Package: Staff

Funciones relacionadas con la gestión de usuarios staff en eventos.

### 1. `create_staff_user`

Crea un usuario staff completo. Flujo transaccional de 3 pasos: (1) crea usuario en Firebase Auth, (2) crea documento en colección `users` con datos personales y contacto de emergencia, (3) crea subcolección `membership/{eventId}` con rol y checkpoints. Rollback automático si cualquier paso falla.

**Tipo**: HTTP Request (POST)  
**Endpoint**: `https://create-staff-user-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/staff/create-user`

**Nota**: Esta función requiere autenticación Bearer token.

#### Headers Requeridos

| Header          | Valor                              | Descripción          |
| --------------- | ---------------------------------- | -------------------- |
| `Authorization` | `Bearer {Firebase Auth Token}`     | Token de autenticación |
| `Content-Type`  | `application/json`                 | Tipo de contenido    |

#### Request Body (JSON)

| Campo                     | Tipo   | Requerido              | Descripción                         |
| ------------------------- | ------ | ---------------------- | ----------------------------------- |
| `personalData`            | object | **Sí**                 | Datos personales                    |
| `personalData.fullName`   | string | **Sí**                 | Nombre completo                     |
| `personalData.email`      | string | **Sí**                 | Email (formato válido)              |
| `personalData.phone`      | string | **Sí**                 | Teléfono (+52..., 10-15 dígitos)    |
| `emergencyContact`        | object | **Sí**                 | Contacto de emergencia              |
| `emergencyContact.fullName` | string | **Sí**               | Nombre del contacto                 |
| `emergencyContact.phone`  | string | **Sí**                 | Teléfono del contacto               |
| `username`                | string | **Sí**                 | Username (mínimo 4 caracteres)      |
| `password`                | string | **Sí**                 | Contraseña (mín 8 chars, 1 letra, 1 número) |
| `confirmPassword`         | string | **Sí**                 | Debe coincidir con password         |
| `eventId`                 | string | **Sí**                 | ID del evento                       |
| `role`                    | string | **Sí**                 | `"organizador"`, `"staff"` o `"checkpoint"` |
| `checkpointId`            | string | **Sí** (si role=checkpoint) | ID del checkpoint              |

#### Campos Retornados (201)

| Campo          | Tipo   | Descripción                    |
| -------------- | ------ | ------------------------------ |
| `id`           | string | ID del usuario en colección `users` |
| `authUserId`   | string | UID de Firebase Auth           |
| `membershipId` | string | ID del evento (= eventId)      |

#### Comandos cURL

**Crear staff con rol "staff":**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/staff/create-user' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -d '{
    "personalData": {
      "fullName": "Ana García",
      "email": "ana@example.com",
      "phone": "+521234567890"
    },
    "emergencyContact": {
      "fullName": "Luis García",
      "phone": "+529876543210"
    },
    "username": "anagarcia",
    "password": "MiPassw0rd123",
    "confirmPassword": "MiPassw0rd123",
    "eventId": "EVENT_ID",
    "role": "staff"
  }'
```

**Crear staff con rol "checkpoint" (requiere checkpointId):**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/staff/create-user' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -d '{
    "personalData": {
      "fullName": "Pedro López",
      "email": "pedro@example.com",
      "phone": "+521234567890"
    },
    "emergencyContact": {
      "fullName": "Rosa López",
      "phone": "+529876543210"
    },
    "username": "pedrolopez",
    "password": "MiPassw0rd123",
    "confirmPassword": "MiPassw0rd123",
    "eventId": "EVENT_ID",
    "role": "checkpoint",
    "checkpointId": "CHECKPOINT_ID"
  }'
```

**Crear staff con rol "organizador":**

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/staff/create-user' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \
  -d '{
    "personalData": {
      "fullName": "Carlos Ruiz",
      "email": "carlos@example.com",
      "phone": "+521234567890"
    },
    "emergencyContact": {
      "fullName": "María Ruiz",
      "phone": "+529876543210"
    },
    "username": "carlosruiz",
    "password": "MiPassw0rd123",
    "confirmPassword": "MiPassw0rd123",
    "eventId": "EVENT_ID",
    "role": "organizador"
  }'
```

#### Respuestas

- **201 Created**: `{"id": "USER_ID", "authUserId": "AUTH_UID", "membershipId": "EVENT_ID"}`
- **400 Bad Request**: Body inválido, campos faltantes, rol inválido, checkpointId faltante para rol checkpoint (sin cuerpo).
- **401 Unauthorized**: Token inválido o faltante (sin cuerpo).
- **409 Conflict**: Email o username ya registrado (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Notas

- Estructura Firestore creada:
  - `users/{userId}` - Documento del usuario (personalData, emergencyContact, userData, authUserId)
  - `users/{userId}/membership/{eventId}` - Relación con evento (role, checkpointIds, assignedAt)
- A diferencia de `create_competitor_user`, no guarda healthData ni vehicleData.
- Roles válidos: `organizador`, `staff`, `checkpoint`.
- Si `role` es `checkpoint`, el campo `checkpointId` es obligatorio.
- Rollback automático: si el paso 2 o 3 falla, se eliminan los recursos creados en pasos anteriores.

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

| Parámetro | Tipo   | Requerido | Descripción                                 |
| --------- | ------ | --------- | ------------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento (puede venir en path o query) |

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

| Parámetro      | Tipo   | Requerido | Descripción                                     |
| -------------- | ------ | --------- | ----------------------------------------------- |
| `checkpointId` | string | **Sí**    | ID del checkpoint (puede venir en path o query) |
| `eventId`      | string | **Sí**    | ID del evento (puede venir en path o query)     |

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
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/checkpoint/competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro      | Tipo   | Requerido | Descripción                                                  |
| -------------- | ------ | --------- | ------------------------------------------------------------ |
| `eventId`      | string | **Sí**    | ID del evento (puede venir en path o query)                  |
| `dayOfRaceId`  | string | **Sí**    | ID del día de carrera (puede venir en path o query)          |
| `checkpointId` | string | **Sí**    | ID del checkpoint para filtrar (puede venir en path o query) |

**Nota**: Los parámetros pueden venir en el path de la URL (`/api/checkpoint/competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}`) o como query parameters (`?eventId=xxx&dayOfRaceId=yyy&checkpointId=zzz`).

#### Campos Retornados (CompetitorTrackingWithRoute)

**Estructura de respuesta (sin wrapper):**

```json
{
  "competitors": [...],
  "routeName": "Nombre de la Ruta"
}
```

**Nota importante**: La respuesta NO incluye un wrapper `{ "success": true, "data": {...} }`. Retorna directamente el objeto `CompetitorTrackingWithRoute`.

**Campos de `competitors` (array de CompetitorTracking):**

- `id`: ID del competidor
- `name`: Nombre del competidor
- `order`: Orden del competidor
- `category`: Categoría del competidor
- `number`: Número del competidor (string)
- `timeToStart`: Fecha y hora de inicio en formato ISO 8601 (puede ser null)
- `createdAt`: Fecha de creación en formato ISO 8601 (**NOTA**: Se genera en el momento de la consulta con `DateTime.now()`, NO se usa el valor de Firestore)
- `updatedAt`: Fecha de actualización en formato ISO 8601 (**NOTA**: Se genera en el momento de la consulta con `DateTime.now()`, NO se usa el valor de Firestore)
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

**Consulta 1: Obtener Todos los Competidores**

- **Ruta**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors`
- **Método**: Obtener todos los documentos sin filtros
- **Timeout**: 20 segundos

**Consulta 2: Obtener Checkpoint Específico por Competidor**

- **Ruta**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints/{checkpointId}`
- **Método**: Obtener documento específico por ID (para cada competidor)
- **Timeout**: 5 segundos por competidor
- **Nota**: Solo se incluyen competidores que tienen el checkpoint específico. Si el checkpoint no existe para un competidor, ese competidor se omite.

**Consulta 3: Obtener Todas las Rutas**

- **Ruta**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/routes`
- **Método**: Obtener todos los documentos sin filtros
- **Timeout**: 20 segundos

#### Lógica de Filtrado: isCompetitorVisible

La función filtra competidores visibles según estas reglas:

| Status                                     | Checkpoint Type           | Visible |
| ------------------------------------------ | ------------------------- | ------- |
| `out`                                      | Cualquiera                | ✅ Sí   |
| `outStart`                                 | `start`                   | ✅ Sí   |
| `outStart`                                 | `finish`                  | ✅ Sí   |
| `outStart`                                 | Otros (pass, timer, etc.) | ❌ No   |
| Otros (none, check, outLast, disqualified) | Cualquiera                | ✅ Sí   |

**Valores de Status**: `none`, `check`, `out`, `outStart`, `outLast`, `disqualified`

**Valores de CheckpointType**: `start`, `pass`, `timer`, `startTimer`, `endTimer`, `finish`

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
  'https://system-track-monitor.web.app/api/checkpoint/competitor-tracking/abc123/day1/cp123' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con valores reales:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/checkpoint/competitor-tracking/cN6ykYvP5WortNOxr3j6/day1_2025-11-13/1AkqicDD0nJBgQSOwIKz' \
  -H 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ...' \
  -H 'Content-Type: application/json'
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
  "competitors": [
    {
      "id": "competitor_123",
      "name": "Juan Pérez",
      "order": 1,
      "category": "Moto",
      "number": "123",
      "timeToStart": "2025-11-13T10:00:00.000Z",
      "createdAt": "2025-11-13T19:48:01.459Z",
      "updatedAt": "2025-11-13T19:48:01.459Z",
      "trackingCheckpoints": [
        {
          "id": "1AkqicDD0nJBgQSOwIKz",
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
  "routeName": "Ruta Principal"
}
```

**200 OK - Sin competidores (lista vacía):**

```json
{
  "competitors": [],
  "routeName": null
}
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta alguno de los parámetros (`eventId`, `dayOfRaceId` o `checkpointId`) o están vacíos

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Algoritmo de Procesamiento

1. **Obtener competidores**: Consulta `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors`
2. **Para cada competidor**: Obtiene su checkpoint específico desde `competitors/{competitorId}/checkpoints/{checkpointId}`
   - Si el checkpoint no existe, se omite el competidor
   - Si existe, se agrega a la lista con `createdAt` y `updatedAt` generados en el momento (DateTime.now())
3. **Obtener rutas**: Consulta `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/routes` en paralelo
4. **Buscar ruta**: Itera sobre las rutas y busca la que contiene el `checkpointId` en su array `checkpointIds`
5. **Filtrar competidores visibles**: Aplica `isCompetitorVisible()` usando el `statusCompetitor` y `checkpointType`
6. **Construir respuesta**: Retorna `{ "competitors": [...], "routeName": ... }` sin wrapper

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors` y para cada competidor obtiene su checkpoint específico.
- **Filtrado**: Solo se incluyen competidores que tienen el checkpoint específico solicitado y que pasan el filtro de visibilidad `isCompetitorVisible`.
- **Ruta**: La función busca la ruta cuyo array `checkpointIds` contiene el `checkpointId` solicitado. Si no se encuentra, `routeName` será `null`.
- **Timestamps**: Los campos `createdAt` y `updatedAt` del `CompetitorTracking` se generan en el momento de la consulta usando `DateTime.now()`, **NO se usan los valores de Firestore**. Los demás campos de fecha (`timeToStart`, `passTime`) sí se convierten de Timestamps de Firestore a formato ISO 8601.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura `CompetitorTrackingWithRoute`.
- **Parámetros flexibles**: Los parámetros pueden venir en el path de la URL (`/api/checkpoint/competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}`) o como query parameters (`?eventId=xxx&dayOfRaceId=yyy&checkpointId=zzz`).
- **Sin wrapper**: La respuesta NO incluye un wrapper `{ "success": true, "data": {...} }`. Retorna directamente el objeto `CompetitorTrackingWithRoute`.
- **Array vacío**: Si no hay competidores o no se encuentran checkpoints, retorna `{ "competitors": [], "routeName": null }` con código 200 OK.

---

### 7. `all_competitor_tracking`

Obtiene todos los competidores de un evento y día de carrera específico, incluyendo **TODOS** los checkpoints de cada competidor (sin filtrar por checkpoint específico). Retorna una lista de `CompetitorTracking` con todos sus checkpoints.

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://all-competitor-tracking-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/checkpoint/all-competitor-tracking/{eventId}/{dayOfRaceId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |

#### Parámetros (Path o Query Parameters)

| Parámetro     | Tipo   | Requerido | Descripción                                         |
| ------------- | ------ | --------- | --------------------------------------------------- |
| `eventId`     | string | **Sí**    | ID del evento (puede venir en path o query)         |
| `dayOfRaceId` | string | **Sí**    | ID del día de carrera (puede venir en path o query) |

**Nota**: Los parámetros pueden venir en el path de la URL (`/api/checkpoint/all-competitor-tracking/{eventId}/{dayOfRaceId}`) o como query parameters (`?eventId=xxx&dayOfRaceId=yyy`).

#### Campos Retornados (Array de CompetitorTracking)

Cada elemento del array contiene:

- `id`: ID del competidor
- `name`: Nombre del competidor
- `order`: Orden del competidor
- `category`: Categoría del competidor
- `number`: Número del competidor (string)
- `timeToStart`: Fecha y hora de inicio en formato ISO 8601 (puede ser null)
- `createdAt`: Fecha de creación en formato ISO 8601 (desde Firestore)
- `updatedAt`: Fecha de actualización en formato ISO 8601 (desde Firestore)
- `trackingCheckpoints`: Array con **TODOS** los checkpoints del competidor:
  - `id`: ID del checkpoint
  - `name`: Nombre del checkpoint
  - `order`: Orden del checkpoint
  - `checkpointType`: Tipo de checkpoint (start, pass, timer, startTimer, endTimer, finish)
  - `statusCompetitor`: Status del competidor (none, check, out, outStart, outLast, disqualified)
  - `checkpointDisable`: ID del checkpoint deshabilitado (string vacío si no hay)
  - `checkpointDisableName`: Nombre del checkpoint deshabilitado (string vacío si no hay)
  - `passTime`: Fecha y hora de paso en formato ISO 8601
  - `note`: Nota opcional (puede ser null)

#### Consultas Firestore

**Consulta 1: Obtener Todos los Competidores**

- **Ruta**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors`
- **Método**: Obtener todos los documentos sin filtros
- **Timeout**: 20 segundos

**Consulta 2: Obtener TODOS los Checkpoints por Competidor**

- **Ruta**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints`
- **Método**: Obtener todos los documentos sin filtros (para cada competidor)
- **Nota**: A diferencia de `competitor_tracking`, esta función obtiene **TODOS** los checkpoints de cada competidor, no solo uno específico.

#### Comandos cURL

**Obtener todos los competidores con todos sus checkpoints (con token Bearer y parámetros en query):**

```bash
curl -X GET \
  'https://all-competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=TU_EVENT_ID&dayOfRaceId=TU_DAY_ID' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con IDs específicos:**

```bash
curl -X GET \
  'https://all-competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=abc123&dayOfRaceId=day1' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Usando el endpoint con Hosting (parámetros en path):**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/checkpoint/all-competitor-tracking/abc123/day1' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Ejemplo con valores reales:**

```bash
curl -X GET \
  'https://system-track-monitor.web.app/api/checkpoint/all-competitor-tracking/cN6ykYvP5WortNOxr3j6/abc123' \
  -H 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ...' \
  -H 'Content-Type: application/json'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://all-competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=abc123&dayOfRaceId=day1' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI'
```

**Probar error 400 (sin parámetros):**

```bash
curl -X GET \
  'https://all-competitor-tracking-xa26lpxdea-uc.a.run.app' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Probar error 401 (sin token):**

```bash
curl -X GET \
  'https://all-competitor-tracking-xa26lpxdea-uc.a.run.app?eventId=abc123&dayOfRaceId=day1' \
  -H 'Content-Type: application/json' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Respuestas

**200 OK - Competidores encontrados (array directo):**

```json
[
  {
    "id": "competitor123",
    "createdAt": "2024-01-15T10:00:00Z",
    "updatedAt": "2024-01-15T12:00:00Z",
    "name": "Juan Pérez",
    "order": 1,
    "category": "Moto A",
    "number": "42",
    "timeToStart": "2024-01-15T08:00:00Z",
    "trackingCheckpoints": [
      {
        "id": "checkpoint1",
        "name": "Checkpoint Inicio",
        "checkpointType": "start",
        "statusCompetitor": "check",
        "checkpointDisable": "",
        "checkpointDisableName": "",
        "passTime": "2024-01-15T08:05:00Z",
        "order": 1,
        "note": null
      },
      {
        "id": "checkpoint2",
        "name": "Checkpoint Intermedio",
        "checkpointType": "pass",
        "statusCompetitor": "none",
        "checkpointDisable": "",
        "checkpointDisableName": "",
        "passTime": "2024-01-15T08:00:00Z",
        "order": 2,
        "note": null
      }
    ]
  }
]
```

**200 OK - Sin competidores (array vacío):**

```json
[]
```

**400 Bad Request** - Sin cuerpo (solo código HTTP) - cuando falta alguno de los parámetros (`eventId` o `dayOfRaceId`) o están vacíos

**401 Unauthorized** - Sin cuerpo (solo código HTTP) - cuando el token Bearer es inválido, expirado o falta el header `Authorization`

**500 Internal Server Error** - Sin cuerpo (solo código HTTP) - errores del servidor al consultar Firestore o procesar datos

### Algoritmo de Procesamiento

1. **Obtener competidores**: Consulta `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors`
2. **Para cada competidor**: Obtiene **TODOS** sus checkpoints desde `competitors/{competitorId}/checkpoints`
   - No se filtra por checkpoint específico
   - Se obtienen todos los checkpoints del competidor
3. **Construir respuesta**: Retorna array directo de `CompetitorTracking` con todos sus checkpoints

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Consulta**: La función consulta `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors` y para cada competidor obtiene **TODOS** sus checkpoints.
- **Sin filtros**: Esta función NO filtra por checkpoint específico. Obtiene todos los checkpoints de todos los competidores.
- **Timestamps**: Los campos `createdAt` y `updatedAt` se obtienen directamente de Firestore (no se generan en el momento como en `competitor_tracking`).
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura `List<CompetitorTracking>`.
- **Parámetros flexibles**: Los parámetros pueden venir en el path de la URL (`/api/checkpoint/all-competitor-tracking/{eventId}/{dayOfRaceId}`) o como query parameters (`?eventId=xxx&dayOfRaceId=yyy`).
- **Sin wrapper**: La respuesta NO incluye un wrapper. Retorna directamente un array de `CompetitorTracking`.
- **Array vacío**: Si no hay competidores, retorna `[]` (array vacío) con código 200 OK.
- **Diferencia con `competitor_tracking`**:
  - `competitor_tracking`: Filtra por checkpoint específico, retorna `CompetitorTrackingWithRoute` con `routeName`
  - `all_competitor_tracking`: Obtiene TODOS los checkpoints, retorna `List<CompetitorTracking>` sin `routeName`

---

### 8. `update_competitor_status`

Actualiza el estado de un competidor en un checkpoint específico. Incluye lógica condicional para manejar diferentes estados y actualiza campos relacionados como `checkpointDisable` y `checkpointDisableName`.

**Tipo**: HTTP Request (PUT)  
**Endpoint**: `https://update-competitor-status-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/checkpoint/update-competitor-status/{eventId}/{dayOfRaceId}/{competitorId}/{checkpointId}`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |
| `Content-Type`  | string | **Sí**    | `application/json`                                      |

#### Parámetros (Path)

| Parámetro      | Tipo   | Requerido | Descripción                              |
| -------------- | ------ | --------- | ---------------------------------------- |
| `eventId`      | string | **Sí**    | ID del evento (viene en el path)         |
| `dayOfRaceId`  | string | **Sí**    | ID del día de carrera (viene en el path) |
| `competitorId` | string | **Sí**    | ID del competidor (viene en el path)     |
| `checkpointId` | string | **Sí**    | ID del checkpoint (viene en el path)     |

#### Request Body

```json
{
  "status": "check",
  "checkpointDisableName": "Nombre del Checkpoint",
  "note": "Nota opcional"
}
```

**Campos del Request:**

- `status` (string, requerido): Nuevo estado del competidor. Valores válidos: `none`, `check`, `out`, `outStart`, `outLast`, `disqualified`
- `checkpointDisableName` (string, condicional): Nombre del checkpoint. **Requerido** cuando `status` es `out`, `outStart` o `outLast`
- `note` (string, opcional): Nota opcional sobre la actualización

#### Lógica Condicional de Actualización

**Cuando `status` NO es `out`, `outStart` o `outLast`:**

- `checkpointDisable`: `null`
- `checkpointDisableName`: `null`

**Cuando `status` ES `out`, `outStart` o `outLast`:**

- `checkpointDisable`: `checkpointId` (del path)
- `checkpointDisableName`: Valor del request (o nombre del checkpoint si no se proporciona)

**Campos siempre actualizados:**

- `statusCompetitor`: Valor del campo `status` del request
- `passTime`: Fecha/hora actual (generada automáticamente)
- `updatedAt`: Fecha/hora actual (generada automáticamente)
- `note`: Nota opcional (si se proporciona)

#### Consulta Firestore

- **Ruta**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints/{checkpointId}`
- **Método**: `update()` - Actualiza el documento del checkpoint específico

#### Comandos cURL

**Actualizar estado del competidor (con token Bearer):**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/checkpoint/update-competitor-status/{eventId}/{dayOfRaceId}/{competitorId}/{checkpointId}' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "check",
    "checkpointDisableName": "Checkpoint Intermedio",
    "note": "Competidor registrado correctamente"
  }'
```

**Ejemplo con valores reales:**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/checkpoint/update-competitor-status/cN6ykYvP5WortNOxr3j6/MelNPSXdEOgyA5ALu0QT/competitor123/1AkqicDD0nJBgQSOwIKz' \
  -H 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "check",
    "checkpointDisableName": "Checkpoint Intermedio",
    "note": "Competidor registrado correctamente"
  }'
```

**Actualizar con status 'out' (requiere checkpointDisableName):**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/checkpoint/update-competitor-status/cN6ykYvP5WortNOxr3j6/MelNPSXdEOgyA5ALu0QT/competitor123/1AkqicDD0nJBgQSOwIKz' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "out",
    "checkpointDisableName": "Checkpoint Inicio",
    "note": "Competidor fuera de carrera"
  }'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X PUT \
  'https://system-track-monitor.web.app/api/checkpoint/update-competitor-status/cN6ykYvP5WortNOxr3j6/MelNPSXdEOgyA5ALu0QT/competitor123/1AkqicDD0nJBgQSOwIKz' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "check",
    "note": "Actualización de estado"
  }'
```

#### Respuestas

**200 OK - Estado actualizado exitosamente:**

```json
{
  "success": true,
  "message": "Estado del competidor actualizado exitosamente",
  "data": {
    "competitorId": "competitor123",
    "checkpointId": "checkpoint456",
    "status": "check",
    "updatedAt": "2024-01-15T10:00:00Z"
  }
}
```

**400 Bad Request** - Cuando faltan parámetros, el request body es inválido, o `checkpointDisableName` es requerido pero no se proporciona:

```json
{
  "success": false,
  "message": "Bad Request",
  "error": "status es requerido"
}
```

**401 Unauthorized** - Cuando el token Bearer es inválido, expirado o falta el header `Authorization`:

```json
{
  "success": false,
  "message": "Unauthorized",
  "error": "Token inválido o faltante"
}
```

**404 Not Found** - Cuando el checkpoint no existe:

```json
{
  "success": false,
  "message": "Not Found",
  "error": "Checkpoint no encontrado"
}
```

**500 Internal Server Error** - Errores del servidor al actualizar Firestore:

```json
{
  "success": false,
  "message": "Internal Server Error",
  "error": "Error procesando la solicitud"
}
```

### Algoritmo de Procesamiento

1. **Validar token**: Verificar que el token Bearer sea válido
2. **Validar parámetros**: Verificar que `eventId`, `dayOfRaceId`, `competitorId`, `checkpointId` existan
3. **Validar request body**: Verificar que `status` sea válido y que `checkpointDisableName` esté presente si `status` es `out`, `outStart` o `outLast`
4. **Verificar checkpoint**: Verificar que el checkpoint exista en Firestore
5. **Construir datos de actualización**: Aplicar lógica condicional según el `status`
6. **Actualizar Firestore**: Actualizar el documento del checkpoint
7. **Retornar respuesta**: Retornar respuesta JSON con el resultado

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Lógica condicional**: El endpoint implementa lógica condicional para establecer `checkpointDisable` y `checkpointDisableName` según el `status`.
- **Timestamps automáticos**: `passTime` y `updatedAt` se generan automáticamente en el servidor (no se envían en el request).
- **Validación de status**: El `status` debe ser uno de los valores válidos del enum `CompetitorsTrackingStatus`.
- **checkpointDisableName requerido**: Cuando el `status` es `out`, `outStart` o `outLast`, el campo `checkpointDisableName` es requerido en el request.
- **Actualización atómica**: La actualización se realiza en una sola operación de Firestore usando `update()`.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura de respuesta con `success`, `message` y `data`.

---

### 9. `days_of_race`

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

| Parámetro | Tipo   | Requerido | Descripción                                 |
| --------- | ------ | --------- | ------------------------------------------- |
| `eventId` | string | **Sí**    | ID del evento (puede venir en path o query) |

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

### 10. `change_competitor_status`

Cambia el estado de un competidor y actualiza todos sus checkpoints relacionados. Esta función consolida tres operaciones:

1. Actualiza el checkpoint específico con el nuevo estado
2. Limpia checkpoints superiores si el status anterior era 'out'
3. Actualiza checkpoints superiores si el nuevo status es 'out'

**Tipo**: HTTP Request (PUT)  
**Endpoint**: `https://change-competitor-status-xa26lpxdea-uc.a.run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/checkpoint/change-competitor-status`

**Nota**: Esta función requiere autenticación Bearer token para validar que el usuario esté autenticado.

#### Headers Requeridos

| Header          | Tipo   | Requerido | Descripción                                             |
| --------------- | ------ | --------- | ------------------------------------------------------- |
| `Authorization` | string | **Sí**    | Bearer token de Firebase Auth (solo para autenticación) |
| `Content-Type`  | string | **Sí**    | `application/json`                                      |

#### Request Body

```json
{
  "eventId": "string (requerido)",
  "dayOfRaceId": "string (requerido)",
  "checkpointId": "string (requerido)",
  "orderCheckpoint": "integer (requerido)",
  "competitorId": "string (requerido)",
  "status": "string (requerido)",
  "lastStatusCompetitor": "string (requerido)",
  "checkpointName": "string (requerido)",
  "note": "string (opcional)"
}
```

**Campos del Request:**

| Parámetro              | Tipo    | Requerido | Descripción                                                                                                                                     |
| ---------------------- | ------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `eventId`              | string  | **Sí**    | ID del evento al que pertenece el competidor                                                                                                    |
| `dayOfRaceId`          | string  | **Sí**    | ID del día de carrera activo                                                                                                                    |
| `checkpointId`         | string  | **Sí**    | ID del checkpoint donde se actualiza el estado                                                                                                  |
| `orderCheckpoint`      | integer | **Sí**    | Orden numérico del checkpoint (usado para determinar checkpoints superiores)                                                                    |
| `competitorId`         | string  | **Sí**    | ID del competidor cuyo estado se actualiza                                                                                                      |
| `status`               | string  | **Sí**    | Nuevo estado del competidor. Valores válidos: `none`, `noneStart`, `noneLast`, `check`, `checkStart`, `checkLast`, `out`, `outStart`, `outLast` |
| `lastStatusCompetitor` | string  | **Sí**    | Estado anterior del competidor. Mismos valores válidos que `status`                                                                             |
| `checkpointName`       | string  | **Sí**    | Nombre del checkpoint (usado para `checkpointDisableName`)                                                                                      |
| `note`                 | string  | No        | Nota opcional asociada al cambio de estado                                                                                                      |

**Valores Válidos para `status` y `lastStatusCompetitor`:**

- `none`, `noneStart`, `noneLast`
- `check`, `checkStart`, `checkLast`
- `out`, `outStart`, `outLast`

**Estados que se consideran "out" (descalificado):** `out`, `outStart`, `outLast`

#### Lógica de Implementación

**Paso 1: Actualizar Checkpoint Específico**

- Actualiza el checkpoint indicado con el nuevo `status`
- Si el nuevo status NO es 'out', limpia `checkpointDisable` y `checkpointDisableName`
- Si el nuevo status ES 'out', establece `checkpointDisable = checkpointId` y `checkpointDisableName = checkpointName`
- Actualiza `passTime` y `updatedAt` con la fecha/hora actual

**Paso 2: Limpiar Checkpoints Superiores** (solo si `lastStatusCompetitor` era 'out')

- Obtiene todos los checkpoints del competidor
- Filtra checkpoints con `order > orderCheckpoint`
- Para cada checkpoint superior:
  - Establece `statusCompetitor = "none"`
  - Limpia `checkpointDisable` y `checkpointDisableName` (establece `null`)
  - Actualiza `updatedAt`

**Paso 3: Actualizar Checkpoints Superiores** (solo si el nuevo `status` es 'out')

- Obtiene todos los checkpoints del competidor
- Filtra checkpoints con `order > orderCheckpoint`
- Para cada checkpoint superior:
  - Establece `statusCompetitor = status` (nuevo status 'out')
  - Establece `checkpointDisable = checkpointId` y `checkpointDisableName = checkpointName`
  - Actualiza `updatedAt`
  - Si se proporciona `note`, la agrega

#### Consulta Firestore

- **Ruta base**: `events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints`
- **Checkpoint específico**: `checkpoints/{checkpointId}`
- **Método**: `update()` - Actualiza documentos de checkpoints

#### Comandos cURL

**Cambiar estado del competidor (con token Bearer):**

```bash
curl -X PUT \
  'https://change-competitor-status-xa26lpxdea-uc.a.run.app' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "eventId": "event123",
    "dayOfRaceId": "day456",
    "checkpointId": "checkpoint789",
    "orderCheckpoint": 5,
    "competitorId": "competitor101",
    "status": "check",
    "lastStatusCompetitor": "none",
    "checkpointName": "Checkpoint 5",
    "note": "Competidor pasó correctamente"
  }'
```

**Ejemplo con valores reales:**

```bash
curl -X PUT \
  'https://change-competitor-status-xa26lpxdea-uc.a.run.app' \
  -H 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...' \
  -H 'Content-Type: application/json' \
  -d '{
    "eventId": "cN6ykYvP5WortNOxr3j6",
    "dayOfRaceId": "MelNPSXdEOgyA5ALu0QT",
    "checkpointId": "1AkqicDD0nJBgQSOwIKz",
    "orderCheckpoint": 10,
    "competitorId": "competitor123",
    "status": "out",
    "lastStatusCompetitor": "check",
    "checkpointName": "CP 10 GASOLINA ENTRADA A PEÑON",
    "note": "Competidor descalificado"
  }'
```

**Usando el endpoint con Hosting:**

```bash
curl -X PUT \
  'https://system-track-monitor.web.app/api/checkpoint/change-competitor-status' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "eventId": "event123",
    "dayOfRaceId": "day456",
    "checkpointId": "checkpoint789",
    "orderCheckpoint": 5,
    "competitorId": "competitor101",
    "status": "check",
    "lastStatusCompetitor": "none",
    "checkpointName": "Checkpoint 5",
    "note": "Competidor pasó correctamente"
  }'
```

**Cambiar de 'out' a 'check' (recuperación - limpia checkpoints superiores):**

```bash
curl -X PUT \
  'https://change-competitor-status-xa26lpxdea-uc.a.run.app' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "eventId": "event123",
    "dayOfRaceId": "day456",
    "checkpointId": "checkpoint789",
    "orderCheckpoint": 5,
    "competitorId": "competitor101",
    "status": "check",
    "lastStatusCompetitor": "out",
    "checkpointName": "Checkpoint 5",
    "note": "Competidor recuperado"
  }'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X PUT \
  'https://change-competitor-status-xa26lpxdea-uc.a.run.app' \
  -H 'Authorization: Bearer TU_TOKEN_FIREBASE_AQUI' \
  -H 'Content-Type: application/json' \
  -d '{
    "eventId": "event123",
    "dayOfRaceId": "day456",
    "checkpointId": "checkpoint789",
    "orderCheckpoint": 5,
    "competitorId": "competitor101",
    "status": "check",
    "lastStatusCompetitor": "none",
    "checkpointName": "Checkpoint 5"
  }'
```

#### Respuestas

**200 OK - Estado actualizado exitosamente:**

```json
{
  "success": true
}
```

**400 Bad Request** - Cuando faltan parámetros, el request body es inválido, o los valores de status son inválidos:

```json
{
  "success": false,
  "message": "Bad Request",
  "error": "Faltan los siguientes parámetros: eventId, dayOfRaceId"
}
```

**401 Unauthorized** - Cuando el token Bearer es inválido, expirado o falta el header `Authorization`:

```json
{
  "success": false,
  "message": "Unauthorized",
  "error": "Token inválido o faltante"
}
```

**404 Not Found** - Cuando el competidor o checkpoint no existe:

```json
{
  "success": false,
  "message": "Not Found",
  "error": "Competidor con ID 'competitor123' no encontrado"
}
```

**500 Internal Server Error** - Errores del servidor al actualizar Firestore:

```json
{
  "success": false,
  "message": "Internal Server Error",
  "error": "Error procesando la solicitud"
}
```

### Algoritmo de Procesamiento

1. **Validar token**: Verificar que el token Bearer sea válido
2. **Validar parámetros**: Verificar que todos los parámetros requeridos estén presentes y sean válidos
3. **Validar tipos**: Verificar que `orderCheckpoint` sea un número entero positivo
4. **Validar status**: Verificar que `status` y `lastStatusCompetitor` sean valores válidos
5. **Verificar recursos**: Verificar que el competidor y checkpoint existan en Firestore
6. **Verificar order**: Verificar que el `order` del checkpoint coincida con `orderCheckpoint`
7. **Paso 1**: Actualizar checkpoint específico con el nuevo status
8. **Paso 2**: Si `lastStatusCompetitor` era 'out', limpiar checkpoints superiores
9. **Paso 3**: Si el nuevo `status` es 'out', actualizar checkpoints superiores
10. **Retornar respuesta**: Retornar `{"success": true}` con código 200

### Notas Importantes

- **Autenticación**: El token Bearer solo se usa para validar que el usuario esté autenticado. No se extrae información del token.
- **Lógica de 3 pasos**: La función implementa una lógica compleja que actualiza el checkpoint específico y maneja checkpoints superiores según el estado anterior y nuevo.
- **Manejo de errores parciales**: Si los Pasos 2 o 3 fallan, se loguea el error pero se retorna éxito (el checkpoint específico ya se actualizó correctamente).
- **Timestamps automáticos**: `passTime` y `updatedAt` se generan automáticamente en el servidor (no se envían en el request).
- **Validación de order**: El `orderCheckpoint` debe coincidir con el `order` del checkpoint en Firestore.
- **Actualización masiva**: Para competidores con muchos checkpoints, las operaciones de actualización masiva pueden tomar tiempo.
- **Compatibilidad**: La respuesta JSON es compatible con modelos Flutter que esperen la estructura de respuesta con `success`.

---

## 📦 Package: Tracking

Funciones relacionadas con el tracking y seguimiento de competidores durante eventos deportivos.

### 9. `track_event_checkpoint`

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

### 10. `track_competitors`

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

### 11. `track_competitors_off`

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

### 12. `track_competitor_position` (SPRTMNTRPP-75)

Recibe posición y datos del competidor en tiempo real (coordenadas, velocidad, tipo, timestamp) y los guarda en **Realtime Database** en la ruta `sport_monitor/tracking/{eventId}/{dayId}/{competitorId}/` con `current` e `historial`. **API pública**: no requiere Bearer token.

**Tipo**: HTTP Request (POST)  
**Endpoint**: `https://track-competitor-position-....run.app`  
**Endpoint con Hosting**: `https://system-track-monitor.web.app/api/tracking/competitor-position?eventId=...&dayId=...&competitorId=...`

**Nota**: Esta función es pública y no requiere autenticación.

#### Parámetros (Query Parameters)

| Parámetro      | Tipo   | Requerido | Descripción             |
| -------------- | ------ | --------- | ----------------------- |
| `eventId`      | string | **Sí**    | UUID del evento         |
| `dayId`        | string | **Sí**    | UUID del día de carrera |
| `competitorId` | string | **Sí**    | UUID del competidor     |

#### Request Body (JSON)

| Campo         | Tipo   | Requerido | Descripción                                    |
| ------------- | ------ | --------- | ---------------------------------------------- |
| `coordinates` | object | **Sí**    | `latitude` (number), `longitude` (number)      |
| `data`        | object | **Sí**    | `speed` (string), `type` (string)              |
| `timeStamp`   | string | **Sí**    | Fecha/hora captura (ej. "DD/MM/YYYY HH:mm:ss") |

Ejemplo:

```json
{
  "coordinates": { "latitude": 19.0, "longitude": 18.0 },
  "data": { "speed": "45", "type": "Millas/km" },
  "timeStamp": "12/12/2026 00:10:10"
}
```

#### Comportamiento

- Los datos se escriben en **Realtime Database** en la ruta `sport_monitor/tracking/{eventId}/{dayId}/{competitorId}/`. **Si la ruta no existe, se crea** al escribir (`update`).
- Se actualizan `current` (posición actual: uuid, latitude, longitude) e `historial` (lista de entradas con coordinates, data, timeStamp). La función genera un `uuid` (timestamp) y lo asigna a `current` y a la nueva entrada de `historial`. El historial tiene un límite de 2000 entradas.
- **Requisito**: El proyecto debe tener Realtime Database habilitado. En producción/config, define la variable de entorno `FIREBASE_DATABASE_URL` (ej. `https://PROJECT_ID-default-rtdb.firebaseio.com`) para que la función pueda conectar; en Cloud Functions se puede configurar en la consola o en el deploy.

#### Respuestas

- **200 OK**: Sin body; la operación se realizó correctamente.
- **400 Bad Request**: Parámetros o body inválidos (sin cuerpo).
- **500 Internal Server Error**: Error interno (sin cuerpo).

#### Comando cURL

```bash
curl -X POST \
  'https://system-track-monitor.web.app/api/tracking/competitor-position?eventId=EVENT_ID&dayId=DAY_ID&competitorId=COMPETITOR_ID' \
  -H 'Content-Type: application/json' \
  -d '{
    "coordinates": { "latitude": 19.0, "longitude": 18.0 },
    "data": { "speed": "45", "type": "Millas/km" },
    "timeStamp": "12/12/2026 00:10:10"
  }'
```

---

## 🔐 Autenticación

### Funciones Públicas (sin autenticación)

Las siguientes funciones pueden ser públicas y no requieren autenticación:

- `competitor_route` - Obtiene competidor y ruta asignada
- `track_competitor_position` - Registra posición y datos del competidor en tiempo real

### Funciones que Requieren Autenticación

Las siguientes funciones requieren autenticación Bearer token:

- `events` - Lista de eventos con paginación (requiere Bearer token)
- `event_detail` - Detalle de un evento (requiere Bearer token)
- `event_categories` - Categorías de un evento (requiere Bearer token)
- `user_route` - Router de usuarios: read (perfil), create (crear/activar), update (actualizar por secciones), read_sections (perfil por sección), subscribedEvents (eventos suscritos paginados), delete_section_item (eliminar contacto o vehículo); paths /api/users/read, /api/users/profile, /api/users/personalData, /api/users/healthData, /api/users/emergencyContacts, /api/users/vehicles, /api/users/membership (GET; DELETE solo emergencyContacts y vehicles), /api/users/subscribedEvents (GET), /api/users/create, /api/users/update (requiere Bearer token)
- `get_vehicles` - Obtiene vehículos de un usuario (requiere Bearer token)
- `update_vehicle` - Actualiza vehículo (requiere Bearer token)
- `delete_vehicle` - Elimina vehículo (requiere Bearer token)
- `search_vehicle` - Busca vehículo por branch, model y year (requiere Bearer token)
- `catalog_route` - Router de catálogos: `/api/catalogs/vehicle`, `/api/catalogs/year`, `/api/catalogs/color` (CRUD masivo), `/api/catalogs/relationship-type` (solo GET), `/api/catalogs/checkpoint-type` (GET, POST, DELETE masivo); requiere Bearer token
- `day_of_race_active` - Obtiene día de carrera activo (requiere token para autenticación)
- `checkpoint` - Obtiene checkpoint específico (requiere token para autenticación)
- `competitor_tracking` - Obtiene tracking de competidores filtrado por checkpoint (requiere token para autenticación)
- `all_competitor_tracking` - Obtiene todos los competidores con todos sus checkpoints (requiere token para autenticación)
- `update_competitor_status` - Actualiza el estado de un competidor en un checkpoint (requiere token para autenticación)
- `change_competitor_status` - Cambia el estado de un competidor y actualiza checkpoints relacionados (requiere token para autenticación)
- `days_of_race` - Obtiene todos los días de carrera (requiere token para autenticación)
- `create_competitor` - Crea competidor básico en un evento (requiere Bearer token)
- `create_competitor_user` - Crea template de usuario competidor + membership + participante en evento, sin Firebase Auth (requiere Bearer token)
- `get_competitor_by_email` - Obtiene usuario competidor por email con todas sus subcolecciones (requiere Bearer token)
- `get_competitor_by_id` - Obtiene competidor por ID (requiere Bearer token)
- `get_event_competitor_by_email` - Obtiene competidor de un evento por email con datos de usuario y register en membership (requiere Bearer token)
- `get_competitors_by_event` - Lista competidores de un evento con filtros (requiere Bearer token)
- `list_competitors_by_event` - Lista paginada de competidores (id, nombre, categoría, número, equipo) por evento (requiere Bearer token)
- `delete_competitor` - Elimina solo el participante del evento (y membership); no elimina el usuario ni sus datos (requiere Bearer token)
- `delete_competitor_user` - Elimina usuario competidor creado con create_competitor_user y todos sus datos (requiere Bearer token)
- `create_staff_user` - Crea usuario staff completo con Auth y membership (requiere Bearer token)
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

# Desplegar solo event_categories
firebase deploy --only functions:event_categories

# Desplegar user_route (read, create, update, subscribedEvents, lectura y DELETE por sección: /api/users/read, /api/users/profile, /api/users/{section}, /api/users/subscribedEvents, /api/users/create, /api/users/update)
firebase deploy --only functions:user_route

# Desplegar solo get_vehicles
firebase deploy --only functions:get_vehicles

# Desplegar solo update_vehicle
firebase deploy --only functions:update_vehicle

# Desplegar solo delete_vehicle
firebase deploy --only functions:delete_vehicle

# Desplegar solo search_vehicle
firebase deploy --only functions:search_vehicle

# Desplegar catálogos (SPRTMNTRPP-82): función router + hosting (rewrites apuntan a catalog_route)
firebase deploy --only functions:catalog_route,hosting

# Desplegar solo day_of_race_active
firebase deploy --only functions:day_of_race_active

# Desplegar solo get_checkpoint
firebase deploy --only functions:get_checkpoint

# Desplegar solo competitor_tracking
firebase deploy --only functions:competitor_tracking

# Desplegar solo all_competitor_tracking
firebase deploy --only functions:all_competitor_tracking

# Desplegar solo update_competitor_status
firebase deploy --only functions:update_competitor_status

# Desplegar solo change_competitor_status
firebase deploy --only functions:change_competitor_status

# Desplegar solo days_of_race
firebase deploy --only functions:days_of_race

# Desplegar solo track_competitor_position
firebase deploy --only functions:track_competitor_position

# Desplegar funciones de tracking
firebase deploy --only functions:track_event_checkpoint,functions:track_competitors,functions:track_competitors_off,functions:track_competitor_position

# Desplegar solo create_competitor
firebase deploy --only functions:create_competitor

# Desplegar solo create_competitor_user
firebase deploy --only functions:create_competitor_user

# Desplegar solo get_competitor_by_email
firebase deploy --only functions:get_competitor_by_email

# Desplegar solo get_event_competitor_by_email
firebase deploy --only functions:get_event_competitor_by_email

# Desplegar solo get_competitor_by_id
firebase deploy --only functions:get_competitor_by_id

# Desplegar solo get_competitors_by_event
firebase deploy --only functions:get_competitors_by_event

# Desplegar solo list_competitors_by_event
firebase deploy --only functions:list_competitors_by_event

# Desplegar solo delete_competitor (solo participante del evento)
firebase deploy --only functions:delete_competitor

# Desplegar solo delete_competitor_user (usuario completo)
firebase deploy --only functions:delete_competitor_user

# Desplegar solo create_staff_user
firebase deploy --only functions:create_staff_user

# Desplegar todas las funciones nuevas de competitors y staff
firebase deploy --only functions:create_competitor,functions:create_competitor_user,functions:delete_competitor,functions:delete_competitor_user,functions:get_competitor_by_email,functions:get_competitor_by_id,functions:get_event_competitor_by_email,functions:get_competitors_by_event,functions:list_competitors_by_event,functions:create_staff_user
```

---

## 🧪 Pruebas Locales

Para probar las funciones localmente, consulta el archivo [README_TESTING.md](./README_TESTING.md).

### Comandos: deploy y emulador

**Despliegue (producción):**

| Acción                         | Comando                                           |
| ------------------------------ | ------------------------------------------------- |
| Desplegar todas las funciones  | `firebase deploy --only functions`                |
| Desplegar una función concreta | `firebase deploy --only functions:NOMBRE_FUNCION` |

Ejemplos: `firebase deploy --only functions:competitor_route`, `firebase deploy --only functions:events`.

**Emulador (local):**

| Acción                                                      | Comando                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------- |
| Iniciar emulador (functions + hosting, con path `/api/...`) | `firebase emulators:start --only functions,hosting`           |
| Iniciar con Firestore                                       | `firebase emulators:start --only functions,hosting,firestore` |
| Solo functions (sin path del API)                           | `firebase emulators:start --only functions`                   |

**Emulador con debug e inspect:**

| Acción                                          | Comando                                                                 |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| Emulador con logs detallados (debug)            | `firebase emulators:start --only functions,hosting --debug`             |
| Emulador con inspector para depurador (Node.js) | `firebase emulators:start --only functions,hosting --inspect-functions` |

**Nota:** `--inspect-functions` solo funciona con funciones en **Node.js**. En proyectos con funciones en **Python** el emulador mostrará _"--inspect-functions not supported for Python functions. Ignored."_ Para depurar funciones Python con breakpoints, usa el flujo descrito en [Depuración con breakpoints](#depuración-con-breakpoints) (debugpy + Attach).

---

### Iniciar emulador

Para poder usar **tanto el path del API como la URL directa de la función**, arranca el emulador con **functions** y **hosting**:

**Requisitos:** El proyecto usa **Python 3.12** (`runtime: python312` en [firebase.json](firebase.json)). El venv está en `functions/venv` con las dependencias en [functions/requirements.txt](functions/requirements.txt). Debes tener sesión en Firebase (`firebase login`).

**Iniciar emulador** (recomendado; así el emulador usa el Python del venv y encuentra el SDK):

```bash
npm run emulators
```

Equivale a poner `functions/venv/bin` en el PATH y ejecutar el emulador. En macOS también se define `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` para evitar el crash de los workers Python al hacer fork (error tipo "objc ... fork() was called").

Si prefieres hacerlo a mano en la misma terminal:

```bash
. functions/venv/bin/activate
# En macOS, si ves crash "objc ... fork() was called", ejecuta antes:
# export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
firebase emulators:start --only functions,hosting
```

(O con Firestore: `firebase emulators:start --only functions,hosting,firestore`.)

Comprobar configuración: `firebase login:list` (cuenta); `functions/venv/bin/python --version` (debe ser 3.12.x).

**Puertos** (definidos en [firebase.json](firebase.json)):

| Servicio  | Puerto | Uso                                      |
| --------- | ------ | ---------------------------------------- |
| Hosting   | 5050   | Acceso por **path del API** (rewrites)   |
| Functions | 5001   | Acceso **directo por nombre de función** |
| Firestore | 8080   | Emulador de base de datos                |
| UI        | 4000   | Interfaz del emulador                    |

**Nota:** El puerto de Hosting está en 5050 (no 5000) para evitar conflicto con otros servicios que suelen usar 5000 (p. ej. AirPlay en macOS).

**Dos formas de llamar a una función:**

1. **Por path del API** (igual que en producción con hosting): las peticiones pasan por Hosting y los rewrites envían a la función.

   ```
   http://localhost:5050/api/competitors/competitor-route?eventId=...&dayId=...&competitorId=...
   http://localhost:5050/api/checkpoint/dayofrace/active/EVENT_ID
   http://localhost:5050/api/checkpoint/competitor-tracking/...
   http://localhost:5050/api/checkpoint/update-competitor-status/...
   http://localhost:5050/api/events
   http://localhost:5050/api/events/detail
   http://localhost:5050/api/event/event-categories/EVENT_ID
   http://localhost:5050/api/users/read
   http://localhost:5050/api/users/profile
   http://localhost:5050/api/users/personalData
   http://localhost:5050/api/users/vehicles
   http://localhost:5050/api/users/subscribedEvents
   http://localhost:5050/api/users/create
   http://localhost:5050/api/users/update
   http://localhost:5050/api/vehicles?userId=UUID
   http://localhost:5050/api/tracking/track-event-checkpoint
   http://localhost:5050/api/tracking/track-competitors
   http://localhost:5050/api/tracking/track-competitors-off
   http://localhost:5050/api/tracking/competitor-position
   ```

2. **Por URL directa de la función** (sin pasar por hosting):
   ```
   http://localhost:5001/system-track-monitor/us-central1/competitor_route?...
   http://localhost:5001/system-track-monitor/us-central1/day_of_race_active?...
   http://localhost:5001/system-track-monitor/us-central1/events
   http://localhost:5001/system-track-monitor/us-central1/track_event_checkpoint
   http://localhost:5001/system-track-monitor/us-central1/track_competitors
   http://localhost:5001/system-track-monitor/us-central1/track_competitors_off
   http://localhost:5001/system-track-monitor/us-central1/track_competitor_position
   http://localhost:5001/system-track-monitor/us-central1/create
   http://localhost:5001/system-track-monitor/us-central1/get_vehicles?userId=UUID
   ```
   (Para POST a competitor-position usar el mismo host con body JSON.)
   Sustituye `system-track-monitor` por tu Project ID si es distinto. Todas las funciones HTTP tienen su path en `/api/...` (ver rewrites en [firebase.json](firebase.json)).

Si solo ejecutas `firebase emulators:start --only functions` (sin hosting), solo funcionará la URL directa en el puerto 5001; el path `/api/...` no estará disponible. Si el puerto 5050 también estuviera ocupado, puedes cambiarlo en `firebase.json` bajo `emulators.hosting.port`.

---

## 📝 Notas Importantes

1. **Paginación**: Para `events`, se recomienda usar `lastDocId` en lugar de `page` para mejor rendimiento con grandes volúmenes de datos.

2. **Códigos HTTP**: Las funciones de eventos (`events`, `event_detail`, `event_categories`), usuarios (`read`, `create`, `update`) y checkpoints (`day_of_race_active`, `checkpoint`, `competitor_tracking`, `all_competitor_tracking`, `days_of_race`) retornan códigos HTTP estándar. Las funciones `update_competitor_status` y `change_competitor_status` retornan objetos JSON con `success`, `message` y `error`. Las funciones de tracking retornan objetos JSON con `success` y `message`.

3. **Errores**: Las funciones de eventos, usuarios y checkpoints retornan solo códigos HTTP en caso de error (400, 401, 404, 500) sin cuerpo JSON, excepto `competitor_tracking`, `update_competitor_status` y `change_competitor_status` que retornan JSON con `success: false` en caso de error. Las funciones de tracking retornan objetos JSON con información del error.

4. **Autenticación**: Las funciones `events`, `event_detail`, `event_categories`, `read`, `create`, `update`, `get_vehicles`, `update_vehicle`, `delete_vehicle`, `search_vehicle`, `catalog_route`, `day_of_race_active`, `checkpoint`, `competitor_tracking`, `all_competitor_tracking`, `update_competitor_status`, `change_competitor_status` y `days_of_race` requieren Bearer token válido de Firebase Auth solo para autenticación. Los parámetros se reciben como parámetros query, path o request body, no se extraen del token. El token solo valida que el usuario esté autenticado.

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
