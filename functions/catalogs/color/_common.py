"""
Helpers compartidos para el catálogo de colores. SPRTMNTRPP-82.
"""

from typing import Any, Dict

from google.cloud.firestore import Client
from models.firestore_collections import FirestoreCollections

_CATALOG_DOC_ID = FirestoreCollections.CATALOGS_DEFAULT_DOC_ID


def colors_ref(db: Client):
    """Referencia a la subcolección colors del catálogo default."""
    return (
        db.collection(FirestoreCollections.CATALOGS)
        .document(_CATALOG_DOC_ID)
        .collection(FirestoreCollections.CATALOGS_COLORS)
    )


def build_color_item(doc) -> Dict[str, Any]:
    """Construye el dict de un color para la respuesta."""
    data = doc.to_dict() or {}
    return {
        "id": doc.id,
        "name": data.get("name", ""),
        "hex": data.get("hex", ""),
    }


def validate_item_color(item: Any) -> str | None:
    """Valida un item de color. Retorna None si es válido, mensaje de error si no."""
    if not item or not isinstance(item, dict):
        return "item inválido"
    if not item.get("name") or not isinstance(item.get("name"), str):
        return "name es requerido y debe ser string"
    if not item.get("hex") or not isinstance(item.get("hex"), str):
        return "hex es requerido y debe ser string"
    return None


def cors_headers() -> Dict[str, str]:
    """Headers CORS para respuestas."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
