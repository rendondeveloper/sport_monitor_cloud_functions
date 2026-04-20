"""
Tests para staff_route: router central de staff.
- Token inválido o faltante -> 401
- Path no reconocido -> 404
- Método inválido (cuando validate_request aplica) -> 405
- Dispatch de ruta pública legacy /api/create_staff_user
"""

import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(method="POST", path="/api/create_staff_user", body=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = {}
    req.headers = {"Authorization": "Bearer valid-test-token"}
    req.get_json = lambda silent=True: body
    return req


@patch("staff.staff_route.verify_bearer_token", return_value=False)
@patch("staff.staff_route.validate_request", return_value=None)
def test_staff_route_invalid_token_returns_401(mock_validate, mock_verify):
    from staff.staff_route import staff_route

    req = _make_request()
    response = staff_route(req)
    assert response.status_code == 401


@patch("staff.staff_route.verify_bearer_token", return_value=True)
@patch("staff.staff_route.validate_request", return_value=None)
def test_staff_route_unknown_path_returns_404(mock_validate, mock_verify):
    from staff.staff_route import staff_route

    req = _make_request(path="/api/create_staff_user_unknown")
    response = staff_route(req)
    assert response.status_code == 404


@patch("staff.staff_route.verify_bearer_token", return_value=True)
def test_staff_route_invalid_method_returns_405_from_validate_request(mock_verify):
    from firebase_functions import https_fn
    from staff.staff_route import staff_route

    req = _make_request(method="GET")
    method_not_allowed = https_fn.Response(
        "",
        status=405,
        headers={"Access-Control-Allow-Origin": "*"},
    )

    with patch(
        "staff.staff_route.validate_request",
        return_value=method_not_allowed,
    ) as mock_validate:
        response = staff_route(req)

    assert response.status_code == 405
    mock_validate.assert_called_once()
    mock_verify.assert_not_called()


@patch("staff.staff_route.verify_bearer_token", return_value=True)
@patch("staff.staff_route.validate_request", return_value=None)
@patch("staff.staff_route._HANDLERS")
def test_staff_route_dispatch_create_staff_user_legacy(
    mock_handlers, mock_validate, mock_verify
):
    from staff.staff_route import _ACTION_CREATE_STAFF_USER_LEGACY, staff_route

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/create_staff_user", method="POST")
    response = staff_route(req)

    assert response.status_code == 201
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_CREATE_STAFF_USER_LEGACY)
    mock_handlers.__getitem__.return_value.assert_called_once_with(req)
