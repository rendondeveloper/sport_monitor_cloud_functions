"""
Router central para catálogos: /api/catalogs/vehicle, /api/catalogs/year,
/api/catalogs/color, /api/catalogs/relationship-type, /api/catalogs/checkpoint-type.

Valida CORS, método HTTP y Bearer token una vez; despacha a los handlers
existentes de cada submódulo (misma lógica y contratos que antes).
"""

import logging
from typing import Optional

from firebase_admin import firestore
from firebase_functions import https_fn
from google.cloud.firestore import Client
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from .checkpoint_type.create_checkpoint_type import handle_create as _checkpoint_type_create
from .checkpoint_type.delete_checkpoint_type import handle_delete as _checkpoint_type_delete
from .checkpoint_type.list_checkpoint_type import handle_list as _checkpoint_type_list
from .color._common import cors_headers as _cors_headers
from .color.create_color import handle_create as _color_create
from .color.delete_color import handle_delete as _color_delete
from .color.list_color import handle_list as _color_list
from .color.update_color import handle_update as _color_update
from .relationship_type.list_relationship_type import handle_list as _relationship_list
from .vehicle.create_vehicle import handle_create as _vehicle_create
from .vehicle.delete_vehicle import handle_delete as _vehicle_delete
from .vehicle.list_vehicle import handle_list as _vehicle_list
from .vehicle.update_vehicle import handle_update as _vehicle_update
from .year.create_year import handle_create as _year_create
from .year.delete_year import handle_delete as _year_delete
from .year.list_year import handle_list as _year_list
from .year.update_year import handle_update as _year_update

LOG_PREFIX = "[catalog_route]"

_CATALOG_VEHICLE = "vehicle"
_CATALOG_YEAR = "year"
_CATALOG_COLOR = "color"
_CATALOG_RELATIONSHIP = "relationship-type"
_CATALOG_CHECKPOINT_TYPE = "checkpoint-type"
_ALLOWED_SEGMENTS = frozenset(
    {
        _CATALOG_VEHICLE,
        _CATALOG_YEAR,
        _CATALOG_COLOR,
        _CATALOG_RELATIONSHIP,
        _CATALOG_CHECKPOINT_TYPE,
    }
)


def _catalog_segment_from_path(path: str) -> Optional[str]:
    """Extrae el segmento de catálogo tras .../catalogs/{segment}."""
    if not path:
        return None
    parts = [p for p in path.strip("/").split("/") if p]
    if "catalogs" in parts:
        idx = parts.index("catalogs")
        if idx + 1 >= len(parts):
            return None
        seg = parts[idx + 1]
        return seg if seg in _ALLOWED_SEGMENTS else None
    if len(parts) == 1 and parts[0] in _ALLOWED_SEGMENTS:
        return parts[0]
    return None


def _vehicle_dispatch(req: https_fn.Request, db: Client) -> https_fn.Response:
    if req.method == "GET":
        return _vehicle_list(db)
    if req.method == "POST":
        return _vehicle_create(req, db)
    if req.method == "PUT":
        return _vehicle_update(req, db)
    if req.method == "DELETE":
        return _vehicle_delete(req, db)
    return https_fn.Response("", status=405, headers=_cors_headers())


def _year_dispatch(req: https_fn.Request, db: Client) -> https_fn.Response:
    if req.method == "GET":
        return _year_list(db)
    if req.method == "POST":
        return _year_create(req, db)
    if req.method == "PUT":
        return _year_update(req, db)
    if req.method == "DELETE":
        return _year_delete(req, db)
    return https_fn.Response("", status=405, headers=_cors_headers())


def _color_dispatch(req: https_fn.Request, db: Client) -> https_fn.Response:
    if req.method == "GET":
        return _color_list(db)
    if req.method == "POST":
        return _color_create(req, db)
    if req.method == "PUT":
        return _color_update(req, db)
    if req.method == "DELETE":
        return _color_delete(req, db)
    return https_fn.Response("", status=405, headers=_cors_headers())


def _relationship_dispatch(req: https_fn.Request, db: Client) -> https_fn.Response:
    if req.method == "GET":
        return _relationship_list(db)
    logging.warning(
        "%s Método %s no permitido para relationship-type (solo GET)",
        LOG_PREFIX,
        req.method,
    )
    return https_fn.Response(
        "",
        status=405,
        headers={**_cors_headers(), "Allow": "GET"},
    )


def _checkpoint_type_dispatch(req: https_fn.Request, db: Client) -> https_fn.Response:
    if req.method == "GET":
        return _checkpoint_type_list(db)
    if req.method == "POST":
        return _checkpoint_type_create(req, db)
    if req.method == "DELETE":
        return _checkpoint_type_delete(req, db)
    logging.warning(
        "%s Método %s no permitido para checkpoint-type (esperado GET, POST o DELETE)",
        LOG_PREFIX,
        req.method,
    )
    return https_fn.Response(
        "",
        status=405,
        headers={**_cors_headers(), "Allow": "GET, POST, DELETE"},
    )


_DISPATCH = {
    _CATALOG_VEHICLE: _vehicle_dispatch,
    _CATALOG_YEAR: _year_dispatch,
    _CATALOG_COLOR: _color_dispatch,
    _CATALOG_RELATIONSHIP: _relationship_dispatch,
    _CATALOG_CHECKPOINT_TYPE: _checkpoint_type_dispatch,
}


@https_fn.on_request(region="us-east4")
def catalog_route(req: https_fn.Request) -> https_fn.Response:
    """
    Una sola Cloud Function para catálogos: valida token y despacha por path.

    Paths: /api/catalogs/vehicle, /api/catalogs/year, /api/catalogs/color
    (GET, POST, PUT, DELETE masivo); /api/catalogs/relationship-type (solo GET);
    /api/catalogs/checkpoint-type (GET, POST, DELETE masivo).
    """
    validation_response = validate_request(
        req,
        ["GET", "POST", "PUT", "DELETE"],
        "catalog_route",
        return_json_error=False,
    )
    if validation_response is not None:
        return validation_response

    if not verify_bearer_token(req, "catalog_route"):
        logging.warning("%s Token inválido o faltante", LOG_PREFIX)
        return https_fn.Response("", status=401, headers=_cors_headers())

    path = getattr(req, "path", "") or ""
    logging.info("%s Path recibido: %r", LOG_PREFIX, path)
    segment = _catalog_segment_from_path(path)
    if segment is None:
        logging.warning("%s Path no reconocido: %s", LOG_PREFIX, path)
        return https_fn.Response("", status=404, headers=_cors_headers())

    try:
        db = firestore.client()
        return _DISPATCH[segment](req, db)
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers=_cors_headers())
