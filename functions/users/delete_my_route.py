"""
Delete my route — Elimina la ruta y subcolecciones notes, points y trackStyles.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import logging
from typing import Dict

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper


def _cors_headers() -> Dict[str, str]:
    return {"Access-Control-Allow-Origin": "*"}


def _success_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


def handle(req: https_fn.Request, route_id: str) -> https_fn.Response:
    """DELETE /api/users/my-routes/{routeId}?userId=..."""
    try:
        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            return https_fn.Response("", status=400, headers=_cors_headers())

        helper = FirestoreHelper()
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            return https_fn.Response("", status=404, headers=_cors_headers())

        routes_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
        )
        route_doc = helper.get_document(routes_path, route_id)
        if route_doc is None:
            return https_fn.Response("", status=404, headers=_cors_headers())

        notes_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}/"
            f"{route_id}/{FirestoreCollections.MY_ROUTE_NOTES}"
        )
        points_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}/"
            f"{route_id}/{FirestoreCollections.MY_ROUTE_POINTS}"
        )
        track_styles_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}/"
            f"{route_id}/{FirestoreCollections.MY_ROUTE_TRACK_STYLES}"
        )

        for note_doc_id in helper.list_document_ids(notes_path):
            helper.delete_document(notes_path, note_doc_id)

        for point_doc_id in helper.list_document_ids(points_path):
            helper.delete_document(points_path, point_doc_id)

        for style_doc_id in helper.list_document_ids(track_styles_path):
            helper.delete_document(track_styles_path, style_doc_id)

        helper.delete_document(routes_path, route_id)

        return https_fn.Response("", status=200, headers=_success_headers())
    except ValueError as e:
        logging.error("delete_my_route: Error de validación: %s", e)
        return https_fn.Response("", status=400, headers=_cors_headers())
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("delete_my_route: Error interno: %s", e, exc_info=True)
        return https_fn.Response("", status=500, headers=_cors_headers())
