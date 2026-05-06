"""
Update my route notes - Reemplaza por completo las notas de una ruta.

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
"""

import logging
from typing import Any, Dict, List, Optional

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper


def _cors_headers() -> Dict[str, str]:
    return {"Access-Control-Allow-Origin": "*"}


def _success_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


def _validate_notes_payload(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return "body inválido"
    notes = payload.get("notes")
    if not isinstance(notes, list):
        return "notes requerido (list)"
    for note in notes:
        if not isinstance(note, dict):
            return "notes inválido"
        if "identifier" not in note or not isinstance(note.get("identifier"), int):
            return "notes[].identifier requerido (int)"
    return None


def _normalize_notes(notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for note in notes:
        item = dict(note)
        photos = item.get("photos")
        item["photos"] = photos if isinstance(photos, list) else []
        normalized.append(item)
    return normalized


def handle(req: https_fn.Request, route_id: str) -> https_fn.Response:
    """PUT /api/users/my-routes/{routeId}/notes?userId=..."""
    try:
        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            return https_fn.Response("", status=400, headers=_cors_headers())

        payload = req.get_json(silent=True)
        validation_error = _validate_notes_payload(payload)
        if validation_error:
            logging.warning("update_my_route_notes: %s", validation_error)
            return https_fn.Response("", status=400, headers=_cors_headers())

        helper = FirestoreHelper()
        user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            return https_fn.Response("", status=404, headers=_cors_headers())

        routes_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}"
        )
        route_doc = helper.get_document(routes_path, route_id)
        if route_doc is None:
            return https_fn.Response("", status=404, headers=_cors_headers())

        notes_path = (
            f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MY_ROUTES}/"
            f"{route_id}/{FirestoreCollections.MY_ROUTE_NOTES}"
        )

        # Reemplazo completo: limpiar notas existentes y escribir las nuevas.
        existing_notes = helper.list_document_ids(notes_path)
        for note_doc_id in existing_notes:
            helper.delete_document(notes_path, note_doc_id)

        normalized_notes = _normalize_notes(payload["notes"])
        for note in normalized_notes:
            note_id = str(note["identifier"])
            helper.create_document_with_id(notes_path, note_id, note)

        helper.update_document(
            routes_path,
            route_id,
            {
                "notesCount": len(normalized_notes),
                "updatedAt": get_current_timestamp(),
            },
        )

        return https_fn.Response("", status=200, headers=_success_headers())
    except ValueError as e:
        logging.error("update_my_route_notes: Error de validación: %s", e)
        return https_fn.Response("", status=400, headers=_cors_headers())
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("update_my_route_notes: Error interno: %s", e, exc_info=True)
        return https_fn.Response("", status=500, headers=_cors_headers())
