"""
Create Staff User - Crear usuario staff completo

Crea el usuario en Firebase Auth, el documento en la colección 'users' con
datos personales y contacto de emergencia (sin healthData ni vehicleData),
y la subcolección 'membership' para relacionarlo con eventos.

Flujo transaccional de 3 pasos con rollback automático.
Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, Optional

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.auth_helper import create_firebase_auth_user, delete_firebase_auth_user
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.validation_helper import (
    validate_email,
    validate_password,
    validate_phone,
    validate_required_fields,
)

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_staff_user]"

# Roles válidos de staff
_VALID_ROLES = {"organizador", "staff", "checkpoint"}

# Campos requeridos
_REQUIRED_TOP_FIELDS = [
    "personalData",
    "emergencyContact",
    "username",
    "password",
    "confirmPassword",
    "eventId",
    "role",
]

_REQUIRED_PERSONAL_DATA_FIELDS = ["fullName", "email", "phone"]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _validate_request_data(request_data: Dict[str, Any]) -> Optional[str]:
    """
    Valida todos los campos del request body.

    Returns:
        None si todo es válido, string con descripción del error si falla.
    """
    # Campos de primer nivel
    is_valid, msg = validate_required_fields(request_data, _REQUIRED_TOP_FIELDS)
    if not is_valid:
        return msg

    # Datos personales
    personal_data = request_data.get("personalData", {})
    is_valid, msg = validate_required_fields(
        personal_data, _REQUIRED_PERSONAL_DATA_FIELDS
    )
    if not is_valid:
        return f"personalData: {msg}"

    # Validar email
    if not validate_email(personal_data.get("email", "")):
        return "Formato de email inválido"

    # Validar teléfono
    if not validate_phone(personal_data.get("phone", "")):
        return "Formato de teléfono inválido"

    # Validar contraseña
    is_valid, msg = validate_password(request_data.get("password", ""))
    if not is_valid:
        return msg

    # Validar que las contraseñas coincidan
    if request_data.get("password") != request_data.get("confirmPassword"):
        return "Las contraseñas no coinciden"

    # Validar username
    username = request_data.get("username", "")
    if len(username) < 4:
        return "El username debe tener al menos 4 caracteres"

    # Validar contacto de emergencia
    ec = request_data.get("emergencyContact", {})
    if not ec.get("fullName") or not ec.get("phone"):
        return "emergencyContact: fullName y phone son requeridos"

    # Validar rol
    role = request_data.get("role", "")
    if role not in _VALID_ROLES:
        return f"Rol inválido: {role}. Valores permitidos: {_VALID_ROLES}"

    # Si el rol es checkpoint, checkpointId es requerido
    if role == "checkpoint":
        checkpoint_id = request_data.get("checkpointId", "")
        if not checkpoint_id or not isinstance(checkpoint_id, str):
            return "checkpointId es requerido para rol checkpoint"

    return None


def _validate_unique_email(helper: FirestoreHelper, email: str) -> bool:
    """Verifica si el email ya está registrado. Retorna True si existe."""
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[
            {"field": "personalData.email", "operator": "==", "value": email}
        ],
    )
    return len(results) > 0


def _validate_unique_username(helper: FirestoreHelper, username: str) -> bool:
    """Verifica si el username ya está en uso. Retorna True si existe."""
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[
            {"field": "userData.username", "operator": "==", "value": username}
        ],
    )
    return len(results) > 0


def _build_user_document(
    request_data: Dict[str, Any],
    auth_user_id: str,
) -> Dict[str, Any]:
    """
    Construye documento de usuario staff (SIN eventStaffRelations).
    Staff no tiene healthData ni vehicleData.
    """
    now = get_current_timestamp()
    personal_data = request_data.get("personalData", {})
    ec = request_data.get("emergencyContact", {})

    return {
        "personalData": {
            "fullName": personal_data.get("fullName", ""),
            "email": personal_data.get("email", ""),
            "phone": personal_data.get("phone", ""),
        },
        "emergencyContact": {
            "fullName": ec.get("fullName", ""),
            "phone": ec.get("phone", ""),
        },
        "userData": {
            "username": request_data.get("username", ""),
        },
        "authUserId": auth_user_id,
        "avatarUrl": None,
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }


def _build_membership_document(
    user_id: str,
    request_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Construye documento de membership para staff.
    Ruta: users/{userId}/membership/{eventId}
    """
    now = get_current_timestamp()
    checkpoint_id = request_data.get("checkpointId", "")

    return {
        "userId": user_id,
        "eventId": request_data.get("eventId", ""),
        "role": request_data.get("role", ""),
        "checkpointIds": [checkpoint_id] if checkpoint_id else [],
        "assignedAt": now,
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }


def _rollback_user_creation(
    helper: FirestoreHelper,
    user_id: Optional[str],
    auth_user_id: Optional[str],
) -> None:
    """Realiza rollback eliminando recursos creados en caso de error."""
    if user_id:
        try:
            helper.delete_document(FirestoreCollections.USERS, user_id)
            LOG.info("%s Rollback: usuario eliminado %s", LOG_PREFIX, user_id)
        except Exception:
            LOG.warning("%s Rollback: error eliminando usuario %s", LOG_PREFIX, user_id)

    if auth_user_id:
        delete_firebase_auth_user(auth_user_id)


# ============================================================================
# ENDPOINT PRINCIPAL
# ============================================================================


@https_fn.on_request()
def create_staff_user(req: https_fn.Request) -> https_fn.Response:
    """
    Crea un usuario staff completo.

    Flujo transaccional (3 pasos):
    1. Crear usuario en Firebase Auth
    2. Crear documento en colección users (SIN eventStaffRelations)
    3. Crear subcolección membership/{eventId}

    Rollback automático si cualquier paso falla.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Request Body (JSON):
    - personalData: object (requerido) - fullName, email, phone
    - emergencyContact: object (requerido) - fullName, phone
    - username: string (requerido) - mínimo 4 caracteres
    - password: string (requerido) - mínimo 8 chars, 1 letra, 1 número
    - confirmPassword: string (requerido) - debe coincidir con password
    - eventId: string (requerido) - ID del evento
    - role: string (requerido) - "organizador" | "staff" | "checkpoint"
    - checkpointId: string (requerido si role=checkpoint) - ID del checkpoint

    Returns:
    - 201: {"id": "...", "authUserId": "...", "membershipId": "..."}
    - 400: Bad Request
    - 401: Unauthorized
    - 409: Conflict (email o username duplicado)
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["POST"], "create_staff_user", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "create_staff_user"):
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

        # Validar campos del request
        validation_error = _validate_request_data(request_data)
        if validation_error:
            LOG.warning("%s Validación fallida: %s", LOG_PREFIX, validation_error)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()
        email = request_data["personalData"]["email"]
        username = request_data["username"]

        # Validar unicidad de email
        if _validate_unique_email(helper, email):
            LOG.warning("%s Email duplicado: %s", LOG_PREFIX, email)
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Validar unicidad de username
        if _validate_unique_username(helper, username):
            LOG.warning("%s Username duplicado: %s", LOG_PREFIX, username)
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        auth_user_id = None
        user_id = None

        # PASO 1: Crear en Firebase Auth
        auth_user_id = create_firebase_auth_user(email, request_data["password"])

        # PASO 2: Crear en colección users
        user_doc = _build_user_document(request_data, auth_user_id)
        try:
            user_id = helper.create_document(FirestoreCollections.USERS, user_doc)
        except Exception:
            _rollback_user_creation(helper, None, auth_user_id)
            raise

        # PASO 3: Crear membership
        event_id = request_data["eventId"]
        membership_doc = _build_membership_document(user_id, request_data)
        membership_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{FirestoreCollections.USER_MEMBERSHIP}"
        )
        try:
            helper.create_document_with_id(membership_path, event_id, membership_doc)
        except Exception:
            _rollback_user_creation(helper, user_id, auth_user_id)
            raise

        LOG.info(
            "%s Usuario staff creado: userId=%s authUserId=%s eventId=%s role=%s",
            LOG_PREFIX,
            user_id,
            auth_user_id,
            event_id,
            request_data.get("role"),
        )

        return https_fn.Response(
            json.dumps(
                {
                    "id": user_id,
                    "authUserId": auth_user_id,
                    "membershipId": event_id,
                },
                ensure_ascii=False,
            ),
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
