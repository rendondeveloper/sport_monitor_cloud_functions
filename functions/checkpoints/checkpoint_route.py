"""
Router central para API de checkpoints.

Paths soportados:
- GET /api/checkpoint/dayofrace/active/**
- GET /api/checkpoint/**/event/**
- GET /api/checkpoint/all-competitor-tracking/**
- GET /api/checkpoint/competitor-tracking/**
- GET /api/checkpoint/days-of-race/**
- PUT /api/checkpoint/update-competitor-status/**
- PUT /api/checkpoint/change-competitor-status

Valida CORS, método HTTP y Bearer token una sola vez; luego despacha por path
y método reutilizando los handlers existentes de checkpoints sin duplicar lógica.
"""

import logging
from contextlib import contextmanager
from unittest.mock import patch

from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from . import all_competitor_tracking as all_competitor_tracking_module
from . import change_competitor_status as change_competitor_status_module
from . import checkpoint as checkpoint_module
from . import competitor_tracking as competitor_tracking_module
from . import day_of_race_active as day_of_race_active_module
from . import days_of_race as days_of_race_module
from . import update_competitor_status as update_competitor_status_module

_ACTION_DAY_OF_RACE_ACTIVE = "day_of_race_active"
_ACTION_CHECKPOINT = "checkpoint"
_ACTION_ALL_COMPETITOR_TRACKING = "all_competitor_tracking"
_ACTION_COMPETITOR_TRACKING = "competitor_tracking"
_ACTION_DAYS_OF_RACE = "days_of_race"
_ACTION_UPDATE_COMPETITOR_STATUS = "update_competitor_status"
_ACTION_CHANGE_COMPETITOR_STATUS = "change_competitor_status"


def _action_from_path(path: str, method: str) -> str | None:
    """Determina la acción por path público y método HTTP."""
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if len(parts) < 3 or parts[0] != "api" or parts[1] != "checkpoint":
        return None

    if method == "GET":
        if len(parts) >= 5 and parts[2] == "dayofrace" and parts[3] == "active":
            return _ACTION_DAY_OF_RACE_ACTIVE
        if len(parts) >= 4 and parts[2] == "all-competitor-tracking":
            return _ACTION_ALL_COMPETITOR_TRACKING
        if len(parts) >= 4 and parts[2] == "competitor-tracking":
            return _ACTION_COMPETITOR_TRACKING
        if len(parts) >= 4 and parts[2] == "days-of-race":
            return _ACTION_DAYS_OF_RACE
        if len(parts) >= 5 and "event" in parts[2:]:
            return _ACTION_CHECKPOINT

    if method == "PUT":
        if len(parts) >= 4 and parts[2] == "update-competitor-status":
            return _ACTION_UPDATE_COMPETITOR_STATUS
        if len(parts) == 3 and parts[2] == "change-competitor-status":
            return _ACTION_CHANGE_COMPETITOR_STATUS

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


def _dispatch_day_of_race_active(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(day_of_race_active_module):
        return day_of_race_active_module.day_of_race_active(req)


def _dispatch_checkpoint(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(checkpoint_module):
        return checkpoint_module.checkpoint(req)


def _dispatch_all_competitor_tracking(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(all_competitor_tracking_module):
        return all_competitor_tracking_module.all_competitor_tracking(req)


def _dispatch_competitor_tracking(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(competitor_tracking_module):
        return competitor_tracking_module.competitor_tracking(req)


def _dispatch_days_of_race(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(days_of_race_module):
        return days_of_race_module.days_of_race(req)


def _dispatch_update_competitor_status(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(update_competitor_status_module):
        return update_competitor_status_module.update_competitor_status(req)


def _dispatch_change_competitor_status(req: https_fn.Request) -> https_fn.Response:
    with _bypass_handler_auth_validation(change_competitor_status_module):
        return change_competitor_status_module.change_competitor_status(req)


_HANDLERS = {
    _ACTION_DAY_OF_RACE_ACTIVE: _dispatch_day_of_race_active,
    _ACTION_CHECKPOINT: _dispatch_checkpoint,
    _ACTION_ALL_COMPETITOR_TRACKING: _dispatch_all_competitor_tracking,
    _ACTION_COMPETITOR_TRACKING: _dispatch_competitor_tracking,
    _ACTION_DAYS_OF_RACE: _dispatch_days_of_race,
    _ACTION_UPDATE_COMPETITOR_STATUS: _dispatch_update_competitor_status,
    _ACTION_CHANGE_COMPETITOR_STATUS: _dispatch_change_competitor_status,
}


@https_fn.on_request()
def checkpoint_route(req: https_fn.Request) -> https_fn.Response:
    """Router único de checkpoints. Valida una vez y despacha por path+método."""
    validation_response = validate_request(
        req, ["GET", "PUT"], "checkpoint_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "checkpoint_route"):
        logging.warning("checkpoint_route: Token inválido o faltante")
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    action = _action_from_path(path, req.method)
    if action is None:
        logging.warning("checkpoint_route: Path no reconocido: %s", path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req)
