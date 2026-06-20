import json
from typing import Any

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
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


def _route_collection(event_id: str):
    db = firestore.client()
    return (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_ROUTES)
    )


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
    for trackpoint_doc in (
        route_ref.collection(FirestoreCollections.EVENT_TRACKPOINTS).stream()
    ):
        trackpoint_doc.reference.delete()
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
