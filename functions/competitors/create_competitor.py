"""
Create Competitor - Crear participante en un evento vinculado a un usuario

Crea el documento del competidor en events/{eventId}/participants usando
el userId como id del documento, para que el mismo id exista en users y en
participantes. Incluye userId en el documento. Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, Optional

from firebase_functions import https_fn
from google.cloud.firestore_v1.base_query import FieldFilter
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_competitor]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _get_collection_path(event_id: str) -> str:
    """Construye la ruta de la colección de participantes."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


def _validate_event_exists(helper: FirestoreHelper, event_id: str) -> bool:
    """Valida que el evento exista antes de crear el competidor."""
    event = helper.get_document(FirestoreCollections.EVENTS, event_id)
    return event is not None


def _check_duplicate_competitor(
    helper: FirestoreHelper,
    event_id: str,
    pilot_number: str,
) -> bool:
    """
    Verifica si ya existe un competidor con el mismo número de piloto
    en el evento. Retorna True si existe duplicado.
    """
    if not pilot_number:
        return False

    collection_path = _get_collection_path(event_id)
    results = helper.query_documents(
        collection_path,
        filters=[
            {
                "field": "competitionCategory.pilotNumber",
                "operator": "==",
                "value": pilot_number,
            }
        ],
    )
    return len(results) > 0


def _build_competitor_document(
    request_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    Construye el documento del competidor para Firestore.
    Acepta "competition" (eventId, pilotNumber, registrationCategory, team) o
    "competitionCategory" + eventId/team a nivel raíz (retrocompatibilidad).
    """
    now = get_current_timestamp()
    comp = request_data.get("competition") or request_data.get("competitionCategory") or {}
    event_id = comp.get("eventId") or request_data.get("eventId", "")
    team = comp.get("team") or request_data.get("team", "")

    return {
        "userId": user_id,
        "eventId": event_id,
        "competitionCategory": {
            "pilotNumber": comp.get("pilotNumber", ""),
            "registrationCategory": comp.get("registrationCategory", ""),
        },
        "registrationDate": request_data.get("registrationDate", now),
        "team": team,
        "score": 0,
        "timesToStart": [],
        "createdAt": now,
        "updatedAt": now,
    }


# ============================================================================
# ENDPOINT PRINCIPAL
# ============================================================================


@https_fn.on_request()
def create_competitor(req: https_fn.Request) -> https_fn.Response:
    """
    Crea un participante en el evento vinculado a un usuario (mismo id en users y en participants).

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Request Body (JSON):
    - userId: string (requerido) - ID del documento en colección users
    - eventId: string (requerido) - ID del evento
    - competitionCategory: object (requerido)
        - pilotNumber: string - Número de piloto
        - registrationCategory: string - Categoría de registro
    - registrationDate: string (opcional) - Fecha ISO 8601
    - team: string (opcional) - Nombre del equipo

    Returns:
    - 201: {"id": "<userId>"} - Mismo id que en users (participante creado en participants)
    - 400: Bad Request - body inválido o campos faltantes
    - 401: Unauthorized - token inválido o faltante
    - 404: Not Found - usuario (userId) o evento no encontrado
    - 409: Conflict - usuario ya participante en el evento o número de piloto duplicado
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["POST"], "create_competitor", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "create_competitor"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Parsear request body
        try:
            request_data = req.get_json(silent=True)
        except (ValueError, TypeError) as e:
            LOG.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if request_data is None:
            LOG.warning("%s Request body inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Validar userId (requerido: id del usuario en colección users)
        user_id = request_data.get("userId", "")
        if not user_id or not isinstance(user_id, str) or user_id.strip() == "":
            LOG.warning("%s userId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_id = user_id.strip()

        # Validar eventId
        event_id = request_data.get("eventId", "")
        if not event_id or not isinstance(event_id, str) or event_id.strip() == "":
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        event_id = event_id.strip()
        helper = FirestoreHelper()

        # Validar que el usuario exista en users
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            LOG.warning("%s Usuario no encontrado: %s", LOG_PREFIX, user_id)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Validar que el evento exista
        if not _validate_event_exists(helper, event_id):
            LOG.warning("%s Evento no encontrado: %s", LOG_PREFIX, event_id)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Verificar si ya existe participante con este userId en el evento
        collection_path = _get_collection_path(event_id)
        existing = helper.get_document(collection_path, user_id)
        if existing is not None:
            LOG.warning(
                "%s Ya existe participante userId=%s en evento %s",
                LOG_PREFIX,
                user_id,
                event_id,
            )
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Verificar duplicados por número de piloto
        competition_category = request_data.get("competitionCategory", {})
        pilot_number = competition_category.get("pilotNumber", "")
        if pilot_number and _check_duplicate_competitor(helper, event_id, pilot_number):
            LOG.warning(
                "%s Número de piloto duplicado: %s en evento %s",
                LOG_PREFIX,
                pilot_number,
                event_id,
            )
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Construir documento y guardar usando userId como id del documento
        competitor_doc = _build_competitor_document(request_data, user_id)
        helper.create_document_with_id(collection_path, user_id, competitor_doc)

        LOG.info(
            "%s Participante creado: userId=%s en evento %s",
            LOG_PREFIX,
            user_id,
            event_id,
        )

        return https_fn.Response(
            json.dumps({"id": user_id}, ensure_ascii=False),
            status=201,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
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
