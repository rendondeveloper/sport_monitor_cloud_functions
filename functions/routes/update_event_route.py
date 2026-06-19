"""
Handler para actualizar una ruta de evento.

Usado por route_route.py para PUT /api/routes/{userId}/update.
"""

import logging

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[update_event_route]"

_CORS = {"Access-Control-Allow-Origin": "*"}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _build_update_payload(body: dict, now: str) -> dict:
    """Construye el payload de actualización con solo los campos presentes."""
    payload: dict = {"updatedAt": now}

    name = (body.get("name") or "").strip()
    if name:
        payload["name"] = name

    color_track = body.get("colorTrack")
    if color_track is not None:
        payload["colorTrack"] = color_track

    width = body.get("width")
    if width is not None:
        payload["width"] = width

    route_url = (body.get("routeUrl") or "").strip()
    if route_url:
        payload["routeUrl"] = route_url

    if "categoryIds" in body:
        payload["categoryIds"] = body.get("categoryIds") or []

    if "dayOfRaceIds" in body:
        payload["dayOfRaceIds"] = body.get("dayOfRaceIds") or []

    visible_for_pilots = body.get("visibleForPilots")
    if visible_for_pilots is not None:
        payload["visibleForPilots"] = visible_for_pilots

    track_points = body.get("trackPoints")
    if track_points and isinstance(track_points, list):
        payload["trackPoints"] = track_points

    return payload


def _replace_waypoints(
    helper: FirestoreHelper, checkpoints_path: str, waypoints: list, now: str
) -> None:
    """Elimina los checkpoints existentes y escribe los nuevos."""
    existing = helper.query_documents(checkpoints_path)
    for doc_id, _ in existing:
        helper.delete_document(checkpoints_path, doc_id)

    if not waypoints:
        return

    operations = []
    for waypoint in waypoints:
        if not isinstance(waypoint, dict):
            continue
        checkpoint_payload = {
            "name": (waypoint.get("name") or "").strip(),
            "order": waypoint.get("order", 0),
            "coordinates": (waypoint.get("coordinates") or "").strip(),
            "checkpointTypeId": (waypoint.get("checkpointTypeId") or "").strip(),
            "assignedStaffIds": waypoint.get("assignedStaffIds") or [],
            "createdAt": now,
            "updatedAt": now,
        }
        icon_custom = (waypoint.get("iconCustom") or "").strip()
        if icon_custom:
            checkpoint_payload["iconCustom"] = icon_custom
        operations.append((checkpoints_path, None, checkpoint_payload))

    if operations:
        helper.batch_set(operations)


# ============================================================================
# ENDPOINT
# ============================================================================


def handle_update(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Actualiza una ruta de evento y opcionalmente reemplaza sus waypoints.

    Body Parameters:
    - eventId: string (requerido)
    - routeId: string (requerido)
    - name: string (opcional)
    - colorTrack: number (opcional)
    - width: number (opcional)
    - routeUrl: string (opcional)
    - categoryIds: array[string] (opcional)
    - dayOfRaceIds: array[string] (opcional)
    - visibleForPilots: boolean (opcional)
    - trackPoints: array[object] (opcional)
    - waypoints: array[object] (opcional — reemplaza todos los checkpoints existentes)

    Returns:
    - 200: Actualización exitosa
    - 400: Body inválido o campo requerido faltante
    - 404: Evento o ruta no encontrados, o usuario no es el creador
    - 500: Error interno
    """
    body = req.get_json(silent=True)
    if not isinstance(body, dict):
        LOG.warning("%s Body inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS)

    event_id = (body.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS)

    route_id = (body.get("id") or "").strip()
    if not route_id:
        LOG.warning("%s id faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=_CORS)

    if get_event_if_owner(event_id, user_id) is None:
        LOG.warning("%s Evento no encontrado o usuario no es el creador", LOG_PREFIX)
        return https_fn.Response("", status=404, headers=_CORS)

    try:
        helper = FirestoreHelper()
        route_collection_path = (
            f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_ROUTES}"
        )

        route_data = helper.get_document(route_collection_path, route_id)
        if route_data is None:
            LOG.warning("%s Ruta no encontrada: %s", LOG_PREFIX, route_id)
            return https_fn.Response("", status=404, headers=_CORS)

        now = get_current_timestamp()
        update_payload = _build_update_payload(body, now)
        helper.update_document(route_collection_path, route_id, update_payload)

        if "waypoints" in body:
            checkpoints_path = (
                f"{route_collection_path}/{route_id}"
                f"/{FirestoreCollections.EVENT_CHECKPOINTS}"
            )
            _replace_waypoints(helper, checkpoints_path, body.get("waypoints") or [], now)

        return https_fn.Response("", status=200, headers=_CORS)

    except Exception as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers=_CORS)
