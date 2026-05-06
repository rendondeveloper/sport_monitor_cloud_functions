"""
Create my route - Crea ruta de usuario y sus subcolecciones points/notes.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper


def _bad_request() -> https_fn.Response:
    return https_fn.Response("", status=400, headers={"Access-Control-Allow-Origin": "*"})


def _json_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


def _validate_request_data(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return "body inválido"
    if not str(data.get("userId", "")).strip():
        return "userId requerido"
    if "identifier" not in data or not isinstance(data.get("identifier"), int):
        return "identifier requerido (int)"
    if not str(data.get("name", "")).strip():
        return "name requerido"
    if not str(data.get("description", "")).strip():
        return "description requerido"
    points = data.get("points")
    notes = data.get("notes")
    if points is not None and not isinstance(points, list):
        return "points debe ser list o null"
    if notes is not None and not isinstance(notes, list):
        return "notes debe ser list o null"
    if isinstance(notes, list):
        for note in notes:
            if not isinstance(note, dict):
                continue
            if "identifier" not in note or not isinstance(note.get("identifier"), int):
                return "notes[].identifier requerido (int)"
    return None


def _extract_valid_lat_lon(points: Any) -> List[Tuple[float, float]]:
    if not isinstance(points, list):
        return []

    valid: List[Tuple[float, float]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        lat = point.get("latitude")
        lon = point.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        valid.append((float(lat), float(lon)))
    return valid


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Radio medio de la Tierra (m)
    r = 6371000.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2.0) ** 2)
    )
    c = 2.0 * math.asin(math.sqrt(a))
    return r * c


def _compute_distance(points: Any) -> float:
    valid = _extract_valid_lat_lon(points)
    if len(valid) < 2:
        return 0.0

    total_meters = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(valid, valid[1:]):
        total_meters += _haversine_meters(lat1, lon1, lat2, lon2)

    km = total_meters / 1000.0
    return math.ceil(km * 10.0) / 10.0


def _build_route_doc(data: Dict[str, Any], now: str) -> Dict[str, Any]:
    points = data.get("points")
    notes = data.get("notes")
    points_count = len(points) if isinstance(points, list) else 0
    notes_count = len(notes) if isinstance(notes, list) else 0
    return {
        "identifier": data.get("identifier"),
        "name": str(data.get("name", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "eventId": data.get("eventId"),
        "distance": _compute_distance(points),
        "pointsCount": points_count,
        "notesCount": notes_count,
        "createdAt": now,
        "updatedAt": now,
    }


def _normalize_points(points: Any) -> List[Dict[str, Any]]:
    if not isinstance(points, list):
        return []
    return [p for p in points if isinstance(p, dict)]


def _normalize_notes(notes: Any) -> List[Dict[str, Any]]:
    if not isinstance(notes, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for note in notes:
        if not isinstance(note, dict):
            continue
        item = dict(note)
        photos = item.get("photos")
        item["photos"] = photos if isinstance(photos, list) else []
        normalized.append(item)
    return normalized


def handle(req: https_fn.Request) -> https_fn.Response:
    """Crea ruta y subdocs points/notes. Responde solo id de ruta."""
    try:
        payload = req.get_json(silent=True)
        validation_error = _validate_request_data(payload)
        if validation_error:
            logging.warning("create_my_route: %s", validation_error)
            return _bad_request()

        user_id = str(payload["userId"]).strip()
        helper = FirestoreHelper()
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            logging.warning("create_my_route: userId no existe: %s", user_id)
            return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})

        now = get_current_timestamp()
        route_collection_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
        )
        route_id = helper.create_document(route_collection_path, _build_route_doc(payload, now))

        points_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}/"
            f"{route_id}/{FirestoreCollections.MY_ROUTE_POINTS}"
        )
        notes_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}/"
            f"{route_id}/{FirestoreCollections.MY_ROUTE_NOTES}"
        )

        for point in _normalize_points(payload.get("points")):
            helper.create_document(points_path, point)

        for note in _normalize_notes(payload.get("notes")):
            note_id = str(note["identifier"])
            helper.create_document_with_id(notes_path, note_id, note)

        return https_fn.Response(
            json.dumps({"id": route_id}, ensure_ascii=False),
            status=201,
            headers=_json_headers(),
        )
    except ValueError as e:
        logging.error("create_my_route: Error de validación: %s", e)
        return _bad_request()
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("create_my_route: Error interno: %s", e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
