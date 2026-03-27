import logging

from firebase_admin import auth
from firebase_functions import https_fn
from typing import Optional

try:
    from firebase_admin._token_gen import ExpiredIdTokenError
except ImportError:
    ExpiredIdTokenError = type("ExpiredIdTokenError", (), {})


def verify_bearer_token(req: https_fn.Request, function_name: str = "function") -> bool:
    """
    Verifica el token Bearer para autenticación

    Args:
        req: Request HTTP de Firebase Functions
        function_name: Nombre de la función que llama (para logging)

    Returns:
        bool: True si el token es válido, False si es inválido o falta
    """
    auth_header = req.headers.get("Authorization")

    if not auth_header:
        logging.warning("%s: Header Authorization faltante", function_name)
        return False


def validate_bearer_token(
    req: https_fn.Request,
    function_name: str = "function",
    return_json_error: bool = False,
) -> Optional[https_fn.Response]:
    """
    Valida que exista Bearer token y sea válido (Firebase Auth).

    Similar a `validate_request()`: retorna Response si hay que cortar el flujo,
    o None si la validación pasó.
    """
    _ = return_json_error  # mantenemos la firma consistente (por ahora no se usa)

    if verify_bearer_token(req, function_name):
        return None

    return https_fn.Response(
        "",
        status=401,
        headers={"Access-Control-Allow-Origin": "*"},
    )

    if not auth_header.startswith("Bearer "):
        logging.warning("%s: Formato de Authorization incorrecto", function_name)
        return False

    token = auth_header.split("Bearer ")[1].strip()

    if not token:
        logging.warning("%s: Token vacío", function_name)
        return False

    try:
        auth.verify_id_token(token)
        return True
    except ExpiredIdTokenError:
        logging.warning("%s: Token expirado", function_name)
        return False
    except (ValueError, TypeError, AttributeError) as e:
        logging.warning("%s: Error validando token: %s", function_name, e)
        return False
    except Exception as e:
        # Cualquier otro error de auth (ej. token revocado, firma inválida) → 401, no 500
        logging.warning("%s: Error validando token: %s", function_name, e)
        return False

