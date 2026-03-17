"""
Get Competitor By Email - Obtener un usuario competidor por su email

Busca al usuario por email en la colección users y retorna el documento
raíz junto con todas las subcolecciones: personalData, healthData,
emergencyContacts, vehicles y membership.

Solo se incluyen en membership los eventos válidos (events/{eventId} con status
IN_PROGRESS o OPEN_REGISTRATION según EventStatus).
Para cada membership válido se retorna id (eventId) y register (number, category, team)
desde events/{eventId}/participants/{userId}.

Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from firebase_functions import https_fn
from models.event_document import EventStatus
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value
from utils.validation_helper import validate_email


LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_competitor_by_email]"

_EXCLUDED_FIELDS = {"createdAt", "updatedAt"}


def _get_participants_path(event_id: str) -> str:
    """Construye la ruta de la colección de participantes del evento."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


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


def _get_subcollection_docs(
    helper: FirestoreHelper, user_id: str, subcollection: str
) -> List[Dict[str, Any]]:
    """Obtiene todos los documentos de una subcolección del usuario (sin createdAt/updatedAt)."""
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


_VALID_EVENT_STATUSES = {
    EventStatus.IN_PROGRESS.value,
    EventStatus.OPEN_REGISTRATION.value,
}


def _is_event_valid_for_membership(helper: FirestoreHelper, event_id: str) -> bool:
    """
    Comprueba si el evento existe y tiene un estado válido para incluir en membership.
    Válidos: IN_PROGRESS (inProgress) o OPEN_REGISTRATION (openRegistration).
    """
    event = helper.get_document(FirestoreCollections.EVENTS, event_id)
    if event is None:
        return False
    status = event.get("status")
    if status is None:
        return False
    return str(status) in _VALID_EVENT_STATUSES


def _build_register(participant_data: Dict[str, Any]) -> Dict[str, Any]:
    """Construye el objeto register a partir de los datos del participante."""
    competition_category = participant_data.get("competitionCategory", {})
    return {
        "number": competition_category.get("pilotNumber", ""),
        "category": competition_category.get("registrationCategory", ""),
        "team": participant_data.get("team", ""),
    }


def _build_active_membership_with_register(
    helper: FirestoreHelper,
    user_id: str,
    membership_doc_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Para cada eventId en membership_doc_ids, comprueba si el evento es válido
    (status IN_PROGRESS o OPEN_REGISTRATION). Si es válido, obtiene el participante
    y retorna { "id": eventId, "register": {...} }. Si no, no se incluye en la lista.
    """
    result = []
    for event_id in membership_doc_ids:
        if not _is_event_valid_for_membership(helper, event_id):
            continue
        participants_path = _get_participants_path(event_id)
        participant_data = helper.get_document(participants_path, user_id)
        if participant_data is None:
            continue
        register = _build_register(participant_data)
        result.append({"id": event_id, "register": register})
    return result


def _check_user_inscribed_in_event(
    helper: FirestoreHelper, user_id: str, event_id: str
) -> bool:
    """
    Verifica si el usuario ya es participante del evento.

    Returns:
        True si existe el documento en events/{eventId}/participants/{userId}.
    """
    participants_path = _get_participants_path(event_id)
    participant = helper.get_document(participants_path, user_id)
    return participant is not None


def _build_user_response(
    user_id: str,
    user_data: Dict[str, Any],
    personal_data: List[Dict[str, Any]],
    health_data: List[Dict[str, Any]],
    emergency_contacts: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    memberships: List[Dict[str, Any]],
    user_was_inscribed_into_event: bool = False,
) -> Dict[str, Any]:
    """Construye el objeto de respuesta con datos raíz y subcolecciones (sin createdAt/updatedAt)."""
    return {
        "id": user_id,
        "email": user_data.get("email", ""),
        "username": user_data.get("username", ""),
        "authUserId": user_data.get("authUserId"),
        "avatarUrl": user_data.get("avatarUrl"),
        "isActive": user_data.get("isActive", False),
        "userWasInscribedIntoEvent": user_was_inscribed_into_event,
        "personalData": personal_data,
        "healthData": health_data,
        "emergencyContacts": emergency_contacts,
        "vehicles": vehicles,
        "membership": memberships,
    }


# ============================================================================
# ENDPOINT
# ============================================================================


@https_fn.on_request(region="us-east4")
def get_competitor_by_email(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene un usuario competidor buscándolo por email.

    Retorna el documento raíz del usuario junto con todas sus subcolecciones:
    personalData, healthData, emergencyContacts, vehicles y membership.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query Parameters:
    - email: string (requerido) - Email del usuario competidor
    - eventId: string (opcional) - ID del evento para verificar inscripción previa

    Returns:
    - 200: Objeto JSON con datos del usuario, subcolecciones y userWasInscribedIntoEvent
    - 400: Bad Request - email faltante o formato inválido
    - 401: Unauthorized - token inválido o faltante
    - 404: Not Found - usuario no encontrado
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["GET"], "get_competitor_by_email", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "get_competitor_by_email"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        email = (req.args.get("email") or "").strip()
        event_id = (req.args.get("eventId") or "").strip()

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

        membership_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{FirestoreCollections.USER_MEMBERSHIP}"
        )
        membership_results = helper.query_documents(membership_path)
        event_ids = [doc_id for doc_id, _ in membership_results]
        memberships = _build_active_membership_with_register(
            helper, user_id, event_ids
        )

        user_was_inscribed = False
        if event_id:
            user_was_inscribed = _check_user_inscribed_in_event(
                helper, user_id, event_id
            )
            LOG.info(
                "%s userWasInscribedIntoEvent=%s para userId=%s eventId=%s",
                LOG_PREFIX,
                user_was_inscribed,
                user_id,
                event_id,
            )

        result = _build_user_response(
            user_id,
            user_data,
            personal_data,
            health_data,
            emergency_contacts,
            vehicles,
            memberships,
            user_was_inscribed_into_event=user_was_inscribed,
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
