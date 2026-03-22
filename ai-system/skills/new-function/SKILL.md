# Skill: /new-function

**Categoria**: Código
**Agente responsable**: functions-endpoint (+ functions-cross para registro)

---

## Cuando usar

Cuando se necesita crear un endpoint HTTP nuevo en cualquier módulo.

---

## Proceso paso a paso

### Paso 1 — Determinar parámetros

Antes de escribir código, confirmar:
- Nombre de la función (snake_case, verbo + recurso): `get_competitor_stats`
- Módulo: `competitors/`
- Método HTTP: `GET` / `POST` / `PUT` / `DELETE`
- Región: `us-east4` o `us-central1`
- Parámetros: tipo (query/body), nombre, requerido/opcional
- Colecciones Firestore afectadas
- Shape de la respuesta exitosa

### Paso 2 — Crear archivo

`functions/<module>/<verb>_<resource>.py`

Aplicar template obligatorio completo:

```python
"""
<Función> — <Descripción de una línea>

<Descripción extendida si es necesaria>

Headers:
- Authorization: Bearer {Firebase Auth Token} (requerido)

Query Parameters:  [o Body si es POST/PUT]
- eventId: string (requerido) — ID del evento
- category: string (opcional) — Filtrar por categoría

Returns:
- 200: Array JSON de <recurso> (vacío si no hay resultados)
- 400: Bad Request — parámetro requerido faltante
- 401: Unauthorized — token inválido o faltante
- 404: Not Found — (solo para GET objeto único)
- 500: Internal Server Error
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[<function_name>]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _get_collection_path(event_id: str) -> str:
    """Construye la ruta de la subcoleccion de participantes."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


def _build_<resource>_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte documento Firestore a dict de respuesta API."""
    return {
        "id": doc_id,
        "eventId": data.get("eventId", ""),
        # ... resto de campos
        "createdAt": convert_firestore_value(data.get("createdAt")),
        "updatedAt": convert_firestore_value(data.get("updatedAt")),
    }


# ============================================================================
# ENDPOINT
# ============================================================================


@https_fn.on_request(region="us-east4")
def <function_name>(req: https_fn.Request) -> https_fn.Response:
    """
    <Descripción corta>. Method: GET.
    Params: eventId (requerido). Returns: 200 list | 400 | 401 | 500.
    """
    validation_response = validate_request(
        req, ["GET"], "<function_name>", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "<function_name>"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "", status=401, headers={"Access-Control-Allow-Origin": "*"}
            )

        # Validar parámetros requeridos
        event_id = (req.args.get("eventId") or "").strip()
        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "", status=400, headers={"Access-Control-Allow-Origin": "*"}
            )

        # Parámetros opcionales
        category = (req.args.get("category") or "").strip()

        # Lógica de negocio
        helper = FirestoreHelper()
        collection_path = _get_collection_path(event_id)

        filters = []
        if category:
            filters.append({
                "field": "competitionCategory.registrationCategory",
                "operator": "==",
                "value": category,
            })

        documents = helper.query_documents(
            collection_path,
            filters=filters if filters else None,
            order_by=[("createdAt", "desc")],
        )

        result = [_build_<resource>_dict(doc_id, data) for doc_id, data in documents]

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

### Paso 3 — Registrar en main.py (functions-cross)

```python
# functions/main.py
from <module> import (
    # ... funciones existentes ...
    <function_name>,  # NUEVO
)
```

### Paso 4 — Verificar con emulador

```bash
firebase emulators:start --only functions
curl -X GET \
  "http://127.0.0.1:5001/<project-id>/us-east4/<function_name>?eventId=test123" \
  -H "Authorization: Bearer <token>"
```

---

## Variantes de template

### POST — crear recurso

```python
@https_fn.on_request(region="us-east4")
def create_<resource>(req: https_fn.Request) -> https_fn.Response:
    """Method: POST. Body: {field1, field2}. Returns: 201 object | 400 | 401 | 500."""
    validation_response = validate_request(req, ["POST"], "create_<resource>", return_json_error=False)
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "create_<resource>"):
            return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})

        body = req.get_json(silent=True)
        if body is None:
            return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

        field1 = (body.get("field1") or "").strip()
        if not field1:
            return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

        from utils.datetime_helper import get_current_timestamp
        now = get_current_timestamp()

        helper = FirestoreHelper()
        new_id = helper.create_document(
            FirestoreCollections.<COLLECTION>,
            {"field1": field1, "createdAt": now, "updatedAt": now},
        )

        return https_fn.Response(
            json.dumps({"id": new_id, "field1": field1}, ensure_ascii=False),
            status=201,
            headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
```

### GET — objeto único con 404

```python
@https_fn.on_request(region="us-east4")
def get_<resource>(req: https_fn.Request) -> https_fn.Response:
    """Method: GET. Params: resourceId. Returns: 200 object | 400 | 401 | 404 | 500."""
    # ... validaciones ...
    doc_data = helper.get_document(FirestoreCollections.<COLLECTION>, resource_id)
    if doc_data is None:
        LOG.warning("%s %s no encontrado: %s", LOG_PREFIX, "Recurso", resource_id)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
    return https_fn.Response(json.dumps(_build_dict(resource_id, doc_data)), status=200, headers={...})
```

---

## Checklist de entrega

- [ ] Archivo creado en `functions/<module>/<verb>_<resource>.py`
- [ ] Template completo aplicado
- [ ] Región correcta en decorator
- [ ] Parámetros validados con early return
- [ ] CORS en toda respuesta
- [ ] JSON directo en éxito (sin wrappers)
- [ ] Errores vacíos
- [ ] FirestoreCollections para colecciones
- [ ] FirestoreHelper para CRUD
- [ ] Lógica en funciones `_auxiliares`
- [ ] Registrado en main.py
- [ ] Max 200 líneas
