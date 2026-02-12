"""
Eliminación masiva en el catálogo de colores (DELETE). SPRTMNTRPP-82.
"""

from firebase_functions import https_fn
from firebase_functions.https_fn import Request
from google.cloud.firestore import Client

from ._common import colors_ref, cors_headers


def handle_delete(req: Request, db: Client) -> https_fn.Response:
    """Elimina por ids. Body: [ \"id1\", \"id2\", ... ] (lista directa de ids)."""
    ref = colors_ref(db)
    try:
        body = req.get_json(silent=True)
    except (ValueError, TypeError):
        return https_fn.Response("", status=400, headers=cors_headers())
    if not isinstance(body, list) or len(body) == 0:
        return https_fn.Response("", status=400, headers=cors_headers())

    for doc_id in body:
        if isinstance(doc_id, str) and doc_id.strip():
            ref.document(doc_id.strip()).delete()

    return https_fn.Response("", status=204, headers=cors_headers())
