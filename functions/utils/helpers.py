from datetime import datetime
from typing import Any


def format_utc_to_local_datetime(utc_datetime: datetime) -> str:
    """
    Convierte un datetime UTC al formato ISO 8601 con Z
    Ejemplo: 2025-10-24T19:03:35Z
    """
    # Formatear como ISO 8601 con Z (UTC)
    formatted_date = utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    return formatted_date


def convert_firestore_value(value: Any) -> Any:
    """
    Convierte valores de Firestore a tipos JSON serializables.

    Maneja:
    - Timestamps de Firestore (convierte a ISO8601)
    - datetime de Python (convierte a ISO8601)
    - dict y list (recursivo)
    - Otros tipos primitivos (str, int, float, bool) se retornan tal cual

    Args:
        value: Valor a convertir (puede ser cualquier tipo de Firestore)

    Returns:
        Valor convertido a tipo JSON serializable
    """
    if value is None:
        return None
    # Timestamp de Firestore (verificar por tipo o método)
    if hasattr(value, "timestamp") and hasattr(value, "to_datetime"):
        # Es un Timestamp de Firestore
        dt = value.to_datetime()
        return dt.isoformat() + "Z" if dt.tzinfo is None else dt.isoformat()
    # datetime de Python
    if isinstance(value, datetime):
        return value.isoformat() + "Z" if value.tzinfo is None else value.isoformat()
    # dict - recursivo
    if isinstance(value, dict):
        return {k: convert_firestore_value(v) for k, v in value.items()}
    # list - recursivo
    if isinstance(value, list):
        return [convert_firestore_value(item) for item in value]
    # Otros tipos (str, int, float, bool) se retornan tal cual
    return value
