"""
Get my routes - Lista rutas del usuario o regresa detalle por routeId.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import json
import logging
from typing import Any, Dict, List

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helpers import convert_firestore_value

_EXCLUDED_LIST_FIELDS = {"createdAt", "updatedAt"}


def _cors_headers() -> Dict[str, str]:
    return {"Access-Control-Allow-Origin": "*"}


def _json_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


def _serialize_doc(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: convert_firestore_value(v) for k, v in data.items()}
    out["id"] = doc_id
    return out


def _serialize_list_item(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        k: convert_firestore_value(v)
        for k, v in data.items()
        if k not in _EXCLUDED_LIST_FIELDS
    }
    out["id"] = doc_id
    return out


def _list_my_routes(helper: FirestoreHelper, user_id: str) -> https_fn.Response:
    collection_path = (
        f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
    )
    docs = helper.query_documents(collection_path)
    data = [_serialize_list_item(doc_id, doc_data) for doc_id, doc_data in docs]
    return https_fn.Response(
        json.dumps(data, ensure_ascii=False),
        status=200,
        headers=_json_headers(),
    )


def _get_route_detail(
    helper: FirestoreHelper, user_id: str, route_id: str
) -> https_fn.Response:
    route_collection_path = (
        f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
    )
    route_doc = helper.get_document(route_collection_path, route_id)
    if route_doc is None:
        return https_fn.Response("", status=404, headers=_cors_headers())

    points_path = f"{route_collection_path}/{route_id}/{FirestoreCollections.MY_ROUTE_POINTS}"
    notes_path = f"{route_collection_path}/{route_id}/{FirestoreCollections.MY_ROUTE_NOTES}"
    points = [_serialize_doc(doc_id, doc_data) for doc_id, doc_data in helper.query_documents(points_path)]
    notes = [_serialize_doc(doc_id, doc_data) for doc_id, doc_data in helper.query_documents(notes_path)]

    body = _serialize_doc(route_id, route_doc)
    body["points"] = points
    body["notes"] = notes
    return https_fn.Response(
        json.dumps(body, ensure_ascii=False),
        status=200,
        headers=_json_headers(),
    )


def handle(req: https_fn.Request) -> https_fn.Response:
    """GET /api/users/my-routes?userId=... [&routeId=...]"""
    try:
        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            logging.warning("get_my_routes: userId faltante")
            return https_fn.Response("", status=400, headers=_cors_headers())

        helper = FirestoreHelper()
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            logging.warning("get_my_routes: userId no existe: %s", user_id)
            return https_fn.Response("", status=404, headers=_cors_headers())

        route_id = (req.args.get("routeId") or "").strip()
        if route_id:
            return _get_route_detail(helper, user_id, route_id)

        return _list_my_routes(helper, user_id)
    except ValueError as e:
        logging.error("get_my_routes: Error de validación: %s", e)
        return https_fn.Response("", status=400, headers=_cors_headers())
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("get_my_routes: Error interno: %s", e, exc_info=True)
        return https_fn.Response("", status=500, headers=_cors_headers())
