from typing import List, Optional
from firebase_functions import https_fn


def handle_cors_preflight(
    req: https_fn.Request,
    allowed_methods: Optional[List[str]] = None,
) -> Optional[https_fn.Response]:
    """
    Maneja la petición CORS preflight (OPTIONS).

    Args:
        req: Request HTTP de Firebase Functions
        allowed_methods: Métodos que acepta el endpoint (ej: ["GET"], ["POST"]).
                        Se incluyen en Access-Control-Allow-Methods junto con OPTIONS.

    Returns:
        Response con headers CORS si es OPTIONS, None si no es OPTIONS
    """
    if req.method == "OPTIONS":
        methods = ", ".join((allowed_methods or ["GET"]) + ["OPTIONS"])
        return https_fn.Response(
            "",
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": methods,
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "3600",
            },
        )
    return None


def validate_http_method(
    req: https_fn.Request,
    allowed_methods: List[str],
    function_name: str = "function",
    return_json_error: bool = False,
) -> Optional[https_fn.Response]:
    """
    Valida que el método HTTP de la petición esté en la lista de métodos permitidos

    Args:
        req: Request HTTP de Firebase Functions
        allowed_methods: Lista de métodos HTTP permitidos (ej: ["GET", "POST"])
        function_name: Nombre de la función (para logging y mensajes de error)
        return_json_error: Si True, retorna error en formato JSON. Si False, solo código HTTP

    Returns:
        Response con error 405 si el método no está permitido, None si es válido
    """
    if req.method in allowed_methods:
        return None

    # Construir lista de métodos permitidos para el header Allow
    allowed_str = ", ".join(allowed_methods + ["OPTIONS"])

    if return_json_error:
        import json

        error_response = {
            "error": {
                "code": "method-not-allowed",
                "message": f"Método {req.method} no permitido. Solo se permite {', '.join(allowed_methods)}.",
            }
        }
        return https_fn.Response(
            json.dumps(error_response),
            status=405,
            headers={
                "Content-Type": "application/json",
                "Allow": allowed_str,
                "Access-Control-Allow-Origin": "*",
            },
        )
    else:
        return https_fn.Response(
            "",
            status=405,
            headers={
                "Allow": allowed_str,
                "Access-Control-Allow-Origin": "*",
            },
        )


def validate_request(
    req: https_fn.Request,
    allowed_methods: List[str],
    function_name: str = "function",
    return_json_error: bool = False,
) -> Optional[https_fn.Response]:
    """
    Valida CORS preflight y método HTTP en una sola llamada

    Args:
        req: Request HTTP de Firebase Functions
        allowed_methods: Lista de métodos HTTP permitidos (ej: ["GET", "POST"])
        function_name: Nombre de la función (para logging y mensajes de error)
        return_json_error: Si True, retorna error en formato JSON. Si False, solo código HTTP

    Returns:
        Response si hay que retornar algo (CORS o error de método), None si todo está bien
    """
    # Primero manejar CORS preflight (incluye los métodos permitidos en la respuesta)
    cors_response = handle_cors_preflight(req, allowed_methods)
    if cors_response is not None:
        return cors_response

    # Luego validar método HTTP
    method_response = validate_http_method(
        req, allowed_methods, function_name, return_json_error
    )
    return method_response

