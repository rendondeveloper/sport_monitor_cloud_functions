"""
Create User - Crear o activar usuario en colección users.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper
from utils.validation_helper import validate_email


def _find_user_by_email(
    helper: FirestoreHelper, email: str
) -> Optional[Tuple[str, Dict[str, Any]]]:
    results = helper.query_documents(
        FirestoreCollections.USERS,
        filters=[{"field": "email", "operator": "==", "value": email}],
        limit=1,
    )
    if not results:
        return None
    return results[0]


def _build_create_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    now = get_current_timestamp()
    email = request_data.get("email", "").strip()
    return {
        "email": email,
        "username": email,
        "authUserId": request_data.get("authUserId"),
        "avatarUrl": request_data.get("avatarUrl"),
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }


def _build_update_fields(
    request_data: Dict[str, Any], existing_username: str
) -> Dict[str, Any]:
    now = get_current_timestamp()
    email = request_data.get("email", "").strip()
    new_username = existing_username if existing_username else email
    return {
        "authUserId": request_data.get("authUserId"),
        "avatarUrl": request_data.get("avatarUrl"),
        "isActive": True,
        "username": new_username,
        "updatedAt": now,
    }


def _validate_body(request_data: Any) -> Optional[str]:
    if not request_data or not isinstance(request_data, dict):
        return "Request body inválido o faltante"
    email = request_data.get("email", "").strip() if isinstance(request_data.get("email"), str) else ""
    if not email:
        return "email es requerido"
    if not validate_email(email):
        return "Formato de email inválido"
    auth_user_id = request_data.get("authUserId")
    if not auth_user_id or not str(auth_user_id).strip():
        return "authUserId es requerido"
    return None


def handle(req: https_fn.Request) -> https_fn.Response:
    """Lógica create: upsert por email. Asume request ya validado y autenticado."""
    try:
        try:
            request_data = req.get_json(silent=True)
        except (ValueError, TypeError) as e:
            logging.warning("create: Error parseando JSON: %s", e)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        validation_error = _validate_body(request_data)
        if validation_error:
            logging.warning("create: Validación fallida: %s", validation_error)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        email = request_data["email"].strip()
        helper = FirestoreHelper()
        existing = _find_user_by_email(helper, email)

        if existing is not None:
            user_id, user_data = existing
            existing_username = user_data.get("username", "") or ""
            update_fields = _build_update_fields(request_data, existing_username)
            helper.update_document(FirestoreCollections.USERS, user_id, update_fields)
            logging.info("create: Template activado: userId=%s email=%s", user_id, email)
            return https_fn.Response(
                json.dumps({"id": user_id}, ensure_ascii=False),
                status=200,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
            )

        user_doc = _build_create_document(request_data)
        new_id = helper.create_document(FirestoreCollections.USERS, user_doc)
        logging.info("create: Usuario creado: userId=%s email=%s", new_id, email)
        return https_fn.Response(
            json.dumps({"id": new_id}, ensure_ascii=False),
            status=201,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("create: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("create: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
