"""
Track Competitor Position - SPRTMNTRPP-75

Recibe posición y datos del competidor en tiempo real (coordenadas, velocidad, tipo, timestamp)
y los guarda en Realtime Database en la ruta sport_monitor/tracking/{eventId}/{dayId}/{competitorId}/
con current e historial. API pública: no requiere Bearer token.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from firebase_admin import db
from firebase_functions import https_fn
from utils.helper_http_verb import validate_request

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[track_competitor_position]"

# Ruta base en Realtime Database (SPRTMNTRPP-75)
RTDB_BASE_PATH = "sport_monitor/tracking"

# Límite de entradas en historial para evitar crecimiento ilimitado
HISTORIAL_MAX_SIZE = 2000

# Realtime Database no permite en claves: . $ # [ ] /
_RTDB_KEY_SANITIZE = re.compile(r"[.$#\[\]/]")


def _rtdb_safe_key(key: str) -> str:
    """Sanitiza una clave para que sea válida en Realtime Database (no permite . $ # [ ] /)."""
    return _RTDB_KEY_SANITIZE.sub("_", key)


def _rtdb_ref(event_id: str, day_id: str, competitor_id: str):
    """Referencia a sport_monitor/tracking/eventId/dayId/competitorId en Realtime Database."""
    path = f"{RTDB_BASE_PATH}/{event_id}/{day_id}/{competitor_id}"
    return db.reference(path)


def _validate_body(body: Dict[str, Any]) -> str | None:
    """
    Valida el request body. Retorna None si es válido, o mensaje de error.
    """
    if not body or not isinstance(body, dict):
        return "Request body inválido o faltante"

    coordinates = body.get("coordinates")
    if not coordinates or not isinstance(coordinates, dict):
        return "coordinates es requerido y debe ser un objeto"
    lat = coordinates.get("latitude")
    lon = coordinates.get("longitude")
    if lat is None or not isinstance(lat, (int, float)):
        return "coordinates.latitude es requerido y debe ser un número"
    if lon is None or not isinstance(lon, (int, float)):
        return "coordinates.longitude es requerido y debe ser un número"

    data = body.get("data")
    if not data or not isinstance(data, dict):
        return "data es requerido y debe ser un objeto"
    if "speed" not in data or not isinstance(data.get("speed"), str):
        return "data.speed es requerido y debe ser un string"
    if "type" not in data or not isinstance(data.get("type"), str):
        return "data.type es requerido y debe ser un string"

    time_stamp = body.get("timeStamp")
    if not time_stamp or not isinstance(time_stamp, str):
        return "timeStamp es requerido y debe ser un string"

    return None


def _time_stamp_to_id(time_stamp: str) -> int:
    """Convierte timeStamp 'DD/MM/YYYY HH:mm:ss' a id numérico (Unix timestamp en segundos, long)."""
    try:
        dt = datetime.strptime(time_stamp.strip(), "%d/%m/%Y %H:%M:%S")
        dt_utc = dt.replace(tzinfo=timezone.utc)
        return int(dt_utc.timestamp())
    except (ValueError, TypeError):
        return 0


def _build_current_entry(
    uuid: str, latitude: float, longitude: float
) -> Dict[str, Any]:
    """Construye el objeto current (solo uuid, latitude, longitude)."""
    return {
        "uuid": uuid,
        "latitude": float(latitude),
        "longitude": float(longitude),
    }


def _build_historial_value(
    id_long: int,
    coordinates: Dict[str, Any],
    data: Dict[str, Any],
    time_stamp: str,
) -> Dict[str, Any]:
    """Construye el valor de una entrada del mapa historial (id, coordinates, data, timeStamp). Sin uuid en data."""
    return {
        "id": id_long,
        "coordinates": {
            "latitude": float(coordinates.get("latitude")),
            "longitude": float(coordinates.get("longitude")),
        },
        "data": {
            "speed": str(data.get("speed", "")),
            "type": str(data.get("type", "")),
        },
        "timeStamp": time_stamp,
    }


@https_fn.on_request()
def track_competitor_position(req: https_fn.Request) -> https_fn.Response:
    """
    Recibe posición y datos del competidor en tiempo real y los guarda en Realtime Database.

    Ruta en RTDB: sport_monitor/tracking/{eventId}/{dayId}/{competitorId}/ con current e historial.
    API pública: no requiere Authorization Bearer.

    Query Parameters:
    - eventId (string, requerido): UUID del evento
    - dayId (string, requerido): UUID del día de carrera
    - competitorId (string, requerido): UUID del competidor

    Request Body (JSON):
    - coordinates: { latitude (number), longitude (number) }
    - data: { speed (string), type (string) }
    - timeStamp (string): ej. "DD/MM/YYYY HH:mm:ss"

    Actualiza current y añade una entrada a historial en Realtime Database.
    - current: uuid, latitude, longitude.
    - historial: mapa (no lista); clave = uuid (ISO string), valor = { id (long desde timeStamp),
      coordinates, data, timeStamp }. El id es el timeStamp del request convertido a Unix timestamp.
    Requiere que el proyecto tenga Realtime Database habilitado y databaseURL configurado.

    Returns:
    - 200: Sin body si la operación es exitosa
    - 400: Parámetros o body inválidos
    - 500: Error interno
    """
    validation_response = validate_request(
        req, ["POST"], "track_competitor_position", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        event_id = (req.args.get("eventId") or "").strip()
        day_id = (req.args.get("dayId") or "").strip()
        competitor_id = (req.args.get("competitorId") or "").strip()

        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not day_id:
            LOG.warning("%s dayId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not competitor_id:
            LOG.warning("%s competitorId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        try:
            body = req.get_json(silent=True)
            if body is None:
                LOG.warning("%s Request body inválido o faltante", LOG_PREFIX)
                return https_fn.Response(
                    "",
                    status=400,
                    headers={"Access-Control-Allow-Origin": "*"},
                )
        except (ValueError, TypeError) as e:
            LOG.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        body_error = _validate_body(body)
        if body_error:
            LOG.warning("%s %s", LOG_PREFIX, body_error)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        ref = _rtdb_ref(event_id, day_id, competitor_id)
        existing = ref.get() or {}

        # Mismo criterio que Dart: DateTime.now().millisecondsSinceEpoch
        uuid = str(int(datetime.now(timezone.utc).timestamp() * 1000))

        coordinates = body.get("coordinates", {})
        data = body.get("data", {})
        time_stamp = body.get("timeStamp", "")

        latitude = float(coordinates.get("latitude"))
        longitude = float(coordinates.get("longitude"))

        current_entry = _build_current_entry(uuid, latitude, longitude)
        id_long = _time_stamp_to_id(time_stamp)
        historial_value = _build_historial_value(id_long, coordinates, data, time_stamp)

        existing_historial = existing.get("historial")
        if existing_historial is None or not isinstance(
            existing_historial, (dict, list)
        ):
            historial: Dict[str, Any] = {}
        elif isinstance(existing_historial, list):
            # Compatibilidad: si venía como lista, convertir a mapa con claves válidas para RTDB
            historial = {
                _rtdb_safe_key(str(item.get("uuid", i))): {
                    "id": _time_stamp_to_id(
                        item.get("timeStamp", "01/01/1970 00:00:00")
                    ),
                    "coordinates": (
                        item.get("coordinates", {})
                        if isinstance(item.get("coordinates"), dict)
                        else {}
                    ),
                    "data": (
                        item.get("data", {})
                        if isinstance(item.get("data"), dict)
                        else {}
                    ),
                    "timeStamp": str(item.get("timeStamp", "")),
                }
                for i, item in enumerate(existing_historial)
                if isinstance(item, dict)
            }
        else:
            historial = dict(existing_historial)
        historial[_rtdb_safe_key(uuid)] = historial_value
        if len(historial) > HISTORIAL_MAX_SIZE:
            sorted_entries = sorted(historial.items(), key=lambda x: x[1].get("id", 0))
            historial = dict(sorted_entries[-HISTORIAL_MAX_SIZE:])

        ref.update(
            {
                "current": current_entry,
                "historial": historial,
            }
        )

        LOG.info(
            "%s OK eventId=%s competitorId=%s dayId=%s uuid=%s",
            LOG_PREFIX,
            event_id,
            competitor_id,
            day_id,
            uuid,
        )
        return https_fn.Response(
            "",
            status=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        LOG.error("%s Error de validación: %s", LOG_PREFIX, e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        # Incluye errores de Firebase (ej. databaseURL no configurado), KeyError, TypeError, etc.
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
