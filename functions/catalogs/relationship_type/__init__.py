"""
Package: Catálogo de tipos de relación para contactos de emergencia.
Endpoint /api/catalogs/relationship-type — solo GET (read).
"""

import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

from ._common import cors_headers
from .list_relationship_type import handle_list

LOG_PREFIX = "[catalog_relationship_type]"


@https_fn.on_request(region="us-east4")
def catalog_relationship_type(req: https_fn.Request) -> https_fn.Response:
    """GET lista de tipos de relación para contactos de emergencia."""
    validation_response = validate_request(
        req, ["GET"], "catalog_relationship_type", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "catalog_relationship_type"):
            logging.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response("", status=401, headers=cors_headers())

        db = firestore.client()

        if req.method == "GET":
            return handle_list(db)

        return https_fn.Response("", status=405, headers=cors_headers())

    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers=cors_headers())
