"""
Router HTTP para tracking.

Rutas soportadas:
- POST /api/tracking/competitor-position

Valida CORS y método HTTP una sola vez y despacha al handler existente
track_competitor_position sin doble validate_request.
"""

import logging

from firebase_functions import https_fn
from utils.helper_http_verb import validate_request

from .track_competitor_position import _handle_track_competitor_position

LOG = logging.getLogger(__name__)

_ACTION_COMPETITOR_POSITION = "competitor-position"


def _action_from_path(path: str) -> str | None:
    """Extrae la acción de tracking desde el path recibido."""
    if not path:
        return None

    parts = [segment for segment in path.strip("/").split("/") if segment]
    if "tracking" not in parts:
        return None

    tracking_index = parts.index("tracking")
    if tracking_index + 1 >= len(parts):
        return None

    action = parts[tracking_index + 1].strip().lower()
    if action == _ACTION_COMPETITOR_POSITION:
        return action
    return None


@https_fn.on_request()
def tracking_route(req: https_fn.Request) -> https_fn.Response:
    """
    Router central HTTP para tracking.

    Endpoint:
    - POST /api/tracking/competitor-position
    """
    validation_response = validate_request(
        req, ["POST"], "tracking_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    action = _action_from_path(getattr(req, "path", "") or "")
    if action is None:
        LOG.warning("tracking_route: Path no reconocido: %s", getattr(req, "path", ""))
        return https_fn.Response(
            "",
            status=404,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    return _handle_track_competitor_position(req, skip_request_validation=True)
