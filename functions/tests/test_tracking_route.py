"""
Pruebas unitarias para tracking_route.
"""

import sys
from unittest.mock import MagicMock, patch

# Asegurar que functions esté en el path
sys.path.insert(0, ".")


def _make_request(method: str = "POST", path: str = "/api/tracking/competitor-position"):
    req = MagicMock()
    req.method = method
    req.path = path
    return req


@patch("tracking.tracking_route.validate_request")
def test_tracking_route_invalid_method_returns_405(mock_validate_request):
    """Método inválido -> 405 por validate_request."""
    from firebase_functions import https_fn
    from tracking.tracking_route import tracking_route

    mock_validate_request.return_value = https_fn.Response(
        "",
        status=405,
        headers={"Access-Control-Allow-Origin": "*"},
    )

    response = tracking_route(_make_request(method="GET"))

    assert response.status_code == 405


@patch("tracking.tracking_route.validate_request")
def test_tracking_route_unknown_path_returns_404(mock_validate_request):
    """Path desconocido -> 404."""
    from tracking.tracking_route import tracking_route

    mock_validate_request.return_value = None
    response = tracking_route(_make_request(path="/api/tracking/otro-endpoint"))

    assert response.status_code == 404


@patch("tracking.tracking_route._handle_track_competitor_position")
@patch("tracking.tracking_route.validate_request")
def test_tracking_route_dispatch_competitor_position(
    mock_validate_request, mock_handle_track_competitor_position
):
    """Dispatch correcto de /api/tracking/competitor-position."""
    from firebase_functions import https_fn
    from tracking.tracking_route import tracking_route

    req = _make_request(path="/api/tracking/competitor-position")
    expected_response = https_fn.Response(
        "",
        status=200,
        headers={"Access-Control-Allow-Origin": "*"},
    )
    mock_validate_request.return_value = None
    mock_handle_track_competitor_position.return_value = expected_response

    response = tracking_route(req)

    assert response.status_code == 200
    mock_handle_track_competitor_position.assert_called_once_with(
        req, skip_request_validation=True
    )
