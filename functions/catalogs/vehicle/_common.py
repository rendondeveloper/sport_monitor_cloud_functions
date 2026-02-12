"""
Helpers compartidos para el catálogo de marcas de motos (vehicles). SPRTMNTRPP-82.
"""

from typing import Any, Dict

from google.cloud.firestore import Client
from models.firestore_collections import FirestoreCollections

_CATALOG_DOC_ID = FirestoreCollections.CATALOGS_DEFAULT_DOC_ID


def vehicles_ref(db: Client):
    """Referencia a la subcolección vehicles del catálogo default."""
    return (
        db.collection(FirestoreCollections.CATALOGS)
        .document(_CATALOG_DOC_ID)
        .collection(FirestoreCollections.CATALOGS_VEHICLES)
    )


def build_vehicle_item(doc) -> Dict[str, Any]:
    """Construye el dict de un vehicle para la respuesta."""
    data = doc.to_dict() or {}
    return {
        "id": doc.id,
        "name": data.get("name", ""),
        "models": data.get("models") or [],
        "logoUrl": data.get("logoUrl"),
    }


def validate_item_vehicle(item: Any) -> str | None:
    """Valida un item de vehicle. Retorna None si es válido, mensaje de error si no."""
    if not item or not isinstance(item, dict):
        return "item inválido"
    if not item.get("name") or not isinstance(item.get("name"), str):
        return "name es requerido y debe ser string"
    models = item.get("models")
    if models is not None and not isinstance(models, list):
        return "models debe ser array"
    if models is not None:
        for m in models:
            if not isinstance(m, str):
                return "cada elemento de models debe ser string"
    return None


def cors_headers() -> Dict[str, str]:
    """Headers CORS para respuestas."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
