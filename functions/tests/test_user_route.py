"""
Tests para user_route: router central de users.
- Token inválido o faltante → 401
- Path no reconocido → 404
- Método no permitido para la acción → 405
- GET /api/users/read con token válido → delega a read.handle
- POST /api/users/create con token válido → delega a create.handle
- PUT /api/users/update con token válido → delega a update.handle
- /api/users/profile (GET) se trata como read
- GET /api/users/profile/{section} delega a read_sections.handle(req, section)
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/users/read", args=None, headers=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = dict(args) if args else {}
    req.headers = dict(headers) if headers else {}
    req.get_json = lambda silent=True: None
    return req


@patch("users.user_route.verify_bearer_token", return_value=False)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_invalid_token_returns_401(mock_validate, mock_verify):
    from users.user_route import user_route

    req = _make_request(path="/api/users/read", headers={"Authorization": "Bearer bad"})
    response = user_route(req)
    assert response.status_code == 401


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_unknown_path_returns_404(mock_validate, mock_verify):
    from users.user_route import user_route

    req = _make_request(path="/api/users/unknown", method="GET")
    response = user_route(req)
    assert response.status_code == 404


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_wrong_method_returns_405(mock_validate, mock_verify):
    from users.user_route import user_route

    req = _make_request(path="/api/users/read", method="POST")
    response = user_route(req)
    assert response.status_code == 405


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_get_read_dispatches_to_read(mock_validate, mock_verify):
    from users.user_route import user_route, _ROUTES

    mock_read_handle = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_read_handle.return_value = mock_resp
    new_routes = dict(_ROUTES)
    new_routes["read"] = ("GET", mock_read_handle)

    with patch.dict("users.user_route._ROUTES", new_routes):
        req = _make_request(path="/api/users/read", method="GET", args={"email": "a@b.com"})
        response = user_route(req)
    assert response.status_code == 200
    mock_read_handle.assert_called_once_with(req)


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_profile_treated_as_read(mock_validate, mock_verify):
    from users.user_route import user_route, _ROUTES

    mock_read_handle = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_read_handle.return_value = mock_resp
    new_routes = dict(_ROUTES)
    new_routes["read"] = ("GET", mock_read_handle)

    with patch.dict("users.user_route._ROUTES", new_routes):
        req = _make_request(path="/api/users/profile", method="GET", args={"email": "a@b.com"})
        response = user_route(req)
    assert response.status_code == 200
    mock_read_handle.assert_called_once_with(req)


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_post_create_dispatches_to_create(mock_validate, mock_verify):
    from users.user_route import user_route, _ROUTES

    mock_create_handle = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_create_handle.return_value = mock_resp
    new_routes = dict(_ROUTES)
    new_routes["create"] = ("POST", mock_create_handle)

    with patch.dict("users.user_route._ROUTES", new_routes):
        req = _make_request(path="/api/users/create", method="POST")
        req.get_json = lambda silent=True: {"email": "x@y.com", "authUserId": "uid1"}
        response = user_route(req)
    assert response.status_code == 201
    mock_create_handle.assert_called_once_with(req)


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_put_update_dispatches_to_update(mock_validate, mock_verify):
    from users.user_route import user_route, _ROUTES

    mock_update_handle = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_update_handle.return_value = mock_resp
    new_routes = dict(_ROUTES)
    new_routes["update"] = ("PUT", mock_update_handle)

    with patch.dict("users.user_route._ROUTES", new_routes):
        req = _make_request(path="/api/users/update", method="PUT", args={"userId": "u1"})
        req.get_json = lambda silent=True: {"email": "n@m.com"}
        response = user_route(req)
    assert response.status_code == 200
    mock_update_handle.assert_called_once_with(req)


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
@patch("users.user_route.read_sections_handle")
def test_user_route_profile_section_dispatches_to_read_sections(mock_read_sections, mock_validate, mock_verify):
    from users.user_route import user_route

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_read_sections.return_value = mock_resp

    req = _make_request(path="/api/users/healthData", method="GET", args={"userId": "user1"})
    response = user_route(req)
    assert response.status_code == 200
    mock_read_sections.assert_called_once_with(req, "healthData")


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
@patch("users.user_route.read_sections_handle")
def test_user_route_profile_membership_dispatches_to_read_sections(mock_read_sections, mock_validate, mock_verify):
    """Path /api/users/profile/membership despacha a read_sections con section membership (subcolección)."""
    from users.user_route import user_route

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_read_sections.return_value = mock_resp

    req = _make_request(path="/api/users/profile/membership", method="GET", args={"userId": "uid1"})
    response = user_route(req)
    assert response.status_code == 200
    mock_read_sections.assert_called_once_with(req, "membership")


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
@patch("users.user_route.read_sections_handle")
def test_user_route_profile_section_fallback_single_segment(mock_read_sections, mock_validate, mock_verify):
    """Path que llega solo como segmento (ej. tras rewrite) también despacha a read_sections."""
    from users.user_route import user_route

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_read_sections.return_value = mock_resp

    req = _make_request(path="/personalData", method="GET", args={"userId": "user1"})
    response = user_route(req)
    assert response.status_code == 200
    mock_read_sections.assert_called_once_with(req, "personalData")


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
@patch("users.user_route.delete_section_item_handle")
def test_user_route_delete_emergency_contacts_dispatches_to_delete_section_item(
    mock_delete_handle, mock_validate, mock_verify
):
    """DELETE /api/users/emergencyContacts despacha a delete_section_item con section emergencyContacts."""
    from users.user_route import user_route

    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_delete_handle.return_value = mock_resp

    req = _make_request(
        path="/api/users/emergencyContacts",
        method="DELETE",
        args={"userId": "user1", "id": "ec1"},
    )
    response = user_route(req)
    assert response.status_code == 204
    mock_delete_handle.assert_called_once_with(req, "emergencyContacts")


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
@patch("users.user_route.delete_section_item_handle")
def test_user_route_delete_vehicles_dispatches_to_delete_section_item(
    mock_delete_handle, mock_validate, mock_verify
):
    """DELETE /api/users/vehicles despacha a delete_section_item con section vehicles."""
    from users.user_route import user_route

    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_delete_handle.return_value = mock_resp

    req = _make_request(
        path="/api/users/vehicles",
        method="DELETE",
        args={"userId": "user1", "id": "veh1"},
    )
    response = user_route(req)
    assert response.status_code == 204
    mock_delete_handle.assert_called_once_with(req, "vehicles")


@patch("users.user_route.verify_bearer_token", return_value=True)
@patch("users.user_route.validate_request", return_value=None)
def test_user_route_delete_personal_data_returns_405(mock_validate, mock_verify):
    """DELETE en sección no permitida (personalData) retorna 405."""
    from users.user_route import user_route

    req = _make_request(
        path="/api/users/personalData",
        method="DELETE",
        args={"userId": "user1", "id": "pd1"},
    )
    response = user_route(req)
    assert response.status_code == 405
