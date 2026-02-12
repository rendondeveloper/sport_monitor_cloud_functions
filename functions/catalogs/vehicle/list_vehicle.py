"""
Listado del catálogo de marcas de motos (GET). SPRTMNTRPP-82.
"""

import json

from firebase_functions import https_fn
from google.cloud.firestore import Client

from ._common import build_vehicle_item, cors_headers, vehicles_ref


def handle_list(db: Client) -> https_fn.Response:
    """Obtiene la lista de vehicles y retorna JSON."""
    ref = vehicles_ref(db)
    snapshot = list(ref.stream())
    result = [build_vehicle_item(doc) for doc in snapshot]
    return https_fn.Response(
        json.dumps(result, ensure_ascii=False),
        status=200,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
