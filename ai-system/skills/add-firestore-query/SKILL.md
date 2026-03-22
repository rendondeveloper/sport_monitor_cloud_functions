# Skill: /add-firestore-query

**Categoria**: Código
**Agente responsable**: functions-endpoint

---

## Cuando usar

Cuando se necesita una query Firestore que va más allá de un `get_document` simple:
- Filtros múltiples con `query_documents`
- Paginación con cursor
- Batch updates
- Consultas en subcolecciones anidadas

---

## Referencia completa de FirestoreHelper

### get_document — leer un documento por ID

```python
from utils.firestore_helper import FirestoreHelper
from models.firestore_collections import FirestoreCollections

helper = FirestoreHelper()

# Colección raíz
user_data = helper.get_document(FirestoreCollections.USERS, user_id)
# Retorna: Dict | None

# Subcolección (path completo como string)
participant_data = helper.get_document(
    f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
    user_id,
)

# Subcolección anidada
vehicle_data = helper.get_document(
    f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_VEHICLES}",
    vehicle_id,
)

# Verificar existencia
if user_data is None:
    return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
```

### query_documents — query con filtros

```python
# Filtro simple
documents = helper.query_documents(
    FirestoreCollections.USERS,
    filters=[{"field": "email", "operator": "==", "value": email}],
)
# Retorna: List[Tuple[str, Dict]]  →  [(doc_id, doc_data), ...]

# Múltiples filtros (AND implícito)
documents = helper.query_documents(
    f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
    filters=[
        {"field": "competitionCategory.registrationCategory", "operator": "==", "value": category},
        {"field": "team", "operator": "==", "value": team},
    ],
    order_by=[("registrationDate", "desc")],
    limit=100,
)

# Con paginación (cursor)
documents = helper.query_documents(
    collection_path,
    order_by=[("createdAt", "desc")],
    limit=20,
    start_after_doc_id=last_doc_id,  # ID del último documento de la página anterior
)

# Operador "in" — buscar por múltiples valores
documents = helper.query_documents(
    collection_path,
    filters=[{"field": "status", "operator": "in", "value": ["active", "pending"]}],
)

# array-contains — buscar en arrays
documents = helper.query_documents(
    collection_path,
    filters=[{"field": "categories", "operator": "array-contains", "value": "Pro"}],
)
```

### create_document — crear documento

```python
from utils.datetime_helper import get_current_timestamp

now = get_current_timestamp()

# Con ID autogenerado
new_id = helper.create_document(
    f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
    {
        "userId": user_id,
        "eventId": event_id,
        "status": "active",
        "competitionCategory": {
            "pilotNumber": pilot_number,
            "registrationCategory": category,
        },
        "createdAt": now,
        "updatedAt": now,
    },
)

# Con ID específico (ej: membership donde ID = eventId)
helper.create_document_with_id(
    f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MEMBERSHIP}",
    event_id,  # ID del documento = ID del evento
    {"eventId": event_id, "status": "active", "joinedAt": now},
)
```

### update_document — actualizar documento

```python
# Merge parcial — solo actualiza los campos especificados
helper.update_document(
    f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
    user_id,
    {
        "status": "finished",
        "finalTime": 3630.5,
        "updatedAt": get_current_timestamp(),
    },
)
```

### delete_document — eliminar documento

```python
# Verificar existencia antes de eliminar
existing = helper.get_document(collection_path, doc_id)
if existing is None:
    return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

helper.delete_document(collection_path, doc_id)
return https_fn.Response("", status=204, headers={"Access-Control-Allow-Origin": "*"})
```

### batch_update — actualizar múltiples documentos

```python
# Actualizar estado de múltiples competidores a la vez
updates = []
for doc_id in competitor_ids:
    updates.append((
        f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
        doc_id,
        {"status": new_status, "updatedAt": get_current_timestamp()},
    ))

helper.batch_update(updates)
```

### list_document_ids — listar IDs

```python
# Útil para saber cuántos documentos hay o para iterar subcolecciones
ids = helper.list_document_ids(
    f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_VEHICLES}"
)
has_vehicles = len(ids) > 0
```

---

## Patrones comunes en el proyecto

### Buscar usuario por email

```python
users = helper.query_documents(
    FirestoreCollections.USERS,
    filters=[{"field": "email", "operator": "==", "value": email.lower()}],
)
if users:
    user_id, user_data = users[0]
    # Flujo B — usuario existente
else:
    # Flujo A — usuario nuevo
```

### Obtener participantes de evento con filtros opcionales

```python
collection_path = (
    f"{FirestoreCollections.EVENTS}/{event_id}"
    f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
)

filters = []
if category:
    filters.append({
        "field": "competitionCategory.registrationCategory",
        "operator": "==",
        "value": category,
    })
if team:
    filters.append({"field": "team", "operator": "==", "value": team})

documents = helper.query_documents(
    collection_path,
    filters=filters if filters else None,
    order_by=[("registrationDate", "desc")],
)
```

### Obtener catálogo (documento fijo con subcolecciones)

```python
# Catálogos tienen estructura: catalogs/default/<subcollection>/{id}
vehicles_path = (
    f"{FirestoreCollections.CATALOGS}"
    f"/{FirestoreCollections.CATALOGS_DEFAULT_DOC_ID}"
    f"/{FirestoreCollections.CATALOGS_VEHICLES}"
)
documents = helper.query_documents(vehicles_path)
```

### Actualizar competidor en evento y en users (batch)

```python
now = get_current_timestamp()
helper.batch_update([
    (
        f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
        user_id,
        {"status": "finished", "updatedAt": now},
    ),
    (
        FirestoreCollections.USERS,
        user_id,
        {"lastEventId": event_id, "updatedAt": now},
    ),
])
```

---

## Reglas de queries

1. Nunca usar `firestore.client()` directamente en un endpoint
2. Usar `FirestoreCollections` para todos los nombres de colección en los paths
3. Los filtros opcionales se construyen en lista y se pasan solo si `filters` no está vacío
4. Para listas: retornar `[]` si no hay resultados — no retornar 404
5. Para objeto único: retornar 404 si `get_document()` retorna `None`
6. Siempre incluir `updatedAt: get_current_timestamp()` en updates
