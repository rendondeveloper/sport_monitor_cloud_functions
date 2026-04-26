"""
Router central para API de rutas.

Paths soportados:
- POST /api/routes/create
- PUT /api/routes/update
- GET /api/routes/get
- GET /api/routes/list
- DELETE /api/routes/delete
- GET /api/routes/event-categories
- GET /api/routes/event-days
"""

import logging

from firebase_functions import https_fn
from utils.helper_http import get_bearer_uid, verify_bearer_token
from utils.helper_http_verb import validate_request

from . import route_handlers

_ACTION_CREATE = "create"
_ACTION_UPDATE = "update"
_ACTION_GET = "get"
_ACTION_LIST = "list"
_ACTION_DELETE = "delete"
_ACTION_EVENT_CATEGORIES = "event_categories"
_ACTION_EVENT_DAYS = "event_days"

_GET_ROUTES = {
    "get": _ACTION_GET,
    "list": _ACTION_LIST,
    "event-categories": _ACTION_EVENT_CATEGORIES,
    "event-days": _ACTION_EVENT_DAYS,
}

_HANDLERS = {
    _ACTION_CREATE: route_handlers.handle_create,
    _ACTION_UPDATE: route_handlers.handle_update,
    _ACTION_GET: route_handlers.handle_get,
    _ACTION_LIST: route_handlers.handle_list,
    _ACTION_DELETE: route_handlers.handle_delete,
    _ACTION_EVENT_CATEGORIES: route_handlers.handle_event_categories,
    _ACTION_EVENT_DAYS: route_handlers.handle_event_days,
}


def _action_from_path(path: str, method: str) -> str | None:
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if len(parts) < 3 or parts[0] != "api" or parts[1] != "routes":
        return None
    endpoint = parts[2]

    if method == "POST" and endpoint == "create":
        return _ACTION_CREATE
    if method == "PUT" and endpoint == "update":
        return _ACTION_UPDATE
    if method == "DELETE" and endpoint == "delete":
        return _ACTION_DELETE
    if method == "GET":
        return _GET_ROUTES.get(endpoint)
    return None


@https_fn.on_request()
def route_route(req: https_fn.Request) -> https_fn.Response:
    validation_response = validate_request(
        req,
        ["GET", "POST", "PUT", "DELETE"],
        "route_route",
        return_json_error=False,
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "route_route"):
        logging.warning("route_route: Token inválido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    user_id = get_bearer_uid(req, "route_route")
    if not user_id:
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    action = _action_from_path(getattr(req, "path", "") or "", req.method)
    if action is None:
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req, user_id)
