"""
Router central para API de staff.

Paths soportados:
- POST /api/create_staff_user (legacy)

Valida CORS, método HTTP y Bearer token una sola vez; luego despacha por path
y método reutilizando los handlers existentes de staff sin duplicar lógica.
"""

import logging
from contextlib import contextmanager
from unittest.mock import patch

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from . import create_staff_user as create_staff_user_module

_ACTION_CREATE_STAFF_USER_LEGACY = "create_staff_user_legacy"


def _action_from_path(path: str, method: str) -> str | None:
    """Determina la acción por path público y método HTTP."""
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if method == "POST" and len(parts) == 2 and parts[0] == "api" and parts[1] == "create_staff_user":
        return _ACTION_CREATE_STAFF_USER_LEGACY
    return None


@contextmanager
def _bypass_handler_auth_validation(module):
    """Bypassea validaciones en handlers internos para evitar doble validación."""
    with patch.object(module, "validate_request", return_value=None):
        if hasattr(module, "verify_bearer_token"):
            with patch.object(module, "verify_bearer_token", return_value=True):
                yield
        else:
            yield


def _dispatch_create_staff_user_legacy(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(create_staff_user_module):
        return create_staff_user_module.create_staff_user(req)


_HANDLERS = {
    _ACTION_CREATE_STAFF_USER_LEGACY: _dispatch_create_staff_user_legacy,
}


@https_fn.on_request()
def staff_route(req: https_fn.Request) -> https_fn.Response:
    """Router único de staff. Valida una vez y despacha por path+método."""
    validation_response = validate_request(
        req, ["POST"], "staff_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "staff_route"):
        logging.warning("staff_route: Token inválido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    action = _action_from_path(path, req.method)
    if action is None:
        logging.warning("staff_route: Path no reconocido: %s", path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req)
