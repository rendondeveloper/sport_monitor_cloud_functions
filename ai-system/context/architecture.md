# Architecture — Sport Monitor Cloud Functions

## Stack

- **Runtime**: Python 3.12, Firebase Admin SDK, Cloud Functions 2nd Gen
- **Database**: Firestore (principal) + Realtime Database (tracking en tiempo real)
- **Auth**: Firebase Authentication — Bearer token verificado con `firebase_admin.auth.verify_id_token`
- **Testing**: pytest con unittest.mock
- **Deploy**: `firebase deploy --only functions:{name}`

---

## Regiones

| Region | Módulos |
|--------|---------|
| `us-east4` | competitors, catalogs, tracking, vehicles, checkpoints |
| `us-central1` | general, monitor, staff, events, users |

Declarar siempre en el decorator:
```python
@https_fn.on_request(region="us-east4")
def mi_funcion(req: https_fn.Request) -> https_fn.Response:
```

---

## Template OBLIGATORIO de Cloud Function

Toda Cloud Function debe seguir este template sin excepción:

```python
import json
import logging

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[function_name]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _build_result(doc_id: str, data: dict) -> dict:
    """Convierte documento Firestore a dict de respuesta."""
    return {
        "id": doc_id,
        "field1": data.get("field1", ""),
        "field2": data.get("field2", 0),
    }


# ============================================================================
# ENDPOINT
# ============================================================================

@https_fn.on_request(region="us-east4")
def function_name(req: https_fn.Request) -> https_fn.Response:
    """
    Descripcion del endpoint.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query Parameters:
    - param1: string (requerido)
    - param2: string (opcional)

    Returns:
    - 200: Array/Object JSON directo
    - 400: Bad Request — parámetro faltante o inválido
    - 401: Unauthorized — token inválido o faltante
    - 404: Not Found — recurso no existe
    - 500: Internal Server Error
    """
    # 1. CORS preflight + método HTTP
    validation_response = validate_request(
        req, ["GET"], "function_name", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # 2. Autenticación
        if not verify_bearer_token(req, "function_name"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "", status=401, headers={"Access-Control-Allow-Origin": "*"}
            )

        # 3. Validar parámetros (Early Return)
        param1 = (req.args.get("param1") or "").strip()
        if not param1:
            LOG.warning("%s param1 faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "", status=400, headers={"Access-Control-Allow-Origin": "*"}
            )

        # 4. Lógica de negocio
        helper = FirestoreHelper()
        documents = helper.query_documents(
            FirestoreCollections.EVENTS,
            filters=[{"field": "eventId", "operator": "==", "value": param1}],
            order_by=[("createdAt", "desc")],
        )

        result = [_build_result(doc_id, data) for doc_id, data in documents]

        # 5. Respuesta — JSON directo, sin wrapper
        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        LOG.error("%s Error de validación: %s", LOG_PREFIX, e)
        return https_fn.Response(
            "", status=400, headers={"Access-Control-Allow-Origin": "*"}
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "", status=500, headers={"Access-Control-Allow-Origin": "*"}
        )
```

---

## Reglas de respuestas HTTP

### Éxito — JSON directo, sin wrappers

```python
# Lista (puede ser vacía)
return https_fn.Response(
    json.dumps(lista, ensure_ascii=False),
    status=200,
    headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
)

# Objeto único
return https_fn.Response(
    json.dumps({"id": "123", "name": "ejemplo"}, ensure_ascii=False),
    status=200,
    headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
)

# Lista vacía — retornar [], no 404
return https_fn.Response(
    json.dumps([], ensure_ascii=False),
    status=200,
    headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
)
```

### Errores — código HTTP vacío (sin JSON)

```python
# 400 Bad Request
return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

# 401 Unauthorized
return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})

# 404 Not Found
return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

# 500 Internal Server Error
return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
```

### Excepción — error con contexto (único caso donde error puede tener JSON)

Solo cuando el cliente necesita saber el campo específico que falló (formularios complejos):
```python
return https_fn.Response(
    json.dumps({"field": "email", "error": "formato_invalido"}, ensure_ascii=False),
    status=422,
    headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
)
```

---

## Flujo de datos

```
HTTP Request
    ↓
validate_request()          # CORS preflight + método HTTP
    ↓
verify_bearer_token()       # Firebase Auth token
    ↓
Validar parámetros          # Early return en cada validación
    ↓
FirestoreHelper()           # CRUD — nunca firestore.client() directo
    ↓
_build_result()             # Auxiliar de transformación
    ↓
json.dumps(result)          # JSON directo, ensure_ascii=False
    ↓
https_fn.Response()         # Con CORS headers
```

---

## Flujo de competidores

### Flujo A — Competidor nuevo (no existe en el sistema)

1. Crear usuario en Firebase Authentication
2. Crear documento en `users/{uid}`
3. Crear documento en `events/{eventId}/participants/{uid}`
4. Crear subcolecciones del participante: `vehicle/`, `emergencyContacts/`

### Flujo B — Competidor existente (ya tiene cuenta)

1. Buscar usuario en Firestore por email (`users` collection)
2. Actualizar datos del participante en `events/{eventId}/participants/{uid}`
3. Opcionalmente actualizar datos en `users/{uid}`

### Payload mixto

La función `create_competitor_user` detecta si el competidor ya existe por email y
ejecuta el flujo correspondiente (A o B) automáticamente.

---

## Colecciones Firestore y sus relaciones

```
events/{eventId}
    ├── checkpoints/{checkpointId}
    ├── day_of_races/{dayId}
    ├── event_categories/{categoryId}
    ├── participants/{userId}           # competidores registrados
    │   ├── vehicle/{vehicleId}
    │   └── emergencyContacts/{contactId}
    ├── staff_users/{staffId}
    ├── routes/{routeId}
    └── event_content/{contentId}

users/{userId}
    ├── vehicles/{vehicleId}
    ├── membership/{eventId}
    ├── emergencyContacts/{contactId}
    ├── healthData/{docId}
    └── personalData/{docId}

events_tracking/{trackingId}
    ├── competitor_tracking/{competitorId}
    ├── competitors/{competitorId}
    └── checkpoints/{checkpointId}

catalogs/default
    ├── vehicles/{vehicleId}
    ├── years/{yearId}
    ├── colors/{colorId}
    └── relationship_types/{typeId}
```

---

## CORS headers obligatorios

Toda respuesta — éxito o error — debe incluir al menos:
```python
headers={"Access-Control-Allow-Origin": "*"}
```

Respuestas exitosas deben incluir también:
```python
headers={
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",      # o POST/PUT/DELETE según el endpoint
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}
```

CORS preflight (OPTIONS) es manejado automáticamente por `validate_request()` con status 204.
