"""
Elimina un evento y todas sus subcolecciones en cascade.
Solo el creador del evento puede eliminarlo.

Cascade: event_content → routes/{id}/checkpoints → routes → evento raíz.

Método: DELETE /api/event-management/delete?eventId=
Headers: Authorization Bearer (requerido)
Query params: eventId (requerido)
Returns: 200 vacío | 400 param faltante | 401 no autorizado | 404 no encontrado | 500 error interno
"""

import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[delete_event]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _delete_route_checkpoints(
    db: firestore.Client,
    route_ref: firestore.DocumentReference,
) -> None:
    """Elimina todos los checkpoints de una ruta."""
    checkpoints = list(route_ref.collection(FirestoreCollections.EVENT_CHECKPOINTS).stream())
    for checkpoint_doc in checkpoints:
        checkpoint_doc.reference.delete()


def _delete_event_routes(event_id: str) -> None:
    """Elimina todas las rutas del evento y sus checkpoints en cascade."""
    db = firestore.client()
    routes = list(
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_ROUTES)
        .stream()
    )
    for route_doc in routes:
        route_ref = route_doc.reference
        _delete_route_checkpoints(db, route_ref)
        route_ref.delete()


def _delete_event_content(helper: FirestoreHelper, event_id: str) -> None:
    """Elimina todos los documentos en la subcolección event_content."""
    content_path = (
        f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"
    )
    for doc_id in helper.list_document_ids(content_path):
        helper.delete_document(content_path, doc_id)


# ============================================================================
# HANDLER
# ============================================================================


def handle_delete(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Elimina el evento y todas sus subcolecciones en cascade.

    Params:
    - user_id: uid del usuario autenticado (extraído del Bearer token por el router)
    - req.args.eventId: ID del evento a eliminar (requerido)

    Returns:
    - 200: vacío (eliminado correctamente)
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
        _delete_event_content(helper, event_id)
        _delete_event_routes(event_id)
        helper.delete_document(FirestoreCollections.EVENTS, event_id)

        LOG.info("%s Evento eliminado eventId=%s", LOG_PREFIX, event_id)
        return https_fn.Response("", status=200, headers={"Access-Control-Allow-Origin": "*"})

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
