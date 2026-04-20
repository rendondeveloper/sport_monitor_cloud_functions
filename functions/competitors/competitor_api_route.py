"""
Router central para API de competitors.

Paths soportados:
- GET /api/competitors/competitor-route
- GET /api/competitors/competitor-route/**
- POST /api/competitors/create-user
- DELETE /api/competitors/delete-competitor
- DELETE /api/competitors/delete-user
- GET /api/competitors/get-competitor-by-email
- GET /api/competitors/get-event-competitor-by-email
- GET /api/competitors/get-event-competitor-by-id
- GET /api/competitors/get-competitor-by-id
- GET /api/competitors/get-competitor-by-id/**
- GET /api/competitors/get-competitors-by-event
- GET /api/competitors/get-competitors-by-event/**
- GET /api/competitors/list-competitors-by-event
- GET /api/competitors/list-competitors-by-event/**
- POST /api/create_competitor (legacy web)

Valida CORS, método HTTP y Bearer token una sola vez; luego despacha por path
y método reutilizando los handlers existentes de competitors sin duplicar lógica.
"""

import logging
from contextlib import contextmanager
from unittest.mock import patch

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from . import competitor_route as competitor_route_module
from . import create_competitor as create_competitor_module
from . import create_competitor_user as create_competitor_user_module
from . import delete_competitor as delete_competitor_module
from . import delete_competitor_user as delete_competitor_user_module
from . import get_competitor_by_email as get_competitor_by_email_module
from . import get_competitor_by_id as get_competitor_by_id_module
from . import get_competitors_by_event as get_competitors_by_event_module
from . import get_event_competitor_by_email as get_event_competitor_by_email_module
from . import get_event_competitor_by_id as get_event_competitor_by_id_module
from . import list_competitors_by_event as list_competitors_by_event_module

_ACTION_COMPETITOR_ROUTE = "competitor_route"
_ACTION_CREATE_COMPETITOR_USER = "create_competitor_user"
_ACTION_DELETE_COMPETITOR = "delete_competitor"
_ACTION_DELETE_COMPETITOR_USER = "delete_competitor_user"
_ACTION_GET_COMPETITOR_BY_EMAIL = "get_competitor_by_email"
_ACTION_GET_EVENT_COMPETITOR_BY_EMAIL = "get_event_competitor_by_email"
_ACTION_GET_EVENT_COMPETITOR_BY_ID = "get_event_competitor_by_id"
_ACTION_GET_COMPETITOR_BY_ID = "get_competitor_by_id"
_ACTION_GET_COMPETITORS_BY_EVENT = "get_competitors_by_event"
_ACTION_LIST_COMPETITORS_BY_EVENT = "list_competitors_by_event"
_ACTION_CREATE_COMPETITOR_LEGACY = "create_competitor_legacy"


def _action_from_path(path: str, method: str) -> str | None:
    """Determina la acción por path público y método HTTP."""
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if not parts:
        return None

    if method == "POST" and len(parts) == 2 and parts[0] == "api" and parts[1] == "create_competitor":
        return _ACTION_CREATE_COMPETITOR_LEGACY

    if len(parts) < 3 or parts[0] != "api" or parts[1] != "competitors":
        return None

    endpoint = parts[2]
    if method == "GET":
        if endpoint == "competitor-route":
            return _ACTION_COMPETITOR_ROUTE
        if endpoint == "get-competitor-by-email":
            return _ACTION_GET_COMPETITOR_BY_EMAIL
        if endpoint == "get-event-competitor-by-email":
            return _ACTION_GET_EVENT_COMPETITOR_BY_EMAIL
        if endpoint == "get-event-competitor-by-id":
            return _ACTION_GET_EVENT_COMPETITOR_BY_ID
        if endpoint == "get-competitor-by-id":
            return _ACTION_GET_COMPETITOR_BY_ID
        if endpoint == "get-competitors-by-event":
            return _ACTION_GET_COMPETITORS_BY_EVENT
        if endpoint == "list-competitors-by-event":
            return _ACTION_LIST_COMPETITORS_BY_EVENT

    if method == "POST" and endpoint == "create-user":
        return _ACTION_CREATE_COMPETITOR_USER

    if method == "DELETE":
        if endpoint == "delete-competitor":
            return _ACTION_DELETE_COMPETITOR
        if endpoint == "delete-user":
            return _ACTION_DELETE_COMPETITOR_USER

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


def _dispatch_competitor_route(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(competitor_route_module):
        return competitor_route_module.competitor_route(req)


def _dispatch_create_competitor_user(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(create_competitor_user_module):
        return create_competitor_user_module.create_competitor_user(req)


def _dispatch_delete_competitor(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(delete_competitor_module):
        return delete_competitor_module.delete_competitor(req)


def _dispatch_delete_competitor_user(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(delete_competitor_user_module):
        return delete_competitor_user_module.delete_competitor_user(req)


def _dispatch_get_competitor_by_email(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(get_competitor_by_email_module):
        return get_competitor_by_email_module.get_competitor_by_email(req)


def _dispatch_get_event_competitor_by_email(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(get_event_competitor_by_email_module):
        return get_event_competitor_by_email_module.get_event_competitor_by_email(req)


def _dispatch_get_event_competitor_by_id(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(get_event_competitor_by_id_module):
        return get_event_competitor_by_id_module.get_event_competitor_by_id(req)


def _dispatch_get_competitor_by_id(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(get_competitor_by_id_module):
        return get_competitor_by_id_module.get_competitor_by_id(req)


def _dispatch_get_competitors_by_event(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(get_competitors_by_event_module):
        return get_competitors_by_event_module.get_competitors_by_event(req)


def _dispatch_list_competitors_by_event(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(list_competitors_by_event_module):
        return list_competitors_by_event_module.list_competitors_by_event(req)


def _dispatch_create_competitor_legacy(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(create_competitor_module):
        return create_competitor_module.create_competitor(req)


_HANDLERS = {
    _ACTION_COMPETITOR_ROUTE: _dispatch_competitor_route,
    _ACTION_CREATE_COMPETITOR_USER: _dispatch_create_competitor_user,
    _ACTION_DELETE_COMPETITOR: _dispatch_delete_competitor,
    _ACTION_DELETE_COMPETITOR_USER: _dispatch_delete_competitor_user,
    _ACTION_GET_COMPETITOR_BY_EMAIL: _dispatch_get_competitor_by_email,
    _ACTION_GET_EVENT_COMPETITOR_BY_EMAIL: _dispatch_get_event_competitor_by_email,
    _ACTION_GET_EVENT_COMPETITOR_BY_ID: _dispatch_get_event_competitor_by_id,
    _ACTION_GET_COMPETITOR_BY_ID: _dispatch_get_competitor_by_id,
    _ACTION_GET_COMPETITORS_BY_EVENT: _dispatch_get_competitors_by_event,
    _ACTION_LIST_COMPETITORS_BY_EVENT: _dispatch_list_competitors_by_event,
    _ACTION_CREATE_COMPETITOR_LEGACY: _dispatch_create_competitor_legacy,
}


@https_fn.on_request()
def competitor_api_route(req: https_fn.Request) -> https_fn.Response:
    """Router único de competitors. Valida una vez y despacha por path+método."""
    validation_response = validate_request(
        req, ["GET", "POST", "DELETE"], "competitor_api_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "competitor_api_route"):
        logging.warning("competitor_api_route: Token inválido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    action = _action_from_path(path, req.method)
    if action is None:
        logging.warning("competitor_api_route: Path no reconocido: %s", path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req)
