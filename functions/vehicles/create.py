"""
Create Vehicle - SPRTMNTRPP-71

Crea un vehiculo de un usuario en Firestore.
Ruta: users/{userId}/vehicles. Requiere userId y body (branch, year, model, color).

Logica de negocio unicamente. La validacion CORS y Bearer token la realiza vehicle_route.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_vehicle]"


def _validate_user_exists(db, user_id: str) -> bool:
    """
    Comprueba que el usuario exista.
    Retorna True si existe, False si no existe.
    """
    user_ref = db.collection(FirestoreCollections.USERS).document(user_id)
    user_doc = user_ref.get()
    return user_doc.exists


def _validate_body(body: Dict[str, Any]) -> str | None:
    """Valida el body. Retorna None si es valido, o mensaje de error."""
    if not body or not isinstance(body, dict):
        return "Request body invalido o faltante"
    if not body.get("branch") or not isinstance(body.get("branch"), str):
        return "branch es requerido y debe ser string"
    if not body.get("model") or not isinstance(body.get("model"), str):
        return "model es requerido y debe ser string"
    if not body.get("color") or not isinstance(body.get("color"), str):
        return "color es requerido y debe ser string"
    year = body.get("year")
    if year is None:
        return "year es requerido"
    try:
        y = int(year)
        if y < 1900 or y > 2100:
            return "year debe ser un ano valido (1900-2100)"
    except (TypeError, ValueError):
        return "year debe ser un entero"
    photo_url = body.get("photoUrl")
    if photo_url is not None:
        if not isinstance(photo_url, str) or not photo_url.strip():
            return "photoUrl debe ser un string no vacio"
    mileage_km = body.get("mileageKm")
    if mileage_km is not None:
        if not isinstance(mileage_km, int) or isinstance(mileage_km, bool) or mileage_km < 0:
            return "mileageKm debe ser un entero >= 0"
    return None


def handle(req: https_fn.Request) -> https_fn.Response:
    """
    Crea un vehiculo para un usuario.
    Asume request ya validado (CORS, Bearer token) por vehicle_route.

    Query Parameters:
    - userId: string (requerido)

    Body:
    - branch: string (requerido)
    - year: int (requerido)
    - model: string (requerido)
    - color: string (requerido)
    - photoUrl: string (opcional)
    - mileageKm: int (opcional)

    Returns:
    - 201: JSON con vehiculo creado
    - 400: parametros faltantes o body invalido
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

        try:
            request_data = req.get_json(silent=True)
        except (ValueError, TypeError) as e:
            logging.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        body = request_data if isinstance(request_data, dict) else None
        err = _validate_body(body)
        if err:
            logging.warning("%s %s", LOG_PREFIX, err)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        db = firestore.client()
        if not _validate_user_exists(db, user_id):
            logging.warning(
                "%s Usuario no encontrado: userId=%s",
                LOG_PREFIX,
                user_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        now = datetime.now(timezone.utc)
        year_val = int(body["year"])

        vehicle_data = {
            "branch": str(body["branch"]).strip(),
            "year": year_val,
            "model": str(body["model"]).strip(),
            "color": str(body["color"]).strip(),
            "createdAt": now,
            "updatedAt": now,
        }
        if body.get("photoUrl") is not None:
            vehicle_data["photoUrl"] = str(body["photoUrl"]).strip()
        if body.get("mileageKm") is not None:
            vehicle_data["mileageKm"] = int(body["mileageKm"])

        vehicles_ref = (
            db.collection(FirestoreCollections.USERS)
            .document(user_id)
            .collection(FirestoreCollections.USER_VEHICLES)
        )
        new_doc = vehicles_ref.document()
        new_doc.set(vehicle_data)

        result = {
            "id": new_doc.id,
            "branch": vehicle_data["branch"],
            "year": vehicle_data["year"],
            "model": vehicle_data["model"],
            "color": vehicle_data["color"],
        }
        if "photoUrl" in vehicle_data:
            result["photoUrl"] = vehicle_data["photoUrl"]
        if "mileageKm" in vehicle_data:
            result["mileageKm"] = vehicle_data["mileageKm"]

        logging.info("%s Vehiculo creado: userId=%s, vehicleId=%s", LOG_PREFIX, user_id, new_doc.id)

        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=201,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
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
