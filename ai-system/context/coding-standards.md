# Coding Standards — Sport Monitor Cloud Functions

## Regla 1 — validate_request + verify_bearer_token en TODA función

Sin excepción. Primero CORS/método, luego token:

```python
validation_response = validate_request(req, ["GET"], "function_name", return_json_error=False)
if validation_response is not None:
    return validation_response

try:
    if not verify_bearer_token(req, "function_name"):
        return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})
```

`validate_request` maneja el OPTIONS preflight (204) y el método HTTP (405).
`verify_bearer_token` valida el token contra Firebase Auth y retorna bool.

---

## Regla 2 — JSON directo sin wrappers en respuestas exitosas

**Correcto:**
```python
# Lista
return https_fn.Response(json.dumps([{"id": "1", "name": "Alfa"}], ensure_ascii=False), status=200, headers={...})

# Objeto
return https_fn.Response(json.dumps({"id": "1", "name": "Alfa"}, ensure_ascii=False), status=200, headers={...})

# Lista vacía — retornar [], nunca 404 para listas
return https_fn.Response(json.dumps([], ensure_ascii=False), status=200, headers={...})
```

**Incorrecto — NUNCA:**
```python
return https_fn.Response(json.dumps({"success": True, "data": [...], "message": "ok"}), status=200)
```

---

## Regla 3 — Errores = código HTTP vacío, sin JSON

**Correcto:**
```python
return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})
return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})
return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
```

**Incorrecto — NUNCA:**
```python
return https_fn.Response(json.dumps({"error": "not found"}), status=404)
```

Única excepción documentada: errores de validación de formularios complejos donde el cliente
necesita saber el campo específico que falló (usar status 422 con JSON mínimo).

---

## Regla 4 — Early Return — nunca anidar if

**Correcto:**
```python
event_id = (req.args.get("eventId") or "").strip()
if not event_id:
    return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

user_id = (req.args.get("userId") or "").strip()
if not user_id:
    return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

# lógica principal aquí — sin anidación
```

**Incorrecto — NUNCA:**
```python
if event_id:
    if user_id:
        # lógica — demasiado anidado
    else:
        return error
else:
    return error
```

---

## Regla 5 — FirestoreCollections siempre para nombres de colecciones

**Correcto:**
```python
from models.firestore_collections import FirestoreCollections

collection_path = f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}"
```

**Incorrecto — NUNCA:**
```python
collection_path = f"events/{event_id}/participants"  # string hardcodeado
```

Si se necesita una colección nueva, agregarla primero en `models/firestore_collections.py`:
```python
class FirestoreCollections:
    # ... constantes existentes ...
    NUEVA_COLECCION = "nueva_coleccion"  # añadir aquí
```

---

## Regla 6 — FirestoreHelper para todo CRUD

**Correcto:**
```python
from utils.firestore_helper import FirestoreHelper

helper = FirestoreHelper()
doc = helper.get_document(FirestoreCollections.USERS, user_id)
docs = helper.query_documents(collection_path, filters=[...], order_by=[...])
new_id = helper.create_document(collection_path, data)
helper.update_document(collection_path, doc_id, {"field": "value"})
```

**Incorrecto — NUNCA:**
```python
from firebase_admin import firestore
db = firestore.client()
doc = db.collection("users").document(user_id).get()  # no hacer esto en endpoints
```

`firestore.client()` solo está permitido en `utils/firestore_helper.py`.

---

## Naming conventions

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Archivos | snake_case | `get_competitors_by_event.py` |
| Funciones | snake_case | `get_competitors_by_event` |
| Variables | snake_case | `event_id`, `user_data` |
| Constantes | UPPER_SNAKE | `FirestoreCollections.EVENTS` |
| Clases | PascalCase | `FirestoreHelper`, `FirestoreCollections` |
| Auxiliares privadas | `_` prefix | `_build_competitor_dict`, `_get_collection_path` |
| LOG prefix | `[function_name]` | `LOG_PREFIX = "[get_competitors_by_event]"` |
| Archivos de módulo | `<verbo>_<recurso>.py` | `create_competitor.py`, `list_competitors_by_event.py` |

---

## Estructura de archivos de módulo

```python
"""
Docstring del módulo — descripción, parámetros, retornos.
"""

import json
import logging
from typing import Any, Dict, List, Tuple  # solo los necesarios

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
# helpers adicionales según necesidad
from utils.helpers import convert_firestore_value
from utils.datetime_helper import get_current_timestamp

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[nombre_funcion]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_collection_path(event_id: str) -> str:
    """Una función auxiliar por responsabilidad."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}"


def _build_result_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte documento Firestore a dict de respuesta."""
    return {
        "id": doc_id,
        "eventId": data.get("eventId", ""),
    }


# ============================================================================
# ENDPOINT
# ============================================================================

@https_fn.on_request(region="us-east4")
def nombre_funcion(req: https_fn.Request) -> https_fn.Response:
    """Docstring obligatorio con params y returns."""
    # ... template obligatorio
```

---

## Límites y restricciones

- **Max 200 líneas** por archivo Python de endpoint
- Lógica compleja debe ir en funciones auxiliares `_privadas`
- Una Cloud Function por archivo (nunca dos `@https_fn.on_request` en el mismo archivo)
- Un archivo de tests por Cloud Function

---

## Logging

```python
LOG = logging.getLogger(__name__)
LOG_PREFIX = "[nombre_funcion]"

# Warnings — validaciones fallidas, tokens inválidos
LOG.warning("%s param1 faltante o vacío", LOG_PREFIX)
LOG.warning("%s Token inválido o faltante", LOG_PREFIX)

# Errors — excepciones con traceback
LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
LOG.error("%s Error de validación: %s", LOG_PREFIX, e)
```

No usar `print()`. No usar f-strings en logging (usar `%s` para lazy evaluation).

---

## CORS headers — obligatorios en TODAS las respuestas

Errores (mínimo):
```python
headers={"Access-Control-Allow-Origin": "*"}
```

Éxito (completo):
```python
headers={
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}
```

---

## Helpers disponibles — reutilizar, NUNCA duplicar

| Helper | Función | Uso |
|--------|---------|-----|
| `datetime_helper.get_current_timestamp()` | Timestamp UTC actual | `createdAt`, `updatedAt` |
| `helpers.convert_firestore_value(value)` | Convierte Firestore Timestamp a string ISO | Campos de fecha en respuesta |
| `helpers.format_utc_to_local_datetime(dt, tz)` | Formatea fecha a timezone local | — |
| `validation_helper.validate_email(email)` | Valida formato de email | bool |
| `validation_helper.validate_phone(phone)` | Valida formato de teléfono | bool |
| `validation_helper.validate_required_fields(data, fields)` | Valida campos requeridos en dict | lista de campos faltantes |
| `validation_helper.validate_password(password)` | Valida requisitos de contraseña | bool |
| `auth_helper.create_firebase_auth_user(email, password, name)` | Crea usuario en Firebase Auth | uid |
| `auth_helper.delete_firebase_auth_user(uid)` | Elimina usuario de Firebase Auth | bool |

---

## Manejo de body en POST/PUT

```python
body = req.get_json(silent=True)
if body is None:
    LOG.warning("%s Body inválido o faltante", LOG_PREFIX)
    return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

# Extraer campos con .get() — nunca acceso directo con []
email = (body.get("email") or "").strip()
if not email:
    return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})
```

---

## Manejo de parámetros query

```python
# Siempre con fallback a string vacío — nunca None directo
event_id = (req.args.get("eventId") or "").strip()
if not event_id:
    return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

# Parámetros opcionales — no retornar 400 si no están
category = (req.args.get("category") or "").strip()  # puede ser ""
```
