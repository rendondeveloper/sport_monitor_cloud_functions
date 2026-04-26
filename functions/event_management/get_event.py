"""
Obtiene un evento por ID. Solo el creador del evento puede accederlo.

Método: GET /api/event-management/{userId}/get?eventId=
Headers: Authorization Bearer (requerido)
Path params: userId (requerido)
Query params: eventId (requerido)
Returns: 200 objeto evento + eventContent | 400 param faltante | 401 no autorizado | 404 no encontrado | 500 error interno
"""

import json
import logging
from typing import Any, Dict

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_event]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _content_path(event_id: str) -> str:
    """Ruta de la subcolección event_content de un evento."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"


def _build_event_response(
    event_id: str, data: Dict[str, Any], event_content: Dict[str, Any]
) -> Dict[str, Any]:
    """Añade el id al evento y la llave eventContent."""
    result = dict(data)
    result["id"] = event_id
    result["eventContent"] = event_content
    return result


# ============================================================================
# HANDLER
# ============================================================================


def handle_get(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Retorna el evento si el usuario es el propietario.

    Params:
    - user_id: uid del usuario autenticado (extraído del Bearer token por el router)
    - req.args.eventId: ID del evento (requerido)

    Returns:
    - 200: objeto evento con id + eventContent
    - 400: eventId faltante
    - 404: evento no existe o el usuario no es el propietario
    - 500: error interno
    """
    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    try:
        event = get_event_if_owner(event_id, user_id)
        if event is None:
            LOG.warning("%s Evento no encontrado o sin permisos eventId=%s", LOG_PREFIX, event_id)
            return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

        helper = FirestoreHelper()
        content_docs = helper.query_documents(_content_path(event_id), limit=1)

        event_content = {}
        if content_docs:
            _, content_data = content_docs[0]
            event_content = dict(content_data)

        response = _build_event_response(event_id, event, event_content)

        return https_fn.Response(
            json.dumps(response, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
