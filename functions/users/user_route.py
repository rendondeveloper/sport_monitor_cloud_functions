"""
Router central para API de usuarios: /api/users/read, /api/users/profile, /api/users/{section}, /api/users/subscribedEvents, /api/users/create, /api/users/update.

Secciones: personalData, healthData, emergencyContacts, vehicles, membership (GET /api/users/{section}).
DELETE solo para emergencyContacts y vehicles (/api/users/{section}?userId=xxx&id=docId).
Valida CORS, método HTTP y Bearer token una vez; despacha por path a create.handle, read.handle, read_sections.handle, delete_section_item.handle o update.handle.
"""

import logging
from typing import Tuple

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from .create import handle as create_handle
from .delete_section_item import DELETE_ALLOWED_SECTIONS, handle as delete_section_item_handle
from .read import handle as read_handle
from .read_sections import ALLOWED_SECTIONS, handle as read_sections_handle
from .subscribed_events import handle as subscribed_events_handle
from .update import handle as update_handle

_ACTION_READ = "read"
_ACTION_READ_SECTION = "read_section"
_ACTION_SUBSCRIBED_EVENTS = "subscribedevents"
_ACTION_CREATE = "create"
_ACTION_UPDATE = "update"

# path segment -> (allowed_method, handler)
_ROUTES = {
    _ACTION_READ: ("GET", read_handle),
    _ACTION_SUBSCRIBED_EVENTS: ("GET", subscribed_events_handle),
    _ACTION_CREATE: ("POST", create_handle),
    _ACTION_UPDATE: ("PUT", update_handle),
}


def _action_from_path(path: str) -> Tuple[str | None, str | None]:
    """
    Extrae (acción, sección) del path.
    - /api/users/{section} (section en ALLOWED_SECTIONS) -> ("read_section", section)
    - read, profile -> ("read", None)
    - create, update -> (acción, None)
    Rutas de sección: /api/users/personalData, /api/users/healthData, etc.
    """
    if not path:
        return (None, None)
    path = (path or "").strip()
    parts = [p for p in path.strip("/").split("/") if p]
    if "users" in parts:
        idx = parts.index("users")
        if idx + 1 >= len(parts):
            return (None, None)
        segment = parts[idx + 1]
        if segment in ALLOWED_SECTIONS:
            return (_ACTION_READ_SECTION, segment)
        segment_lower = segment.lower()
        if segment_lower == "profile":
            if idx + 2 < len(parts) and parts[idx + 2] in ALLOWED_SECTIONS:
                return (_ACTION_READ_SECTION, parts[idx + 2])
            return (_ACTION_READ, None)
        if segment_lower in _ROUTES:
            return (segment_lower, None)
    # Fallback: path puede llegar solo como segmento (ej. "personalData")
    if len(parts) == 1 and parts[0] in ALLOWED_SECTIONS:
        return (_ACTION_READ_SECTION, parts[0])
    return (None, None)


@https_fn.on_request()
def user_route(req: https_fn.Request) -> https_fn.Response:
    """
    Una sola Cloud Function para users: valida token y despacha por path.
    Paths: /api/users/read, /api/users/profile (GET), /api/users/{section} (GET o DELETE), /api/users/subscribedEvents (GET), /api/users/create (POST), /api/users/update (PUT).
    """
    validation_response = validate_request(
        req, ["GET", "POST", "PUT", "DELETE"], "user_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "user_route"):
        logging.warning("user_route: Token inválido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    logging.info("user_route: Path recibido: %r", path)
    action, section = _action_from_path(path)
    if action is None:
        logging.warning("user_route: Path no reconocido: %s", path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    if action == _ACTION_READ_SECTION:
        if req.method == "GET":
            logging.info("user_route: Despachando read_section section=%s", section)
            return read_sections_handle(req, section)
        if req.method == "DELETE":
            if section not in DELETE_ALLOWED_SECTIONS:
                logging.warning(
                    "user_route: DELETE no permitido para sección %s (solo emergencyContacts, vehicles)",
                    section,
                )
                return https_fn.Response(
                    "",
                    status=405,
                    headers={
                        "Allow": "GET, DELETE",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            logging.info("user_route: Despachando delete_section_item section=%s", section)
            return delete_section_item_handle(req, section)
        logging.warning(
            "user_route: Método %s no permitido para read_section (esperado GET o DELETE)",
            req.method,
        )
        return https_fn.Response(
            "",
            status=405,
            headers={"Allow": "GET, DELETE", "Access-Control-Allow-Origin": "*"},
        )

    allowed_method, handler = _ROUTES[action]
    if req.method != allowed_method:
        logging.warning(
            "user_route: Método %s no permitido para %s (esperado %s)",
            req.method,
            action,
            allowed_method,
        )
        return https_fn.Response(
            "",
            status=405,
            headers={
                "Allow": allowed_method,
                "Access-Control-Allow-Origin": "*",
            },
        )

    return handler(req)
