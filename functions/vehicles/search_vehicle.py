"""
Search Vehicle

Cloud Function GET que busca un vehículo de un usuario en Firestore
por coincidencia exacta de model, branch y year.
Ruta: users/{userId}/vehicles.  Requiere Bearer token.
"""

import logging

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[search_vehicle]"


def _build_collection_path(user_id: str) -> str:
    """Construye la ruta de la subcolección vehicles del usuario."""
    return (
        f"{FirestoreCollections.USERS}/{user_id}/"
        f"{FirestoreCollections.USER_VEHICLES}"
    )


def _search_vehicle_in_firestore(
    fs: FirestoreHelper,
    user_id: str,
    branch: str,
    model: str,
    year: int,
):
    """
    Busca un vehículo que coincida exactamente en branch, model y year.

    Returns:
        Tupla (vehicle_id, vehicle_data) si encuentra coincidencia, o None.
    """
    collection_path = _build_collection_path(user_id)
    results = fs.query_documents(
        collection_path,
        filters=[
            {"field": "branch", "operator": "==", "value": branch},
            {"field": "model", "operator": "==", "value": model},
            {"field": "year", "operator": "==", "value": year},
        ],
        limit=1,
    )
    if results:
        return results[0]
    return None


@https_fn.on_request()
def search_vehicle(req: https_fn.Request) -> https_fn.Response:
    """
    Busca un vehículo de un usuario por branch, model y year.

    Headers:
        - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query params:
        - userId: str (requerido) — ID del usuario dueño del vehículo.
        - branch: str (requerido) — Marca del vehículo.
        - model: str (requerido) — Modelo del vehículo.
        - year: int  (requerido) — Año del vehículo (1900-2100).

    Returns:
        - 200: JSON con el vehículo encontrado.
        - 400: Parámetros faltantes o inválidos.
        - 401: Token inválido o faltante.
        - 404: Usuario o vehículo no encontrado.
        - 500: Error interno.
    """
    validation_response = validate_request(
        req, ["GET"], "search_vehicle", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "search_vehicle"):
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

        branch = (req.args.get("branch") or "").strip()
        if not branch:
            logging.warning("%s branch faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        model = (req.args.get("model") or "").strip()
        if not model:
            logging.warning("%s model faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        year_raw = (req.args.get("year") or "").strip()
        if not year_raw:
            logging.warning("%s year faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            year = int(year_raw)
            if year < 1900 or year > 2100:
                raise ValueError("year fuera de rango")
        except (ValueError, TypeError):
            logging.warning("%s year inválido: %s", LOG_PREFIX, year_raw)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        fs = FirestoreHelper()

        user_doc = fs.get_document(FirestoreCollections.USERS, user_id)
        if user_doc is None:
            logging.warning("%s Usuario no encontrado: %s", LOG_PREFIX, user_id)
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        match = _search_vehicle_in_firestore(fs, user_id, branch, model, year)

        if match is None:
            logging.info(
                "%s Vehículo no encontrado: userId=%s, branch=%s, model=%s, year=%d",
                LOG_PREFIX,
                user_id,
                branch,
                model,
                year,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        vehicle_id, vehicle_data = match
        import json

        result = {
            "id": vehicle_id,
            "branch": vehicle_data.get("branch"),
            "model": vehicle_data.get("model"),
            "year": vehicle_data.get("year"),
            "color": vehicle_data.get("color"),
            "createdAt": convert_firestore_value(vehicle_data.get("createdAt")),
            "updatedAt": convert_firestore_value(vehicle_data.get("updatedAt")),
        }

        logging.info(
            "%s Vehículo encontrado: userId=%s, vehicleId=%s",
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
