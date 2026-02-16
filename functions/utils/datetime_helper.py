"""
DateTime Helper - Utilidades para manejo de fechas y timestamps.

Usar get_current_timestamp() para createdAt y updatedAt.
Mantener consistencia de formato en toda la aplicación.
"""

from datetime import datetime, timezone


def get_current_timestamp() -> str:
    """
    Obtiene el timestamp actual en formato ISO 8601 UTC.

    Returns:
        String con timestamp, ej: "2026-02-15T12:00:00+00:00"
    """
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Convierte string ISO 8601 a objeto datetime.

    Args:
        iso_string: String en formato ISO 8601.

    Returns:
        Objeto datetime.
    """
    return datetime.fromisoformat(iso_string)


def format_datetime_for_firestore(dt: datetime) -> str:
    """
    Formatea datetime para guardar en Firestore.

    Args:
        dt: Objeto datetime.

    Returns:
        String en formato ISO 8601.
    """
    return dt.isoformat()
