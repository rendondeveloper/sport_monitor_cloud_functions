"""
Create Competitor User - Crear template de usuario competidor y participante en el evento (sin Firebase Auth)

Flujo en una sola llamada:
1. Crea documento en colección 'users' (campos raíz: email, userData, isActive, etc.).
2.1. Crea subcolección users/{userId}/personalData (documento con id autogenerado).
2.2. Crea subcolección users/{userId}/healthData (documento con id autogenerado).
2.3. Crea subcolección users/{userId}/emergencyContact (un doc por contacto, id autogenerado; map).
2.4. Si hay vehicleData: documento en users/{userId}/vehicles (id autogenerado; branch, year, model, color).
3. Crea subcolección users/{userId}/membership/{eventId}.
4. Crea participante en events/{eventId}/participants con el mismo userId como id.

Rollback automático si falla cualquier paso (incluye borrado de subcolecciones). Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, Optional

# Reutilizar lógica de create_competitor para el participante en el evento
from competitors.create_competitor import (
    _build_competitor_document,
    _check_duplicate_competitor,
    _get_collection_path,
    _validate_event_exists,
)
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.validation_helper import (
    validate_email,
    validate_phone,
    validate_required_fields,
)

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_competitor_user]"

# Campos de primer nivel requeridos en el request body (sin password: no se crea Auth)
_REQUIRED_TOP_FIELDS = [
    "personalData",
    "emergencyContacts",
    "username",
    "email",
    "competition",
]

_REQUIRED_PERSONAL_DATA_FIELDS = ["fullName", "phone"]

# Nombres de subcolecciones (fallback si no existen en FirestoreCollections)
_USER_PERSONAL_DATA = getattr(
    FirestoreCollections, "USER_PERSONAL_DATA", "personalData"
)
_USER_HEALTH_DATA = getattr(
    FirestoreCollections, "USER_HEALTH_DATA", "healthData"
)
_USER_EMERGENCY_CONTACT = getattr(
    FirestoreCollections, "USER_EMERGENCY_CONTACT", "emergencyContacts"
)


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

    # Validar email (a nivel raíz, misma altura que username)
    email = request_data.get("email", "")
    if not validate_email(email):
        return "Formato de email inválido"

    # Validar teléfono
    if not validate_phone(personal_data.get("phone", "")):
        return "Formato de teléfono inválido"

    # Validar username
    username = request_data.get("username", "")
    if len(username) < 4:
        return "El username debe tener al menos 4 caracteres"

    # Validar emergencyContacts: debe ser una lista con al menos un contacto
    emergency_contacts = request_data.get("emergencyContacts")
    if not isinstance(emergency_contacts, list):
        return "emergencyContacts debe ser una lista"
    if len(emergency_contacts) < 1:
        return "emergencyContacts debe tener al menos un contacto"
    for i, contact in enumerate(emergency_contacts):
        if not isinstance(contact, dict):
            return f"emergencyContacts[{i}] debe ser un objeto"
        if not contact.get("fullName") or not contact.get("phone"):
            return f"emergencyContacts[{i}]: fullName y phone son requeridos"

    # Validar competition (debe ser objeto y contener eventId)
    comp = request_data.get("competition", {})
    if not isinstance(comp, dict):
        return "competition debe ser un objeto"
    if not comp.get("eventId"):
        return "competition.eventId es requerido"

    return None


def _validate_unique_email(helper: FirestoreHelper, email: str) -> bool:
    """Verifica si el email ya está registrado. Retorna True si existe."""
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "email", "operator": "==", "value": email}],
    )
    return len(results) > 0


def _validate_unique_username(helper: FirestoreHelper, username: str) -> bool:
    """Verifica si el username ya está en uso. Retorna True si existe."""
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "username", "operator": "==", "value": username}],
    )
    return len(results) > 0


def _build_user_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construye el documento raíz del usuario (solo campos de nivel superior).
    email y username a la misma altura. personalData, healthData, emergencyContact
    y vehicles van en subcolecciones con ids autogenerados.
    """
    now = get_current_timestamp()

    return {
        "email": request_data.get("email", ""),
        "username": request_data.get("username", ""),
        "authUserId": None,
        "avatarUrl": None,
        "isActive": False,
        "createdAt": now,
        "updatedAt": now,
    }


def _build_vehicle_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construye el documento de vehículo para users/{userId}/vehicles.
    El id se genera automáticamente al crear el documento.
    Campos: branch, year, model, color, createdAt, updatedAt.
    """
    now = get_current_timestamp()
    v = request_data.get("vehicleData") or {}
    if not isinstance(v, dict):
        v = {}
    # Aceptar "branch" o "brand" en el request; guardar como "branch"
    branch = v.get("branch") or v.get("brand", "")
    return {
        "branch": branch,
        "year": v.get("year"),
        "model": v.get("model", ""),
        "color": v.get("color", ""),
        "createdAt": now,
        "updatedAt": now,
    }


def _build_personal_data_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Documento para subcolección users/{userId}/personalData (id autogenerado; email en raíz del usuario)."""
    now = get_current_timestamp()
    personal_data = request_data.get("personalData", {})
    return {
        "fullName": personal_data.get("fullName", ""),
        "phone": personal_data.get("phone", ""),
        "dateOfBirth": personal_data.get("dateOfBirth"),
        "address": personal_data.get("address", ""),
        "city": personal_data.get("city", ""),
        "state": personal_data.get("state", ""),
        "country": personal_data.get("country", ""),
        "postalCode": personal_data.get("postalCode", ""),
        "createdAt": now,
        "updatedAt": now,
    }


def _build_health_data_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Documento para subcolección users/{userId}/healthData (id autogenerado)."""
    now = get_current_timestamp()
    health_data = request_data.get("healthData", {})
    return {
        "bloodType": health_data.get("bloodType", ""),
        "allergies": health_data.get("allergies", ""),
        "medications": health_data.get("medications", ""),
        "medicalConditions": health_data.get("medicalConditions", ""),
        "insuranceProvider": health_data.get("insuranceProvider", ""),
        "insuranceNumber": health_data.get("insuranceNumber", ""),
        "createdAt": now,
        "updatedAt": now,
    }


def _build_emergency_contact_document(contact: Dict[str, Any]) -> Dict[str, Any]:
    """Documento para un contacto en users/{userId}/emergencyContact/{docId}."""
    now = get_current_timestamp()
    return {
        "fullName": contact.get("fullName", ""),
        "relationship": contact.get("relationship", ""),
        "phone": contact.get("phone", ""),
        "createdAt": now,
        "updatedAt": now,
    }


def _build_membership_document(
    user_id: str,
    request_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Construye el documento de membership para relacionar usuario con evento.
    Ruta: users/{userId}/membership/{eventId}
    """
    now = get_current_timestamp()
    comp = request_data.get("competition", {})

    return {
        "userId": user_id,
        "eventId": comp.get("eventId", ""),
        "createdAt": now,
        "updatedAt": now,
    }


def _rollback_user_subcollections(
    helper: FirestoreHelper,
    user_id: str,
    created_personal_data_id: Optional[str] = None,
    created_health_data_id: Optional[str] = None,
    created_emergency_contact_ids: Optional[list] = None,
    created_vehicle_id: Optional[str] = None,
) -> None:
    """Elimina por id los documentos creados en subcolecciones (todos con id autogenerado)."""
    if not user_id:
        return
    base = f"{FirestoreCollections.USERS}/{user_id}"
    created_emergency_contact_ids = created_emergency_contact_ids or []

    # vehicles
    if created_vehicle_id:
        try:
            path = f"{base}/{FirestoreCollections.USER_VEHICLES}"
            helper.delete_document(path, created_vehicle_id)
            LOG.info("%s Rollback: vehicles/%s eliminado", LOG_PREFIX, created_vehicle_id)
        except Exception:
            LOG.warning(
                "%s Rollback: error eliminando vehicles/%s", LOG_PREFIX, created_vehicle_id
            )

    # emergencyContact (ids autogenerados)
    path_ec = f"{base}/{_USER_EMERGENCY_CONTACT}"
    for doc_id in created_emergency_contact_ids:
        try:
            helper.delete_document(path_ec, doc_id)
            LOG.info("%s Rollback: emergencyContact/%s eliminado", LOG_PREFIX, doc_id)
        except Exception:
            LOG.warning(
                "%s Rollback: error eliminando emergencyContact/%s", LOG_PREFIX, doc_id
            )

    # healthData (id autogenerado)
    if created_health_data_id:
        try:
            path = f"{base}/{_USER_HEALTH_DATA}"
            helper.delete_document(path, created_health_data_id)
            LOG.info("%s Rollback: healthData/%s eliminado", LOG_PREFIX, created_health_data_id)
        except Exception:
            LOG.warning("%s Rollback: error eliminando healthData", LOG_PREFIX)

    # personalData (id autogenerado)
    if created_personal_data_id:
        try:
            path = f"{base}/{_USER_PERSONAL_DATA}"
            helper.delete_document(path, created_personal_data_id)
            LOG.info("%s Rollback: personalData/%s eliminado", LOG_PREFIX, created_personal_data_id)
        except Exception:
            LOG.warning("%s Rollback: error eliminando personalData", LOG_PREFIX)


def _rollback_user_creation(
    helper: FirestoreHelper,
    user_id: Optional[str],
    event_id: Optional[str] = None,
    rollback_subcollections: bool = True,
    created_personal_data_id: Optional[str] = None,
    created_health_data_id: Optional[str] = None,
    created_emergency_contact_ids: Optional[list] = None,
    created_vehicle_id: Optional[str] = None,
) -> None:
    """
    Rollback: elimina membership (si event_id), subcolecciones del usuario
    (vehicles, emergencyContact, healthData, personalData por id) y luego el documento users.
    """
    if user_id and event_id:
        try:
            membership_path = (
                f"{FirestoreCollections.USERS}/{user_id}"
                f"/{FirestoreCollections.USER_MEMBERSHIP}"
            )
            helper.delete_document(membership_path, event_id)
            LOG.info(
                "%s Rollback: membership eliminado %s/%s", LOG_PREFIX, user_id, event_id
            )
        except Exception:
            LOG.warning("%s Rollback: error eliminando membership", LOG_PREFIX)
    if user_id and rollback_subcollections:
        _rollback_user_subcollections(
            helper,
            user_id,
            created_personal_data_id=created_personal_data_id,
            created_health_data_id=created_health_data_id,
            created_emergency_contact_ids=created_emergency_contact_ids,
            created_vehicle_id=created_vehicle_id,
        )
    if user_id:
        try:
            helper.delete_document(FirestoreCollections.USERS, user_id)
            LOG.info("%s Rollback: usuario eliminado %s", LOG_PREFIX, user_id)
        except Exception:
            LOG.warning("%s Rollback: error eliminando usuario %s", LOG_PREFIX, user_id)


# ============================================================================
# ENDPOINT PRINCIPAL
# ============================================================================


@https_fn.on_request()
def create_competitor_user(req: https_fn.Request) -> https_fn.Response:
    """
    Crea en una sola llamada: template de usuario (users), membership y participante en el evento.

    Flujo:
    1) Documento en users (campos raíz: email, username, isActive, etc.; sin userData).
    2.1) Subcolección users/{userId}/personalData (id autogenerado).
    2.2) Subcolección users/{userId}/healthData (id autogenerado).
    2.3) Subcolección users/{userId}/emergencyContact (map: un doc por contacto, id autogenerado).
    2.4) Si hay vehicleData: documento en users/{userId}/vehicles (id autogenerado; branch, year, model, color).
    3) Subcolección users/{userId}/membership/{eventId}.
    4) Participante en events/{eventId}/participants con id = userId.

    Si falla cualquier paso se hace rollback. Requiere Bearer token.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Request Body (JSON):
    - personalData: object (requerido) - fullName, phone, dateOfBirth, address, ... (email va a nivel raíz)
    - healthData: object (opcional) - bloodType, allergies, medications, ...
    - emergencyContacts: array (requerido) - al menos un elemento; cada uno: fullName, phone, relationship (opcional)
    - vehicleData: object (opcional) - se guarda en users/{userId}/vehicles con id autogenerado; campos: branch (o brand), year, model, color
    - username: string (requerido) - mínimo 4 caracteres
    - competition: object (requerido) - eventId, pilotNumber, registrationCategory, team
    - registrationDate: string (opcional) - Fecha ISO 8601
    - team: string (opcional) - Nombre del equipo

    Returns:
    - 201: {"id": "<userId>", "membershipId": "<eventId>"} (usuario + participante creados)
    - 400: Bad Request
    - 401: Unauthorized
    - 404: Evento no encontrado
    - 409: Conflict (email/username duplicado, o piloto duplicado en evento)
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["POST"], "create_competitor_user", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "create_competitor_user"):
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
        email = request_data.get("email", "")
        username = request_data.get("username", "")

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

        user_id = None

        # PASO 1: Crear documento template en colección users (isActive: false, sin Auth)
        user_doc = _build_user_document(request_data)
        try:
            user_id = helper.create_document(FirestoreCollections.USERS, user_doc)
        except Exception:
            raise

        event_id = request_data.get("competition", {}).get("eventId", "")
        emergency_contacts = request_data.get("emergencyContacts") or []
        if not isinstance(emergency_contacts, list):
            emergency_contacts = []

        created_personal_data_id = None
        created_health_data_id = None
        created_emergency_contact_ids = []

        # PASO 2.1: Subcolección personalData (documento con id autogenerado)
        personal_data_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{_USER_PERSONAL_DATA}"
        )
        try:
            personal_data_doc = _build_personal_data_document(request_data)
            created_personal_data_id = helper.create_document(
                personal_data_path, personal_data_doc
            )
        except Exception:
            _rollback_user_creation(
                helper,
                user_id,
                None,
                rollback_subcollections=True,
                created_personal_data_id=None,
                created_health_data_id=None,
                created_emergency_contact_ids=[],
                created_vehicle_id=None,
            )
            raise

        # PASO 2.2: Subcolección healthData (documento con id autogenerado)
        health_data_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{_USER_HEALTH_DATA}"
        )
        try:
            health_data_doc = _build_health_data_document(request_data)
            created_health_data_id = helper.create_document(
                health_data_path, health_data_doc
            )
        except Exception:
            _rollback_user_creation(
                helper,
                user_id,
                None,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=None,
                created_emergency_contact_ids=[],
                created_vehicle_id=None,
            )
            raise

        # PASO 2.3: Subcolección emergencyContact (un documento por contacto, id autogenerado)
        emergency_contact_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{_USER_EMERGENCY_CONTACT}"
        )
        try:
            for contact in emergency_contacts:
                contact_doc = _build_emergency_contact_document(
                    contact if isinstance(contact, dict) else {}
                )
                doc_id = helper.create_document(emergency_contact_path, contact_doc)
                created_emergency_contact_ids.append(doc_id)
        except Exception:
            _rollback_user_creation(
                helper,
                user_id,
                None,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=None,
            )
            raise

        # PASO 2.4: Subcolección users/{userId}/vehicles (un documento si hay vehicleData; id autogenerado)
        created_vehicle_id = None
        vehicle_data = request_data.get("vehicleData")
        if vehicle_data and isinstance(vehicle_data, dict):
            vehicles_path = (
                f"{FirestoreCollections.USERS}/{user_id}"
                f"/{FirestoreCollections.USER_VEHICLES}"
            )
            try:
                vehicle_doc = _build_vehicle_document(request_data)
                created_vehicle_id = helper.create_document(vehicles_path, vehicle_doc)
            except Exception:
                _rollback_user_creation(
                    helper,
                    user_id,
                    None,
                    rollback_subcollections=True,
                    created_personal_data_id=created_personal_data_id,
                    created_health_data_id=created_health_data_id,
                    created_emergency_contact_ids=created_emergency_contact_ids,
                    created_vehicle_id=None,
                )
                raise

        # PASO 3: Subcolección membership
        membership_doc = _build_membership_document(user_id, request_data)
        membership_path = (
            f"{FirestoreCollections.USERS}/{user_id}"
            f"/{FirestoreCollections.USER_MEMBERSHIP}"
        )
        try:
            helper.create_document_with_id(membership_path, event_id, membership_doc)
        except Exception:
            _rollback_user_creation(
                helper,
                user_id,
                event_id,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=created_vehicle_id,
            )
            raise

        # PASO 4: Crear participante en events/{eventId}/participants (mismo id que users)
        collection_path = _get_collection_path(event_id)
        if not _validate_event_exists(helper, event_id):
            LOG.warning("%s Evento no encontrado: %s", LOG_PREFIX, event_id)
            _rollback_user_creation(
                helper,
                user_id,
                event_id,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=created_vehicle_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        existing_participant = helper.get_document(collection_path, user_id)
        if existing_participant is not None:
            LOG.warning(
                "%s Ya existe participante userId=%s en evento %s",
                LOG_PREFIX,
                user_id,
                event_id,
            )
            _rollback_user_creation(
                helper,
                user_id,
                event_id,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=created_vehicle_id,
            )
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        competition = request_data.get("competition", {})
        pilot_number = competition.get("pilotNumber", "")
        if pilot_number and _check_duplicate_competitor(helper, event_id, pilot_number):
            LOG.warning(
                "%s Número de piloto duplicado: %s en evento %s",
                LOG_PREFIX,
                pilot_number,
                event_id,
            )
            _rollback_user_creation(
                helper,
                user_id,
                event_id,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=created_vehicle_id,
            )
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            competitor_doc = _build_competitor_document(request_data, user_id)
            helper.create_document_with_id(collection_path, user_id, competitor_doc)
        except Exception:
            _rollback_user_creation(
                helper,
                user_id,
                event_id,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=created_vehicle_id,
            )
            raise

        LOG.info(
            "%s Usuario competidor y participante creados: userId=%s eventId=%s",
            LOG_PREFIX,
            user_id,
            event_id,
        )

        return https_fn.Response(
            json.dumps(
                {
                    "id": user_id,
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
