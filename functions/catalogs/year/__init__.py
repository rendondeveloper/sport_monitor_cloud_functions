"""
Package: Catálogo de años. SPRTMNTRPP-82.
Un endpoint /api/catalogs/year con GET (list), POST/PUT/DELETE masivo.
"""

import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from ._common import cors_headers
from .create_year import handle_create
from .delete_year import handle_delete
from .list_year import handle_list
from .update_year import handle_update

LOG_PREFIX = "[catalog_year]"


@https_fn.on_request()
def catalog_year(req: https_fn.Request) -> https_fn.Response:
    """GET lista, POST/PUT/DELETE masivo para catálogo años."""
    validation_response = validate_request(
        req, ["GET", "POST", "PUT", "DELETE"], "catalog_year", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "catalog_year"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response("", status=401, headers=cors_headers())

        db = firestore.client()

        if req.method == "GET":
            return handle_list(db)
        if req.method == "POST":
            return handle_create(req, db)
        if req.method == "PUT":
            return handle_update(req, db)
        if req.method == "DELETE":
            return handle_delete(req, db)

        return https_fn.Response("", status=405, headers=cors_headers())

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers=cors_headers())
