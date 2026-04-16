"""
List Vehicles - SPRTMNTRPP-70

Obtiene todos los vehiculos de un usuario/competidor desde Firestore.
Ruta: users/{userId}/vehicles.

Logica de negocio unicamente. La validacion CORS y Bearer token la realiza vehicle_route.
"""

import json
import logging
from typing import Any, Dict, List

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[list_vehicles]"


def _get_vehicles_from_firestore(db, user_id: str):
    """
    Obtiene la referencia a la subcoleccion de vehiculos del usuario.
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
    """Construye el diccionario de un vehiculo para la respuesta JSON."""
    data = doc.to_dict() or {}
    result = {
        "id": doc.id,
        "branch": data.get("branch"),
        "year": data.get("year"),
        "model": data.get("model"),
        "color": data.get("color"),
    }
    if data.get("photoUrl"):
        result["photoUrl"] = data.get("photoUrl")
    if data.get("mileageKm") is not None:
        result["mileageKm"] = data.get("mileageKm")
    return result


def handle(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene todos los vehiculos de un usuario.
    Asume request ya validado (CORS, Bearer token) por vehicle_route.

    Query Parameters:
    - userId: string (requerido)

    Returns:
    - 200: Array JSON directo
    - 400: userId faltante
    - 404: usuario no encontrado
    - 500: error interno
    """
    try:
        user_id = (req.args.get("userId") or "").strip()
        if not user_id:
            logging.warning("%s userId faltante o vacio", LOG_PREFIX)
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
            "%s Vehiculos obtenidos para usuario %s: %d",
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
        logging.error("%s Error de validacion: %s", LOG_PREFIX, e)
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
