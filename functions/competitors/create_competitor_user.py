"""
Create Competitor User - Crear template de usuario competidor y participante en el evento (sin Firebase Auth)

Flujo en una sola llamada:
1. Crea documento en colección 'users' (campos raíz: email, userData, isActive, etc.).
2.1. Crea subcolección users/{userId}/personalData (documento con id autogenerado).
2.2. Crea subcolección users/{userId}/healthData (documento con id autogenerado).
2.3. Procesa emergencyContacts (array mixto):
     - Contacto con datos completos: crea en users/{userId}/emergencyContacts → {"id": autoId} en evento
     - Contacto solo con {id}: valida existencia en users/ → {"id": id} en evento (400 si no existe)
2.4. Si hay vehicleData: documento en users/{userId}/vehicles (id autogenerado; branch, year, model, color).
3. Crea subcolección users/{userId}/membership/{eventId}.
4. Crea participante en events/{eventId}/participants con el mismo userId como id.

Si el usuario ya existe (mismo email) se ejecuta Flujo B: no se recrea el usuario, solo se registra
en el evento con merge de datos y los mismos contactos (array mixto).

Rollback automático si falla cualquier paso (incluye borrado de subcolecciones y contactos del evento).
Requiere Bearer token.
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

# Único campo requerido a nivel raíz: email. competition se crea con defaults si no existe.
_REQUIRED_TOP_FIELDS = [
    "email",
]

_REQUIRED_COMPETITION_FIELDS = ["eventId"]

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
    Valida el request body. Requerido: email.
    Si competition no existe, se crea con valores por defecto.
    Campos de competition: eventId (requerido); category y number (opcionales).
    source: campo opcional en la raíz del request (ej: "web", "mobile-ios", "mobile-android").
    system: campo opcional en la raíz del request (ej: "rally-app", "backoffice").

    Returns:
        None si todo es válido, string con descripción del error si falla.
    """
    # Campos de primer nivel requeridos
    is_valid, msg = validate_required_fields(request_data, _REQUIRED_TOP_FIELDS)
    if not is_valid:
        return msg

    # Email (formato)
    email = request_data.get("email", "")
    if not validate_email(email):
        return "Formato de email inválido"

    # Competition: crear objeto vacío si no existe
    comp = request_data.get("competition")
    if comp is None:
        request_data["competition"] = {}
        comp = {}
    if not isinstance(comp, dict):
        return "competition debe ser un objeto"
    is_valid, msg = validate_required_fields(comp, _REQUIRED_COMPETITION_FIELDS)
    if not is_valid:
        return f"competition: {msg}"

    # Opcionales: validar solo si están presentes
    personal_data = request_data.get("personalData", {})
    if personal_data is not None and isinstance(personal_data, dict):
        phone = personal_data.get("phone", "")
        if phone and not validate_phone(phone):
            return "personalData.phone: formato de teléfono inválido"

    username = request_data.get("username", "")
    if username and len(username) < 4:
        return "El username debe tener al menos 4 caracteres"

    vehicle_data = request_data.get("vehicleData")
    if vehicle_data is not None:
        if not isinstance(vehicle_data, dict):
            return "vehicleData debe ser un objeto"
        existing_id = vehicle_data.get("id")
        has_data = vehicle_data.get("branch") or vehicle_data.get("brand") or vehicle_data.get("model")
        if not existing_id and not has_data:
            return "vehicleData: debe tener id o datos del vehículo (branch/brand, model)"
        if existing_id and has_data:
            return "vehicleData: no puede tener id y datos al mismo tiempo"
        if existing_id and not isinstance(existing_id, str):
            return "vehicleData.id debe ser un string"

    emergency_contacts = request_data.get("emergencyContacts")
    if emergency_contacts is not None:
        if not isinstance(emergency_contacts, list):
            return "emergencyContacts debe ser una lista"
        for i, contact in enumerate(emergency_contacts):
            if not isinstance(contact, dict):
                return f"emergencyContacts[{i}] debe ser un objeto"
            existing_id = contact.get("id")
            has_data = contact.get("fullName") or contact.get("phone")
            if not existing_id and not has_data:
                return f"emergencyContacts[{i}]: debe tener id o datos completos (fullName y phone)"
            if existing_id and has_data:
                return f"emergencyContacts[{i}]: no puede tener id y datos al mismo tiempo"
            if existing_id and not isinstance(existing_id, str):
                return f"emergencyContacts[{i}].id debe ser un string"
            if has_data:
                if not contact.get("fullName") or not contact.get("phone"):
                    return f"emergencyContacts[{i}]: fullName y phone son requeridos si se envía el contacto"

    return None


def _event_has_categories(helper: FirestoreHelper, event_id: str) -> bool:
    """
    Retorna True si el evento tiene al menos una categoría en
    events/{eventId}/event_categories.
    """
    categories_path = (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_CATEGORIES}"
    )
    categories = helper.query_documents(categories_path, limit=1)
    return len(categories) > 0


def _validate_competition_category_requirement(
    helper: FirestoreHelper,
    request_data: Dict[str, Any],
) -> Optional[https_fn.Response]:
    """
    Valida de forma condicional competition.category:
    - Si el evento no existe -> 404.
    - Si el evento tiene categorías -> category es obligatoria (400 si falta/vacía).
    - Si el evento no tiene categorías -> category puede omitirse o ir vacía.
    """
    competition = request_data.get("competition") or {}
    event_id = (competition.get("eventId") or "").strip()

    # eventId se valida previamente en _validate_request_data, pero proteger por robustez.
    if not event_id:
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    if not _validate_event_exists(helper, event_id):
        LOG.warning("%s Evento no encontrado: %s", LOG_PREFIX, event_id)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    if not _event_has_categories(helper, event_id):
        return None

    category = (competition.get("category") or "").strip()
    if not category:
        LOG.warning(
            "%s competition.category es obligatorio para eventos con categorías: %s",
            LOG_PREFIX,
            event_id,
        )
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

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


def _apply_source_and_system_fields(
    competitor_doc: Dict[str, Any], request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Agrega campos opcionales de tracking de origen en el documento del participante.
    Se persisten exactamente como llegan en el payload raíz:
    - source
    - system
    """
    source = request_data.get("source")
    if source is not None:
        competitor_doc["source"] = source

    system = request_data.get("system")
    if system is not None:
        competitor_doc["system"] = system

    return competitor_doc


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
        "socialSecurityNumber": health_data.get("socialSecurityNumber", ""),
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


def _build_membership_document() -> Dict[str, Any]:
    """
    Construye el documento de membership para relacionar usuario con evento.
    Ruta: users/{userId}/membership/{eventId}
    userId y eventId están implícitos en la ruta del documento.
    """
    now = get_current_timestamp()

    return {
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
    created_event_ec_ids: Optional[list] = None,
    created_event_vehicle_id: Optional[str] = None,
) -> None:
    """
    Rollback: elimina vehículo y emergency contacts del evento, membership, subcolecciones del usuario y el documento users.
    """
    if user_id and event_id and created_event_vehicle_id:
        participant_vehicle_path = (
            f"{FirestoreCollections.EVENTS}/{event_id}"
            f"/{FirestoreCollections.EVENT_PARTICIPANTS}/{user_id}"
            f"/{FirestoreCollections.PARTICIPANT_VEHICLE}"
        )
        try:
            helper.delete_document(participant_vehicle_path, created_event_vehicle_id)
            LOG.info("%s Rollback: event vehicle/%s eliminado", LOG_PREFIX, created_event_vehicle_id)
        except Exception:
            LOG.warning(
                "%s Rollback: error eliminando event vehicle/%s", LOG_PREFIX, created_event_vehicle_id
            )
    if user_id and event_id and created_event_ec_ids:
        participant_ec_path = (
            f"{FirestoreCollections.EVENTS}/{event_id}"
            f"/{FirestoreCollections.EVENT_PARTICIPANTS}/{user_id}"
            f"/{FirestoreCollections.PARTICIPANT_EMERGENCY_CONTACTS}"
        )
        for ec_id in created_event_ec_ids:
            try:
                helper.delete_document(participant_ec_path, ec_id)
                LOG.info("%s Rollback: event emergencyContact/%s eliminado", LOG_PREFIX, ec_id)
            except Exception:
                LOG.warning(
                    "%s Rollback: error eliminando event emergencyContact/%s", LOG_PREFIX, ec_id
                )
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
# FUNCIONES AUXILIARES - FLUJO B (Usuario existente)
# ============================================================================


def _find_existing_user_by_email(
    helper: FirestoreHelper, email: str
) -> Optional[tuple]:
    """
    Busca un usuario existente por email.
    Returns: (user_id, user_data) o None si no existe.
    """
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "email", "operator": "==", "value": email}],
        limit=1,
    )
    if not results:
        return None
    return results[0]


def _merge_update_personal_data(
    helper: FirestoreHelper, user_id: str, request_data: Dict[str, Any]
) -> None:
    """
    Actualiza personalData del usuario con merge: solo reemplaza campos no vacíos/nulos.
    Si no existe el documento, lo crea.
    """
    path = f"{FirestoreCollections.USERS}/{user_id}/{_USER_PERSONAL_DATA}"
    pd = request_data.get("personalData") or {}
    existing_docs = helper.query_documents(path, limit=1)
    if not existing_docs:
        helper.create_document(path, _build_personal_data_document(request_data))
        return
    doc_id, _ = existing_docs[0]
    fields = [
        "fullName", "phone", "dateOfBirth", "address",
        "city", "state", "country", "postalCode",
    ]
    update_fields = {f: pd[f] for f in fields if pd.get(f)}
    if update_fields:
        update_fields["updatedAt"] = get_current_timestamp()
        helper.update_document(path, doc_id, update_fields)


def _merge_update_health_data(
    helper: FirestoreHelper, user_id: str, request_data: Dict[str, Any]
) -> None:
    """
    Actualiza healthData del usuario con merge: solo reemplaza campos no vacíos/nulos.
    Si no existe el documento, lo crea.
    """
    path = f"{FirestoreCollections.USERS}/{user_id}/{_USER_HEALTH_DATA}"
    hd = request_data.get("healthData") or {}
    existing_docs = helper.query_documents(path, limit=1)
    if not existing_docs:
        helper.create_document(path, _build_health_data_document(request_data))
        return
    doc_id, _ = existing_docs[0]
    fields = [
        "bloodType", "socialSecurityNumber", "medications",
        "medicalConditions", "insuranceProvider", "insuranceNumber",
    ]
    update_fields = {f: hd[f] for f in fields if hd.get(f)}
    if update_fields:
        update_fields["updatedAt"] = get_current_timestamp()
        helper.update_document(path, doc_id, update_fields)


def _process_emergency_contacts(
    helper: FirestoreHelper,
    user_id: str,
    event_id: str,
    emergency_contacts: list,
    out_user_ec_ids: Optional[list] = None,
) -> Optional[str]:
    """
    Procesa contactos de emergencia (array mixto). Válido para Flujo A y Flujo B.

    - Item con datos completos: crea en users/emergencyContacts → {"id": autoId} en evento
    - Item solo con {id}: valida existencia en users/emergencyContacts → {"id": id} en evento

    Args:
        out_user_ec_ids: lista mutable donde se acumulan los IDs creados en users/ (para rollback).

    Returns:
        None si todo ok, o el id del contacto no encontrado si falla la validación.
    """
    participant_ec_path = (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}/{user_id}"
        f"/{FirestoreCollections.PARTICIPANT_EMERGENCY_CONTACTS}"
    )
    user_ec_path = (
        f"{FirestoreCollections.USERS}/{user_id}/{_USER_EMERGENCY_CONTACT}"
    )

    for contact in emergency_contacts:
        if not isinstance(contact, dict):
            continue
        existing_id = contact.get("id")
        has_data = contact.get("fullName") or contact.get("phone")

        if has_data:
            # Contacto nuevo: crear en users → {"id": autoId} en evento
            contact_doc = _build_emergency_contact_document(contact)
            auto_id = helper.create_document(user_ec_path, contact_doc)
            if out_user_ec_ids is not None:
                out_user_ec_ids.append(auto_id)
            helper.create_document_with_id(participant_ec_path, auto_id, {"id": auto_id})
            LOG.info("%s Nuevo contacto creado: %s", LOG_PREFIX, auto_id)
        elif existing_id:
            # Contacto existente: validar que exista en users antes de referenciar
            existing_doc = helper.get_document(user_ec_path, existing_id)
            if existing_doc is None:
                LOG.warning("%s Contacto no encontrado en users: %s", LOG_PREFIX, existing_id)
                return existing_id
            helper.create_document_with_id(
                participant_ec_path, existing_id, {"id": existing_id}
            )
            LOG.info("%s Contacto existente referenciado: %s", LOG_PREFIX, existing_id)

    return None


def _process_vehicle(
    helper: FirestoreHelper,
    user_id: str,
    event_id: str,
    request_data: Dict[str, Any],
    out_vehicle_id: Optional[list] = None,
) -> Optional[str]:
    """
    Procesa vehicleData del request. Válido para Flujo A y Flujo B.

    - Datos completos: crea en users/{userId}/vehicles → {"id": autoId} en evento
    - Solo {id}: valida existencia en users/{userId}/vehicles → {"id": id} en evento

    Args:
        out_vehicle_id: lista mutable de un elemento donde se guarda el ID creado en users/ (para rollback).

    Returns:
        None si todo ok, o el id del vehículo no encontrado si falla la validación.
    """
    vehicle_data = request_data.get("vehicleData")
    if not vehicle_data or not isinstance(vehicle_data, dict):
        return None

    vehicles_path = (
        f"{FirestoreCollections.USERS}/{user_id}"
        f"/{FirestoreCollections.USER_VEHICLES}"
    )
    participant_vehicle_path = (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}/{user_id}"
        f"/{FirestoreCollections.PARTICIPANT_VEHICLE}"
    )

    existing_id = vehicle_data.get("id")
    has_data = vehicle_data.get("branch") or vehicle_data.get("brand") or vehicle_data.get("model")

    if has_data:
        # Vehículo nuevo: crear en users → {"id": autoId} en evento
        vehicle_doc = _build_vehicle_document(request_data)
        auto_id = helper.create_document(vehicles_path, vehicle_doc)
        if out_vehicle_id is not None:
            out_vehicle_id.append(auto_id)
        helper.create_document_with_id(participant_vehicle_path, auto_id, {"id": auto_id})
        LOG.info("%s Vehículo creado: %s", LOG_PREFIX, auto_id)
    elif existing_id:
        # Vehículo existente: validar que exista en users antes de referenciar
        existing_doc = helper.get_document(vehicles_path, existing_id)
        if existing_doc is None:
            LOG.warning("%s Vehículo no encontrado en users: %s", LOG_PREFIX, existing_id)
            return existing_id
        helper.create_document_with_id(participant_vehicle_path, existing_id, {"id": existing_id})
        LOG.info("%s Vehículo existente referenciado: %s", LOG_PREFIX, existing_id)

    return None


def _create_competitor_for_existing_user(
    helper: FirestoreHelper,
    user_id: str,
    request_data: Dict[str, Any],
) -> https_fn.Response:
    """
    Flujo B: El usuario ya existe en Firestore.
    Registra al usuario en un nuevo evento sin recrear su documento raíz.
    """
    competition = request_data.get("competition", {})
    event_id = competition.get("eventId", "")

    # Verificar que NO sea ya participante del evento → 409
    collection_path = _get_collection_path(event_id)
    if helper.get_document(collection_path, user_id) is not None:
        LOG.warning(
            "%s [FlujoB] Usuario %s ya inscrito en evento %s",
            LOG_PREFIX, user_id, event_id,
        )
        return https_fn.Response(
            "", status=409, headers={"Access-Control-Allow-Origin": "*"}
        )

    # Verificar número de piloto no duplicado → 409
    pilot_number = competition.get("number", "")
    if pilot_number and _check_duplicate_competitor(helper, event_id, pilot_number):
        LOG.warning(
            "%s [FlujoB] Número de piloto duplicado: %s en evento %s",
            LOG_PREFIX, pilot_number, event_id,
        )
        return https_fn.Response(
            "", status=409, headers={"Access-Control-Allow-Origin": "*"}
        )

    # Actualizar datos del usuario (merge: solo campos no vacíos)
    _merge_update_personal_data(helper, user_id, request_data)
    _merge_update_health_data(helper, user_id, request_data)

    # Procesar contactos de emergencia (array mixto: existentes + nuevos)
    emergency_contacts = request_data.get("emergencyContacts") or []
    if isinstance(emergency_contacts, list):
        failed_id = _process_emergency_contacts(
            helper, user_id, event_id, emergency_contacts
        )
        if failed_id is not None:
            return https_fn.Response(
                json.dumps(
                    {"error": f"emergencyContact {failed_id} no encontrado"},
                    ensure_ascii=False,
                ),
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

    # Procesar vehículo (nuevo con datos o existente con {id})
    failed_vehicle_id = _process_vehicle(helper, user_id, event_id, request_data)
    if failed_vehicle_id is not None:
        return https_fn.Response(
            json.dumps(
                {"error": f"vehicle {failed_vehicle_id} no encontrado"},
                ensure_ascii=False,
            ),
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    # Crear membership
    membership_path = (
        f"{FirestoreCollections.USERS}/{user_id}"
        f"/{FirestoreCollections.USER_MEMBERSHIP}"
    )
    helper.create_document_with_id(membership_path, event_id, _build_membership_document())
    LOG.info("%s [FlujoB] Membership creado: %s/%s", LOG_PREFIX, user_id, event_id)

    # Crear participante en el evento
    competitor_doc = _build_competitor_document(request_data, user_id)
    competitor_doc = _apply_source_and_system_fields(competitor_doc, request_data)
    helper.create_document_with_id(collection_path, user_id, competitor_doc)
    LOG.info(
        "%s [FlujoB] Participante creado: userId=%s eventId=%s",
        LOG_PREFIX, user_id, event_id,
    )

    return https_fn.Response(
        json.dumps({"id": user_id, "membershipId": event_id}, ensure_ascii=False),
        status=201,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


# ============================================================================
# ENDPOINT PRINCIPAL
# ============================================================================


@https_fn.on_request(region="us-east4")
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
    Requeridos:
    - email: string (raíz) - formato válido
    - competition: object - eventId (requerido), number/team (opcionales) y
      category condicional (obligatorio solo si el evento tiene categorías en
      events/{eventId}/event_categories).
      Si no se envía, se crea con valores por defecto.
    Opcionales:
    - source: string - origen de la solicitud (ej: "web", "mobile-ios", "mobile-android")
    - system: string - sistema origen de la solicitud (ej: "rally-app", "backoffice")
    - personalData: object - fullName, phone, dateOfBirth, address, city, state, country, postalCode
    - healthData: object - bloodType, socialSecurityNumber, medications, medicalConditions, insuranceProvider, insuranceNumber
    - emergencyContacts: array - cada elemento: fullName, phone, relationship (opcional)
    - vehicleData: object - branch (o brand), year, model, color
    - username: string - si se envía, mínimo 4 caracteres y único
    Nota: registrationDate se asigna automáticamente por la función.

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
        event_id = (request_data.get("competition", {}).get("eventId", "") or "").strip()

        # Validación condicional única para category y existencia de evento
        competition_validation_response = _validate_competition_category_requirement(
            helper, request_data
        )
        if competition_validation_response is not None:
            return competition_validation_response

        # Verificar si el usuario ya existe → Flujo B
        existing_user = _find_existing_user_by_email(helper, email)
        if existing_user is not None:
            LOG.info(
                "%s Usuario existente, iniciando Flujo B: %s", LOG_PREFIX, email
            )
            existing_user_id, _ = existing_user
            return _create_competitor_for_existing_user(
                helper, existing_user_id, request_data
            )

        # Validar unicidad de username solo si se envió (opcional)
        if username and _validate_unique_username(helper, username):
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

        # PASO 2.3: Subcolección emergencyContact en users + referencia {"id"} en evento
        try:
            failed_id = _process_emergency_contacts(
                helper, user_id, event_id, emergency_contacts,
                out_user_ec_ids=created_emergency_contact_ids,
            )
            if failed_id is not None:
                _rollback_user_creation(
                    helper,
                    user_id,
                    event_id,
                    rollback_subcollections=True,
                    created_personal_data_id=created_personal_data_id,
                    created_health_data_id=created_health_data_id,
                    created_emergency_contact_ids=created_emergency_contact_ids,
                    created_vehicle_id=None,
                    created_event_ec_ids=created_emergency_contact_ids,
                )
                return https_fn.Response(
                    json.dumps(
                        {"error": f"emergencyContact {failed_id} no encontrado"},
                        ensure_ascii=False,
                    ),
                    status=400,
                    headers={"Access-Control-Allow-Origin": "*"},
                )
        except Exception:
            _rollback_user_creation(
                helper,
                user_id,
                event_id,
                rollback_subcollections=True,
                created_personal_data_id=created_personal_data_id,
                created_health_data_id=created_health_data_id,
                created_emergency_contact_ids=created_emergency_contact_ids,
                created_vehicle_id=None,
                created_event_ec_ids=created_emergency_contact_ids,
            )
            raise

        # PASO 2.4: Vehículo en users + referencia {"id"} en evento
        created_vehicle_id = None
        out_vehicle_id: list = []
        vehicle_data = request_data.get("vehicleData")
        if vehicle_data and isinstance(vehicle_data, dict):
            try:
                failed_vehicle_id = _process_vehicle(
                    helper, user_id, event_id, request_data,
                    out_vehicle_id=out_vehicle_id,
                )
                if out_vehicle_id:
                    created_vehicle_id = out_vehicle_id[0]
                if failed_vehicle_id is not None:
                    _rollback_user_creation(
                        helper,
                        user_id,
                        event_id,
                        rollback_subcollections=True,
                        created_personal_data_id=created_personal_data_id,
                        created_health_data_id=created_health_data_id,
                        created_emergency_contact_ids=created_emergency_contact_ids,
                        created_vehicle_id=None,
                        created_event_ec_ids=created_emergency_contact_ids,
                        created_event_vehicle_id=None,
                    )
                    return https_fn.Response(
                        json.dumps(
                            {"error": f"vehicle {failed_vehicle_id} no encontrado"},
                            ensure_ascii=False,
                        ),
                        status=400,
                        headers={"Access-Control-Allow-Origin": "*"},
                    )
            except Exception:
                _rollback_user_creation(
                    helper,
                    user_id,
                    event_id,
                    rollback_subcollections=True,
                    created_personal_data_id=created_personal_data_id,
                    created_health_data_id=created_health_data_id,
                    created_emergency_contact_ids=created_emergency_contact_ids,
                    created_vehicle_id=None,
                    created_event_ec_ids=created_emergency_contact_ids,
                    created_event_vehicle_id=None,
                )
                raise

        # PASO 3: Subcolección membership
        membership_doc = _build_membership_document()
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
                created_event_ec_ids=created_emergency_contact_ids,
                created_event_vehicle_id=created_vehicle_id,
            )
            raise

        # PASO 4: Crear participante en events/{eventId}/participants (mismo id que users)
        collection_path = _get_collection_path(event_id)
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
                created_event_ec_ids=created_emergency_contact_ids,
                created_event_vehicle_id=created_vehicle_id,
            )
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        competition = request_data.get("competition", {})
        pilot_number = competition.get("number", "")
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
                created_event_ec_ids=created_emergency_contact_ids,
                created_event_vehicle_id=created_vehicle_id,
            )
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            competitor_doc = _build_competitor_document(request_data, user_id)
            competitor_doc = _apply_source_and_system_fields(
                competitor_doc, request_data
            )
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
                created_event_ec_ids=created_emergency_contact_ids,
                created_event_vehicle_id=created_vehicle_id,
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
