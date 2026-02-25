"""
Get Event Competitor By Email - Obtener competidor de un evento por email

Busca al usuario por email en la colección users, valida que exista como
participante en events/{eventId}/participants y retorna los datos del
usuario (con subcolecciones) más el competitionCategory del participante.

Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value
from utils.validation_helper import validate_email

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_event_competitor_by_email]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _find_user_by_email(
    helper: FirestoreHelper, email: str
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Busca un usuario por email en la colección users.

    Returns:
        Tupla (user_id, user_data) si existe, None si no se encuentra.
    """
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "email", "operator": "==", "value": email}],
        limit=1,
    )
    if not results:
        return None
    return results[0]


def _get_participants_path(event_id: str) -> str:
    """Construye la ruta de la colección de participantes del evento."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


_EXCLUDED_FIELDS = {"createdAt", "updatedAt"}


def _get_subcollection_docs(
    helper: FirestoreHelper, user_id: str, subcollection: str
) -> List[Dict[str, Any]]:
    """Obtiene todos los documentos de una subcolección del usuario."""
    path = f"{FirestoreCollections.USERS}/{user_id}/{subcollection}"
    results = helper.query_documents(path)
    docs = []
    for doc_id, doc_data in results:
        converted = {
            k: convert_firestore_value(v)
            for k, v in doc_data.items()
            if k not in _EXCLUDED_FIELDS
        }
        converted["id"] = doc_id
        docs.append(converted)
    return docs


def _build_register(participant_data: Dict[str, Any]) -> Dict[str, Any]:
    """Construye el objeto register a partir de los datos del participante."""
    competition_category = participant_data.get("competitionCategory", {})
    return {
        "number": competition_category.get("pilotNumber", ""),
        "category": competition_category.get("registrationCategory", ""),
        "team": participant_data.get("team", ""),
    }


def _build_response(
    user_id: str,
    user_data: Dict[str, Any],
    participant_data: Dict[str, Any],
    event_id: str,
    personal_data: List[Dict[str, Any]],
    health_data: List[Dict[str, Any]],
    emergency_contacts: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    memberships: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construye el objeto de respuesta con register dentro de membership."""
    register = _build_register(participant_data)

    enriched_memberships = []
    for m in memberships:
        entry = dict(m)
        if entry.get("id") == event_id or entry.get("eventId") == event_id:
            entry["register"] = register
        enriched_memberships.append(entry)

    return {
        "id": user_id,
        "email": user_data.get("email", ""),
        "personalData": personal_data,
        "healthData": health_data,
        "emergencyContacts": emergency_contacts,
        "vehicles": vehicles,
        "membership": enriched_memberships,
    }


# ============================================================================
# ENDPOINT
# ============================================================================


@https_fn.on_request(region="us-east4")
def get_event_competitor_by_email(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene un competidor de un evento buscándolo por email.

    Busca al usuario por email, valida que sea participante del evento
    y retorna los datos del usuario (con subcolecciones) más los datos
    de competición (competitionCategory, team, score, registrationDate).

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query Parameters:
    - eventId: string (requerido) - ID del evento
    - email: string (requerido) - Email del usuario competidor

    Returns:
    - 200: Objeto JSON con datos del usuario, subcolecciones y competitionCategory
    - 400: Bad Request - parámetros faltantes o email inválido
    - 401: Unauthorized - token inválido o faltante
    - 404: Not Found - usuario no encontrado o no es participante del evento
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["GET"], "get_event_competitor_by_email", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "get_event_competitor_by_email"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        event_id = (req.args.get("eventId") or "").strip()
        email = (req.args.get("email") or "").strip()

        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not email:
            LOG.warning("%s email faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not validate_email(email):
            LOG.warning("%s Formato de email inválido: %s", LOG_PREFIX, email)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()

        user_result = _find_user_by_email(helper, email)
        if user_result is None:
            LOG.warning("%s Usuario no encontrado con email: %s", LOG_PREFIX, email)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_id, user_data = user_result

        participants_path = _get_participants_path(event_id)
        participant_data = helper.get_document(participants_path, user_id)

        if participant_data is None:
            LOG.warning(
                "%s Usuario %s no es participante del evento %s",
                LOG_PREFIX,
                user_id,
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        personal_data = _get_subcollection_docs(
            helper, user_id, FirestoreCollections.USER_PERSONAL_DATA
        )
        health_data = _get_subcollection_docs(
            helper, user_id, FirestoreCollections.USER_HEALTH_DATA
        )
        emergency_contacts = _get_subcollection_docs(
            helper, user_id, FirestoreCollections.USER_EMERGENCY_CONTACT
        )
        vehicles = _get_subcollection_docs(
            helper, user_id, FirestoreCollections.USER_VEHICLES
        )
        memberships = _get_subcollection_docs(
            helper, user_id, FirestoreCollections.USER_MEMBERSHIP
        )

        result = _build_response(
            user_id,
            user_data,
            participant_data,
            event_id,
            personal_data,
            health_data,
            emergency_contacts,
            vehicles,
            memberships,
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
