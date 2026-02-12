"""
Update Vehicle - SPRTMNTRPP-72

Cloud Function PUT para actualizar un vehículo de un usuario en Firestore.
Path: /api/vehicles/{vehicleId}. Query: userId, authUserId. Body: branch, year, model, color.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value

from vehicles.delete_vehicle import delete_vehicle as delete_vehicle_handler

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[update_vehicle]"


def _vehicle_id_from_path(path: str) -> str | None:
    """Extrae vehicleId del path /api/vehicles/{vehicleId}. Retorna None si no hay segmento."""
    if not path:
        return None
    parts = [p for p in path.rstrip("/").split("/") if p]
    # ["api", "vehicles", "vehicleId"] -> vehicleId
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "vehicles":
        return parts[2] if len(parts) > 2 else None
    return None


def _validate_user_and_auth(db, user_id: str, auth_user_id: str) -> bool:
    """Comprueba que el usuario exista y que authUserId coincida."""
    user_ref = db.collection(FirestoreCollections.USERS).document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return False
    data = user_doc.to_dict() or {}
    doc_auth_uid = (data.get("authUserId") or "").strip()
    return doc_auth_uid == auth_user_id.strip()


def _validate_body(body: Dict[str, Any]) -> str | None:
    """Valida el body. Retorna None si es válido, o mensaje de error."""
    if not body or not isinstance(body, dict):
        return "Request body inválido o faltante"
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
            return "year debe ser un año válido (1900-2100)"
    except (TypeError, ValueError):
        return "year debe ser un entero"
    return None


@https_fn.on_request()
def update_vehicle(req: https_fn.Request) -> https_fn.Response:
    """
    Actualiza un vehículo. Path: /api/vehicles/{vehicleId}. Query: userId, authUserId.
    Body: { branch, year, model, color }. No modifica createdAt.
    """
    validation_response = validate_request(
        req, ["PUT", "DELETE"], "update_vehicle", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    if req.method == "DELETE":
        return delete_vehicle_handler(req)

    try:
        if not verify_bearer_token(req, "update_vehicle"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

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
        auth_user_id = (req.args.get("authUserId") or "").strip()

        if not user_id:
            logging.warning("%s userId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not auth_user_id:
            logging.warning("%s authUserId faltante o vacío", LOG_PREFIX)
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
        if not _validate_user_and_auth(db, user_id, auth_user_id):
            logging.warning(
                "%s Usuario no encontrado o authUserId no coincide: userId=%s",
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
                "%s Vehículo no encontrado: userId=%s, vehicleId=%s",
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
        iso_now = now.isoformat().replace("+00:00", "Z")

        update_data = {
            "branch": str(body["branch"]).strip(),
            "year": year_val,
            "model": str(body["model"]).strip(),
            "color": str(body["color"]).strip(),
            "updatedAt": now,
        }
        vehicle_ref.update(update_data)

        created_iso = convert_firestore_value(existing.get("createdAt")) or iso_now

        result = {
            "id": vehicle_id,
            "branch": update_data["branch"],
            "year": update_data["year"],
            "model": update_data["model"],
            "color": update_data["color"],
            "createdAt": created_iso,
            "updatedAt": iso_now,
        }

        logging.info(
            "%s Vehículo actualizado: userId=%s, vehicleId=%s",
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
