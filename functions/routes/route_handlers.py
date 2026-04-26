import json
from typing import Any, Dict, Optional

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.event_owner_helper import get_event_if_owner

_JSON_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
}
_CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


def _json_response(payload: Any, status: int = 200) -> https_fn.Response:
    return https_fn.Response(
        json.dumps(payload, ensure_ascii=False),
        status=status,
        headers=_JSON_HEADERS,
    )


def _empty(status: int) -> https_fn.Response:
    return https_fn.Response("", status=status, headers=_CORS_HEADERS)


def _parse_body(req: https_fn.Request) -> Optional[Dict[str, Any]]:
    try:
        body = req.get_json(silent=True)
    except Exception:
        return None
    return body if isinstance(body, dict) else None


def _route_collection(event_id: str):
    db = firestore.client()
    return (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_ROUTES)
    )


def _replace_checkpoints(route_ref: firestore.DocumentReference, checkpoints: list[Dict[str, Any]]) -> None:
    old_docs = list(route_ref.collection(FirestoreCollections.EVENT_CHECKPOINTS).stream())
    for old_doc in old_docs:
        old_doc.reference.delete()

    for item in checkpoints:
        checkpoint_payload = dict(item)
        checkpoint_id = str(checkpoint_payload.pop("id", "")).strip()
        if checkpoint_id:
            route_ref.collection(FirestoreCollections.EVENT_CHECKPOINTS).document(
                checkpoint_id
            ).set(checkpoint_payload)
        else:
            route_ref.collection(FirestoreCollections.EVENT_CHECKPOINTS).document().set(
                checkpoint_payload
            )


def _serialize_route(route_doc: firestore.DocumentSnapshot) -> Dict[str, Any]:
    route_data = route_doc.to_dict() or {}
    route_data["id"] = route_doc.id
    checkpoints = []
    for checkpoint_doc in (
        route_doc.reference.collection(FirestoreCollections.EVENT_CHECKPOINTS).stream()
    ):
        checkpoint_data = checkpoint_doc.to_dict() or {}
        checkpoint_data["id"] = checkpoint_doc.id
        checkpoints.append(checkpoint_data)
    route_data["checkpoints"] = checkpoints
    return route_data


def handle_create(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = _parse_body(req)
    if body is None:
        return _empty(400)

    event_id = (body.get("eventId") or "").strip()
    if not event_id:
        return _empty(400)
    if get_event_if_owner(event_id, user_id) is None:
        return _empty(404)

    checkpoints = body.get("checkpoints") or []
    if not isinstance(checkpoints, list):
        return _empty(400)

    route_payload = dict(body)
    route_payload.pop("eventId", None)
    route_payload.pop("checkpoints", None)
    route_payload["updatedAt"] = get_current_timestamp()
    route_payload["createdAt"] = route_payload.get("createdAt") or get_current_timestamp()

    route_id = str(route_payload.pop("routeId", "") or "").strip()
    routes_ref = _route_collection(event_id)
    route_ref = routes_ref.document(route_id) if route_id else routes_ref.document()
    route_ref.set(route_payload)
    _replace_checkpoints(route_ref, checkpoints)
    return _json_response(_serialize_route(route_ref.get()), 200)


def handle_update(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = _parse_body(req)
    if body is None:
        return _empty(400)

    event_id = (body.get("eventId") or "").strip()
    route_id = (body.get("routeId") or "").strip()
    if not event_id or not route_id:
        return _empty(400)
    if get_event_if_owner(event_id, user_id) is None:
        return _empty(404)

    routes_ref = _route_collection(event_id)
    route_ref = routes_ref.document(route_id)
    route_doc = route_ref.get()
    if not route_doc.exists:
        return _empty(404)

    checkpoints = body.get("checkpoints") or []
    if not isinstance(checkpoints, list):
        return _empty(400)

    update_payload = dict(body)
    update_payload.pop("eventId", None)
    update_payload.pop("routeId", None)
    update_payload.pop("checkpoints", None)
    update_payload["updatedAt"] = get_current_timestamp()
    route_ref.update(update_payload)
    _replace_checkpoints(route_ref, checkpoints)
    return _json_response(_serialize_route(route_ref.get()), 200)


def handle_get(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = (req.args.get("eventId") or "").strip()
    route_id = (req.args.get("routeId") or "").strip()
    if not event_id or not route_id:
        return _empty(400)
    if get_event_if_owner(event_id, user_id) is None:
        return _empty(404)

    route_doc = _route_collection(event_id).document(route_id).get()
    if not route_doc.exists:
        return _empty(404)
    return _json_response(_serialize_route(route_doc), 200)


def handle_list(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        return _empty(400)
    if get_event_if_owner(event_id, user_id) is None:
        return _empty(404)

    response = []
    for route_doc in _route_collection(event_id).stream():
        data = route_doc.to_dict() or {}
        data["id"] = route_doc.id
        response.append(data)
    return _json_response(response, 200)


def handle_delete(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = (req.args.get("eventId") or "").strip()
    route_id = (req.args.get("routeId") or "").strip()
    if not event_id or not route_id:
        return _empty(400)
    if get_event_if_owner(event_id, user_id) is None:
        return _empty(404)

    route_ref = _route_collection(event_id).document(route_id)
    route_doc = route_ref.get()
    if not route_doc.exists:
        return _empty(404)

    for checkpoint_doc in (
        route_ref.collection(FirestoreCollections.EVENT_CHECKPOINTS).stream()
    ):
        checkpoint_doc.reference.delete()
    route_ref.delete()
    return _empty(200)


def handle_event_categories(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        return _empty(400)
    event = get_event_if_owner(event_id, user_id)
    if event is None:
        return _empty(404)

    categories = event.get("categories") or event.get("eventCategories") or []
    if not isinstance(categories, list):
        categories = []
    return _json_response(categories, 200)


def handle_event_days(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = (req.args.get("eventId") or "").strip()
    if not event_id:
        return _empty(400)
    if get_event_if_owner(event_id, user_id) is None:
        return _empty(404)

    db = firestore.client()
    day_docs = (
        db.collection(FirestoreCollections.DAY_OF_RACES)
        .where(filter=firestore.FieldFilter("eventId", "==", event_id))
        .stream()
    )
    response = []
    for day_doc in day_docs:
        data = day_doc.to_dict() or {}
        data["id"] = day_doc.id
        response.append(data)
    return _json_response(response, 200)
