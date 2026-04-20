"""
Tests para checkpoint_route: router central de checkpoints.
- Token inválido o faltante -> 401
- Path no reconocido -> 404
- Método inválido (cuando validate_request aplica) -> 405
- Dispatch de rutas públicas de checkpoints
"""

import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/checkpoint/dayofrace/active/evt1", args=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = dict(args) if args else {}
    req.headers = {"Authorization": "Bearer valid-test-token"}
    req.get_json = lambda silent=True: None
    return req


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=False)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
def test_checkpoint_route_invalid_token_returns_401(mock_validate, mock_verify):
    from checkpoints.checkpoint_route import checkpoint_route

    req = _make_request()
    response = checkpoint_route(req)
    assert response.status_code == 401


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
def test_checkpoint_route_unknown_path_returns_404(mock_validate, mock_verify):
    from checkpoints.checkpoint_route import checkpoint_route

    req = _make_request(path="/api/checkpoint/unknown/path")
    response = checkpoint_route(req)
    assert response.status_code == 404


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
def test_checkpoint_route_invalid_method_returns_405_from_validate_request(mock_verify):
    from checkpoints.checkpoint_route import checkpoint_route
    from firebase_functions import https_fn

    req = _make_request(method="POST")
    method_not_allowed = https_fn.Response(
        "",
        status=405,
        headers={"Access-Control-Allow-Origin": "*"},
    )

    with patch(
        "checkpoints.checkpoint_route.validate_request",
        return_value=method_not_allowed,
    ) as mock_validate:
        response = checkpoint_route(req)

    assert response.status_code == 405
    mock_validate.assert_called_once()
    mock_verify.assert_not_called()


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_day_of_race_active(
    mock_handlers, mock_validate, mock_verify
):
    from checkpoints.checkpoint_route import checkpoint_route, _ACTION_DAY_OF_RACE_ACTIVE

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/checkpoint/dayofrace/active/event-1")
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_DAY_OF_RACE_ACTIVE)


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_checkpoint(mock_handlers, mock_validate, mock_verify):
    from checkpoints.checkpoint_route import checkpoint_route, _ACTION_CHECKPOINT

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/checkpoint/cp-1/event/event-1")
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_CHECKPOINT)


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_all_competitor_tracking(
    mock_handlers, mock_validate, mock_verify
):
    from checkpoints.checkpoint_route import (
        _ACTION_ALL_COMPETITOR_TRACKING,
        checkpoint_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/checkpoint/all-competitor-tracking/event-1/day-1")
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_ALL_COMPETITOR_TRACKING)


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_competitor_tracking(
    mock_handlers, mock_validate, mock_verify
):
    from checkpoints.checkpoint_route import _ACTION_COMPETITOR_TRACKING, checkpoint_route

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/checkpoint/competitor-tracking/event-1/day-1/cp-1")
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_COMPETITOR_TRACKING)


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_days_of_race(
    mock_handlers, mock_validate, mock_verify
):
    from checkpoints.checkpoint_route import _ACTION_DAYS_OF_RACE, checkpoint_route

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/checkpoint/days-of-race/event-1")
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_DAYS_OF_RACE)


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_update_competitor_status(
    mock_handlers, mock_validate, mock_verify
):
    from checkpoints.checkpoint_route import (
        _ACTION_UPDATE_COMPETITOR_STATUS,
        checkpoint_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(
        method="PUT",
        path="/api/checkpoint/update-competitor-status/event-1/day-1/comp-1/cp-1",
    )
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_UPDATE_COMPETITOR_STATUS)


@patch("checkpoints.checkpoint_route.verify_bearer_token", return_value=True)
@patch("checkpoints.checkpoint_route.validate_request", return_value=None)
@patch("checkpoints.checkpoint_route._HANDLERS")
def test_checkpoint_route_dispatch_change_competitor_status(
    mock_handlers, mock_validate, mock_verify
):
    from checkpoints.checkpoint_route import (
        _ACTION_CHANGE_COMPETITOR_STATUS,
        checkpoint_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(method="PUT", path="/api/checkpoint/change-competitor-status")
    response = checkpoint_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_CHANGE_COMPETITOR_STATUS)
