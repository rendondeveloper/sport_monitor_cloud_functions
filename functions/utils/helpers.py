from datetime import datetime


def format_utc_to_local_datetime(utc_datetime: datetime) -> str:
    """
    Convierte un datetime UTC al formato ISO 8601 con Z
    Ejemplo: 2025-10-24T19:03:35Z
    """
    # Formatear como ISO 8601 con Z (UTC)
    formatted_date = utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    return formatted_date

