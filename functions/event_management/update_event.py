"""
Actualiza un evento existente. Solo el creador del evento puede hacerlo.
Los campos eventId, id y creator son inmutables. El backend agrega updatedAt.
La clave event_content no se persiste en el documento del evento: se guarda
en la subcolección event_content (mismo criterio que create_event).

Si el body incluye campos raíz, deben cumplir:
- source ∈ {app, web}
- typeEvent ∈ {individual, organization}
- duration: numérico
- sendNotifications: booleano (solo se recibe, no se persiste)

Método: PUT /api/event-management/{userId}/update?eventId={eventId}
Body JSON: campos a actualizar (eventId opcional para compatibilidad)
Headers: Authorization Bearer (requerido)
Returns: 200 objeto evento actualizado | 400 body inválido o eventId faltante | 401 no autorizado | 404 no encontrado | 500 error interno
"""

import json
import logging
from typing import Any, Dict

from firebase_functions import https_fn
from event_management.event_field_validation import validate_source_type_event_for_update
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[update_event]"

_IMMUTABLE_FIELDS = {"eventId", "id", "creator"}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _build_update_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """Elimina campos inmutables y agrega updatedAt."""
    updates = {k: v for k, v in body.items() if k not in _IMMUTABLE_FIELDS}
    updates["updatedAt"] = get_current_timestamp()
    return updates


def _build_event_response(event_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Añade el id al documento retornado."""
    result = dict(data)
    result["id"] = event_id
    return result


def _resolve_event_id(req: https_fn.Request, body: Dict[str, Any]) -> str:
    """Obtiene eventId desde query y mantiene compatibilidad con body."""
    event_id_from_query = (req.args.get("eventId") or "").strip()
    if event_id_from_query:
        return event_id_from_query

    return (body.get("eventId") or body.get("id") or "").strip()


def _content_path(event_id: str) -> str:
    """Ruta de la subcolección event_content de un evento."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"


def _upsert_event_content(
    helper: FirestoreHelper, event_id: str, event_content: Dict[str, Any]
) -> None:
    """
    Crea o actualiza el documento en events/{id}/event_content (alineado con save_event_info).
    """
    content_path = _content_path(event_id)
    info_payload = {k: v for k, v in event_content.items() if k != "eventId"}
    info_payload["updatedAt"] = get_current_timestamp()
    existing_docs = helper.query_documents(content_path, limit=1)
    if existing_docs:
        info_id, _ = existing_docs[0]
        helper.update_document(content_path, info_id, info_payload)
    else:
        info_payload["createdAt"] = get_current_timestamp()
        helper.create_document(content_path, info_payload)


# ============================================================================
# HANDLER
# ============================================================================


def handle_update(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Actualiza un evento verificando que el usuario sea el propietario.

    Params:
    - user_id: uid del usuario autenticado (extraído del Bearer token por el router)
    - query.eventId: ID del evento a actualizar (recomendado)
    - body.eventId o body.id: compatibilidad hacia atrás

    Returns:
    - 200: objeto evento actualizado con id
    - 400: body faltante o eventId ausente
    - 404: evento no existe o el usuario no es el propietario
    - 500: error interno
    """
    body = req.get_json(silent=True)
    if not isinstance(body, dict):
        LOG.warning("%s Body inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    event_id = _resolve_event_id(req, body)
    if not event_id:
        LOG.warning("%s eventId faltante en query/body", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    ok_fields, bad_field = validate_source_type_event_for_update(body)
    if not ok_fields:
        LOG.warning("%s Campo raíz inválido: %s", LOG_PREFIX, bad_field)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    try:
        event = get_event_if_owner(event_id, user_id)
        if event is None:
            LOG.warning("%s Evento no encontrado o sin permisos eventId=%s", LOG_PREFIX, event_id)
            return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

        # Se recibe para validación/flujo pero no se persiste en el documento raíz.
        body.pop("sendNotifications", None)
        event_content = body.pop("event_content", None)
        updates = _build_update_payload(body)

        helper = FirestoreHelper()
        helper.update_document(FirestoreCollections.EVENTS, event_id, updates)
        if isinstance(event_content, dict) and event_content:
            _upsert_event_content(helper, event_id, event_content)
        updated = helper.get_document(FirestoreCollections.EVENTS, event_id) or {}
        response = _build_event_response(event_id, updated)

        return https_fn.Response(
            json.dumps(response, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "PUT, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
