"""
Listado del catálogo de años (GET). SPRTMNTRPP-82.
"""

import json

from firebase_functions import https_fn
from google.cloud.firestore import Client

from ._common import build_year_item, cors_headers, years_ref


def handle_list(db: Client) -> https_fn.Response:
    """Obtiene la lista de años y retorna JSON."""
    ref = years_ref(db)
    snapshot = list(ref.stream())
    result = [build_year_item(doc) for doc in snapshot]
    return https_fn.Response(
        json.dumps(result, ensure_ascii=False),
        status=200,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
