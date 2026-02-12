"""
Creación masiva en el catálogo de marcas de motos (POST). SPRTMNTRPP-82.
"""

import json
import logging

from firebase_functions import https_fn
from firebase_functions.https_fn import Request
from google.cloud.firestore import Client

from ._common import cors_headers, validate_item_vehicle, vehicles_ref

LOG_PREFIX = "[catalog_vehicle]"


def handle_create(req: Request, db: Client) -> https_fn.Response:
    """Crea items masivamente. Body: [ { \"name\", \"models\"?, \"logoUrl\"? }, ... ] (lista directa)."""
    ref = vehicles_ref(db)
    try:
        body = req.get_json(silent=True)
    except (ValueError, TypeError) as e:
        logging.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
        return https_fn.Response("", status=400, headers=cors_headers())
    if not isinstance(body, list) or len(body) == 0:
        logging.warning("%s Request body debe ser un array no vacío", LOG_PREFIX)
        return https_fn.Response("", status=400, headers=cors_headers())

    ids = []
    for i, item in enumerate(body):
        err = validate_item_vehicle(item)
        if err:
            logging.warning("%s [%s]: %s", LOG_PREFIX, i, err)
            return https_fn.Response("", status=400, headers=cors_headers())
        data = {
            "name": str(item["name"]).strip(),
            "models": [
                str(m).strip() for m in (item.get("models") or []) if isinstance(m, str)
            ],
        }
        if item.get("logoUrl") is not None:
            data["logoUrl"] = str(item["logoUrl"]).strip()
        doc_ref = ref.document()
        doc_ref.set(data)
        ids.append(doc_ref.id)

    return https_fn.Response(
        json.dumps(ids, ensure_ascii=False),
        status=201,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
