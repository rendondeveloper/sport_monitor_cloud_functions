"""
Delete Competitor - Eliminar solo el participante del evento (no el usuario)

Elimina el documento del competidor en events/{eventId}/participants/{userId}
y opcionalmente el membership en users/{userId}/membership/{eventId}.
No elimina el documento users ni sus subcolecciones (vehicles, healthData, etc.).
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
LOG_PREFIX = "[delete_competitor]"


def delete_competitor_resources(
    helper: FirestoreHelper,
    user_id: str,
    event_id: str,
) -> None:
    """
    Elimina solo el participante del evento y el membership.
    No toca el documento users ni sus subcolecciones.
    """
    # 1. Participante en events/{eventId}/participants/{userId}
    # Sin try/except: si falla, la excepción se propaga y el handler devuelve 500.
    collection_path = _get_collection_path(event_id)
    helper.delete_document(collection_path, user_id)
    LOG.info(
        "%s delete_competitor_resources: participante eliminado %s en evento %s",
        LOG_PREFIX,
        user_id,
        event_id,
    )

    # 2. Membership users/{userId}/membership/{eventId}
    # Con try/except: si falla, se registra y se continúa (participante ya eliminado).
    try:
        membership_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{FirestoreCollections.USER_MEMBERSHIP}"
        )
        helper.delete_document(membership_path, event_id)
        LOG.info(
            "%s delete_competitor_resources: membership eliminado %s/%s",
            LOG_PREFIX,
            user_id,
            event_id,
        )
    except Exception as e:
        LOG.warning(
            "%s delete_competitor_resources: error eliminando membership (continuando): %s",
            LOG_PREFIX,
            e,
        )


@https_fn.on_request(region="us-east4")
def delete_competitor(req: https_fn.Request) -> https_fn.Response:
    """
    Elimina solo el participante del evento (y su membership).
    No elimina el usuario ni sus datos en users.

    Requiere Bearer token.

    Método: DELETE
    Body (JSON):
      - "eventId": "<id>" (requerido)
      - "userId": "<id>" o "email": "<email>" (al menos uno requerido)
    También se aceptan event_id, user_id.

    Returns:
    - 204: No Content (eliminado correctamente)
    - 400: Bad Request (body inválido, faltan eventId o userId/email)
    - 401: Unauthorized
    - 404: Usuario no encontrado
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["DELETE"], "delete_competitor", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "delete_competitor"):
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
            LOG.warning("%s delete_competitor: falta eventId en el body", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not user_id and not email:
            LOG.warning(
                "%s delete_competitor: debe enviarse userId o email en el body",
                LOG_PREFIX,
            )
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()

        if not user_id and email:
            results = helper.query_documents(
                FirestoreCollections.USERS,
                filters=[{"field": "email", "operator": "==", "value": email}],
                limit=1,
            )
            if not results:
                LOG.warning(
                    "%s delete_competitor: no existe usuario con email %s",
                    LOG_PREFIX,
                    email,
                )
                return https_fn.Response(
                    "",
                    status=404,
                    headers={"Access-Control-Allow-Origin": "*"},
                )
            user_id = results[0][0]

        # Opcional: comprobar que el participante exista (evita 500 por doc inexistente si se desea 404).
        # Firestore delete() sobre documento inexistente no lanza, así que no es obligatorio.
        participant_path = _get_collection_path(event_id)
        participant_doc = helper.get_document(participant_path, user_id)
        if participant_doc is None:
            LOG.warning(
                "%s delete_competitor: participante no encontrado %s en evento %s",
                LOG_PREFIX,
                user_id,
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        delete_competitor_resources(helper, user_id, event_id)

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
            "%s delete_competitor error: %s", LOG_PREFIX, e, exc_info=True
        )
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
