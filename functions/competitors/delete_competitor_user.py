"""
Delete Competitor User - Eliminar usuario competidor creado con create_competitor_user

Elimina en orden: participante, membership, subcolecciones del usuario
(emergencyContacts como colección, healthData, personalData) y documento users.
Requiere Bearer token.
"""

import logging

from competitors.create_competitor import _get_collection_path
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[delete_competitor_user]"

# Nombre de la subcolección de contactos de emergencia (fallback si no existe en FirestoreCollections)
_USER_EMERGENCY_CONTACTS = getattr(
    FirestoreCollections, "USER_EMERGENCY_CONTACT", "emergencyContacts"
)


def _delete_user_subcollections(helper: FirestoreHelper, user_id: str) -> None:
    """
    Elimina vehicles, personalData, healthData y todos los documentos de emergencyContacts.
    Si alguna subcolección no existe o falla, se registra el warning y se continúa.
    """
    base = f"{FirestoreCollections.USERS}/{user_id}"

    # vehicles: listar todos los documentos y borrarlos (users/{userId}/vehicles)
    try:
        vehicles_path = f"{base}/{FirestoreCollections.USER_VEHICLES}"
        vehicle_ids = helper.list_document_ids(vehicles_path)
        for doc_id in vehicle_ids:
            try:
                helper.delete_document(vehicles_path, doc_id)
                LOG.info(
                    "%s delete_competitor_user_resources: %s/%s eliminado",
                    LOG_PREFIX,
                    FirestoreCollections.USER_VEHICLES,
                    doc_id,
                )
            except Exception as e:
                LOG.warning(
                    "%s delete_competitor_user_resources: error eliminando %s/%s: %s",
                    LOG_PREFIX,
                    FirestoreCollections.USER_VEHICLES,
                    doc_id,
                    e,
                )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error listando vehicles (puede no existir): %s",
            LOG_PREFIX,
            e,
        )

    # emergencyContacts: listar todos los documentos y borrarlos (contact_0, contact_1, ...)
    try:
        emergency_path = f"{base}/{_USER_EMERGENCY_CONTACTS}"
        doc_ids = helper.list_document_ids(emergency_path)
        for doc_id in doc_ids:
            try:
                helper.delete_document(emergency_path, doc_id)
                LOG.info(
                    "%s delete_competitor_user_resources: %s/%s eliminado",
                    LOG_PREFIX,
                    _USER_EMERGENCY_CONTACTS,
                    doc_id,
                )
            except Exception as e:
                LOG.warning(
                    "%s delete_competitor_user_resources: error eliminando %s/%s: %s",
                    LOG_PREFIX,
                    _USER_EMERGENCY_CONTACTS,
                    doc_id,
                    e,
                )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error listando %s (puede no existir): %s",
            LOG_PREFIX,
            _USER_EMERGENCY_CONTACTS,
            e,
        )

    # healthData: documentos con id autogenerado (listar y borrar todos)
    try:
        health_path = f"{base}/{FirestoreCollections.USER_HEALTH_DATA}"
        doc_ids = helper.list_document_ids(health_path)
        for doc_id in doc_ids:
            try:
                helper.delete_document(health_path, doc_id)
                LOG.info(
                    "%s delete_competitor_user_resources: %s/%s eliminado",
                    LOG_PREFIX,
                    FirestoreCollections.USER_HEALTH_DATA,
                    doc_id,
                )
            except Exception as e:
                LOG.warning(
                    "%s delete_competitor_user_resources: error eliminando %s/%s: %s",
                    LOG_PREFIX,
                    FirestoreCollections.USER_HEALTH_DATA,
                    doc_id,
                    e,
                )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error listando healthData (puede no existir): %s",
            LOG_PREFIX,
            e,
        )

    # personalData: documentos con id autogenerado (listar y borrar todos)
    try:
        personal_path = f"{base}/{FirestoreCollections.USER_PERSONAL_DATA}"
        doc_ids = helper.list_document_ids(personal_path)
        for doc_id in doc_ids:
            try:
                helper.delete_document(personal_path, doc_id)
                LOG.info(
                    "%s delete_competitor_user_resources: %s/%s eliminado",
                    LOG_PREFIX,
                    FirestoreCollections.USER_PERSONAL_DATA,
                    doc_id,
                )
            except Exception as e:
                LOG.warning(
                    "%s delete_competitor_user_resources: error eliminando %s/%s: %s",
                    LOG_PREFIX,
                    FirestoreCollections.USER_PERSONAL_DATA,
                    doc_id,
                    e,
                )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error listando personalData (puede no existir): %s",
            LOG_PREFIX,
            e,
        )


def delete_competitor_user_resources(
    helper: FirestoreHelper,
    user_id: str,
    event_id: str,
) -> None:
    """
    Elimina todo lo creado por create_competitor_user para un userId y eventId.

    Orden (inverso al de creación): participante -> membership -> subcolecciones
    (vehicles, emergencyContacts, healthData, personalData) -> usuario.
    Si algún documento no existe, se registra y se continúa con el resto.
    """
    # 1. Participante en events/{eventId}/participants/{userId}
    try:
        collection_path = _get_collection_path(event_id)
        helper.delete_document(collection_path, user_id)
        LOG.info(
            "%s delete_competitor_user_resources: participante eliminado %s en evento %s",
            LOG_PREFIX,
            user_id,
            event_id,
        )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error eliminando participante: %s",
            LOG_PREFIX,
            e,
        )

    # 2. Membership users/{userId}/membership/{eventId}
    try:
        membership_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{FirestoreCollections.USER_MEMBERSHIP}"
        )
        helper.delete_document(membership_path, event_id)
        LOG.info(
            "%s delete_competitor_user_resources: membership eliminado %s/%s",
            LOG_PREFIX,
            user_id,
            event_id,
        )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error eliminando membership: %s",
            LOG_PREFIX,
            e,
        )

    # 3. Subcolecciones del usuario: emergencyContacts, healthData, personalData
    # Si no existen o fallan, se registra y se continúa
    try:
        _delete_user_subcollections(helper, user_id)
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error en subcolecciones (continuando): %s",
            LOG_PREFIX,
            e,
        )

    # 4. Documento usuario en users/{userId}
    try:
        helper.delete_document(FirestoreCollections.USERS, user_id)
        LOG.info(
            "%s delete_competitor_user_resources: usuario eliminado %s",
            LOG_PREFIX,
            user_id,
        )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_user_resources: error eliminando usuario: %s",
            LOG_PREFIX,
            e,
        )


@https_fn.on_request()
def delete_competitor_user(req: https_fn.Request) -> https_fn.Response:
    """
    Elimina el usuario competidor creado con create_competitor_user y sus datos asociados.

    Borra en orden: participante, membership, subcolecciones (emergencyContacts,
    healthData, personalData) y documento users.

    Requiere Bearer token.

    Método: DELETE
    Body (JSON): se puede identificar al usuario por userId o por email (al menos uno requerido):
      - "userId": "<id>" (opcional si se envía email)
      - "email": "<email>" (opcional si se envía userId)
      - "eventId": "<id>" (requerido)
    También se aceptan user_id, event_id como nombres de campo.

    Returns:
    - 204: No Content (eliminado correctamente)
    - 400: Bad Request (body inválido, faltan eventId o faltan userId y email)
    - 401: Unauthorized
    - 404: Usuario no encontrado
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["DELETE"], "delete_competitor_user", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "delete_competitor_user"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            request_data = req.get_json(silent=True)
        except (ValueError, TypeError):
            request_data = None

        if not request_data or not isinstance(request_data, dict):
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_id = request_data.get("userId") or request_data.get("user_id")
        email = request_data.get("email")
        event_id = request_data.get("eventId") or request_data.get("event_id")

        if not event_id:
            LOG.warning(
                "%s delete_competitor_user: falta eventId en el body",
                LOG_PREFIX,
            )
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not user_id and not email:
            LOG.warning(
                "%s delete_competitor_user: debe enviarse userId o email en el body",
                LOG_PREFIX,
            )
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()

        # Si no hay userId pero sí email, buscar usuario por email
        if not user_id and email:
            results = helper.query_documents(
                FirestoreCollections.USERS,
                filters=[{"field": "email", "operator": "==", "value": email}],
                limit=1,
            )
            if not results:
                LOG.warning(
                    "%s delete_competitor_user: no existe usuario con email %s",
                    LOG_PREFIX,
                    email,
                )
                return https_fn.Response(
                    "",
                    status=404,
                    headers={"Access-Control-Allow-Origin": "*"},
                )
            user_id = results[0][0]  # (document_id, data)

        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            LOG.warning(
                "%s delete_competitor_user: usuario no encontrado %s",
                LOG_PREFIX,
                user_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        delete_competitor_user_resources(helper, user_id, event_id)

        return https_fn.Response(
            "",
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error(
            "%s delete_competitor_user error: %s", LOG_PREFIX, e, exc_info=True
        )
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
