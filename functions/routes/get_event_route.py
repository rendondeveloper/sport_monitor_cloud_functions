"""
Handler para obtener una ruta de evento por ID.

Usado por route_route.py para GET /api/routes/{userId}/get.

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
LOG_PREFIX = "[get_event_route]"

_JSON_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
}
_CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _checkpoints_path(event_id: str, route_id: str) -> str:
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_ROUTES}/{route_id}"
        f"/{FirestoreCollections.EVENT_CHECKPOINTS}"
    )


def _serialize_route(route_id: str, route_data: Dict[str, Any], event_id: str) -> Dict[str, Any]:
    """Convierte datos de ruta a dict de respuesta, incluyendo sus checkpoints."""
    result = dict(route_data)
    result["id"] = route_id
    helper = FirestoreHelper()
    checkpoint_docs = helper.query_documents(_checkpoints_path(event_id, route_id))
    result["checkpoints"] = [{"id": cp_id, **cp_data} for cp_id, cp_data in checkpoint_docs]
    return result


# ============================================================================
# HANDLER
# ============================================================================


def handle_get(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Retorna una ruta de evento con sus checkpoints incluidos.

    Path params:
    - user_id: uid del propietario del evento (extraído del path URL, no del token)

    Query params:
    - eventId: string (requerido)
    - routeId: string (requerido)

    Returns:
    - 200: objeto ruta con array checkpoints
    - 400: user_id, eventId o routeId faltante o vacío
    - 404: evento no encontrado, usuario no es el creador, o ruta no existe
    - 500: error interno
    """
    if not user_id:
        LOG.warning("%s user_id faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS_HEADERS)

    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS_HEADERS)

    route_id = (req.args.get("routeId") or "").strip()
    if not route_id:
        LOG.warning("%s routeId faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS_HEADERS)

    if get_event_if_owner(event_id, user_id) is None:
        LOG.warning(
            "%s Evento no encontrado o usuario no es el creador eventId=%s",
            LOG_PREFIX,
            event_id,
        )
        return https_fn.Response("", status=404, headers=_CORS_HEADERS)

    try:
        route_path = f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_ROUTES}"
        helper = FirestoreHelper()
        route_data = helper.get_document(route_path, route_id)
        if route_data is None:
            LOG.warning("%s Ruta no encontrada routeId=%s", LOG_PREFIX, route_id)
            return https_fn.Response("", status=404, headers=_CORS_HEADERS)

        result = _serialize_route(route_id, route_data, event_id)
        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=200,
            headers=_JSON_HEADERS,
        )

    except Exception as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers=_CORS_HEADERS)
