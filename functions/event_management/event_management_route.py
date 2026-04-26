"""
Router para la API de gestión de eventos por propietario.

Solo el creador de un evento puede crear, actualizar, obtener, listar,
eliminar o gestionar su información adicional.

Paths soportados:
- POST   /api/event-management/{userId}/create
- PUT    /api/event-management/{userId}/update
- GET    /api/event-management/{userId}/get?eventId=
- GET    /api/event-management/{userId}/list[?status=]
- DELETE /api/event-management/{userId}/delete?eventId=
- GET    /api/event-management/{userId}/get-info?eventId=
- POST   /api/event-management/{userId}/save-info

Valida CORS, método HTTP y Bearer token una sola vez. El `user_id` va en la
URL del path (no se obtiene del token); luego se despacha al handler por path + método.
"""

import logging

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from .create_event import handle_create
from .delete_event import handle_delete
from .get_event import handle_get
from .get_event_info import handle_get_info
from .list_events import handle_list
from .save_event_info import handle_save_info
from .update_event import handle_update

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[event_management_route]"

_BASE = "event-management"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _resolve_action_and_user(path: str, method: str) -> tuple[str | None, str | None]:
    """
    Determina la acción a partir del path y el método HTTP.

    Retorna (accion, user_id). Si el path no coincide, retorna (None, None).
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]

    if len(parts) < 4:
        return None, None
    if parts[0] != "api" or parts[1] != _BASE:
        return None, None

    user_id = parts[2].strip()
    if not user_id:
        return None, None

    segment = parts[3]

    if method == "POST" and segment == "create":
        return "create", user_id
    if method == "PUT" and segment == "update":
        return "update", user_id
    if method == "GET" and segment == "get":
        return "get", user_id
    if method == "GET" and segment == "list":
        return "list", user_id
    if method == "DELETE" and segment == "delete":
        return "delete", user_id
    if method == "GET" and segment == "get-info":
        return "get_info", user_id
    if method == "POST" and segment == "save-info":
        return "save_info", user_id

    return None, None


def _dispatch(action: str, req: https_fn.Request, user_id: str) -> https_fn.Response:
    """Despacha al handler correspondiente según la acción."""
    if action == "create":
        return handle_create(req, user_id)
    if action == "update":
        return handle_update(req, user_id)
    if action == "get":
        return handle_get(req, user_id)
    if action == "list":
        return handle_list(req, user_id)
    if action == "delete":
        return handle_delete(req, user_id)
    if action == "get_info":
        return handle_get_info(req, user_id)
    return handle_save_info(req, user_id)


# ============================================================================
# CLOUD FUNCTION
# ============================================================================


@https_fn.on_request()
def event_management_route(req: https_fn.Request) -> https_fn.Response:
    """
    Router único de event-management. Valida una vez y despacha por path.

    Headers: Authorization Bearer (requerido)
    """
    validation_response = validate_request(
        req, ["GET", "POST", "PUT", "DELETE"], "event_management_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "event_management_route"):
        LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})

    path = getattr(req, "path", "") or ""
    action, user_id = _resolve_action_and_user(path, req.method)

    if action is None or not user_id:
        LOG.warning("%s Path no reconocido: %s %s", LOG_PREFIX, req.method, path)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

    return _dispatch(action, req, user_id)
