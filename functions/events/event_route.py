"""
Router central para API de events (consultas públicas).

Paths soportados:
- GET /api/events
- GET /api/events/{userId}/list (userId en path, no del token; query opcional status=)
- GET /api/events/detail
- GET /api/event/event-categories/**

Valida CORS, método HTTP y Bearer token una sola vez; luego despacha por path.
"""

import logging
from contextlib import contextmanager
from unittest.mock import patch

from firebase_functions import https_fn
from event_management.list_events import handle_list
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from . import event_categories as event_categories_module
from . import events_customer as events_customer_module
from . import events_detail_customer as events_detail_customer_module

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[event_route]"

_ACTION_EVENTS = "events"
_ACTION_EVENTS_LIST = "events_list"
_ACTION_EVENT_DETAIL = "event_detail"
_ACTION_EVENT_CATEGORIES = "event_categories"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _action_from_path(path: str, method: str) -> str | None:
    """
    Determina la acción a partir del path para rutas públicas de events.

    - /api/events           -> events
    - /api/events/{userId}/list -> events_list
    - /api/events/detail    -> event_detail
    - /api/event/event-categories/** -> event_categories
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if not parts:
        return None

    if len(parts) >= 2 and parts[0] == "api" and parts[1] == "events":
        if len(parts) == 2:
            return _ACTION_EVENTS
        if len(parts) == 4 and parts[3] == "list":
            return _ACTION_EVENTS_LIST
        if len(parts) >= 3 and parts[2] == "detail":
            return _ACTION_EVENT_DETAIL

    if (
        method == "GET"
        and len(parts) >= 4
        and parts[0] == "api"
        and parts[1] == "event"
        and parts[2] == "event-categories"
    ):
        return _ACTION_EVENT_CATEGORIES

    return None


@contextmanager
def _bypass_handler_auth_validation(module):
    """
    Bypasea las validaciones internas del handler para evitar doble validación.
    El router ya validó CORS, método y Bearer token antes de llamar al handler.
    """
    with patch.object(module, "validate_request", return_value=None):
        if hasattr(module, "verify_bearer_token"):
            with patch.object(module, "verify_bearer_token", return_value=True):
                yield
        else:
            yield


def _dispatch_events(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(events_customer_module):
        return events_customer_module.events(req)


def _dispatch_event_detail(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(events_detail_customer_module):
        return events_detail_customer_module.event_detail(req)


def _dispatch_event_categories(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(event_categories_module):
        return event_categories_module.event_categories(req)


def _dispatch_events_list(req: https_fn.Request) -> https_fn.Response:
    """Lista eventos con creator == userId del path (el userId no se toma del token)."""
    path = getattr(req, "path", "") or ""
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) != 4 or parts[3] != "list":
        LOG.warning("%s Path list inválido: %s", LOG_PREFIX, path)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
    user_id = parts[2].strip()
    if not user_id:
        LOG.warning("%s userId vacío en path list", LOG_PREFIX)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})
    return handle_list(req, user_id)


_HANDLERS = {
    _ACTION_EVENTS: _dispatch_events,
    _ACTION_EVENTS_LIST: _dispatch_events_list,
    _ACTION_EVENT_DETAIL: _dispatch_event_detail,
    _ACTION_EVENT_CATEGORIES: _dispatch_event_categories,
}


# ============================================================================
# CLOUD FUNCTION
# ============================================================================


@https_fn.on_request()
def event_route(req: https_fn.Request) -> https_fn.Response:
    """
    Router único de events (consultas públicas). Valida una vez y despacha por path.
    """
    validation_response = validate_request(
        req, ["GET"], "event_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "event_route"):
        LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=401, headers={"Access-Control-Allow-Origin": "*"})

    path = getattr(req, "path", "") or ""
    action = _action_from_path(path, req.method)

    if action is None:
        LOG.warning("%s Path no reconocido: %s", LOG_PREFIX, path)
        return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

    return _HANDLERS[action](req)
