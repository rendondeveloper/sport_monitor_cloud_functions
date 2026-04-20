"""
Tests para event_route: router central de events.
- Token inválido o faltante -> 401
- Path no reconocido -> 404
- Método inválido (cuando validate_request aplica) -> 405
- GET /api/events despacha
- GET /api/events/detail despacha
- GET /api/event/event-categories/{id} despacha
"""

import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/events", args=None, headers=None):
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


@patch("events.event_route.verify_bearer_token", return_value=False)
@patch("events.event_route.validate_request", return_value=None)
def test_event_route_invalid_token_returns_401(mock_validate, mock_verify):
    from events.event_route import event_route

    req = _make_request(path="/api/events", headers={"Authorization": "Bearer bad"})
    response = event_route(req)
    assert response.status_code == 401


@patch("events.event_route.verify_bearer_token", return_value=True)
@patch("events.event_route.validate_request", return_value=None)
def test_event_route_unknown_path_returns_404(mock_validate, mock_verify):
    from events.event_route import event_route

    req = _make_request(path="/api/events/unknown", method="GET")
    response = event_route(req)
    assert response.status_code == 404


@patch("events.event_route.verify_bearer_token", return_value=True)
def test_event_route_invalid_method_returns_405_from_validate_request(mock_verify):
    from events.event_route import event_route
    from firebase_functions import https_fn

    req = _make_request(method="POST", path="/api/events")

    method_not_allowed = https_fn.Response(
        "",
        status=405,
        headers={"Access-Control-Allow-Origin": "*"},
    )

    with patch(
        "events.event_route.validate_request",
        return_value=method_not_allowed,
    ) as mock_validate:
        response = event_route(req)

    assert response.status_code == 405
    mock_validate.assert_called_once()
    mock_verify.assert_not_called()


@patch("events.event_route.verify_bearer_token", return_value=True)
@patch("events.event_route.validate_request", return_value=None)
@patch("events.event_route._HANDLERS")
def test_event_route_events_dispatches(mock_handlers, mock_validate, mock_verify):
    from events.event_route import event_route, _ACTION_EVENTS

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/events", method="GET")
    response = event_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_EVENTS)
    mock_handlers.__getitem__.return_value.assert_called_once_with(req)


@patch("events.event_route.verify_bearer_token", return_value=True)
@patch("events.event_route.validate_request", return_value=None)
@patch("events.event_route._HANDLERS")
def test_event_route_event_detail_dispatches(mock_handlers, mock_validate, mock_verify):
    from events.event_route import event_route, _ACTION_EVENT_DETAIL

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(path="/api/events/detail", method="GET", args={"eventId": "evt1"})
    response = event_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_EVENT_DETAIL)
    mock_handlers.__getitem__.return_value.assert_called_once_with(req)


@patch("events.event_route.verify_bearer_token", return_value=True)
@patch("events.event_route.validate_request", return_value=None)
@patch("events.event_route._HANDLERS")
def test_event_route_event_categories_dispatches(mock_handlers, mock_validate, mock_verify):
    from events.event_route import event_route, _ACTION_EVENT_CATEGORIES

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    req = _make_request(
        path="/api/event/event-categories/evt1",
        method="GET",
        args={"eventId": "evt1"},
    )
    response = event_route(req)

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_EVENT_CATEGORIES)
    mock_handlers.__getitem__.return_value.assert_called_once_with(req)
