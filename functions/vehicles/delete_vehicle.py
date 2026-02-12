"""
Delete Vehicle - SPRTMNTRPP-73

Cloud Function DELETE para eliminar un vehículo de un usuario en Firestore.
Path: /api/vehicles/{vehicleId}. Query: userId, authUserId.
Respuesta exitosa: 204 No Content.
"""

import logging
from typing import TYPE_CHECKING

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

if TYPE_CHECKING:
    from firebase_admin.firestore import Client as FirestoreClient

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[delete_vehicle]"


def _vehicle_id_from_path(path: str) -> str | None:
    """Extrae vehicleId del path /api/vehicles/{vehicleId}. Retorna None si no hay segmento."""
    if not path:
        return None
    parts = [p for p in path.rstrip("/").split("/") if p]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "vehicles":
        return parts[2] if len(parts) > 2 else None
    return None


def _validate_user_and_auth(
    db: "FirestoreClient", user_id: str, auth_user_id: str
) -> bool:
    """Comprueba que el usuario exista y que authUserId coincida."""
    user_ref = db.collection(FirestoreCollections.USERS).document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return False
    data = user_doc.to_dict() or {}
    doc_auth_uid = (data.get("authUserId") or "").strip()
    return doc_auth_uid == auth_user_id.strip()


def _validate_vehicle(db: "FirestoreClient", user_id: str, vehicle_id: str) -> bool:
    """Comprueba que el vehículo exista en users/{userId}/vehicles/{vehicleId}."""
    vehicle_ref = (
        db.collection(FirestoreCollections.USERS)
        .document(user_id)
        .collection(FirestoreCollections.USER_VEHICLES)
        .document(vehicle_id)
    )
    return vehicle_ref.get().exists


def _delete_vehicle_from_firestore(
    db: "FirestoreClient", user_id: str, vehicle_id: str
) -> None:
    """Elimina el documento del vehículo en Firestore."""
    vehicle_ref = (
        db.collection(FirestoreCollections.USERS)
        .document(user_id)
        .collection(FirestoreCollections.USER_VEHICLES)
        .document(vehicle_id)
    )
    vehicle_ref.delete()


def _cors_headers_204() -> dict:
    """Headers CORS para respuesta 204."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


@https_fn.on_request()
def delete_vehicle(req: https_fn.Request) -> https_fn.Response:
    """
    Elimina un vehículo. Path: /api/vehicles/{vehicleId}. Query: userId, authUserId.
    Retorna 204 No Content en éxito.
    """
    validation_response = validate_request(
        req, ["DELETE"], "delete_vehicle", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "delete_vehicle"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers=_cors_headers_204(),
            )

        vehicle_id = _vehicle_id_from_path(getattr(req, "path", "") or "")
        if not vehicle_id:
            vehicle_id = (req.args.get("vehicleId") or "").strip()
        if not vehicle_id:
            logging.warning("%s vehicleId faltante (path o query)", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers=_cors_headers_204(),
            )

        user_id = (req.args.get("userId") or "").strip()
        auth_user_id = (req.args.get("authUserId") or "").strip()

        if not user_id:
            logging.warning("%s userId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers=_cors_headers_204(),
            )
        if not auth_user_id:
            logging.warning("%s authUserId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers=_cors_headers_204(),
            )

        db = firestore.client()
        if not _validate_user_and_auth(db, user_id, auth_user_id):
            logging.warning(
                "%s Usuario no encontrado o authUserId no coincide: userId=%s",
                LOG_PREFIX,
                user_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers=_cors_headers_204(),
            )

        if not _validate_vehicle(db, user_id, vehicle_id):
            logging.warning(
                "%s Vehículo no encontrado: userId=%s, vehicleId=%s",
                LOG_PREFIX,
                user_id,
                vehicle_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers=_cors_headers_204(),
            )

        _delete_vehicle_from_firestore(db, user_id, vehicle_id)

        logging.info(
            "%s Vehículo eliminado: userId=%s, vehicleId=%s",
            LOG_PREFIX,
            user_id,
            vehicle_id,
        )

        return https_fn.Response(
            "",
            status=204,
            headers=_cors_headers_204(),
        )

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers=_cors_headers_204(),
        )
