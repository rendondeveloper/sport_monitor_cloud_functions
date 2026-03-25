"""
Creación masiva en el catálogo de tipos de checkpoint (POST).

Body: array de `{ "type": "<categoría>", "items": [ ... ] }`.
Cada ítem: name, type, icon, description (string); abbreviation opcional (string o null).
"""

import json
import logging

from firebase_functions import https_fn
from firebase_functions.https_fn import Request
from google.cloud.firestore import Client

from ._common import checkpoint_types_ref, cors_headers, validate_checkpoint_groups_body

LOG_PREFIX = "[catalog_checkpoint_type]"


def handle_create(req: Request, db: Client) -> https_fn.Response:
    """Crea documentos por grupo; retorna lista de ids en orden de inserción."""
    ref = checkpoint_types_ref(db)
    try:
        body = req.get_json(silent=True)
    except (ValueError, TypeError) as e:
        logging.warning("%s Error parseando JSON: %s", LOG_PREFIX, e)
        return https_fn.Response("", status=400, headers=cors_headers())

    err = validate_checkpoint_groups_body(body)
    if err:
        logging.warning("%s %s", LOG_PREFIX, err)
        return https_fn.Response("", status=400, headers=cors_headers())

    ids: list[str] = []
    for group in body:
        category = str(group["type"]).strip()
        for item in group["items"]:
            data = {
                "category": category,
                "name": str(item["name"]).strip(),
                "type": str(item["type"]).strip(),
                "icon": str(item["icon"]).strip(),
                "description": str(item["description"]).strip(),
            }
            ab_raw = item.get("abbreviation")
            if isinstance(ab_raw, str) and ab_raw.strip():
                data["abbreviation"] = ab_raw.strip()
            doc_ref = ref.document()
            doc_ref.set(data)
            ids.append(doc_ref.id)

    return https_fn.Response(
        json.dumps(ids, ensure_ascii=False),
        status=201,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
