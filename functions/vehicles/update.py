"""
Update Vehicle - SPRTMNTRPP-72

Actualiza un vehiculo de un usuario en Firestore.
Path: /api/vehicles/{vehicleId}. Query: userId. Body: branch, year, model, color.

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
LOG_PREFIX = "[update_vehicle]"


def _vehicle_id_from_path(path: str) -> str | None:
    """Extrae vehicleId del path /api/vehicles/{vehicleId}. Retorna None si no hay segmento."""
    if not path:
        return None
    parts = [p for p in path.rstrip("/").split("/") if p]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "vehicles":
        return parts[2] if len(parts) > 2 else None
    return None


def _validate_user_exists(db, user_id: str) -> bool:
    """Comprueba que el usuario exista."""
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
    Actualiza un vehiculo.
    Asume request ya validado (CORS, Bearer token) por vehicle_route.

    Path: /api/vehicles/{vehicleId}
    Query: userId
    Body: { branch, year, model, color, photoUrl?, mileageKm? }

    Returns:
    - 200: JSON con vehiculo actualizado
    - 400: parametros faltantes o body invalido
    - 404: usuario/vehiculo no encontrado
    - 500: error interno
    """
    try:
        vehicle_id = _vehicle_id_from_path(getattr(req, "path", "") or "")
        if not vehicle_id:
            vehicle_id = (req.args.get("vehicleId") or "").strip()
        if not vehicle_id:
            logging.warning("%s vehicleId faltante (path o query)", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

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

        vehicle_ref = (
            db.collection(FirestoreCollections.USERS)
            .document(user_id)
            .collection(FirestoreCollections.USER_VEHICLES)
            .document(vehicle_id)
        )
        vehicle_doc = vehicle_ref.get()
        if not vehicle_doc.exists:
            logging.warning(
                "%s Vehiculo no encontrado: userId=%s, vehicleId=%s",
                LOG_PREFIX,
                user_id,
                vehicle_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        existing = vehicle_doc.to_dict() or {}
        year_val = int(body["year"])
        now = datetime.now(timezone.utc)

        update_data = {
            "branch": str(body["branch"]).strip(),
            "year": year_val,
            "model": str(body["model"]).strip(),
            "color": str(body["color"]).strip(),
            "updatedAt": now,
        }
        if body.get("photoUrl") is not None:
            update_data["photoUrl"] = str(body["photoUrl"]).strip()
        if body.get("mileageKm") is not None:
            update_data["mileageKm"] = int(body["mileageKm"])
        vehicle_ref.update(update_data)

        result = {
            "id": vehicle_id,
            "branch": update_data["branch"],
            "year": update_data["year"],
            "model": update_data["model"],
            "color": update_data["color"],
        }
        if "photoUrl" in update_data:
            result["photoUrl"] = update_data["photoUrl"]
        elif existing.get("photoUrl"):
            result["photoUrl"] = existing["photoUrl"]
        if "mileageKm" in update_data:
            result["mileageKm"] = update_data["mileageKm"]
        elif existing.get("mileageKm") is not None:
            result["mileageKm"] = existing["mileageKm"]

        logging.info(
            "%s Vehiculo actualizado: userId=%s, vehicleId=%s",
            LOG_PREFIX,
            user_id,
            vehicle_id,
        )

        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
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
