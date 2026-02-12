"""
Creación masiva en el catálogo de años (POST). SPRTMNTRPP-82.
"""

import json
import logging

from firebase_functions import https_fn
from firebase_functions.https_fn import Request
from google.cloud.firestore import Client

from ._common import cors_headers, validate_item_year, years_ref

LOG_PREFIX = "[catalog_year]"


def handle_create(req: Request, db: Client) -> https_fn.Response:
    """Crea items masivamente. Body: [ { \"year\" }, ... ] (lista directa)."""
    ref = years_ref(db)
    try:
        body = req.get_json(silent=True)
    except (ValueError, TypeError) as e:
        logging.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
        return https_fn.Response("", status=400, headers=cors_headers())
    if not isinstance(body, list) or len(body) == 0:
        return https_fn.Response("", status=400, headers=cors_headers())

    ids = []
    for i, item in enumerate(body):
        err = validate_item_year(item)
        if err:
            logging.warning("%s [%s]: %s", LOG_PREFIX, i, err)
            return https_fn.Response("", status=400, headers=cors_headers())
        doc_ref = ref.document()
        doc_ref.set({"year": int(item["year"])})
        ids.append(doc_ref.id)

    return https_fn.Response(
        json.dumps(ids, ensure_ascii=False),
        status=201,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
