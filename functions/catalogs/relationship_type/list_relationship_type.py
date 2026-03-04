"""
Listado del catálogo de tipos de relación (GET).
"""

import json

from firebase_functions import https_fn
from google.cloud.firestore import Client

from ._common import build_relationship_type_item, cors_headers, relationship_types_ref


def handle_list(db: Client) -> https_fn.Response:
    """Obtiene la lista de tipos de relación ordenada por `order` y retorna JSON."""
    ref = relationship_types_ref(db)
    snapshot = list(ref.stream())
    result = [build_relationship_type_item(doc) for doc in snapshot]
    result.sort(key=lambda x: x.get("order", 0))
    return https_fn.Response(
        json.dumps(result, ensure_ascii=False),
        status=200,
        headers={**cors_headers(), "Content-Type": "application/json; charset=utf-8"},
    )
