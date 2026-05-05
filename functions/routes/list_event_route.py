"""
Handler para listar las rutas de un evento.

Usado por route_route.py para GET /api/routes/{userId}/list.

El userId viene del path URL, no del token. El token solo autentica;
la autorización de ownership se verifica con get_event_if_owner.
"""

import json
import logging
from typing import Any, Dict

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[list_event_route]"

_JSON_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
}
_CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _routes_path(event_id: str) -> str:
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_ROUTES}"


def _checkpoints_path(event_id: str, route_id: str) -> str:
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_ROUTES}/{route_id}"
        f"/{FirestoreCollections.EVENT_CHECKPOINTS}"
    )


_TIMESTAMP_FIELDS = {"createdAt", "updatedAt"}


def _strip_timestamps(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k not in _TIMESTAMP_FIELDS}


def _serialize_route(route_id: str, route_data: Dict[str, Any], event_id: str) -> Dict[str, Any]:
    """Convierte datos de ruta a dict de respuesta, incluyendo sus checkpoints."""
    result = _strip_timestamps(route_data)
    result["id"] = route_id
    helper = FirestoreHelper()
    checkpoint_docs = helper.query_documents(_checkpoints_path(event_id, route_id))
    result["checkpoints"] = [
        {"id": cp_id, **_strip_timestamps(cp_data)} for cp_id, cp_data in checkpoint_docs
    ]
    return result


# ============================================================================
# HANDLER
# ============================================================================


def handle_list(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Retorna la lista de rutas de un evento. Retorna [] si no hay rutas.

    Path params:
    - user_id: uid del propietario del evento (extraído del path URL, no del token)

    Query params:
    - eventId: string (requerido)

    Returns:
    - 200: array de rutas (puede ser vacío)
    - 400: user_id o eventId faltante o vacío
    - 404: evento no encontrado o usuario no es el creador
    - 500: error interno
    """
    if not user_id:
        LOG.warning("%s user_id faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS_HEADERS)

    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS_HEADERS)

    if get_event_if_owner(event_id, user_id) is None:
        LOG.warning(
            "%s Evento no encontrado o usuario no es el creador eventId=%s",
            LOG_PREFIX,
            event_id,
        )
        return https_fn.Response("", status=404, headers=_CORS_HEADERS)

    try:
        helper = FirestoreHelper()
        route_docs = helper.query_documents(_routes_path(event_id))
        routes = [_serialize_route(route_id, route_data, event_id) for route_id, route_data in route_docs]

        return https_fn.Response(
            json.dumps(routes, ensure_ascii=False),
            status=200,
            headers=_JSON_HEADERS,
        )

    except Exception as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers=_CORS_HEADERS)
