"""
Router central para API de events.

Paths soportados:
- GET /api/events
- GET /api/events/detail
- GET /api/event/event-categories/**

Valida CORS, método HTTP y Bearer token una sola vez; luego despacha por path
reutilizando los handlers existentes de events sin duplicar su lógica.
"""

import logging
from contextlib import contextmanager
from unittest.mock import patch

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from . import event_categories as event_categories_module
from . import events_customer as events_customer_module
from . import events_detail_customer as events_detail_customer_module

_ACTION_EVENTS = "events"
_ACTION_EVENT_DETAIL = "event_detail"
_ACTION_EVENT_CATEGORIES = "event_categories"


def _action_from_path(path: str) -> str | None:
    """
    Determina la acción por path público.

    - /api/events -> events
    - /api/events/detail -> event_detail
    - /api/event/event-categories/** -> event_categories
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if not parts:
        return None

    if len(parts) >= 2 and parts[0] == "api" and parts[1] == "events":
        if len(parts) == 2:
            return _ACTION_EVENTS
        if len(parts) >= 3 and parts[2] == "detail":
            return _ACTION_EVENT_DETAIL

    if (
        len(parts) >= 4
        and parts[0] == "api"
        and parts[1] == "event"
        and parts[2] == "event-categories"
    ):
        return _ACTION_EVENT_CATEGORIES

    return None


@contextmanager
def _bypass_handler_auth_validation(module):
    """
    Bypassea validaciones en handlers internos para evitar doble validación.
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


_HANDLERS = {
    _ACTION_EVENTS: _dispatch_events,
    _ACTION_EVENT_DETAIL: _dispatch_event_detail,
    _ACTION_EVENT_CATEGORIES: _dispatch_event_categories,
}


@https_fn.on_request()
def event_route(req: https_fn.Request) -> https_fn.Response:
    """
    Router único de events. Valida una vez y despacha por path.
    """
    validation_response = validate_request(
        req, ["GET"], "event_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "event_route"):
        logging.warning("event_route: Token inválido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    action = _action_from_path(path)
    if action is None:
        logging.warning("event_route: Path no reconocido: %s", path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req)
