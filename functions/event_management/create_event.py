"""
Crea un nuevo evento. El cliente envía los campos del evento; el backend
agrega creator, createdAt y updatedAt.

Campos raíz obligatorios:
- source (app|web)
- typeEvent (individual|organization)
- duration (numérico)
- sendNotifications (booleano; solo se recibe, no se persiste)

Método: POST /api/event-management/{userId}/create
Body JSON: campos del evento (requerido)
Headers: Authorization Bearer (requerido)
Returns: 201 creado | 400 body inválido | 401 no autorizado | 500 error interno
"""

import logging
from typing import Any, Dict

from firebase_functions import https_fn
from event_management.event_field_validation import validate_source_type_event_for_create
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_event]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _build_event_payload(body: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Construye el payload a guardar en Firestore."""
    now = get_current_timestamp()
    payload = dict(body)
    payload["creator"] = user_id
    payload["createdAt"] = payload.get("createdAt") or now
    payload["updatedAt"] = now
    return payload


def _content_path(event_id: str) -> str:
    """Ruta de la subcolección event_content de un evento."""
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"


def _build_info_payload(event_content: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara el payload de event_content con timestamps."""
    now = get_current_timestamp()
    payload = dict(event_content)
    payload["createdAt"] = payload.get("createdAt") or now
    payload["updatedAt"] = now
    return payload


def _create_event_with_content_atomic(
    helper: FirestoreHelper, event_payload: Dict[str, Any], event_content: Dict[str, Any]
) -> None:
    """
    Crea evento + event_content en un solo batch atómico.

    Si el commit falla, no se persiste ninguno de los dos documentos.
    """
    event_ref = helper.db.collection(FirestoreCollections.EVENTS).document()
    content_ref = helper.db.collection(_content_path(event_ref.id)).document()
    info_payload = _build_info_payload(event_content)

    batch = helper.db.batch()
    batch.set(event_ref, event_payload)
    batch.set(content_ref, info_payload)
    batch.commit()


def handle_create(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Crea un evento y retorna solo código HTTP.

    Params:
    - user_id: uid del usuario autenticado (extraído del Bearer token por el router)
    - body: dict con los campos del evento (requerido)

    Returns:
    - 201: creado exitosamente
    - 400: body faltante o inválido
    - 500: error interno
    """
    body = req.get_json(silent=True)
    if not isinstance(body, dict):
        LOG.warning("%s Body inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    ok_fields, bad_field = validate_source_type_event_for_create(body)
    if not ok_fields:
        LOG.warning("%s Campo raíz inválido o faltante: %s", LOG_PREFIX, bad_field)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    try:
        # Se recibe para control de flujo cliente/backend, pero no se guarda en Firestore.
        body.pop("sendNotifications", None)
        event_content = body.pop("event_content", None)
        payload = _build_event_payload(body, user_id)

        helper = FirestoreHelper()
        if isinstance(event_content, dict) and event_content:
            _create_event_with_content_atomic(helper, payload, event_content)
        else:
            helper.create_document(FirestoreCollections.EVENTS, payload)
        return https_fn.Response(
            "",
            status=201,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
