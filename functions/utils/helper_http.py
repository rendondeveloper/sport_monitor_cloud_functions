import logging
from firebase_admin import auth
from firebase_functions import https_fn


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
    except (ValueError, TypeError, AttributeError) as e:
        logging.warning("%s: Error validando token: %s", function_name, e)
        return False

