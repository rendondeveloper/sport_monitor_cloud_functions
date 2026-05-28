"""
Router para checklists de evento (paths planos).

- GET    /api/events/checklists/list
- GET    /api/events/checklists/get
- POST   /api/events/checklists/create
- PUT    /api/events/checklists/update
- PUT    /api/events/checklists/update-photos
- DELETE /api/events/checklists/delete
- GET    /api/events/checklists/participant-progress
"""

import logging

from firebase_functions import https_fn
from utils.helper_http import get_bearer_uid, verify_bearer_token
from utils.helper_http_verb import validate_request

from .create_checklist import handle_create
from .delete_checklist import handle_delete
from .get_checklist import handle_get
from .get_participant_progress import handle_participant_progress
from .list_checklists import handle_list
from .update_checklist import handle_update
from .update_checklist_photos import handle_update_photos

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[checklist_route]"

_ACTION_LIST = "list"
_ACTION_GET = "get"
_ACTION_CREATE = "create"
_ACTION_UPDATE = "update"
_ACTION_UPDATE_PHOTOS = "update_photos"
_ACTION_DELETE = "delete"
_ACTION_PROGRESS = "participant_progress"

_HANDLERS = {
    _ACTION_LIST: handle_list,
    _ACTION_GET: handle_get,
    _ACTION_CREATE: handle_create,
    _ACTION_UPDATE: handle_update,
    _ACTION_UPDATE_PHOTOS: handle_update_photos,
    _ACTION_DELETE: handle_delete,
    _ACTION_PROGRESS: handle_participant_progress,
}


def _resolve_action(path: str, method: str) -> str | None:
    parts = [segment for segment in (path or "").strip("/").split("/") if segment]
    if len(parts) != 4:
        return None
    if parts[0] != "api" or parts[1] != "events" or parts[2] != "checklists":
        return None

    segment = parts[3]
    if method == "GET" and segment == "list":
        return _ACTION_LIST
    if method == "GET" and segment == "get":
        return _ACTION_GET
    if method == "POST" and segment == "create":
        return _ACTION_CREATE
    if method == "PUT" and segment == "update":
        return _ACTION_UPDATE
    if method == "PUT" and segment == "update-photos":
        return _ACTION_UPDATE_PHOTOS
    if method == "DELETE" and segment == "delete":
        return _ACTION_DELETE
    if method == "GET" and segment == "participant-progress":
        return _ACTION_PROGRESS
    return None


@https_fn.on_request(region="us-central1")
def checklist_route(req: https_fn.Request) -> https_fn.Response:

    LOG.warning("%s Checklist route", LOG_PREFIX)
    
    validation_response = validate_request(
        req,
        ["GET", "POST", "PUT", "DELETE"],
        "checklist_route",
        return_json_error=False,
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "checklist_route"):
        LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    uid = get_bearer_uid(req, "checklist_route")
    if not uid:
        return https_fn.Response(
            "",
            status=401,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    path = getattr(req, "path", "") or ""
    action = _resolve_action(path, req.method)
    LOG.info("%s Path=%s Method=%s Action=%s", LOG_PREFIX, path, req.method, action)
    if action is None:
        LOG.warning("%s Path no reconocido: %s %s", LOG_PREFIX, req.method, path)
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _HANDLERS[action](req, uid)
