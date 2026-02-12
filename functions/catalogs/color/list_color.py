"""
Listado del catálogo de colores (GET). SPRTMNTRPP-82.
"""

import json

from firebase_functions import https_fn
from google.cloud.firestore import Client

from ._common import build_color_item, colors_ref, cors_headers


def handle_list(db: Client) -> https_fn.Response:
    """Obtiene la lista de colores y retorna JSON."""
    ref = colors_ref(db)
    snapshot = list(ref.stream())
    result = [build_color_item(doc) for doc in snapshot]
    return https_fn.Response(
        json.dumps(result, ensure_ascii=False),
        status=200,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
