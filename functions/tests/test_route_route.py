import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/routes/list", args=None, headers=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = dict(args) if args else {}
    req.headers = (
        dict(headers)
        if headers
        else {"Authorization": "Bearer valid-test-token"}
    )
    req.get_json = lambda silent=True: None
    return req


@patch("routes.route_route.verify_bearer_token", return_value=False)
@patch("routes.route_route.validate_request", return_value=None)
def test_route_route_invalid_token_returns_401(mock_validate, mock_verify):
    from routes.route_route import route_route

    req = _make_request(path="/api/routes/list")
    response = route_route(req)
    assert response.status_code == 401


@patch("routes.route_route.verify_bearer_token", return_value=True)
@patch("routes.route_route.get_bearer_uid", return_value="uid1")
@patch("routes.route_route.validate_request", return_value=None)
def test_route_route_unknown_path_returns_404(mock_validate, mock_uid, mock_verify):
    from routes.route_route import route_route

    req = _make_request(path="/api/routes/unknown")
    response = route_route(req)
    assert response.status_code == 404


@patch("routes.route_route.verify_bearer_token", return_value=True)
@patch("routes.route_route.get_bearer_uid", return_value="uid1")
@patch("routes.route_route.validate_request", return_value=None)
@patch("routes.route_route._HANDLERS")
def test_route_route_dispatches_list(mock_handlers, mock_validate, mock_uid, mock_verify):
    from routes.route_route import route_route, _ACTION_LIST

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/routes/list", args={"eventId": "evt1"})
    response = route_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_LIST)
    mock_handlers.__getitem__.return_value.assert_called_once_with(req, "uid1")
