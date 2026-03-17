"""
Read profile sections - Obtiene una subcolección del usuario (personalData, healthData, etc.).

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
Formato de respuesta alineado a get_event_competitor_by_email (excluir createdAt/updatedAt, incluir id).
"""

import json
import logging
from typing import Any, Dict, List, Optional

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helpers import convert_firestore_value

_EXCLUDED_FIELDS = {"createdAt", "updatedAt"}

ALLOWED_SECTIONS = ("personalData", "healthData", "emergencyContacts", "vehicles", "membership")
FIRST_DOC_SECTIONS = ("personalData", "healthData")  # emergencyContacts, vehicles, membership devuelven lista

# Campos de la respuesta personalData cuando no hay documento en la subcolección (resto en null)
_PERSONAL_DATA_RESPONSE_FIELDS = (
    "id",
    "fullName",
    "phone",
    "dateOfBirth",
    "address",
    "city",
    "state",
    "country",
    "postalCode",
)


def _resolve_user_id(helper: FirestoreHelper, user_id: str) -> Optional[str]:
    """userId es el ID del documento en users. Retorna userId si el documento existe, None si no."""
    if not user_id or not user_id.strip():
        return None
    user_id = user_id.strip()
    doc = helper.get_document(FirestoreCollections.USERS, user_id)
    return user_id if doc is not None else None


def _doc_to_response_item(doc_id: str, doc_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convierte un documento a dict de respuesta: excluye createdAt/updatedAt, añade id, convert_firestore_value."""
    if doc_data is None:
        return {"id": doc_id}
    converted = {
        k: convert_firestore_value(v)
        for k, v in doc_data.items()
        if k not in _EXCLUDED_FIELDS
    }
    converted["id"] = doc_id
    return converted


def handle(req: https_fn.Request, section: str) -> https_fn.Response:
    """
    Lee una sección del perfil del usuario. Asume request ya validado y autenticado.
    - personalData: objeto con email (del user) + campos de la subcolección; si la subcolección está vacía, 200 con email y el resto null.
    - healthData: primer documento (objeto único); 404 si vacío.
    - emergencyContacts, vehicles, membership: lista de documentos (puede ser []).
    """
    try:
        if section not in ALLOWED_SECTIONS:
            logging.warning("read_sections: Sección no permitida: %s", section)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_id_param = (req.args.get("userId") or "").strip()
        logging.info("read_sections: section=%s userId_param=%r", section, user_id_param)

        if not user_id_param:
            logging.warning("read_sections: userId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()
        user_id = _resolve_user_id(helper, user_id_param)
        if user_id is None:
            logging.warning("read_sections: Usuario no encontrado (userId=%s, doc no existe en users)", user_id_param)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        subcollection_path = f"{FirestoreCollections.USERS}/{user_id}/{section}"

        if section in FIRST_DOC_SECTIONS:
            results = helper.query_documents(subcollection_path, limit=1)
            if not results:
                if section == "personalData":
                    user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
                    email_val = (user_doc.get("email") if user_doc else None)
                    body = {
                        "email": convert_firestore_value(email_val) if email_val is not None else None,
                    }
                    for field in _PERSONAL_DATA_RESPONSE_FIELDS:
                        body[field] = None
                    logging.info("read_sections: personalData vacío, retornando email y nulls: userId=%s", user_id)
                    return https_fn.Response(
                        json.dumps(body, ensure_ascii=False),
                        status=200,
                        headers={
                            "Content-Type": "application/json; charset=utf-8",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET, OPTIONS",
                            "Access-Control-Allow-Headers": "Content-Type, Authorization",
                        },
                    )
                else:
                    logging.warning("read_sections: Subcolección vacía (404): userId=%s section=%s", user_id, section)
                    return https_fn.Response(
                        "",
                        status=404,
                        headers={"Access-Control-Allow-Origin": "*"},
                    )
            else:
                doc_id, doc_data = results[0]
                body = _doc_to_response_item(doc_id, doc_data)
                if section == "personalData":
                    user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
                    if user_doc is not None:
                        body["email"] = convert_firestore_value(user_doc.get("email"))
        else:
            results = helper.query_documents(subcollection_path)
            body = [_doc_to_response_item(doc_id, doc_data) for doc_id, doc_data in results]

        return https_fn.Response(
            json.dumps(body, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("read_sections: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("read_sections: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
