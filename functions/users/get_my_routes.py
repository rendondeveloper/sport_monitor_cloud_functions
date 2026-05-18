"""
Get my routes - Lista rutas del usuario o regresa detalle por routeId.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import json
import logging
import math
from typing import Any, Dict, List, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from models.paginated_response import PaginatedResponse
from utils.firestore_helper import FirestoreHelper
from utils.helpers import convert_firestore_value

_EXCLUDED_LIST_FIELDS = {
    "createdAt",
    "updatedAt",
    "description",
}
_EXCLUDED_ROUTE_DETAIL_FIELDS = frozenset(
    {
        "updatedAt",
        "description",
        "createdAt",
    }
)
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100


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


def _track_style_sort_key(item: Dict[str, Any]) -> int:
    raw = item.get("startPointIndex")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return raw


def _serialize_route_detail(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        k: convert_firestore_value(v)
        for k, v in data.items()
        if k not in _EXCLUDED_ROUTE_DETAIL_FIELDS
    }
    out["id"] = doc_id
    return out


def _to_distance_km(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else 0.0
    if isinstance(value, str):
        try:
            v = float(value.strip())
            return v if math.isfinite(v) else 0.0
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _compute_distance_total(docs_all_routes: List[Tuple[str, Dict[str, Any]]]) -> float:
    total = 0.0
    for _, doc_data in docs_all_routes:
        total += _to_distance_km(doc_data.get("distance"))
    if not math.isfinite(total):
        return 0.0
    return math.ceil(total * 10.0) / 10.0


def _parse_limit(raw_limit: str | None) -> int:
    if raw_limit is None:
        return _DEFAULT_LIMIT

    try:
        limit = int(raw_limit)
        if limit < 1:
            return _DEFAULT_LIMIT
        return min(limit, _MAX_LIMIT)
    except (ValueError, TypeError):
        return _DEFAULT_LIMIT


def _parse_start_after_doc_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value if value else None


def _list_my_routes(helper: FirestoreHelper, user_id: str) -> https_fn.Response:
    collection_path = (
        f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
    )
    docs = helper.query_documents(collection_path)
    distance_total = _compute_distance_total(docs)
    data = [_serialize_list_item(doc_id, doc_data) for doc_id, doc_data in docs]
    for item in data:
        item["distanceTotal"] = distance_total
    return https_fn.Response(
        json.dumps(data, ensure_ascii=False),
        status=200,
        headers=_json_headers(),
    )


def _list_my_routes_paginated(
    helper: FirestoreHelper,
    user_id: str,
    raw_limit: str | None,
    raw_start_after_doc_id: str | None,
) -> https_fn.Response:
    requested_limit = _parse_limit(raw_limit)
    start_after_doc_id = _parse_start_after_doc_id(raw_start_after_doc_id)

    collection_path = (
        f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
    )

    docs_all_routes = helper.query_documents(collection_path)
    distance_total = _compute_distance_total(docs_all_routes)

    query_limit = requested_limit + 1
    docs = helper.query_documents(
        collection_path,
        order_by=[("createdAt", "desc")],
        limit=query_limit,
        start_after_doc_id=start_after_doc_id,
    )

    has_more = len(docs) > requested_limit
    docs_page = docs[:requested_limit]

    items = [_serialize_list_item(doc_id, doc_data) for doc_id, doc_data in docs_page]
    for item in items:
        item["distanceTotal"] = distance_total
    last_doc_id = docs_page[-1][0] if has_more and docs_page else None

    body = PaginatedResponse.create(
        items,
        limit=requested_limit,
        page=1,
        has_more=has_more,
        last_doc_id=last_doc_id,
    ).to_dict()

    return https_fn.Response(
        json.dumps(body, ensure_ascii=False),
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
    track_styles_path = (
        f"{route_collection_path}/{route_id}/{FirestoreCollections.MY_ROUTE_TRACK_STYLES}"
    )
    points = [_serialize_doc(doc_id, doc_data) for doc_id, doc_data in helper.query_documents(points_path)]
    notes = [_serialize_doc(doc_id, doc_data) for doc_id, doc_data in helper.query_documents(notes_path)]
    track_styles = [
        _serialize_doc(doc_id, doc_data)
        for doc_id, doc_data in helper.query_documents(track_styles_path)
    ]
    track_styles.sort(key=_track_style_sort_key)

    body = _serialize_route_detail(route_id, route_doc)
    body["points"] = points
    body["notes"] = notes
    body["trackStyles"] = track_styles
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

        has_pagination_params = (
            req.args.get("limit") is not None
            or req.args.get("startAfterDocId") is not None
        )
        if not has_pagination_params:
            return _list_my_routes(helper, user_id)

        return _list_my_routes_paginated(
            helper,
            user_id,
            raw_limit=req.args.get("limit"),
            raw_start_after_doc_id=req.args.get("startAfterDocId"),
        )
    except ValueError as e:
        logging.error("get_my_routes: Error de validación: %s", e)
        return https_fn.Response("", status=400, headers=_cors_headers())
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("get_my_routes: Error interno: %s", e, exc_info=True)
        return https_fn.Response("", status=500, headers=_cors_headers())
