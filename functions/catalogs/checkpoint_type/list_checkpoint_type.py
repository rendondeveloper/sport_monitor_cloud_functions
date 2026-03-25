"""
Listado del catálogo de tipos de checkpoint (GET).

Respuesta: array de `{ "type": "<categoría>", "items": [ { id, name, type, icon, abbreviation, description }, ... ] }`.
"""

import json

from firebase_functions import https_fn
from google.cloud.firestore import Client

from ._common import build_grouped_checkpoint_types_response, checkpoint_types_ref, cors_headers


def handle_list(db: Client) -> https_fn.Response:
    """Obtiene tipos agrupados por categoría y retorna JSON."""
    ref = checkpoint_types_ref(db)
    snapshot = list(ref.stream())
    result = build_grouped_checkpoint_types_response(snapshot)
    return https_fn.Response(
        json.dumps(result, ensure_ascii=False),
        status=200,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
