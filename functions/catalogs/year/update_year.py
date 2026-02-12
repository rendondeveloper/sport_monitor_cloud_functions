"""
Actualización masiva en el catálogo de años (PUT). SPRTMNTRPP-82.
"""

import logging

from firebase_functions import https_fn
from firebase_functions.https_fn import Request
from google.cloud.firestore import Client

from ._common import cors_headers, validate_item_year, years_ref

LOG_PREFIX = "[catalog_year]"


def handle_update(req: Request, db: Client) -> https_fn.Response:
    """Actualiza items masivamente. Body: [ { \"id\", \"year\" }, ... ] (lista directa)."""
    ref = years_ref(db)
    try:
        body = req.get_json(silent=True)
    except (ValueError, TypeError) as e:
        logging.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
        return https_fn.Response("", status=400, headers=cors_headers())
    if not isinstance(body, list) or len(body) == 0:
        return https_fn.Response("", status=400, headers=cors_headers())

    for i, item in enumerate(body):
        if not item.get("id"):
            return https_fn.Response("", status=400, headers=cors_headers())
        err = validate_item_year(item)
        if err:
            logging.warning("%s [%s]: %s", LOG_PREFIX, i, err)
            return https_fn.Response("", status=400, headers=cors_headers())
        doc_ref = ref.document(item["id"])
        if not doc_ref.get().exists:
            return https_fn.Response("", status=404, headers=cors_headers())
        doc_ref.update({"year": int(item["year"])})

    return https_fn.Response("", status=200, headers=cors_headers())
