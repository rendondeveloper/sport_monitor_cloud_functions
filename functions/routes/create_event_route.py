"""
Handler para crear una ruta de evento.

Usado por route_route.py para POST /api/routes/create.
"""

import logging

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.event_owner_helper import get_event_if_owner
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_event_route]"


# ============================================================================
# ENDPOINT
# ============================================================================


def handle_create(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Crea una ruta de evento con sus waypoints (checkpoints) opcionales.

    Body Parameters:
    - name: string (requerido)
    - eventId: string (requerido)
    - colorTrack: any (requerido — puede ser 0, validar con `is None`)
    - width: any (requerido — puede ser 0, validar con `is None`)
    - categoryIds: list (opcional, default [])
    - dayOfRaceIds: list (opcional, default [])
    - routeUrl: string (opcional)
    - visibleForPilots: bool (opcional)
    - trackPoints: list (opcional)
    - waypoints: list de dicts (opcional — se crean como checkpoints de la ruta)

    Returns:
    - 200: {"id": route_id, "name": name, "createdAt": ..., "updatedAt": ...}
    - 400: Body inválido, campo requerido faltante o vacío
    - 404: Evento no encontrado o el usuario no es el creador
    - 500: Error interno
    """
    body = req.get_json(silent=True)
    if not isinstance(body, dict):
        LOG.warning("%s Body inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    name = (body.get("name") or "").strip()
    if not name:
        LOG.warning("%s name faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    event_id = (body.get("eventId") or "").strip()
    if not event_id:
        LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    color_track = body.get("colorTrack")
    if color_track is None:
        LOG.warning("%s colorTrack faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    width = body.get("width")
    if width is None:
        LOG.warning("%s width faltante", LOG_PREFIX)
        return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})

    if get_event_if_owner(event_id, user_id) is None:
        LOG.warning("%s Evento no encontrado o usuario no es el creador", LOG_PREFIX)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

    try:
        helper = FirestoreHelper()
        route_collection_path = (
            f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_ROUTES}"
        )
        route_id = helper.new_document_id(route_collection_path)
        now = get_current_timestamp()

        route_payload = {
            "name": name,
            "colorTrack": color_track,
            "width": width,
            "categoryIds": body.get("categoryIds") or [],
            "dayOfRaceIds": body.get("dayOfRaceIds") or [],
            "createdAt": now,
            "updatedAt": now,
        }

        route_url = (body.get("routeUrl") or "").strip()
        if route_url:
            route_payload["routeUrl"] = route_url

        visible_for_pilots = body.get("visibleForPilots")
        if visible_for_pilots is not None:
            route_payload["visibleForPilots"] = visible_for_pilots

        track_points = body.get("trackPoints")
        if track_points and isinstance(track_points, list):
            route_payload["trackPoints"] = track_points

        operations = [(route_collection_path, route_id, route_payload)]

        waypoints = body.get("waypoints")
        if waypoints and isinstance(waypoints, list):
            checkpoints_path = (
                f"{FirestoreCollections.EVENTS}/{event_id}"
                f"/{FirestoreCollections.EVENT_ROUTES}/{route_id}"
                f"/{FirestoreCollections.EVENT_CHECKPOINTS}"
            )
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

        helper.batch_set(operations)

        return https_fn.Response("", status=200, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
