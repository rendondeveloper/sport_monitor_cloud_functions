"""
Obtiene la información adicional (event_content) de un evento.
Solo el creador del evento puede accederla. Retorna {} si no existe.

Método: GET /api/event-management/get-info?eventId=
Headers: Authorization Bearer (requerido)
Query params: eventId (requerido)
Returns: 200 objeto info o {} | 400 param faltante | 401 no autorizado | 404 no encontrado | 500 error interno
"""

import json
import logging
from typing import Any, Dict

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_event_info]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _content_path(event_id: str) -> str:
    """Ruta de la subcolección event_content de un evento."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"


def _build_info_response(info_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Añade el id al documento de info retornado."""
    result = dict(data)
    result["id"] = info_id
    return result


# ============================================================================
# HANDLER
# ============================================================================


def handle_get_info(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Retorna el documento event_content del evento si el usuario es el propietario.
    Retorna {} si no existe ningún documento de info.

    Params:
    - user_id: uid del usuario autenticado (extraído del Bearer token por el router)
    - req.args.eventId: ID del evento (requerido)

    Returns:
    - 200: objeto info con id, o {} si no existe
    - 400: eventId faltante
    - 404: evento no existe o el usuario no es el propietario
    - 500: error interno
    """
    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    try:
        if get_event_if_owner(event_id, user_id) is None:
            LOG.warning("%s Evento no encontrado o sin permisos eventId=%s", LOG_PREFIX, event_id)
            return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

        helper = FirestoreHelper()
        docs = helper.query_documents(_content_path(event_id), limit=1)

        if not docs:
            return https_fn.Response(
                json.dumps({}, ensure_ascii=False),
                status=200,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
            )

        info_id, info_data = docs[0]
        response = _build_info_response(info_id, info_data)

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
