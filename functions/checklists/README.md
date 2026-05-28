# Checklists — Event CRM API (v3)

API para listas de verificación de un evento. **No** es el módulo de _checkpoints_ de carrera (`events/.../checkpoints/`).

Contrato HTTP extendido también en el [README raíz](../../README.md) (sección _Package: Checklists_).

---

## En una frase

El organizador define **tareas** (ítems) en un checklist. Cada tarea puede ser opcional, obligatoria para **todos** los competidores del evento, o obligatoria solo para **unos pilotos**. El progreso (marcar cumplida) se guarda por piloto en Firestore.

---

## Analogía rápida

Imagina un formulario “Documentación del rally” con varias filas:

1. **Foto del auto** — opcional para todos.
2. **Licencia vigente** — obligatoria para todos los inscritos.
3. **Certificado médico** — obligatoria solo para Ana y Juan (lista en esa fila).

Todos los del evento pueden ver el formulario (según `visibilityMode` en móvil). Solo quien debe una fila la tiene en su seguimiento y debe marcarla.

---

## Dónde se guarda (Firestore)

```
events/{eventId}                 ← photoUrl (imagen del evento, vía update-photos)
  participants/{userId}          ← alta del piloto en el evento (nombre, número…)
  checklists/{checklistId}       ← title, description, photoUrl, visibilityMode
    items/{itemId}               ← plantilla: name, photoUrl, isRequired, participantIds[], …
    participants/{userId}        ← progreso de ESE piloto en ESTE checklist
```

- **`events/{eventId}.photoUrl`** = imagen del evento (una URL). Se actualiza con `PUT update-photos`, no con create/update del checklist.
- **`checklists/.../photoUrl`** = imagen de portada del checklist (create/update o lectura en get/list).
- **`items/`** = qué tareas existen, foto por fila (`photoUrl`) y a quién aplican.
- **`checklists/.../participants/`** = qué ha cumplido cada piloto (`itemProgress`).
- **`events/.../participants/`** = datos del competidor; el backend solo los lee para validar UIDs y copiar nombre/número.

### Flujo de fotos (CRM)

1. Subir archivos a Firebase Storage desde el cliente.
2. Llamar **`PUT update-photos`** con las URLs finales (galería del evento y/o fotos de ítems por `id`).
3. No usar **`PUT update`** solo para cambiar imágenes: usar **`PUT update-photos`**. **`PUT update`** es **patch-only** (no reemplaza ítems ni crea IDs nuevos).

---

## Tres tipos de ítem

| Tipo     | Cómo lo configuras en create/update             | Quién debe cumplirlo | En `itemProgress` |
| -------- | ----------------------------------------------- | -------------------- | ----------------- |
| Opcional | `isRequired: false`, `participantIds: []`       | Nadie (no afecta completitud) | Sí, todos |
| Global   | `isRequired: true`, `participantIds: []`        | Todos los del evento | Sí, todos         |
| Dirigido | `isRequired: false`, `participantIds: ["uid_a", …]` (lista no vacía) | Solo esos UIDs (**requerido por participante**) | Sí, solo ellos    |

Reglas de validación:

- No se permite `isRequired: true` **y** `participantIds` con valores a la vez → **400**.
- Cada UID en `participantIds` debe existir en `events/{eventId}/participants/{uid}` → **400** si no.
- El campo **`assignedParticipantIds` en el body del checklist ya no existe** → **400** si se envía.

Tras **create**, el backend crea o actualiza un doc en `checklists/.../participants/` por **cada** competidor del evento. Tras **update**, lo mismo **solo** si el patch incluye `visibilityMode` o cambia `isRequired` / `participantIds` en algún ítem.

---

## Quién usa qué

| Actor                         | Qué hace                                                                                                              |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| CRM web (usuario autenticado) | CRUD checklist, ver progreso (`participant-progress`)                                                                 |
| App móvil (piloto)            | Ver sus ítems y marcar cumplidos — PATCH `participant-update` **pendiente**                                           |
| `visibilityMode`              | `participants` o `eventDates`: **cuándo** el piloto puede ver el checklist en móvil, no sustituye las reglas de ítems |

---

## Auth

`Authorization: Bearer {Firebase ID token}` — cualquier usuario autenticado con token válido.

## Endpoints

| Método | Path                                          | Parámetros                                                  |
| ------ | --------------------------------------------- | ----------------------------------------------------------- |
| GET    | `/api/events/checklists/list`                 | query `eventId`                                             |
| GET    | `/api/events/checklists/get`                  | query `eventId`, `checklistId`                              |
| POST   | `/api/events/checklists/create`               | body JSON                                                   |
| PUT    | `/api/events/checklists/update`               | body JSON patch-only (`checklistId` o `id`; `items[]` / `participants[]` opcionales) |
| PUT    | `/api/events/checklists/update-photos`        | body JSON (portada checklist y/o fotos de ítems)            |
| DELETE | `/api/events/checklists/delete`               | query `eventId`, `checklistId`                              |
| GET    | `/api/events/checklists/participant-progress` | query `eventId`, `checklistId`, `limit`, `cursor`, `search` |

---

## Request / Response (v3)

Errores: cuerpo vacío (`400`, `401`, `404`, `500`). Éxito: JSON salvo `DELETE` → `204`; `GET list` → array directo de resúmenes (vacío = `[]`); `PUT update-photos` → `200` (detalle del checklist si hay `checklistId`, vacío si solo foto del evento).

### PUT `update-photos` — body

Actualización parcial de imágenes **sin** reemplazar el checklist completo (no borra ítems ni cambia IDs).

| Campo         | Tipo           | Requerido                                    | Notas                                                                                                                       |
| ------------- | -------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `eventId`     | string         | sí                                           |                                                                                                                             |
| `photoUrl`    | string \| null | no\*                                         | Con `checklistId`: portada en `checklists/{checklistId}.photoUrl`. Sin `checklistId`: imagen en `events/{eventId}.photoUrl` |
| `checklistId` | string         | sí si envías `items` o `photoUrl` de portada |                                                                                                                             |
| `items`       | array          | no\*                                         | `{ "id": string, "photoUrl": string \| null }` — foto de plantilla en `items/{id}`                                          |

\*Debe venir al menos uno: clave `photoUrl` en el body **o** `items` con al menos un elemento.

**Request — solo foto del evento:**

```json
{
  "eventId": "evt_123",
  "photoUrl": "https://storage.googleapis.com/.../event-cover.jpg"
}
```

**Request — solo fotos de ítems:**

```json
{
  "eventId": "evt_123",
  "checklistId": "chk_abc",
  "items": [
    {
      "id": "item_1",
      "photoUrl": "https://storage.googleapis.com/.../item-1.jpg"
    },
    { "id": "item_2", "photoUrl": null }
  ]
}
```

**Request — ambos en una llamada:**

```json
{
  "eventId": "evt_123",
  "photoUrl": "https://storage.googleapis.com/.../event-cover.jpg",
  "checklistId": "chk_abc",
  "items": [
    {
      "id": "item_1",
      "photoUrl": "https://storage.googleapis.com/.../item-1.jpg"
    }
  ]
}
```

**Response — `200 OK`:**

JSON del checklist (con `items`) si el body incluye `checklistId`. Cuerpo vacío si solo actualizas `events/{eventId}.photoUrl` sin `checklistId`.

Para leer URLs actualizadas después del 200:

- Foto del evento: `GET` detalle de evento (p. ej. `event_detail`) → campo `photoUrl` (si está en el documento).
- Checklist e ítems: `GET /api/events/checklists/get?eventId=&checklistId=`.

**Errores:** `400` (body inválido, `items` sin `id`/`photoUrl`, IDs duplicados, sin ningún cambio), `401`, `404` (evento, checklist o ítem inexistente), `500`.

### POST `create` — body

| Campo            | Tipo                               | Requerido                                   |
| ---------------- | ---------------------------------- | ------------------------------------------- |
| `eventId`        | string                             | sí                                          |
| `title`          | string                             | sí                                          |
| `description`    | string                             | no (default `""`)                           |
| `photoUrl`       | string \| null                     | no (imagen del checklist; `null` si no hay) |
| `visibilityMode` | `"participants"` \| `"eventDates"` | sí                                          |
| `items`          | array                              | sí (puede ser `[]`)                         |

> `description` y `photoUrl` en la **raíz** del body son del checklist completo. Los ítems tienen su propia `description` y `photoUrl` por fila.

**Cada elemento de `items[]` (create):**

| Campo                               | Tipo     | Notas                            |
| ----------------------------------- | -------- | -------------------------------- |
| `name`                              | string   | obligatorio                      |
| `description`                       | string   | default `""`                     |
| `photoUrl`, `latitude`, `longitude` | opcional |                                  |
| `isRequired`                        | boolean  | global si `participantIds` vacío |
| `participantIds`                    | string[] | dirigido; UIDs del evento        |
| `order`                             | number   | default índice                   |

En **create**, el servidor **ignora** `id` en ítems del body (genera IDs nuevos en Firestore).

### PUT `update` — patch-only (sin reemplazo)

> **Cambio incompatible (2026-05-27):** versiones anteriores trataban `PUT update` como **reemplazo completo** del checklist y de todos los ítems (borraba ítems no enviados y regeneraba IDs). El contrato actual es **solo parche**: envía únicamente los campos que quieres cambiar. No borra ítems omitidos, no crea ítems nuevos sin `id` existente en Firestore. Contrato canónico: [`ai-system/changes/checklists/design-patch-update-amendment.md`](../../ai-system/changes/checklists/design-patch-update-amendment.md).

| Campo            | Tipo                               | Requerido | Regla |
| ---------------- | ---------------------------------- | --------- | ----- |
| `eventId`        | string                             | sí        | no vacío |
| `checklistId` o `id` | string                         | sí        | no vacío |
| `title`          | string                             | no        | si la key está presente → valor no vacío tras trim |
| `description`    | string                             | no        | si presente → actualiza (permite `""`) |
| `photoUrl`       | string \| null                     | no        | si presente → normaliza URL; `null` limpia |
| `visibilityMode` | `"participants"` \| `"eventDates"` | no     | si presente → valor válido |
| `items`          | array                              | no        | patch por ítem existente; `id` recomendado |
| `participants`   | array                              | no        | patch por doc en `checklists/.../participants/`; **no toca progreso** |

Debe haber **al menos un campo actualizable** (raíz del checklist, al menos un ítem con cambios y/o al menos un participante con `id` + campo permitido). Solo `eventId` + `checklistId` → **400**. Si `participants[]` solo contiene entradas sin `id` o sin campos permitidos, **no cuenta** como cambio → **400** (salvo que haya otro campo actualizable).

**Cada elemento de `items[]` (update):** solo se aplican las keys **presentes** entre `name`, `description`, `photoUrl`, `latitude`, `longitude`, `isRequired`, `participantIds`, `order`. Prohibido reemplazar la subcolección.

- **Entry sin `id`**: se ignora (no-op; no 400/404).
- **`id` real** (no vacío y no `client-*`): **patch-only**. Si el doc no existe y el entry trae campos actualizables → **404**.
- **`id` con prefijo `client-*`**: **create con ID autogenerado**. Si el doc no existe en Firestore, el backend crea un item **nuevo** con ID autogenerado (ignora el `client-*`) con `createdAt/updatedAt = now` y defaults razonables para campos omitidos. **Para crear, `name` es obligatorio** (si falta o es vacío tras trim → **400**). Si (por alguna razón) ya existe un doc con ese `id`, se trata como patch normal.

**Cada elemento de `participants[]` (update):** patch parcial sobre un doc **existente** en `checklists/.../participants/`. **Entries sin `id` se ignoran** (no-op; no 400/404). Solo se aplican las keys **presentes** entre `participantName`, `pilotNumber`, `email`. **Prohibido** enviar campos de progreso: `itemProgress`, `isCompleted`, `lastUpdateDate`, `assignedAt` → **400**. No dispara sync de `participants/` (el sync sigue ligado a `visibilityMode` / `isRequired` / `participantIds` en ítems).

**400** además si: body inválido; `items` con `id` duplicado (incluye `client-*`); `participants` no es array; `participants` con `id` duplicado entre entradas con id; `participants[]` con campos de progreso prohibidos; `assignedParticipantIds` en body; `visibilityMode` inválido; `name` presente y vacío tras trim en un ítem; `isRequired: true` y `participantIds` no vacío en el mismo ítem; algún UID de `participantIds` no existe en `events/{eventId}/participants`.

**404** si el checklist no existe, si algún `items[].id` **real** enviado (no vacío, no `client-*`) con campos actualizables no existe, o si algún `participants[].id` **enviado** (con al menos un campo permitido) no existe.

**Sync de `checklists/.../participants/`** (`sync_all_event_participants`) si el patch incluye `visibilityMode` en la raíz **o** algún ítem (real o `client-*`) con `isRequired` y/o `participantIds`. **No** sync si el patch solo toca metadata del checklist (`title`, `description`, `photoUrl`), geodata/fotos/nombre/orden de ítems sin cambiar obligatoriedad ni audiencia, o datos CRM en `participants[]`.

**200:** JSON mínimo:

```json
{
  "eventId": "evt_123",
  "checklistId": "chk_abc",
  "items": [
    { "id": "item_1" },
    { "id": "item_2" }
  ]
}
```

**Ejemplo create:**

```json
{
  "eventId": "evt_123",
  "title": "Documentación",
  "description": "Requisitos generales antes del scrutineering",
  "photoUrl": "https://storage.googleapis.com/.../checklist-cover.jpg",
  "visibilityMode": "participants",
  "items": [
    {
      "name": "Foto vehículo",
      "description": "",
      "photoUrl": "https://storage.googleapis.com/.../item-vehicle.jpg",
      "isRequired": false,
      "participantIds": [],
      "order": 0
    },
    {
      "name": "Licencia",
      "isRequired": true,
      "participantIds": [],
      "order": 1
    },
    {
      "name": "Certificado médico",
      "isRequired": false,
      "participantIds": ["user_ana", "user_juan"],
      "order": 2
    }
  ]
}
```

### GET `get` — 200

Objeto en la raíz (sin `assignedParticipantIds`):

```json
{
  "id": "chk_abc",
  "eventId": "evt_123",
  "title": "Documentación",
  "description": "Requisitos generales antes del scrutineering",
  "photoUrl": "https://storage.googleapis.com/.../checklist-cover.jpg",
  "visibilityMode": "participants",
  "items": [
    {
      "id": "item_1",
      "name": "Licencia",
      "description": "",
      "photoUrl": null,
      "latitude": null,
      "longitude": null,
      "isRequired": true,
      "participantIds": [],
      "order": 1,
      "createdAt": "...",
      "updatedAt": "..."
    }
  ],
  "createdAt": "...",
  "updatedAt": "..."
}
```

### GET `list` — 200

Array JSON directo (vacío = `[]`). `photoUrl` opcional en cada resumen.

```json
[
  {
    "id": "chk_abc",
    "title": "Documentación",
    "description": "Requisitos generales antes del scrutineering",
    "photoUrl": "https://storage.googleapis.com/.../checklist-cover.jpg",
    "visibilityMode": "participants",
    "itemCount": 3,
    "assignedCount": 25,
    "createdAt": "...",
    "updatedAt": "..."
  }
]
```

`assignedCount` = cantidad de docs en `checklists/.../participants/` (competidores del evento sincronizados tras el último guardado).

### GET `participant-progress` — 200

Cada fila muestra los ítems que el piloto puede ver en su seguimiento:

- **Override por participante (`participantIds`)**: si un ítem trae `participantIds` (lista no vacía), su `isRequired` en la respuesta es el **efectivo para ese participante** (`true` solo si su `participantId` está en la lista).
- **Visibilidad vs obligatoriedad**: un ítem puede ser visible en el progreso aunque no sea requerido para ese participante; la visibilidad no implica que cuente para completitud.
- **Cálculo de `isCompleted`**: solo considera ítems con `isRequired: true` **para ese participante** (globales y dirigidos efectivos). Los no requeridos no afectan `isCompleted`.

`participantName` puede ser `string` o `null` (se denormaliza desde `users/{participantId}/personalData.fullName` con fallbacks y se refresca cuando corre el sync de `participants/`):

```json
{
  "result": [
    {
      "participantId": "user_ana",
      "participantName": "Ana Lopez",
      "pilotNumber": "7",
      "items": [
        {
          "itemId": "item_2",
          "name": "Licencia",
          "photoUrl": "https://storage.googleapis.com/.../license.jpg",
          "isRequired": true,
          "check": false,
          "updateDate": null
        },
        {
          "itemId": "item_3",
          "name": "Certificado médico",
          "photoUrl": null,
          "isRequired": true,
          "check": true,
          "updateDate": "..."
        }
      ],
      "isCompleted": false,
      "lastUpdateDate": null
    }
  ],
  "pagination": {
    "hasMore": false,
    "lastDocId": "user_ana",
    "count": 1,
    "limit": 20
  },
  "summary": {
    "assignedCount": 25,
    "completedCount": 10,
    "incompleteCount": 15
  }
}
```

---

## Migración desde v2

Checklists creados con `assignedParticipantIds` a nivel checklist deben **re-guardarse** desde el CRM con `participantIds` por ítem. Un patch que cambie `visibilityMode`, `isRequired` o `participantIds` dispara el sync para todos los competidores del evento.

### Migración cliente — PUT `update` ya no reemplaza

Integraciones que enviaban el checklist completo en cada guardado deben:

1. Enviar solo campos modificados (raíz y/o `items` con `id` existente).
2. Usar **`PUT update-photos`** para cambiar solo imágenes.
3. No esperar que omitir un ítem en `items[]` lo elimine (usar flujo de borrado de checklist/ítem si aplica en producto).

---

## Ejemplos curl

```bash
export BASE="https://system-track-monitor.web.app"
export TOKEN="..."

curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/list?eventId=EVENT_ID"

curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/get?eventId=EVENT_ID&checklistId=CHK_ID"

curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","title":"Technical","description":"","photoUrl":null,"visibilityMode":"participants","items":[{"name":"License","isRequired":true,"participantIds":[],"order":0}]}' \
  "$BASE/api/events/checklists/create"

# Update — patch solo título (ítems intactos; sin sync de participants/)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","checklistId":"CHK_ID","title":"Documentación actualizada"}' \
  "$BASE/api/events/checklists/update"

# Update — patch lat/long de un ítem existente (sin sync)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","checklistId":"CHK_ID","items":[{"id":"ITEM_ID","latitude":-12.0464,"longitude":-77.0428}]}' \
  "$BASE/api/events/checklists/update"

# Update — patch isRequired/participantIds (dispara sync de participants/)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","checklistId":"CHK_ID","items":[{"id":"ITEM_ID","isRequired":false,"participantIds":["user_ana","user_juan"]}]}' \
  "$BASE/api/events/checklists/update"

# Update — patch datos CRM de participants[] (sin tocar itemProgress; entry sin id se ignora)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","checklistId":"CHK_ID","participants":[{"id":"user_ana","participantName":"Ana López","pilotNumber":"7"},{"pilotNumber":"99"}]}' \
  "$BASE/api/events/checklists/update"

curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/events/checklists/participant-progress?eventId=EVENT_ID&checklistId=CHK_ID&limit=20"

curl -s -o /dev/null -w "%{http_code}" -X PUT \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventId":"EVENT_ID","photoUrl":"https://storage.googleapis.com/.../event.jpg","checklistId":"CHK_ID","items":[{"id":"ITEM_ID","photoUrl":"https://storage.googleapis.com/.../item.jpg"}]}' \
  "$BASE/api/events/checklists/update-photos"
```

---

## Código

| Archivo                                   | Rol                                                       |
| ----------------------------------------- | --------------------------------------------------------- |
| `checklist_route.py`                      | Router: auth + dispatch por path                          |
| `checklist_common.py`                     | Normalización, build de respuestas, persistencia de ítems |
| `checklist_participant_service.py`        | Sync `participants/` tras create/update                   |
| `create_checklist.py`                     | POST create                                               |
| `update_checklist.py`                     | PUT update (patch-only; ver amendment)                    |
| `update_checklist_photos.py`              | PUT update-photos (parcial)                               |
| `get_checklist.py` / `list_checklists.py` | Lecturas                                                  |
| `get_participant_progress.py`             | Progreso CRM                                              |
| `delete_checklist.py`                     | DELETE                                                    |

## Cliente web

- Enviar `participantIds` por ítem; no usar `assignedParticipantIds`.
- Tras upload a Storage, llamar **`update-photos`** con `photoUrl` del evento y `items[].id` + `photoUrl`.
- `path_patch_checklist_participant` en dart-define — backend PATCH móvil aún no expuesto.
