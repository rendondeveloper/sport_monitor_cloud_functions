# Skill: /update-readme

**Categoria**: Proceso
**Agente responsable**: functions-docs
**Output**: `functions/<module>/README.md`

---

## Cuando usar

Siempre en Wave 3, después de crear o modificar un endpoint.
Es obligatorio — nunca omitir.

---

## Proceso

1. Revisar si `functions/<module>/README.md` ya existe
2. Si existe: añadir nueva sección y actualizar changelog (append-only)
3. Si no existe: crear desde el template completo

---

## Template completo para README nuevo

```markdown
# <Module> — Sport Monitor Cloud Functions

<Descripción de una o dos frases del propósito del módulo>

## Endpoints

| Función | Método | Descripción |
|---------|--------|-------------|
| `get_items` | GET | Lista todos los items de un evento |
| `get_item_by_id` | GET | Obtiene item por ID |
| `create_item` | POST | Crea nuevo item en un evento |

---

## GET `get_items`

<Descripción del endpoint>

**Región**: `us-east4`

**URL**:
- Emulador: `http://127.0.0.1:5001/<project-id>/us-east4/get_items`
- Producción: `https://us-east4-<project-id>.cloudfunctions.net/get_items`

**Headers**:

| Header | Tipo | Requerido | Descripción |
|--------|------|-----------|-------------|
| Authorization | string | Si | `Bearer {Firebase Auth Token}` |

**Query Parameters**:

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| eventId | string | Si | ID del evento |
| category | string | No | Filtrar por categoría (ej: "Pro", "Amateur") |

**Respuesta exitosa (200)**:

```json
[
  {
    "id": "item_doc_id",
    "eventId": "event123",
    "category": "Pro",
    "score": 10,
    "createdAt": "2026-03-21T10:00:00",
    "updatedAt": "2026-03-21T10:00:00"
  }
]
```

> Lista vacía retorna `[]` con status 200, no 404.

**Errores**:

| Código | Causa |
|--------|-------|
| 400 | `eventId` faltante o vacío |
| 401 | Token inválido o faltante |
| 500 | Error interno |

**Ejemplo cURL — éxito**:

```bash
curl -X GET \
  "https://us-east4-<project-id>.cloudfunctions.net/get_items?eventId=event123" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo cURL — con filtro**:

```bash
curl -X GET \
  "https://us-east4-<project-id>.cloudfunctions.net/get_items?eventId=event123&category=Pro" \
  -H "Authorization: Bearer <token>"
```

**Colecciones Firestore**:

| Constante | Path | Operación |
|-----------|------|-----------|
| `EVENTS / EVENT_PARTICIPANTS` | `events/{eventId}/participants` | Query |

---

## POST `create_item`

Crea un nuevo item en el evento. Requiere body JSON.

**Región**: `us-east4`

**URL**: `https://us-east4-<project-id>.cloudfunctions.net/create_item`

**Headers**:

| Header | Tipo | Requerido |
|--------|------|-----------|
| Authorization | string (Bearer) | Si |
| Content-Type | application/json | Si |

**Body**:

```json
{
  "eventId": "event123",
  "category": "Pro",
  "pilotNumber": "42"
}
```

**Campos del body**:

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| eventId | string | Si | ID del evento |
| category | string | Si | Categoría de competición |
| pilotNumber | string | No | Número de piloto (default: "") |

**Respuesta exitosa (201)**:

```json
{
  "id": "auto_generated_doc_id",
  "eventId": "event123",
  "category": "Pro",
  "pilotNumber": "42",
  "createdAt": "2026-03-21T10:00:00"
}
```

**Errores**:

| Código | Causa |
|--------|-------|
| 400 | Body vacío o campos requeridos faltantes |
| 401 | Token inválido o faltante |
| 500 | Error interno |

**Ejemplo cURL**:

```bash
curl -X POST \
  "https://us-east4-<project-id>.cloudfunctions.net/create_item" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": "event123",
    "category": "Pro",
    "pilotNumber": "42"
  }'
```

---

## Colecciones Firestore del módulo

| Constante | Colección | Descripción |
|-----------|-----------|-------------|
| `FirestoreCollections.EVENTS` | `events` | Colección principal |
| `FirestoreCollections.EVENT_PARTICIPANTS` | `participants` | Subcolección de participantes |
| `FirestoreCollections.USERS` | `users` | Usuarios del sistema |

---

## Deploy

```bash
# Función específica
firebase deploy --only functions:get_items

# Módulo completo
firebase deploy --only functions:get_items,create_item,get_item_by_id
```

---

## Changelog

### YYYY-MM-DD
- Añadido: `get_items` con filtros opcionales por category
- Añadido: `create_item` para registro de nuevos items
```

---

## Reglas de README

1. **Append-only en changelog** — nunca borrar entradas anteriores
2. **Tabla de endpoints actualizada** al inicio del README en cada cambio
3. **Response shape exacto** — copiar JSON real del endpoint, no inventar
4. **cURL funcionales** — con parámetros de ejemplo válidos
5. **Todos los errores documentados** — todos los códigos HTTP que puede retornar la función
6. **Lista vacía documentada** — si el endpoint retorna lista, aclarar que vacío = 200 `[]`
