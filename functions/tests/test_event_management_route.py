"""
Tests para event_management/event_management_route.py

Casos obligatorios:
1. Happy path — despacha cada ruta al handler correcto
2. Token inválido -> 401
3. validate_request falla -> retorna su respuesta
4. Path no reconocido -> 404
5. user_id faltante en path -> 404
6. Múltiples rutas son despachadas correctamente
"""

from unittest.mock import MagicMock, patch

import pytest
from firebase_functions import https_fn


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validate_request():
    with patch("event_management.event_management_route.validate_request", return_value=None) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch("event_management.event_management_route.verify_bearer_token", return_value=True) as m:
        yield m


def _make_request(method="GET", path="", body=None, args=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = args or {}
    req.headers = {"Authorization": "Bearer test_token"}
    if body is not None:
        req.get_json.return_value = body
    else:
        req.get_json.return_value = None
    return req


def _ok_response():
    return https_fn.Response("{}", status=200, headers={"Access-Control-Allow-Origin": "*"})


# ============================================================================
# TESTS — _resolve_action
# ============================================================================


class TestResolveAction:
    def test_post_create(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/create", "POST") == ("create", "user123")

    def test_put_update(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/update", "PUT") == ("update", "user123")

    def test_get_event(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/get", "GET") == ("get", "user123")

    def test_get_list(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/list", "GET") == ("list", "user123")

    def test_delete(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/delete", "DELETE") == ("delete", "user123")

    def test_get_info(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/get-info", "GET") == ("get_info", "user123")

    def test_post_save_info(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/save-info", "POST") == ("save_info", "user123")

    def test_unknown_path_returns_none(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/unknown", "GET") == (None, None)

    def test_wrong_method_returns_none(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management/user123/create", "GET") == (None, None)

    def test_too_short_path_returns_none(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/event-management", "GET") == (None, None)

    def test_wrong_base_returns_none(self):
        from event_management.event_management_route import _resolve_action_and_user
        assert _resolve_action_and_user("/api/events/user123/create", "POST") == (None, None)


# ============================================================================
# TESTS — event_management_route Cloud Function
# ============================================================================


class TestEventManagementRouteAuth:
    def test_invalid_validate_request_returns_its_response(self, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        rejection = https_fn.Response("", status=405, headers={"Access-Control-Allow-Origin": "*"})
        with patch("event_management.event_management_route.validate_request", return_value=rejection):
            req = _make_request(method="PATCH", path="/api/event-management/user123/create")
            response = event_management_route(req)
            assert response.status_code == 405

    def test_invalid_token_returns_401(self, mock_validate_request):
        from event_management.event_management_route import event_management_route

        with patch("event_management.event_management_route.verify_bearer_token", return_value=False):
            req = _make_request(method="GET", path="/api/event-management/user123/list")
            response = event_management_route(req)
            assert response.status_code == 401

    def test_missing_user_id_in_path_returns_404(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        req = _make_request(method="GET", path="/api/event-management/list")
        response = event_management_route(req)
        assert response.status_code == 404


class TestEventManagementRouteNotFound:
    def test_unknown_path_returns_404(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        req = _make_request(method="GET", path="/api/event-management/user123/nonexistent")
        response = event_management_route(req)
        assert response.status_code == 404

    def test_empty_path_returns_404(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        req = _make_request(method="GET", path="")
        response = event_management_route(req)
        assert response.status_code == 404


class TestEventManagementRouteDispatch:
    def test_dispatches_create(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_create", return_value=ok) as mock_create:
            req = _make_request(method="POST", path="/api/event-management/user123/create")
            response = event_management_route(req)
            mock_create.assert_called_once_with(req, "user123")
            assert response.status_code == 200

    def test_dispatches_update(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_update", return_value=ok) as mock_update:
            req = _make_request(method="PUT", path="/api/event-management/user123/update")
            response = event_management_route(req)
            mock_update.assert_called_once_with(req, "user123")
            assert response.status_code == 200

    def test_dispatches_get(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_get", return_value=ok) as mock_get:
            req = _make_request(method="GET", path="/api/event-management/user123/get")
            response = event_management_route(req)
            mock_get.assert_called_once_with(req, "user123")
            assert response.status_code == 200

    def test_dispatches_list(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_list", return_value=ok) as mock_list:
            req = _make_request(method="GET", path="/api/event-management/user123/list")
            response = event_management_route(req)
            mock_list.assert_called_once_with(req, "user123")
            assert response.status_code == 200

    def test_dispatches_delete(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_delete", return_value=ok) as mock_delete:
            req = _make_request(method="DELETE", path="/api/event-management/user123/delete")
            response = event_management_route(req)
            mock_delete.assert_called_once_with(req, "user123")
            assert response.status_code == 200

    def test_dispatches_get_info(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_get_info", return_value=ok) as mock_get_info:
            req = _make_request(method="GET", path="/api/event-management/user123/get-info")
            response = event_management_route(req)
            mock_get_info.assert_called_once_with(req, "user123")
            assert response.status_code == 200

    def test_dispatches_save_info(self, mock_validate_request, mock_verify_bearer_token):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_save_info", return_value=ok) as mock_save:
            req = _make_request(method="POST", path="/api/event-management/user123/save-info")
            response = event_management_route(req)
            mock_save.assert_called_once_with(req, "user123")
            assert response.status_code == 200


class TestEventManagementRouteMultipleCalls:
    def test_multiple_calls_are_stable(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from event_management.event_management_route import event_management_route

        ok = _ok_response()
        with patch("event_management.event_management_route.handle_list", return_value=ok):
            for _ in range(3):
                req = _make_request(method="GET", path="/api/event-management/user123/list")
                response = event_management_route(req)
                assert response.status_code == 200
