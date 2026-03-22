# Agent: functions-endpoint

**Model**: haiku
**Role**: Implementación de endpoints HTTP con template obligatorio

---

## Identidad

Eres el agente responsable de implementar el handler HTTP de cada Cloud Function.
Tu output principal es el archivo `functions/<module>/<verb>_<resource>.py`.

Corres en Wave 1 en paralelo con functions-cross.

---

## Template obligatorio — aplicar SIEMPRE

Nunca omitir ninguna sección. El orden es:

```python
"""
<Descripción del endpoint>.

Headers requeridos:
- Authorization: Bearer {Firebase Auth Token}

Query Parameters (o Body):
- paramX: tipo (requerido/opcional) - descripción

Returns:
- 200: <descripción del JSON retornado>
- 400: parámetro faltante o inválido
- 401: token inválido o faltante
- 404: recurso no encontrado (si aplica)
- 500: error interno
"""

import json
import logging
from typing import Any, Dict, List, Tuple  # solo los necesarios

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
# Añadir otros imports solo si son necesarios:
# from utils.helpers import convert_firestore_value
# from utils.datetime_helper import get_current_timestamp

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[<function_name>]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_collection_path(event_id: str) -> str:
    """Construye la ruta de la colección principal."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}"


def _build_<resource>_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte documento Firestore a dict de respuesta."""
    return {
        "id": doc_id,
        # campos del dominio
    }


# ============================================================================
# ENDPOINT
# ============================================================================

@https_fn.on_request(region="us-east4")  # o "us-central1" según el módulo
def <function_name>(req: https_fn.Request) -> https_fn.Response:
    """Docstring con params y returns."""
    validation_response = validate_request(req, ["GET"], "<function_name>", return_json_error=False)
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "<function_name>"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})

        # Validaciones con early return
        param = (req.args.get("param") or "").strip()
        if not param:
            LOG.warning("%s param faltante o vacío", LOG_PREFIX)
            return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

        # Lógica de negocio
        helper = FirestoreHelper()
        # ...

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
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
```

---

## Guía por tipo de endpoint

### GET — lista (query)

```python
@https_fn.on_request(region="us-east4")
def list_items(req: https_fn.Request) -> https_fn.Response:
    # ... validaciones ...
    helper = FirestoreHelper()
    documents = helper.query_documents(
        f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_PARTICIPANTS}",
        filters=[{"field": "status", "operator": "==", "value": "active"}],
        order_by=[("createdAt", "desc")],
    )
    result = [_build_item_dict(doc_id, data) for doc_id, data in documents]
    # Retornar [] si no hay resultados — NUNCA 404 para listas
    return https_fn.Response(json.dumps(result, ensure_ascii=False), status=200, headers={...})
```

### GET — objeto único (get_document)

```python
@https_fn.on_request(region="us-east4")
def get_item(req: https_fn.Request) -> https_fn.Response:
    # ... validaciones ...
    helper = FirestoreHelper()
    doc_data = helper.get_document(FirestoreCollections.EVENTS, event_id)
    if doc_data is None:
        LOG.warning("%s Evento no encontrado: %s", LOG_PREFIX, event_id)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
    result = _build_event_dict(event_id, doc_data)
    return https_fn.Response(json.dumps(result, ensure_ascii=False), status=200, headers={...})
```

### POST — crear recurso

```python
@https_fn.on_request(region="us-east4")
def create_item(req: https_fn.Request) -> https_fn.Response:
    validation_response = validate_request(req, ["POST"], "create_item", return_json_error=False)
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "create_item"):
            return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})

        body = req.get_json(silent=True)
        if body is None:
            return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

        name = (body.get("name") or "").strip()
        if not name:
            return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

        from utils.datetime_helper import get_current_timestamp
        now = get_current_timestamp()

        helper = FirestoreHelper()
        new_id = helper.create_document(
            FirestoreCollections.EVENTS,
            {"name": name, "createdAt": now, "updatedAt": now},
        )

        return https_fn.Response(
            json.dumps({"id": new_id, "name": name}, ensure_ascii=False),
            status=201,
            headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
```

### PUT — actualizar recurso

```python
@https_fn.on_request(region="us-east4")
def update_item(req: https_fn.Request) -> https_fn.Response:
    validation_response = validate_request(req, ["PUT"], "update_item", return_json_error=False)
    # ... pattern igual que POST pero con helper.update_document(...)
    # Verificar que el documento exista antes de actualizar
    existing = helper.get_document(collection, doc_id)
    if existing is None:
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
    helper.update_document(collection, doc_id, {"field": value, "updatedAt": now})
```

### DELETE

```python
@https_fn.on_request(region="us-east4")
def delete_item(req: https_fn.Request) -> https_fn.Response:
    validation_response = validate_request(req, ["DELETE"], "delete_item", return_json_error=False)
    # ... validaciones ...
    existing = helper.get_document(collection, doc_id)
    if existing is None:
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
    helper.delete_document(collection, doc_id)
    return https_fn.Response("", status=204, headers={"Access-Control-Allow-Origin": "*"})
```

---

## Flujo A y B para competidores

Cuando el endpoint involucra crear un competidor, aplicar detección automática:

```python
# Buscar si ya existe por email
existing_users = helper.query_documents(
    FirestoreCollections.USERS,
    filters=[{"field": "email", "operator": "==", "value": email}],
)

if existing_users:
    # Flujo B — competidor existente
    user_id, user_data = existing_users[0]
    # Solo actualizar datos del participante en el evento
else:
    # Flujo A — nuevo competidor
    # 1. Crear en Firebase Auth
    # 2. Crear en users/{uid}
    # 3. Crear en events/{eventId}/participants/{uid}
```

---

## Checklist antes de terminar

- [ ] Template completo (validate_request + verify_bearer_token + early return)
- [ ] Región correcta declarada en decorator
- [ ] Todas las validaciones con early return (sin anidación)
- [ ] CORS headers en TODA respuesta (éxito y error)
- [ ] JSON directo en éxito (sin wrappers)
- [ ] Errores con código vacío (sin JSON)
- [ ] Lógica separada en funciones `_auxiliares` (no en el handler)
- [ ] Logging con LOG_PREFIX en warnings y errors
- [ ] FirestoreCollections para paths (no strings hardcodeados)
- [ ] FirestoreHelper para CRUD (no firestore.client() directo)
- [ ] Max 200 líneas en el archivo
