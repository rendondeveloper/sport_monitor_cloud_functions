# Comandos cURL para Probar Funciones en Postman

## Información del Proyecto

- **Project ID**: `system-track-monitor`
- **Región**: `us-central1`

## ⚠️ SOLUCIÓN RÁPIDA: Error "Unauthenticated"

Si recibes el error `{"error": {"message": "Unauthenticated", "status": "UNAUTHENTICATED"}}`, tienes dos opciones:

### Opción 1: Hacer get_events Pública (Recomendado) ✅

Para `get_events` que solo devuelve datos públicos, hazla pública usando gcloud:

```bash
gcloud functions add-iam-policy-binding get_events \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/cloudfunctions.invoker" \
  --project=system-track-monitor
```

**O desde Firebase Console:**

1. Ve a [Firebase Console](https://console.firebase.google.com/) → Tu proyecto → **Functions**
2. Busca `get_events` y haz clic en los **tres puntos** (⋮)
3. Selecciona **"Edit"** o **"Configurar"**
4. Ve a **"Permissions"** → **"Invoker"**
5. Selecciona **"allUsers"** y guarda

Después de esto, puedes llamar a `get_events` **SIN** el header `Authorization`.

### Opción 2: Usar Autenticación Anónima

**1. Obtener tu API Key:**

- Firebase Console → Project Settings → General → **Web API Key**

**2. Obtener token anónimo:**

```bash
curl -X POST \
  'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=TU_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"returnSecureToken": true}'
```

**3. Usa el `idToken` de la respuesta en Postman como:**

```
Authorization: Bearer {idToken}
```

**O desde la consola del navegador:**

```javascript
const apiKey = "TU_API_KEY";
fetch(
  `https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${apiKey}`,
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ returnSecureToken: true }),
  }
)
  .then((r) => r.json())
  .then((d) => console.log("Token:", d.idToken));
```

**Nota**: Primero debes habilitar "Anonymous" en Firebase Console → Authentication → Sign-in method.

---

## Nota Importante

Las funciones callable de Firebase requieren autenticación por defecto. Para `get_events` (datos públicos), recomiendo hacerla pública. Para las otras funciones que modifican datos, mantén la autenticación requerida.

---

## 1. get_events

Obtiene eventos de Firestore con soporte de paginación. Retorna todos los eventos usando el modelo EventDocument.

### Parámetros Opcionales

- `limit`: Número de eventos por página (default: 50, máximo: 100)
- `page`: Número de página (default: 1)
- `lastDocId`: ID del último documento de la página anterior (para cursor-based pagination, más eficiente)

### cURL (Si la función es pública - SIN autenticación) ✅

**Primera página (sin parámetros):**
```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events' \
  -H 'Content-Type: application/json' \
  -d '{
    "data": {}
  }'
```

**Con paginación (limit y page):**
```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events' \
  -H 'Content-Type: application/json' \
  -d '{
    "data": {
      "limit": 20,
      "page": 1
    }
  }'
```

**Paginación con cursor (más eficiente):**
```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events' \
  -H 'Content-Type: application/json' \
  -d '{
    "data": {
      "limit": 20,
      "lastDocId": "id-del-ultimo-documento"
    }
  }'
```

### cURL (Si requiere autenticación)

```bash
curl -X POST \
  'https://us-central1-system-track-monitor.cloudfunctions.net/get_events' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_ID_TOKEN' \
  -d '{
    "data": {
      "limit": 20,
      "page": 1
    }
  }'
```

### Postman Configuración

- **Method**: `POST`
- **URL**: `https://us-central1-system-track-monitor.cloudfunctions.net/get_events`
- **Headers**:
  - `Content-Type`: `application/json`
  - `Authorization`: `Bearer YOUR_ID_TOKEN` ⚠️ Solo si la función NO es pública
- **Body** (raw JSON):

**Sin paginación:**
```json
{
  "data": {}
}
```

**Con paginación:**
```json
{
  "data": {
    "limit": 20,
    "page": 1
  }
}
```

**Con cursor (recomendado):**
```json
{
  "data": {
    "limit": 20,
    "lastDocId": "id-del-ultimo-documento-de-la-pagina-anterior"
  }
}
```

### Respuesta Esperada

```json
{
  "events": [
    {
      "id": "event-id-1",
      "name": "Evento 1",
      "description": "Descripción del evento",
      "status": "published",
      "subtitle": "Subtítulo",
      "rallySystemId": "rally-id",
      "staffMembers": [],
      "createdBy": "user-id",
      "location": "Ubicación",
      "date": "2025-01-01",
      "participants": [],
      "createdAt": "2025-01-01T00:00:00",
      "updatedAt": "2025-01-01T00:00:00"
    },
    {
      "id": "event-id-2",
      ...
    }
  ],
  "pagination": {
    "limit": 20,
    "page": 1,
    "hasMore": true,
    "count": 20,
    "lastDocId": "event-id-20"
  }
}
```

### Ejemplo de Uso con Paginación

**Página 1:**
```json
{
  "data": {
    "limit": 20,
    "page": 1
  }
}
```

**Página 2 (usando cursor - más eficiente):**
```json
{
  "data": {
    "limit": 20,
    "lastDocId": "event-id-del-ultimo-de-pagina-1"
  }
}
```

---

## 2. track_event_checkpoint

Crea la colección `tracking_checkpoint` para un evento cuando el status es `inProgress`.

### cURL

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

### Postman Configuración

- **Method**: `POST`
- **URL**: `https://us-central1-system-track-monitor.cloudfunctions.net/track_event_checkpoint`
- **Headers**:
  - `Content-Type`: `application/json`
  - `Authorization`: `Bearer YOUR_ID_TOKEN`
- **Body** (raw JSON):

```json
{
  "data": {
    "eventId": "tu-event-id-aqui",
    "status": "inProgress",
    "day": "day1"
  }
}
```

### Respuesta Esperada

```json
{
  "success": true,
  "message": "Colección 'tracking_checkpoint' creada para el evento 'Nombre del Evento' (event-id)",
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

## 3. track_competitors

Crea la estructura de tracking de competidores para un evento y día específico.

### cURL

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

### Postman Configuración

- **Method**: `POST`
- **URL**: `https://us-central1-system-track-monitor.cloudfunctions.net/track_competitors`
- **Headers**:
  - `Content-Type`: `application/json`
  - `Authorization`: `Bearer YOUR_ID_TOKEN`
- **Body** (raw JSON):

```json
{
  "data": {
    "eventId": "tu-event-id-aqui",
    "dayId": "tu-day-id-aqui",
    "status": "inProgress",
    "dayName": "Día 1"
  }
}
```

### Respuesta Esperada

```json
{
  "success": true,
  "message": "Tracking de competidores creado para el evento 'Nombre del Evento' día day-id",
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

## 4. track_competitors_off

Desactiva el tracking de competidores para un evento y día específico.

### cURL

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

### Postman Configuración

- **Method**: `POST`
- **URL**: `https://us-central1-system-track-monitor.cloudfunctions.net/track_competitors_off`
- **Headers**:
  - `Content-Type`: `application/json`
  - `Authorization`: `Bearer YOUR_ID_TOKEN`
- **Body** (raw JSON):

```json
{
  "data": {
    "eventId": "tu-event-id-aqui",
    "dayId": "tu-day-id-aqui"
  }
}
```

### Respuesta Esperada

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

## Cómo Obtener el Token de Autenticación

### Opción 1: Desde tu App Cliente (Flutter/Web)

Si tienes una app cliente, puedes obtener el token así:

**Flutter:**

```dart
String? token = await FirebaseAuth.instance.currentUser?.getIdToken();
```

**JavaScript/Web:**

```javascript
const token = await firebase.auth().currentUser.getIdToken();
```

### Opción 2: Usar Firebase Admin SDK (para pruebas)

Puedes crear un script temporal para generar un token de prueba.

### Opción 3: Probar sin Autenticación (Solo para Desarrollo)

Si necesitas probar sin autenticación, puedes configurar la función para permitir acceso no autenticado desde la consola de Firebase:

1. Ve a Firebase Console → Functions
2. Selecciona la función
3. En "Permissions", configura para permitir acceso no autenticado

**Nota**: Esto solo es recomendable para funciones públicas como `get_events`.

---

## Importar a Postman

1. Abre Postman
2. Crea una nueva Collection llamada "Sport Monitor Functions"
3. Crea una nueva Request para cada función
4. Copia la configuración de cada función desde arriba
5. Reemplaza `YOUR_ID_TOKEN` con tu token real
6. Reemplaza los valores de ejemplo (`tu-event-id-aqui`, etc.) con datos reales

---

## Variables de Entorno en Postman

Para facilitar el uso, puedes crear variables de entorno en Postman:

- `base_url`: `https://us-central1-system-track-monitor.cloudfunctions.net`
- `auth_token`: `YOUR_ID_TOKEN`
- `event_id`: `tu-event-id-aqui`
- `day_id`: `tu-day-id-aqui`

Luego usa las variables así:

- URL: `{{base_url}}/get_events`
- Header Authorization: `Bearer {{auth_token}}`
- Body: `{ "data": { "eventId": "{{event_id}}" } }`

---

## Errores Comunes

### Error 401: Unauthorized

- Verifica que el token de autenticación sea válido
- Asegúrate de que el usuario esté autenticado en Firebase

### Error 403: Forbidden

- Verifica los permisos de IAM en Firebase Console
- Asegúrate de que la función tenga los permisos correctos

### Error 400: Bad Request

- Verifica que el formato del JSON sea correcto
- Asegúrate de incluir todos los parámetros requeridos en `data`

### Error 404: Not Found

- Verifica que la URL sea correcta
- Asegúrate de que la función esté desplegada correctamente
