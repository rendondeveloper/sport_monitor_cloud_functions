# Sport Monitor Cloud Functions — Firebase (Python)

@../ai-system/context/architecture.md
@../ai-system/context/coding-standards.md
@../ai-system/context/readability.md
@../ai-system/context/project-structure.md
@../ai-system/context/workflow.md
@../ai-system/rules/readability-rule.md

## Regla global de legibilidad

Priorizar legibilidad humana sobre soluciones complejas. Si dos soluciones son correctas, elegir la mas simple y explicita.

## Propósito
Backend REST API basado en Firebase Cloud Functions (2nd Gen). Gestión de eventos, usuarios, competidores, staff, checkpoints, tracking, vehículos y catálogos.

## Stack
- Python 3.12, Firebase Admin SDK, Cloud Functions framework
- Región: `us-east4`
- Runtime: hasta 10 instancias simultáneas

## Estructura

```
functions/
├── main.py                    # Entry point — importa y registra todas las funciones
├── events/                    # Consultas de eventos
├── users/                     # Gestión de usuarios
├── competitors/               # Registro y gestión de competidores
├── staff/                     # Creación de staff
├── checkpoints/               # Tracking de checkpoints
├── tracking/                  # Tracking en tiempo real
├── vehicles/                  # Gestión de vehículos
├── catalogs/                  # Datos estáticos (catálogos)
├── models/                    # Modelos Firestore + constantes de colecciones
│   └── firestore_collections.py  # FirestoreCollections — SIEMPRE usar estas constantes
├── utils/                     # Helpers compartidos
│   ├── firestore_helper.py    # FirestoreHelper — CRUD de Firestore
│   ├── helper_http.py         # verify_bearer_token()
│   ├── helper_http_verb.py    # validate_request()
│   ├── auth_helper.py         # Firebase Auth utilities
│   ├── validation_helper.py   # Validaciones de body/params
│   └── datetime_helper.py     # Timestamps y fechas
└── tests/                     # pytest
```

## Reglas obligatorias

### 1. Toda función usa validate_request + verify_bearer_token
```python
validation_response = validate_request(req, ["GET"], "fn_name", return_json_error=False)
if validation_response is not None:
    return validation_response

if not verify_bearer_token(req, "fn_name"):
    return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})
```

### 2. Respuestas exitosas: JSON directo (sin wrappers)
```python
# CORRECTO
return https_fn.Response(
    json.dumps(result, ensure_ascii=False),
    status=200,
    headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
)

# INCORRECTO — nunca usar success/message/data como wrapper
json.dumps({"success": True, "data": result})
```

### 3. Errores: solo código HTTP, sin cuerpo JSON
```python
# CORRECTO
return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

# INCORRECTO
return https_fn.Response(json.dumps({"error": "mensaje"}), status=400)
```

**Excepción**: Errores con contexto específico (ej. competidor duplicado, ID no encontrado) SÍ retornan JSON:
```python
return https_fn.Response(
    json.dumps({"error": "competidor ya inscrito"}, ensure_ascii=False),
    status=409,
    headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
)
```

### 4. Early Return siempre — nunca anidar validaciones

### 5. Usar siempre FirestoreCollections para nombres de colecciones
```python
from models.firestore_collections import FirestoreCollections
path = f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}"
```

### 6. Usar FirestoreHelper para CRUD — no llamar firestore.client() directamente

## Colecciones Firestore relevantes
```python
EVENTS = "events"
USERS = "users"
EVENT_PARTICIPANTS = "participants"       # subcol bajo events
DAY_OF_RACES = "day_of_races"
EVENT_CATEGORIES = "event_categories"
USER_VEHICLES = "vehicles"
USER_EMERGENCY_CONTACT = "emergencyContacts"   # plural, bajo users
PARTICIPANT_EMERGENCY_CONTACTS = "emergencyContact"  # singular, bajo participants
PARTICIPANT_VEHICLE = "vehicle"
USER_MEMBERSHIP = "membership"
```

## Flujo competidores (create_competitor_user.py)

### Flujo A — Usuario nuevo
1. Crear Firebase Auth user
2. Crear `users/{id}` + subcols: `personalData`, `healthData`, `emergencyContacts`, `vehicles`
3. Crear contactos y vehículo en evento: `events/{eventId}/participants/{id}/emergencyContact`, `vehicle`
4. Crear `users/{id}/membership/{eventId}`
5. Crear `events/{eventId}/participants/{id}`
6. Rollback completo si falla cualquier paso

### Flujo B — Usuario existente, nuevo evento
1. Buscar userId por email en `users`
2. Verificar que NO sea ya participante (→ 409)
3. Verificar número de piloto no duplicado (→ 409)
4. Merge de `personalData` y `healthData` (solo campos vacíos)
5. Procesar contactos y vehículo (mismo `_process_*` que Flujo A)
6. Crear membership y participante
7. Sin rollback en Flujo B

### Payload mixto de contactos de emergencia
```json
[
  { "fullName": "Nuevo", "phone": "123", "relationship": "Familiar" },
  { "id": "existingContactId" }
]
```
- Item con datos completos → crear en `users/emergencyContacts` → `{"id": autoId}` en evento
- Item con solo `{id}` → validar que exista en `users/emergencyContacts` → `{"id": id}` en evento → 400 si no existe

## Template base de función
```python
@https_fn.on_request(region="us-east4")
def function_name(req: https_fn.Request) -> https_fn.Response:
    """Descripción. Params: ... Returns: 200/400/401/404/500"""
    validation_response = validate_request(req, ["GET"], "function_name", return_json_error=False)
    if validation_response is not None:
        return validation_response
    try:
        if not verify_bearer_token(req, "function_name"):
            return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})
        # ... lógica ...
        return https_fn.Response(json.dumps(result, ensure_ascii=False), status=200,
            headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error("function_name: %s", e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
```
