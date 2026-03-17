"""
Update User - Actualiza datos de un usuario existente por secciones.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper
from utils.validation_helper import validate_email, validate_phone

_KNOWN_SECTIONS = {"email", "username", "personalData", "healthData", "emergencyContacts", "vehicleData"}


def _validate_request_data(request_data: Dict[str, Any]) -> Optional[str]:
    if not request_data or not isinstance(request_data, dict):
        return "Request body inválido o faltante"
    if not any(k in request_data for k in _KNOWN_SECTIONS):
        return "No hay datos para actualizar"
    email = request_data.get("email")
    if email is not None:
        if not isinstance(email, str) or not email.strip():
            return "email no puede estar vacío"
        if not validate_email(email.strip()):
            return "Formato de email inválido"
    username = request_data.get("username")
    if username is not None:
        if not isinstance(username, str) or len(username.strip()) < 4:
            return "El username debe tener al menos 4 caracteres"
    personal_data = request_data.get("personalData")
    if personal_data is not None:
        if not isinstance(personal_data, dict):
            return "personalData debe ser un objeto"
        phone = personal_data.get("phone", "")
        if phone and not validate_phone(phone):
            return "personalData.phone: formato de teléfono inválido"
    health_data = request_data.get("healthData")
    if health_data is not None and not isinstance(health_data, dict):
        return "healthData debe ser un objeto"
    emergency_contacts = request_data.get("emergencyContacts")
    if emergency_contacts is not None:
        if not isinstance(emergency_contacts, list):
            return "emergencyContacts debe ser una lista"
        for i, contact in enumerate(emergency_contacts):
            if not isinstance(contact, dict):
                return f"emergencyContacts[{i}] debe ser un objeto"
            if not contact.get("fullName") or not contact.get("phone"):
                return f"emergencyContacts[{i}]: fullName y phone son requeridos"
    vehicle_data = request_data.get("vehicleData")
    if vehicle_data is not None and not isinstance(vehicle_data, dict):
        return "vehicleData debe ser un objeto"
    return None


def _validate_unique_email(helper: FirestoreHelper, email: str, exclude_user_id: str) -> bool:
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "email", "operator": "==", "value": email}],
    )
    for doc_id, _ in results:
        if doc_id != exclude_user_id:
            return True
    return False


def _validate_unique_username(helper: FirestoreHelper, username: str, exclude_user_id: str) -> bool:
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "username", "operator": "==", "value": username}],
    )
    for doc_id, _ in results:
        if doc_id != exclude_user_id:
            return True
    return False


def _update_root_fields(helper: FirestoreHelper, user_id: str, request_data: Dict[str, Any]) -> None:
    fields: Dict[str, Any] = {"updatedAt": get_current_timestamp()}
    email = request_data.get("email")
    if email is not None:
        fields["email"] = email.strip()
    username = request_data.get("username")
    if username is not None:
        fields["username"] = username.strip()
    helper.update_document(FirestoreCollections.USERS, user_id, fields)
    logging.info("update: Campos raíz actualizados: userId=%s", user_id)


def _update_personal_data(helper: FirestoreHelper, user_id: str, personal_data: Dict[str, Any]) -> None:
    now = get_current_timestamp()
    subcol_path = f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_PERSONAL_DATA}"
    fields = {k: v for k, v in personal_data.items() if k != "email"}
    fields["updatedAt"] = now
    existing_ids = helper.list_document_ids(subcol_path)
    if existing_ids:
        helper.update_document(subcol_path, existing_ids[0], fields)
        logging.info("update: personalData actualizado: userId=%s docId=%s", user_id, existing_ids[0])
    else:
        fields["createdAt"] = now
        helper.create_document(subcol_path, fields)
        logging.info("update: personalData creado: userId=%s", user_id)


def _update_health_data(helper: FirestoreHelper, user_id: str, health_data: Dict[str, Any]) -> None:
    now = get_current_timestamp()
    subcol_path = f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_HEALTH_DATA}"
    fields = {k: v for k, v in health_data.items()}
    fields["updatedAt"] = now
    existing_ids = helper.list_document_ids(subcol_path)
    if existing_ids:
        helper.update_document(subcol_path, existing_ids[0], fields)
        logging.info("update: healthData actualizado: userId=%s docId=%s", user_id, existing_ids[0])
    else:
        fields["createdAt"] = now
        helper.create_document(subcol_path, fields)
        logging.info("update: healthData creado: userId=%s", user_id)


def _replace_emergency_contacts(
    helper: FirestoreHelper, user_id: str, contacts: List[Dict[str, Any]]
) -> None:
    now = get_current_timestamp()
    subcol_path = f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_EMERGENCY_CONTACT}"
    existing_ids = helper.list_document_ids(subcol_path)
    for doc_id in existing_ids:
        helper.delete_document(subcol_path, doc_id)
    for contact in contacts:
        doc = {
            "fullName": contact.get("fullName", ""),
            "relationship": contact.get("relationship", ""),
            "phone": contact.get("phone", ""),
            "createdAt": now,
            "updatedAt": now,
        }
        helper.create_document(subcol_path, doc)
    logging.info("update: emergencyContacts reemplazados: userId=%s total=%d", user_id, len(contacts))


def _upsert_vehicle(helper: FirestoreHelper, user_id: str, vehicle_data: Dict[str, Any]) -> None:
    now = get_current_timestamp()
    subcol_path = f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_VEHICLES}"
    vehicle_id = vehicle_data.get("id")
    branch = vehicle_data.get("branch") or vehicle_data.get("brand", "")
    fields: Dict[str, Any] = {
        "branch": branch,
        "model": vehicle_data.get("model", ""),
        "year": vehicle_data.get("year"),
        "color": vehicle_data.get("color", ""),
        "updatedAt": now,
    }
    if vehicle_id:
        existing = helper.get_document(subcol_path, vehicle_id)
        if existing is not None:
            helper.update_document(subcol_path, vehicle_id, fields)
            logging.info("update: vehicle actualizado: userId=%s vehicleId=%s", user_id, vehicle_id)
        else:
            fields["createdAt"] = now
            helper.create_document_with_id(subcol_path, vehicle_id, fields)
            logging.info("update: vehicle creado con id: userId=%s vehicleId=%s", user_id, vehicle_id)
    else:
        fields["createdAt"] = now
        new_id = helper.create_document(subcol_path, fields)
        logging.info("update: vehicle nuevo creado: userId=%s newVehicleId=%s", user_id, new_id)


def handle(req: https_fn.Request) -> https_fn.Response:
    """Lógica update: actualizar por secciones. Asume request ya validado y autenticado."""
    try:
        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            logging.warning("update: userId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            request_data = req.get_json(silent=True)
        except (ValueError, TypeError) as e:
            logging.warning("update: Error parseando JSON: %s", e)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if request_data is None:
            logging.warning("update: Request body inválido o faltante")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        validation_error = _validate_request_data(request_data)
        if validation_error:
            logging.warning("update: Validación fallida: %s", validation_error)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            logging.warning("update: Usuario no encontrado: userId=%s", user_id)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        email = request_data.get("email")
        if email is not None and _validate_unique_email(helper, email.strip(), user_id):
            logging.warning("update: Email duplicado: %s", email)
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        username = request_data.get("username")
        if username is not None and _validate_unique_username(helper, username.strip(), user_id):
            logging.warning("update: Username duplicado: %s", username)
            return https_fn.Response(
                "",
                status=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        updated_sections: List[str] = []
        if email is not None or username is not None:
            _update_root_fields(helper, user_id, request_data)
            if email is not None:
                updated_sections.append("email")
            if username is not None:
                updated_sections.append("username")
        personal_data = request_data.get("personalData")
        if personal_data is not None:
            _update_personal_data(helper, user_id, personal_data)
            updated_sections.append("personalData")
        health_data = request_data.get("healthData")
        if health_data is not None:
            _update_health_data(helper, user_id, health_data)
            updated_sections.append("healthData")
        emergency_contacts = request_data.get("emergencyContacts")
        if emergency_contacts is not None:
            _replace_emergency_contacts(helper, user_id, emergency_contacts)
            updated_sections.append("emergencyContacts")
        vehicle_data = request_data.get("vehicleData")
        if vehicle_data is not None:
            _upsert_vehicle(helper, user_id, vehicle_data)
            updated_sections.append("vehicleData")

        logging.info("update: Usuario actualizado: userId=%s secciones=%s", user_id, updated_sections)
        return https_fn.Response(
            json.dumps({"id": user_id, "updated": updated_sections}, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "PUT, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("update: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("update: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
