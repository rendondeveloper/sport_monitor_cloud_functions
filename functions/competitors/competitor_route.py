"""
Competitor Route - SPRTMNTRPP-74

Obtiene información del competidor y su ruta para un evento y día de carrera.
API pública: no requiere Bearer token.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from firebase_admin import firestore
from firebase_functions import https_fn
from google.cloud.firestore_v1.base_query import FieldFilter
from models.firestore_collections import FirestoreCollections
from utils.helper_http_verb import validate_request
from utils.helpers import format_utc_to_local_datetime

# Prefijo para filtrar logs: grep "[competitor_route]" o grep "competitor_route"
LOG = logging.getLogger(__name__)
LOG_PREFIX = "[competitor_route]"


def _get_participant_doc(db: firestore.Client, event_id: str, competitor_id: str):
    """Obtiene el documento del participante en events/{eventId}/participants/{competitorId}."""
    participant_ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_PARTICIPANTS)
        .document(competitor_id)
    )
    return participant_ref.get()


def _get_day_of_race_doc(db: firestore.Client, event_id: str, day_id: str):
    """Obtiene el documento del día de carrera en events/{eventId}/day_of_races/{dayId}."""
    day_ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.DAY_OF_RACES)
        .document(day_id)
    )
    return day_ref.get()


def _get_category_id_by_name(
    db: firestore.Client, event_id: str, registration_category: str
) -> Optional[str]:
    """
    Busca en event_categories el documento cuyo campo name coincide con registration_category.
    Retorna el id del documento o None si no existe.
    """
    if not registration_category or not registration_category.strip():
        return None
    categories_ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_CATEGORIES)
    )
    query = categories_ref.where(
        filter=FieldFilter("name", "==", registration_category.strip())
    ).limit(1)
    snapshot = query.get()
    if not snapshot:
        return None
    return snapshot[0].id


def _get_route_for_category_and_day(
    db: firestore.Client,
    event_id: str,
    category_id: str,
    day_id: str,
) -> Optional[firestore.DocumentSnapshot]:
    """
    Busca en events/{eventId}/routes un documento donde categoryIds contenga category_id
    y dayOfRaceIds contenga day_id. Firestore solo permite un array_contains por query,
    por eso se filtra por dayOfRaceIds en la query y por categoryIds en memoria.
    """
    routes_ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_ROUTES)
    )
    query = routes_ref.where(
        filter=FieldFilter("dayOfRaceIds", "array_contains", day_id)
    ).limit(50)
    snapshot = query.get()
    for doc in snapshot:
        data = doc.to_dict() or {}
        if category_id in data.get("categoryIds", []):
            return doc
    return None


def _build_response(
    participant_data: Dict[str, Any],
    route_doc: firestore.DocumentSnapshot,
) -> Dict[str, Any]:
    """Construye el JSON de respuesta según la especificación SPRTMNTRPP-74."""
    competition_category = participant_data.get("competitionCategory") or {}
    pilot_number = competition_category.get("pilotNumber")
    registration_category = competition_category.get("registrationCategory", "")

    # competitor.category = valor de pilotNumber (ej: "ORO"); nombre = registrationCategory (ej: "25F")
    category_str = (
        str(pilot_number) if pilot_number is not None else registration_category or ""
    )
    competitor_payload = {
        "category": category_str,
        "nombre": registration_category or "",
    }

    route_data = route_doc.to_dict() or {}
    route_url = route_data.get("routeUrl", "")
    total_distance = route_data.get("totalDistance")
    if total_distance is None:
        total_distance = 0
    typedistance = route_data.get("typedistance") or route_data.get(
        "typeDistance", ""
    )

    route_payload = {
        "name": route_data.get("name", ""),
        "route": route_url,
        "version": 1,
        "totalDistance": total_distance,
        "typedistance": typedistance,
    }

    now_utc = datetime.now(timezone.utc)
    last_update = format_utc_to_local_datetime(now_utc)

    return {
        "competitor": competitor_payload,
        "route": route_payload,
        "lastUpdate": last_update,
    }


@https_fn.on_request()
def competitor_route(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene información del competidor y su ruta para un evento y día de carrera.

    API pública: no requiere Authorization Bearer.

    Query/Path Parameters:
    - eventId: ID del evento (requerido)
    - dayId: ID del día de carrera (requerido)
    - competitorId: ID del competidor (requerido)

    Validaciones:
    - events/{eventId}/participants/{competitorId} debe existir y isAvailable == True
    - events/{eventId}/day_of_races/{dayId} debe existir y isActivate == True
    - Se obtiene categoryId desde event_categories donde name == competitionCategory.registrationCategory
    - Se busca en routes donde categoryIds contiene categoryId y dayOfRaceIds contiene dayId

    Returns:
    - 200: JSON con competitor, route y lastUpdate (ISO 8601)
    - 400: Parámetros faltantes o inválidos
    - 404: Participante no encontrado/no disponible, día no activo o ruta no encontrada
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["GET"], "competitor_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Extraer parámetros: primero query, luego path si falta alguno
        event_id = (req.args.get("eventId") or "").strip()
        day_id = (req.args.get("dayId") or "").strip()
        competitor_id = (req.args.get("competitorId") or "").strip()

        if not event_id or not day_id or not competitor_id:
            path_parts = [p for p in (req.path or "").split("/") if p]
            if "competitor-route" in path_parts:
                idx = path_parts.index("competitor-route")
                if idx + 3 <= len(path_parts):
                    if not event_id:
                        event_id = path_parts[idx + 1]
                    if not day_id:
                        day_id = path_parts[idx + 2]
                    if not competitor_id:
                        competitor_id = path_parts[idx + 3]
            event_id = (event_id or "").strip()
            day_id = (day_id or "").strip()
            competitor_id = (competitor_id or "").strip()

        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not day_id:
            LOG.warning("%s dayId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not competitor_id:
            LOG.warning("%s competitorId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        db = firestore.client()

        # 1. Participante: debe existir y isAvailable == True
        participant_doc = _get_participant_doc(db, event_id, competitor_id)
        if not participant_doc.exists:
            LOG.warning(
                "%s Participante no encontrado eventId=%s competitorId=%s",
                LOG_PREFIX,
                event_id,
                competitor_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        participant_data = participant_doc.to_dict() or {}
        if not participant_data.get("isAvailable", False):
            LOG.warning(
                "%s Participante no disponible (isAvailable=false) competitorId=%s",
                LOG_PREFIX,
                competitor_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # 2. Día de carrera: debe existir y isActivate == True
        day_doc = _get_day_of_race_doc(db, event_id, day_id)
        if not day_doc.exists:
            LOG.warning(
                "%s Día de carrera no encontrado eventId=%s dayId=%s",
                LOG_PREFIX,
                event_id,
                day_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        day_data = day_doc.to_dict() or {}
        if not day_data.get("isActivate", False):
            LOG.warning("%s Día de carrera no activo dayId=%s", LOG_PREFIX, day_id)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # 3. categoryId desde event_categories por name == registrationCategory
        competition_category = participant_data.get("competitionCategory") or {}
        registration_category = competition_category.get("registrationCategory", "")
        category_id = _get_category_id_by_name(db, event_id, registration_category)
        if not category_id:
            LOG.warning(
                "%s Categoría no encontrada name=%s eventId=%s",
                LOG_PREFIX,
                registration_category,
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # 4. Ruta: categoryIds contiene categoryId y dayOfRaceIds contiene dayId
        route_doc = _get_route_for_category_and_day(
            db, event_id, category_id, day_id
        )
        if not route_doc:
            LOG.warning(
                "%s Ruta no encontrada eventId=%s categoryId=%s dayId=%s",
                LOG_PREFIX,
                event_id,
                category_id,
                day_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # 5. Respuesta
        result = _build_response(participant_data, route_doc)
        LOG.info(
            "%s OK eventId=%s competitorId=%s dayId=%s",
            LOG_PREFIX,
            event_id,
            competitor_id,
            day_id,
        )
        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        LOG.error("%s Error de validación: %s", LOG_PREFIX, e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
