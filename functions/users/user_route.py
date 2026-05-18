"""
Router central para API de usuarios: /api/users/read, /api/users/profile, /api/users/{section}, /api/users/subscribedEvents, /api/users/create, /api/users/update, /api/users/my-routes.

Secciones: personalData, healthData, emergencyContacts, vehicles, membership (GET /api/users/{section}).
DELETE solo para emergencyContacts y vehicles (/api/users/{section}?userId=xxx&id=docId).
Rutas my-routes: POST/GET en /api/users/my-routes; PUT/DELETE en /api/users/my-routes/{routeId}/notes; DELETE en /api/users/my-routes/{routeId}.
Valida CORS, método HTTP y Bearer token una vez; despacha por path a create.handle, read.handle, read_sections.handle, delete_section_item.handle, update.handle, create_my_route.handle, get_my_routes.handle (detalle con points, notes y trackStyles), update_my_route_notes, delete_my_route_notes o delete_my_route.
"""

import logging
from typing import Tuple

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from .create import handle as create_handle
from .create_my_route import handle as create_my_route_handle
from .delete_my_route import handle as delete_my_route_handle
from .delete_my_route_notes import handle as delete_my_route_notes_handle
from .delete_section_item import DELETE_ALLOWED_SECTIONS, handle as delete_section_item_handle
from .get_my_routes import handle as get_my_routes_handle
from .read import handle as read_handle
from .read_sections import ALLOWED_SECTIONS, handle as read_sections_handle
from .subscribed_events import handle as subscribed_events_handle
from .update import handle as update_handle
from .update_my_route_notes import handle as update_my_route_notes_handle

_ACTION_READ = "read"
_ACTION_READ_SECTION = "read_section"
_ACTION_SUBSCRIBED_EVENTS = "subscribedevents"
_ACTION_CREATE = "create"
_ACTION_UPDATE = "update"
_ACTION_MY_ROUTES = "my-routes"

# path segment -> (allowed_method, handler)
_ROUTES = {
    _ACTION_READ: ("GET", read_handle),
    _ACTION_SUBSCRIBED_EVENTS: ("GET", subscribed_events_handle),
    _ACTION_CREATE: ("POST", create_handle),
    _ACTION_UPDATE: ("PUT", update_handle),
    _ACTION_MY_ROUTES: ("GET_OR_POST", None),
}


def _action_from_path(path: str) -> Tuple[str | None, str | None]:
    """
    Extrae (acción, sección) del path.
    - /api/users/{section} (section en ALLOWED_SECTIONS) -> ("read_section", section)
    - read, profile -> ("read", None)
    - create, update, my-routes -> (acción, None)
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


def _extract_my_route_notes_route_id(path: str) -> str | None:
    """
    Extrae routeId de /api/users/my-routes/{routeId}/notes.
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    # Esperado: ["api", "users", "my-routes", "{routeId}", "notes"]
    if len(parts) >= 5 and parts[1] == "users" and parts[2] == "my-routes" and parts[4] == "notes":
        return parts[3].strip() or None
    return None


def _extract_my_route_delete_route_id(path: str) -> str | None:
    """
    Extrae routeId de DELETE /api/users/my-routes/{routeId} (exactamente 4 segmentos).
    No debe coincidir con paths que tengan más segmentos (p. ej. .../notes).
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if len(parts) != 4:
        return None
    if parts[0] != "api" or parts[1] != "users" or parts[2] != "my-routes":
        return None
    return parts[3].strip() or None


@https_fn.on_request()
def user_route(req: https_fn.Request) -> https_fn.Response:
    """
    Una sola Cloud Function para users: valida token y despacha por path.
    Paths: /api/users/read, /api/users/profile (GET), /api/users/{section} (GET o DELETE), /api/users/subscribedEvents (GET), /api/users/create (POST), /api/users/update (PUT), /api/users/my-routes (GET/POST), /api/users/my-routes/{routeId} (DELETE), /api/users/my-routes/{routeId}/notes (PUT/DELETE).
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

    route_id_for_notes = _extract_my_route_notes_route_id(path)
    if route_id_for_notes is not None:
        if req.method == "DELETE":
            return delete_my_route_notes_handle(req, route_id_for_notes)
        if req.method == "PUT":
            return update_my_route_notes_handle(req, route_id_for_notes)
        return https_fn.Response(
            "",
            status=405,
            headers={
                "Allow": "PUT, DELETE",
                "Access-Control-Allow-Origin": "*",
            },
        )

    route_id_for_delete_route = _extract_my_route_delete_route_id(path)
    if route_id_for_delete_route is not None:
        if req.method == "DELETE":
            return delete_my_route_handle(req, route_id_for_delete_route)
        return https_fn.Response(
            "",
            status=405,
            headers={
                "Allow": "DELETE",
                "Access-Control-Allow-Origin": "*",
            },
        )

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

    if action == _ACTION_MY_ROUTES:
        if req.method == "POST":
            return create_my_route_handle(req)
        if req.method == "GET":
            return get_my_routes_handle(req)
        return https_fn.Response(
            "",
            status=405,
            headers={
                "Allow": "GET, POST",
                "Access-Control-Allow-Origin": "*",
            },
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
