"""
Tests para competitor_api_route: router central de competitors.
- Token inválido o faltante -> 401
- Path no reconocido -> 404
- Método inválido (cuando validate_request aplica) -> 405
- Dispatch de rutas públicas de competitors + legado /api/create_competitor
"""

import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/competitors/competitor-route", args=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = dict(args) if args else {}
    req.headers = {"Authorization": "Bearer valid-test-token"}
    req.get_json = lambda silent=True: None
    return req


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=False)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
def test_competitor_api_route_invalid_token_returns_401(mock_validate, mock_verify):
    from competitors.competitor_api_route import competitor_api_route

    req = _make_request()
    response = competitor_api_route(req)
    assert response.status_code == 401


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
def test_competitor_api_route_unknown_path_returns_404(mock_validate, mock_verify):
    from competitors.competitor_api_route import competitor_api_route

    req = _make_request(path="/api/competitors/unknown-path")
    response = competitor_api_route(req)
    assert response.status_code == 404


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
def test_competitor_api_route_invalid_method_returns_405_from_validate_request(mock_verify):
    from competitors.competitor_api_route import competitor_api_route
    from firebase_functions import https_fn

    req = _make_request(method="PUT")
    method_not_allowed = https_fn.Response(
        "",
        status=405,
        headers={"Access-Control-Allow-Origin": "*"},
    )

    with patch(
        "competitors.competitor_api_route.validate_request",
        return_value=method_not_allowed,
    ) as mock_validate:
        response = competitor_api_route(req)

    assert response.status_code == 405
    mock_validate.assert_called_once()
    mock_verify.assert_not_called()


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_competitor_route(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_COMPETITOR_ROUTE,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/competitor-route")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_COMPETITOR_ROUTE)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_competitor_route_wildcard(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_COMPETITOR_ROUTE,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/competitor-route/extra/segment")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_COMPETITOR_ROUTE)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_create_user(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_CREATE_COMPETITOR_USER,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(method="POST", path="/api/competitors/create-user")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_CREATE_COMPETITOR_USER)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_delete_competitor(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_DELETE_COMPETITOR,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(method="DELETE", path="/api/competitors/delete-competitor")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_DELETE_COMPETITOR)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_delete_user(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_DELETE_COMPETITOR_USER,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(method="DELETE", path="/api/competitors/delete-user")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_DELETE_COMPETITOR_USER)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_competitor_by_email(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_COMPETITOR_BY_EMAIL,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-competitor-by-email")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_GET_COMPETITOR_BY_EMAIL)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_event_competitor_by_email(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_EVENT_COMPETITOR_BY_EMAIL,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-event-competitor-by-email")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(
        _ACTION_GET_EVENT_COMPETITOR_BY_EMAIL
    )


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_event_competitor_by_id(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_EVENT_COMPETITOR_BY_ID,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-event-competitor-by-id")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_GET_EVENT_COMPETITOR_BY_ID)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_competitor_by_id(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_COMPETITOR_BY_ID,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-competitor-by-id")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_GET_COMPETITOR_BY_ID)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_competitor_by_id_wildcard(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_COMPETITOR_BY_ID,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-competitor-by-id/user-1")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_GET_COMPETITOR_BY_ID)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_competitors_by_event(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_COMPETITORS_BY_EVENT,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-competitors-by-event")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_GET_COMPETITORS_BY_EVENT)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_get_competitors_by_event_wildcard(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_GET_COMPETITORS_BY_EVENT,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/get-competitors-by-event/event-1/day-1")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_GET_COMPETITORS_BY_EVENT)


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_list_competitors_by_event(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_LIST_COMPETITORS_BY_EVENT,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/list-competitors-by-event")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(
        _ACTION_LIST_COMPETITORS_BY_EVENT
    )


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_list_competitors_by_event_wildcard(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_LIST_COMPETITORS_BY_EVENT,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/competitors/list-competitors-by-event/event-1/day-1")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(
        _ACTION_LIST_COMPETITORS_BY_EVENT
    )


@patch("competitors.competitor_api_route.verify_bearer_token", return_value=True)
@patch("competitors.competitor_api_route.validate_request", return_value=None)
@patch("competitors.competitor_api_route._HANDLERS")
def test_competitor_api_route_dispatch_legacy_create_competitor(
    mock_handlers, mock_validate, mock_verify
):
    from competitors.competitor_api_route import (
        _ACTION_CREATE_COMPETITOR_LEGACY,
        competitor_api_route,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(method="POST", path="/api/create_competitor")
    response = competitor_api_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_CREATE_COMPETITOR_LEGACY)
