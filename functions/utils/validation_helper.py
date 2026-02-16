"""
Validation Helper - Validaciones comunes para todas las APIs.

Funciones reutilizables de validación. NO duplicar lógica de
validación en cada Cloud Function.
"""

import re
from typing import Dict, List, Tuple


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Valida que la contraseña cumpla con los requisitos de seguridad.

    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una letra
    - Al menos un número

    Args:
        password: Contraseña a validar.

    Returns:
        Tupla (es_válida, mensaje_error). Si es válida, mensaje vacío.
    """
    if not password or len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"

    if not re.search(r"[a-zA-Z]", password):
        return False, "La contraseña debe incluir al menos una letra"

    if not re.search(r"\d", password):
        return False, "La contraseña debe incluir al menos un número"

    return True, ""


def validate_phone(phone: str) -> bool:
    """
    Valida formato de teléfono.

    Acepta formatos:
    - +521234567890
    - 1234567890
    - (123) 456-7890

    Args:
        phone: Número de teléfono.

    Returns:
        True si el formato es válido.
    """
    if not phone:
        return False

    # Remover espacios, paréntesis y guiones
    clean_phone = re.sub(r"[\s()\-]", "", phone)

    # Validar entre 10 y 15 dígitos (incluyendo código de país)
    return bool(re.match(r"^\+?\d{10,15}$", clean_phone))


def validate_required_fields(
    data: Dict, required_fields: List[str]
) -> Tuple[bool, str]:
    """
    Valida que los campos requeridos estén presentes y no vacíos.

    Args:
        data: Diccionario con los datos.
        required_fields: Lista de campos requeridos.

    Returns:
        Tupla (son_válidos, mensaje_error). Si son válidos, mensaje vacío.
    """
    if not data or not isinstance(data, dict):
        return False, "Datos vacíos o inválidos"

    for field in required_fields:
        if field not in data:
            return False, f"Campo requerido faltante: {field}"

        value = data[field]
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return False, f"Campo requerido vacío: {field}"

    return True, ""


def validate_email(email: str) -> bool:
    """
    Valida formato de email.

    Args:
        email: Email a validar.

    Returns:
        True si el formato es válido.
    """
    if not email:
        return False

    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
