"""
Router central para API de vehiculos: /api/vehicles, /api/vehicles/search, /api/vehicles/{vehicleId}.

GET /api/vehicles -- listar vehiculos del usuario.
POST /api/vehicles -- crear vehiculo.
GET /api/vehicles/search -- buscar vehiculo por branch, model, year.
PUT /api/vehicles/{vehicleId} -- actualizar vehiculo.
DELETE /api/vehicles/{vehicleId} -- eliminar vehiculo.

Valida CORS, metodo HTTP y Bearer token una vez; despacha por path a list.handle, create.handle,
search.handle, update.handle o delete.handle.
"""

import logging

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from .create import handle as create_handle
from .delete import handle as delete_handle
from .list import handle as list_handle
from .search import handle as search_handle
from .update import handle as update_handle

_ACTION_LIST = "list"
_ACTION_CREATE = "create"
_ACTION_SEARCH = "search"
_ACTION_UPDATE = "update"
_ACTION_DELETE = "delete"


def _action_from_request(path: str, method: str) -> str | None:
    """
    Determina la accion a partir del path y metodo HTTP.

    Path parsing:
    - /api/vehicles -> list (GET) | create (POST)
    - /api/vehicles/search -> search (GET)
    - /api/vehicles/{vehicleId} -> update (PUT) | delete (DELETE)
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]

    if "vehicles" not in parts:
        return None

    idx = parts.index("vehicles")
    remaining = parts[idx + 1:]

    if not remaining:
        if method == "GET":
            return _ACTION_LIST
        if method == "POST":
            return _ACTION_CREATE
        return None

    if remaining[0] == "search":
        if method == "GET":
            return _ACTION_SEARCH
        return None

    # /api/vehicles/{vehicleId}
    if method == "PUT":
        return _ACTION_UPDATE
    if method == "DELETE":
        return _ACTION_DELETE
    return None


_HANDLERS = {
    _ACTION_LIST: list_handle,
    _ACTION_CREATE: create_handle,
    _ACTION_SEARCH: search_handle,
    _ACTION_UPDATE: update_handle,
    _ACTION_DELETE: delete_handle,
}


@https_fn.on_request()
def vehicle_route(req: https_fn.Request) -> https_fn.Response:
    """
    Una sola Cloud Function para vehicles: valida token y despacha por path+metodo.

    Paths:
    - GET /api/vehicles -- listar
    - POST /api/vehicles -- crear
    - GET /api/vehicles/search -- buscar
    - PUT /api/vehicles/{vehicleId} -- actualizar
    - DELETE /api/vehicles/{vehicleId} -- eliminar
    """
    validation_response = validate_request(
        req, ["GET", "POST", "PUT", "DELETE"], "vehicle_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "vehicle_route"):
        logging.warning("vehicle_route: Token invalido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    logging.info("vehicle_route: Path recibido: %r, Method: %s", path, req.method)

    action = _action_from_request(path, req.method)
    if action is None:
        logging.warning("vehicle_route: Path/metodo no reconocido: %s %s", req.method, path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req)
