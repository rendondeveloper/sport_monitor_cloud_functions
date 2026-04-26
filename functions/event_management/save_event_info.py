"""
Guarda (crea o actualiza) la información adicional de un evento.
Solo el creador del evento puede guardar info.
El backend agrega updatedAt siempre; createdAt solo al crear.

Método: POST /api/event-management/save-info
Body JSON: eventId (requerido) + campos de info
Headers: Authorization Bearer (requerido)
Returns: 200 objeto info guardado | 400 body/param inválido | 401 no autorizado | 404 no encontrado | 500 error interno
"""

import json
import logging
from typing import Any, Dict

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[save_event_info]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _content_path(event_id: str) -> str:
    """Ruta de la subcolección event_content de un evento."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"


def _build_info_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara el payload eliminando eventId y añadiendo updatedAt."""
    payload = {k: v for k, v in body.items() if k != "eventId"}
    payload["updatedAt"] = get_current_timestamp()
    return payload


def _build_info_response(info_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Añade el id al documento de info retornado."""
    result = dict(data)
    result["id"] = info_id
    return result


# ============================================================================
# HANDLER
# ============================================================================


def handle_save_info(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Crea o actualiza el documento event_content del evento.

    Si ya existe un documento → update.
    Si no existe → create con createdAt adicional.

    Params:
    - user_id: uid del usuario autenticado (extraído del Bearer token por el router)
    - body.eventId: ID del evento (requerido)
    - body.*: campos adicionales de info del evento

    Returns:
    - 200: objeto info guardado con id
    - 400: body inválido o eventId faltante
    - 404: evento no existe o el usuario no es el propietario
    - 500: error interno
    """
    body = req.get_json(silent=True)
    if not isinstance(body, dict):
        LOG.warning("%s Body inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    event_id = (body.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante en body", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    try:
        if get_event_if_owner(event_id, user_id) is None:
            LOG.warning("%s Evento no encontrado o sin permisos eventId=%s", LOG_PREFIX, event_id)
            return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

        info_payload = _build_info_payload(body)
        content_path = _content_path(event_id)

        helper = FirestoreHelper()
        existing_docs = helper.query_documents(content_path, limit=1)

        if existing_docs:
            info_id, _ = existing_docs[0]
            helper.update_document(content_path, info_id, info_payload)
        else:
            info_payload["createdAt"] = get_current_timestamp()
            info_id = helper.create_document(content_path, info_payload)

        saved = helper.get_document(content_path, info_id) or info_payload
        response = _build_info_response(info_id, saved)

        LOG.info("%s Info guardada eventId=%s infoId=%s", LOG_PREFIX, event_id, info_id)
        return https_fn.Response(
            json.dumps(response, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
