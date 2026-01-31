"""
Create User - Crear usuario en colección users

Recibe un cuerpo JSON con la estructura UserDocument (personalData, emergencyContact,
userData, eventStaffRelations, authUserId, createdAt, updatedAt, isActive).
Todos los campos son opcionales. Requiere Bearer token.
Crea un nuevo documento en la colección users (Firestore genera el ID).
"""

import json
import logging
from typing import Any, Dict

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_user]"

# Claves de primer nivel permitidas (UserDocument). Todos opcionales.
_ALLOWED_TOP_KEYS = frozenset(
    {
        "authUserId",
        "avatarUrl",
        "createdAt",
        "emergencyContact",
        "eventStaffRelations",
        "isActive",
        "personalData",
        "updatedAt",
        "userData",
    }
)


def _build_user_dict(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construye el diccionario para el documento en Firestore:
    solo incluye claves permitidas que estén presentes en body.
    Acepta avatarUrl o avatarUrl (se guarda siempre como avatarUrl).
    """
    if not body or not isinstance(body, dict):
        return {}
    result = {k: v for k, v in body.items() if k in _ALLOWED_TOP_KEYS}
    # Asegurar avatarUrl en el documento: aceptar avatarUrl o avatarUrl del body
    avatar = body.get("avatarUrl") if "avatarUrl" in body else body.get("avatarUrl")
    if avatar is not None or "avatarUrl" in body or "avatarUrl" in body:
        result["avatarUrl"] = avatar
    return result


@https_fn.on_request()
def create_user(req: https_fn.Request) -> https_fn.Response:
    """
    Crea un nuevo documento de usuario en la colección users.
    Acepta el body con estructura UserDocument. Todos los campos son opcionales. Requiere Bearer token.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Request Body (JSON, UserDocument, todos los campos opcionales):
    - personalData: { fullName, email, phone }
    - emergencyContact: { fullName, phone }
    - userData: { username }
    - eventStaffRelations: [ { eventId, role (organizador|staff), assignedAt, checkpointIds: [] } ]
    - authUserId: string
    - avatarUrl: string | null (URL del avatar)
    - createdAt: string (ISO 8601)
    - updatedAt: string (ISO 8601)
    - isActive: boolean

    Returns:
    - 201: JSON con el id del nuevo documento: {"id": "<document_id>"}
    - 400: Bad Request - body inválido
    - 401: Unauthorized - token inválido o faltante
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["POST"], "create_user", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "create_user"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            request_data = req.get_json(silent=True)
        except (ValueError, TypeError) as e:
            logging.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if request_data is None:
            logging.warning("%s Request body inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_data = _build_user_dict(request_data)

        db = firestore.client()
        users_ref = db.collection(FirestoreCollections.USERS)
        new_doc_ref = users_ref.document()
        new_doc_ref.set(user_data)

        new_id = new_doc_ref.id
        logging.info("%s Usuario creado correctamente: %s", LOG_PREFIX, new_id)

        return https_fn.Response(
            json.dumps({"id": new_id}, ensure_ascii=False),
            status=201,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("%s Error de validación: %s", LOG_PREFIX, e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
