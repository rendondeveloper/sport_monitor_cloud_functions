# Sport Monitor Cloud Functions

## 📋 Descripción del Proyecto

Este proyecto contiene las **Cloud Functions de Firebase** desarrolladas en Python para el sistema **Sport Monitor**. Estas funciones proporcionan servicios backend para la gestión y control de eventos deportivos, incluyendo:

- **Gestión de Eventos**: Obtención de listados y detalles de eventos deportivos
- **Tracking de Competidores**: Seguimiento en tiempo real de competidores durante eventos
- **Gestión de Checkpoints**: Control de puntos de control en eventos deportivos

Las funciones están desplegadas en **Firebase Cloud Functions** y proporcionan APIs REST para ser consumidas desde aplicaciones cliente (Flutter, Web, etc.).

## 🏗️ Arquitectura

### Estructura del Proyecto

```
functions/
├── events/              # Package: Gestión de Eventos
│   ├── events_customer.py          # get_events
│   └── events_detail_customer.py  # event_detail
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

### 1. `get_events`

Obtiene una lista paginada de eventos desde Firestore. Retorna eventos en formato `EventShortDocument` (versión simplificada con campos esenciales).

**Tipo**: HTTP Request (GET)  
**Endpoint**: `https://us-central1-system-track-monitor.cloudfunctions.net/get_events`

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
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events' \
  -H 'Content-Type: application/json'
```

**Con paginación (size y page):**

```bash
curl -X GET \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events?size=20&page=1' \
  -H 'Content-Type: application/json'
```

**Paginación con cursor (recomendado - más eficiente):**

```bash
curl -X GET \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events?size=20&lastDocId=id-del-ultimo-documento' \
  -H 'Content-Type: application/json'
```

**Con todos los parámetros:**

```bash
curl -X GET \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events?size=20&page=1&lastDocId=id-del-ultimo-documento' \
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
**Endpoint**: `https://us-central1-system-track-monitor.cloudfunctions.net/event_detail`

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
  'https://us-central1-system-track-monitor.cloudfunctions.net/event_detail?eventId=TU_EVENT_ID' \
  -H 'Content-Type: application/json'
```

**Ejemplo con eventId específico:**

```bash
curl -X GET \
  'https://us-central1-system-track-monitor.cloudfunctions.net/event_detail?eventId=abc123' \
  -H 'Content-Type: application/json'
```

**Con verbose (para ver headers y respuesta completa):**

```bash
curl -v -X GET \
  'https://us-central1-system-track-monitor.cloudfunctions.net/event_detail?eventId=abc123' \
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

## 📦 Package: Tracking

Funciones relacionadas con el tracking y seguimiento de competidores durante eventos deportivos.

### 3. `track_event_checkpoint`

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

### 4. `track_competitors`

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

### 5. `track_competitors_off`

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

- `get_events` - Solo lectura de datos públicos
- `event_detail` - Solo lectura de datos públicos

### Funciones que Requieren Autenticación

Las siguientes funciones requieren autenticación ya que modifican datos:

- `track_event_checkpoint`
- `track_competitors`
- `track_competitors_off`

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
# Desplegar solo get_events
firebase deploy --only functions:get_events

# Desplegar solo event_detail
firebase deploy --only functions:event_detail

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

1. **Paginación**: Para `get_events`, se recomienda usar `lastDocId` en lugar de `page` para mejor rendimiento con grandes volúmenes de datos.

2. **Códigos HTTP**: Las funciones de eventos (`get_events`, `event_detail`) retornan códigos HTTP estándar. Las funciones de tracking retornan objetos JSON con `success` y `message`.

3. **Errores**: Las funciones de eventos retornan solo códigos HTTP en caso de error (400, 404, 500) sin cuerpo JSON, mientras que las funciones de tracking retornan objetos JSON con información del error.

4. **CORS**: Todas las funciones HTTP incluyen headers CORS para permitir llamadas desde aplicaciones web.

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
