"""
Get Vehicles - SPRTMNTRPP-70

Cloud Function GET que obtiene todos los vehículos de un usuario/competidor desde Firestore.
Ruta: users/{userId}/vehicles. Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, List

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_vehicles]"


def _get_vehicles_from_firestore(db, user_id: str):
    """
    Obtiene la referencia a la subcolección de vehículos del usuario.
    Retorna (user_exists, snapshot_vehicles).
    Si el usuario no existe, user_exists=False y snapshot_vehicles es None.
    """
    user_ref = db.collection(FirestoreCollections.USERS).document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return False, None
    vehicles_ref = user_ref.collection(FirestoreCollections.USER_VEHICLES)
    snapshot = vehicles_ref.stream()
    return True, list(snapshot)


def _build_vehicle_dict(doc) -> Dict[str, Any]:
    """Construye el diccionario de un vehículo para la respuesta JSON."""
    data = doc.to_dict() or {}
    result = {
        "id": doc.id,
        "branch": data.get("branch"),
        "year": data.get("year"),
        "model": data.get("model"),
        "color": data.get("color"),
        "createdAt": convert_firestore_value(data.get("createdAt")),
        "updatedAt": convert_firestore_value(data.get("updatedAt")),
    }
    return result


@https_fn.on_request()
def get_vehicles(req: https_fn.Request) -> https_fn.Response:
    """
    GET: Obtiene todos los vehículos de un usuario.
    POST: Crea un vehículo (delega a create_vehicle_handler). Mismo path /api/vehicles.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    GET Query: userId (requerido).
    POST Query: userId, authUserId (requeridos). Body: { branch, year, model, color }.
    """
    validation_response = validate_request(
        req, ["GET", "POST"], "get_vehicles", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if req.method == "POST":
        from vehicles.create_vehicle import create_vehicle_handler
        return create_vehicle_handler(req)

    try:
        if not verify_bearer_token(req, "get_vehicles"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            logging.warning("%s userId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        db = firestore.client()
        user_exists, vehicles_docs = _get_vehicles_from_firestore(db, user_id)

        if not user_exists:
            logging.warning("%s Usuario no encontrado: %s", LOG_PREFIX, user_id)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        result: List[Dict[str, Any]] = [
            _build_vehicle_dict(doc) for doc in (vehicles_docs or [])
        ]
        logging.info(
            "%s Vehículos obtenidos para usuario %s: %d",
            LOG_PREFIX,
            user_id,
            len(result),
        )

        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("%s Error de validación: %s", LOG_PREFIX, e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
