"""
Delete section item - Elimina un documento de una subcolección del usuario (emergencyContacts o vehicles).

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
DELETE /api/users/emergencyContacts?userId=xxx&id=docId
DELETE /api/users/vehicles?userId=xxx&id=vehicleId
Respuesta exitosa: 204 No Content.
"""

import logging

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper

DELETE_ALLOWED_SECTIONS = ("emergencyContacts", "vehicles")

_CORS_HEADERS_204 = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def handle(req: https_fn.Request, section: str) -> https_fn.Response:
    """
    Elimina un documento de la subcolección del usuario (emergencyContacts o vehicles).
    Asume request ya validado (CORS, Bearer token) y section en DELETE_ALLOWED_SECTIONS.

    Parámetros query:
    - userId (requerido): ID del documento del usuario en users.
    - id (requerido): ID del documento a eliminar en la subcolección.

    Returns:
    - 204: eliminado correctamente.
    - 400: userId o id faltantes/vacíos.
    - 404: usuario no existe o documento no existe en la subcolección.
    - 500: error interno.
    """
    try:
        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            logging.warning("delete_section_item: userId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers=_CORS_HEADERS_204,
            )

        doc_id = (req.args.get("id") or "").strip()
        if not doc_id:
            logging.warning("delete_section_item: id faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers=_CORS_HEADERS_204,
            )

        helper = FirestoreHelper()
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            logging.warning("delete_section_item: Usuario no encontrado: userId=%s", user_id)
            return https_fn.Response(
                "",
                status=404,
                headers=_CORS_HEADERS_204,
            )

        subcollection_path = f"{FirestoreCollections.USERS}/{user_id}/{section}"
        existing_doc = helper.get_document(subcollection_path, doc_id)
        if existing_doc is None:
            logging.warning(
                "delete_section_item: Documento no encontrado: userId=%s section=%s id=%s",
                user_id,
                section,
                doc_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers=_CORS_HEADERS_204,
            )

        helper.delete_document(subcollection_path, doc_id)
        logging.info(
            "delete_section_item: Eliminado userId=%s section=%s id=%s",
            user_id,
            section,
            doc_id,
        )

        return https_fn.Response(
            "",
            status=204,
            headers=_CORS_HEADERS_204,
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("delete_section_item: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers=_CORS_HEADERS_204,
        )
