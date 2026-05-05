"""
Router central para API de rutas.

Paths soportados:
- POST   /api/routes/{userId}/create
- PUT    /api/routes/{userId}/update
- GET    /api/routes/{userId}/get
- GET    /api/routes/{userId}/list
- DELETE /api/routes/{userId}/delete
- GET    /api/routes/{userId}/event-categories
- GET    /api/routes/{userId}/event-days

El userId va en la URL (no se extrae del token). El token se valida solo
para autenticación; la autorización de ownership se verifica en cada handler.
"""

import logging

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from . import route_handlers
from .create_event_route import handle_create
from .get_event_route import handle_get
from .list_event_route import handle_list
from .update_event_route import handle_update

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[route_route]"

_ACTION_CREATE = "create"
_ACTION_UPDATE = "update"
_ACTION_GET = "get"
_ACTION_LIST = "list"
_ACTION_DELETE = "delete"
_ACTION_EVENT_CATEGORIES = "event_categories"
_ACTION_EVENT_DAYS = "event_days"

_GET_ACTIONS = {
    "get": _ACTION_GET,
    "list": _ACTION_LIST,
    "event-categories": _ACTION_EVENT_CATEGORIES,
    "event-days": _ACTION_EVENT_DAYS,
}

_HANDLERS = {
    _ACTION_CREATE: handle_create,
    _ACTION_UPDATE: handle_update,
    _ACTION_GET: handle_get,
    _ACTION_LIST: handle_list,
    _ACTION_DELETE: route_handlers.handle_delete,
    _ACTION_EVENT_CATEGORIES: route_handlers.handle_event_categories,
    _ACTION_EVENT_DAYS: route_handlers.handle_event_days,
}


def _resolve_action_and_user(path: str, method: str) -> tuple[str | None, str | None]:
    """
    Extrae la acción y el userId del path.

    Formato esperado: /api/routes/{userId}/{action}
    Retorna (accion, user_id) o (None, None) si el path no coincide.
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]

    if len(parts) < 4 or parts[0] != "api" or parts[1] != "routes":
        return None, None

    user_id = parts[2].strip()
    if not user_id:
        return None, None

    segment = parts[3]

    if method == "POST" and segment == "create":
        return _ACTION_CREATE, user_id
    if method == "PUT" and segment == "update":
        return _ACTION_UPDATE, user_id
    if method == "DELETE" and segment == "delete":
        return _ACTION_DELETE, user_id
    if method == "GET":
        action = _GET_ACTIONS.get(segment)
        if action:
            return action, user_id
        return None, None

    return None, None


@https_fn.on_request(region="us-central1")
def route_route(req: https_fn.Request) -> https_fn.Response:
    """
    Router único de routes. Valida token una vez y despacha por path.

    Headers: Authorization Bearer (requerido)
    """
    validation_response = validate_request(
        req,
        ["GET", "POST", "PUT", "DELETE"],
        "route_route",
        return_json_error=False,
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "route_route"):
        LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    action, user_id = _resolve_action_and_user(path, req.method)

    if action is None or not user_id:
        LOG.warning("%s Path no reconocido: %s %s", LOG_PREFIX, req.method, path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req, user_id)
