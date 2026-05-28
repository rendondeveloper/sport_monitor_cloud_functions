import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/events/checklists/list", args=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = dict(args) if args else {}
    req.headers = {"Authorization": "Bearer valid-test-token"}
    req.get_json = lambda silent=True: None
    return req


@patch("checklists.checklist_route.verify_bearer_token", return_value=False)
@patch("checklists.checklist_route.validate_request", return_value=None)
def test_checklist_route_invalid_token_returns_401(mock_validate, mock_verify):
    from checklists.checklist_route import checklist_route

    response = checklist_route(_make_request())
    assert response.status_code == 401


@patch("checklists.checklist_route.get_bearer_uid", return_value=None)
@patch("checklists.checklist_route.verify_bearer_token", return_value=True)
@patch("checklists.checklist_route.validate_request", return_value=None)
def test_checklist_route_missing_uid_returns_401(mock_validate, mock_verify, mock_uid):
    from checklists.checklist_route import checklist_route

    response = checklist_route(_make_request())
    assert response.status_code == 401


@patch("checklists.checklist_route.get_bearer_uid", return_value="uid-1")
@patch("checklists.checklist_route.verify_bearer_token", return_value=True)
@patch("checklists.checklist_route.validate_request", return_value=None)
def test_checklist_route_unknown_path_returns_404(mock_validate, mock_verify, mock_uid):
    from checklists.checklist_route import checklist_route

    response = checklist_route(_make_request(path="/api/events/checklists/unknown"))
    assert response.status_code == 404


@patch("checklists.checklist_route.get_bearer_uid", return_value="uid-1")
@patch("checklists.checklist_route.verify_bearer_token", return_value=True)
def test_checklist_route_validate_request_early_return(mock_verify, mock_uid):
    from checklists.checklist_route import checklist_route
    from firebase_functions import https_fn

    cors_response = https_fn.Response("", status=405, headers={"Access-Control-Allow-Origin": "*"})
    with patch("checklists.checklist_route.validate_request", return_value=cors_response):
        response = checklist_route(_make_request(method="PATCH"))
    assert response.status_code == 405
    mock_verify.assert_not_called()


@patch("checklists.checklist_route.get_bearer_uid", return_value="uid-1")
@patch("checklists.checklist_route.verify_bearer_token", return_value=True)
@patch("checklists.checklist_route.validate_request", return_value=None)
@patch("checklists.checklist_route._HANDLERS")
def test_checklist_route_dispatches_list(mock_handlers, mock_validate, mock_verify, mock_uid):
    from checklists.checklist_route import _ACTION_LIST, checklist_route

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_handlers.__getitem__.return_value = MagicMock(return_value=mock_response)

    response = checklist_route(
        _make_request(path="/api/events/checklists/list", args={"eventId": "evt-1"})
    )

    assert response.status_code == 200
    mock_handlers.__getitem__.assert_called_once_with(_ACTION_LIST)


pytest_cases = [
    ("GET", "/api/events/checklists/get", "get"),
    ("POST", "/api/events/checklists/create", "create"),
    ("PUT", "/api/events/checklists/update", "update"),
    ("PUT", "/api/events/checklists/update-photos", "update_photos"),
    ("DELETE", "/api/events/checklists/delete", "delete"),
    ("GET", "/api/events/checklists/participant-progress", "participant_progress"),
]


@patch("checklists.checklist_route.get_bearer_uid", return_value="uid-1")
@patch("checklists.checklist_route.verify_bearer_token", return_value=True)
@patch("checklists.checklist_route.validate_request", return_value=None)
@patch("checklists.checklist_route._HANDLERS")
def test_checklist_route_dispatches_all_actions(
    mock_handlers, mock_validate, mock_verify, mock_uid
):
    from checklists.checklist_route import checklist_route

    for method, path, action_key in pytest_cases:
        mock_handlers.reset_mock()
        handler = MagicMock(return_value=MagicMock(status_code=200))
        mock_handlers.__getitem__.return_value = handler

        response = checklist_route(_make_request(method=method, path=path))

        assert response.status_code == 200
        mock_handlers.__getitem__.assert_called_once_with(action_key)
        handler.assert_called_once()


def test_resolve_action_invalid_paths():
    from checklists.checklist_route import _resolve_action

    assert _resolve_action("/api/events/checklists/list", "POST") is None
    assert _resolve_action("/api/other/checklists/list", "GET") is None
    assert _resolve_action("/api/events/checklists", "GET") is None
    assert _resolve_action("", "GET") is None
    assert _resolve_action("/api/events/checklists/update-photos", "PUT") == "update_photos"
    assert _resolve_action("/api/events/checklists/update-photos", "POST") is None
