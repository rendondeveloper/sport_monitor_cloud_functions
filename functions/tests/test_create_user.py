"""
Pruebas unitarias para create.handle (upsert por email en users).
La validación CORS y token la hace user_route; aquí solo se prueba la lógica de negocio.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(method: str = "POST", body: dict | None = None):
    req = MagicMock()
    req.method = method
    req.args.get.side_effect = lambda k, default=None: None
    req.get_json.side_effect = lambda silent=True: body
    return req


def _valid_body(
    email: str = "test@example.com",
    auth_user_id: str = "firebase_uid_123",
    avatar_url: str | None = "https://example.com/avatar.jpg",
) -> dict:
    return {"email": email, "authUserId": auth_user_id, "avatarUrl": avatar_url}


_PATCH_HELPER = "users.create.FirestoreHelper"


@patch(_PATCH_HELPER)
def test_create_user_happy_path_new_user(mock_helper_cls):
    mock_helper_cls.return_value.query_documents.return_value = []
    mock_helper_cls.return_value.create_document.return_value = "newUserId1"

    from users.create import handle as create_handle
    response = create_handle(_make_request(body=_valid_body()))

    assert response.status_code == 201
    data = json.loads(response.get_data(as_text=True))
    assert data == {"id": "newUserId1"}
    mock_helper_cls.return_value.create_document.assert_called_once()
    created_doc = mock_helper_cls.return_value.create_document.call_args[0][1]
    assert created_doc["email"] == "test@example.com"
    assert created_doc["username"] == "test@example.com"
    assert created_doc["authUserId"] == "firebase_uid_123"
    assert created_doc["isActive"] is True
    assert "createdAt" in created_doc
    assert "updatedAt" in created_doc


@patch(_PATCH_HELPER)
def test_create_user_happy_path_existing_user(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.query_documents.return_value = [
        ("existingUserId", {"email": "test@example.com", "username": "", "isActive": False})
    ]

    from users.create import handle as create_handle
    response = create_handle(_make_request(body=_valid_body()))

    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data == {"id": "existingUserId"}
    helper.update_document.assert_called_once()
    update_fields = helper.update_document.call_args[0][2]
    assert update_fields["authUserId"] == "firebase_uid_123"
    assert update_fields["isActive"] is True
    helper.create_document.assert_not_called()


@patch(_PATCH_HELPER)
def test_update_preserves_existing_username(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.query_documents.return_value = [
        ("uid99", {"email": "test@example.com", "username": "piloto_real", "isActive": False})
    ]

    from users.create import handle as create_handle
    response = create_handle(_make_request(body=_valid_body()))

    assert response.status_code == 200
    update_fields = helper.update_document.call_args[0][2]
    assert update_fields["username"] == "piloto_real"


@patch(_PATCH_HELPER)
def test_update_assigns_email_as_username_when_empty(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.query_documents.return_value = [
        ("uid88", {"email": "test@example.com", "username": None, "isActive": False})
    ]

    from users.create import handle as create_handle
    response = create_handle(_make_request(body=_valid_body()))

    assert response.status_code == 200
    update_fields = helper.update_document.call_args[0][2]
    assert update_fields["username"] == "test@example.com"


def test_create_user_body_null():
    from users.create import handle as create_handle
    req = _make_request(body=None)
    req.get_json.side_effect = lambda silent=True: None
    response = create_handle(req)
    assert response.status_code == 400


def test_create_user_body_empty():
    from users.create import handle as create_handle
    response = create_handle(_make_request(body={}))
    assert response.status_code == 400


def test_create_user_missing_email():
    from users.create import handle as create_handle
    response = create_handle(_make_request(body={"authUserId": "uid1"}))
    assert response.status_code == 400


def test_create_user_invalid_email_format():
    from users.create import handle as create_handle
    response = create_handle(_make_request(body={"email": "not-an-email", "authUserId": "uid1"}))
    assert response.status_code == 400


def test_create_user_missing_auth_user_id():
    from users.create import handle as create_handle
    response = create_handle(_make_request(body={"email": "test@example.com"}))
    assert response.status_code == 400


@patch(_PATCH_HELPER)
def test_create_user_firestore_error(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.query_documents.return_value = []
    helper.create_document.side_effect = RuntimeError("Firestore down")

    from users.create import handle as create_handle
    response = create_handle(_make_request(body=_valid_body()))
    assert response.status_code == 500


@patch(_PATCH_HELPER)
def test_create_user_multiple_calls(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.query_documents.return_value = []
    helper.create_document.side_effect = ["idA", "idB"]

    from users.create import handle as create_handle

    r1 = create_handle(_make_request(body=_valid_body(email="a@example.com", auth_user_id="uid_a")))
    r2 = create_handle(_make_request(body=_valid_body(email="b@example.com", auth_user_id="uid_b")))
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert json.loads(r1.get_data(as_text=True))["id"] == "idA"
    assert json.loads(r2.get_data(as_text=True))["id"] == "idB"
    assert helper.create_document.call_count == 2


@patch(_PATCH_HELPER)
def test_create_user_avatar_url_none(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.query_documents.return_value = []
    helper.create_document.return_value = "uid_noavatar"

    from users.create import handle as create_handle
    response = create_handle(_make_request(body=_valid_body(avatar_url=None)))
    assert response.status_code == 201
    created_doc = helper.create_document.call_args[0][1]
    assert created_doc["avatarUrl"] is None
