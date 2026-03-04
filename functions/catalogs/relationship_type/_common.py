"""
Helpers compartidos para el catálogo de tipos de relación.
"""

from typing import Any, Dict

from google.cloud.firestore import Client
from models.firestore_collections import FirestoreCollections
from utils.helpers import convert_firestore_value

_CATALOG_DOC_ID = FirestoreCollections.CATALOGS_DEFAULT_DOC_ID


def relationship_types_ref(db: Client):
    """Referencia a la subcolección relationship_types del catálogo default."""
    return (
        db.collection(FirestoreCollections.CATALOGS)
        .document(_CATALOG_DOC_ID)
        .collection(FirestoreCollections.CATALOGS_RELATIONSHIP_TYPES)
    )


def build_relationship_type_item(doc) -> Dict[str, Any]:
    """Construye el dict de un tipo de relación para la respuesta."""
    data = doc.to_dict() or {}
    return {
        "id": doc.id,
        "label": convert_firestore_value(data.get("label", "")),
        "order": convert_firestore_value(data.get("order", 0)),
    }


def cors_headers() -> Dict[str, str]:
    """Headers CORS para respuestas."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
