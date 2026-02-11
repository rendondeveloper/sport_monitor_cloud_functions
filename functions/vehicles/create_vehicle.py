"""
Create Vehicle - SPRTMNTRPP-71

Lógica POST para crear un vehículo de un usuario en Firestore.
Ruta: users/{userId}/vehicles. Requiere userId, authUserId y body (branch, year, model, color).
Se invoca desde get_vehicles cuando el método es POST (mismo path /api/vehicles).
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

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_vehicle]"


def _validate_user_and_auth(db, user_id: str, auth_user_id: str) -> bool:
    """
    Comprueba que el usuario exista y que authUserId coincida con el documento.
    Retorna True si es válido, False si no existe o no coincide.
    """
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


def create_vehicle_handler(req: https_fn.Request) -> https_fn.Response:
    """
    Crea un vehículo para un usuario. Requiere Bearer token, userId, authUserId y body.
    """
    validation_response = validate_request(
        req, ["POST"], "create_vehicle", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "create_vehicle"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
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

        now = datetime.now(timezone.utc)
        iso_now = now.isoformat().replace("+00:00", "Z")
        year_val = int(body["year"])

        vehicle_data = {
            "branch": str(body["branch"]).strip(),
            "year": year_val,
            "model": str(body["model"]).strip(),
            "color": str(body["color"]).strip(),
            "createdAt": now,
            "updatedAt": now,
        }

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
            "createdAt": iso_now,
            "updatedAt": iso_now,
        }

        logging.info("%s Vehículo creado: userId=%s, vehicleId=%s", LOG_PREFIX, user_id, new_doc.id)

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
