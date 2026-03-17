"""
Read profile - Obtiene perfil básico de usuario (id, authUserId, avatarUrl, email, username).

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import json
import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helpers import convert_firestore_value
from utils.validation_helper import validate_email

USER_PROFILE_FIELDS = ("authUserId", "avatarUrl", "email", "username")


def _find_user_by_email(db, email_param: str):
    """Busca usuario solo por email. Retorna el snapshot del documento o None."""
    if not email_param or not email_param.strip():
        return None
    users_ref = db.collection(FirestoreCollections.USERS)
    query_snapshot = (
        users_ref.where("email", "==", email_param.strip()).limit(1).get()
    )
    if query_snapshot and len(query_snapshot) > 0:
        return query_snapshot[0]
    return None


def _build_profile_response(user_doc) -> dict:
    user_data = user_doc.to_dict()
    if user_data is None:
        return {}
    result = {"id": user_doc.id}
    for field in USER_PROFILE_FIELDS:
        value = user_data.get(field)
        result[field] = convert_firestore_value(value) if value is not None else None
    return result


def handle(req: https_fn.Request) -> https_fn.Response:
    """Lógica read: perfil solo por email. Asume request ya validado y autenticado."""
    try:
        email_param = (req.args.get("email") or "").strip()

        if not email_param:
            logging.warning("read: email faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not validate_email(email_param):
            logging.warning("read: email con formato inválido")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        db = firestore.client()
        user_doc = _find_user_by_email(db, email_param)

        if user_doc is None:
            logging.info("read: Usuario no encontrado (email=%s)", email_param)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_data = user_doc.to_dict()
        if user_data is None:
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        profile_data = _build_profile_response(user_doc)
        return https_fn.Response(
            json.dumps(profile_data, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("read: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("read: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
