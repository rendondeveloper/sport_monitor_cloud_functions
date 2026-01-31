"""
Pruebas unitarias para create_user (crear usuarios en colección users).
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(method: str = "POST", body: dict | None = None):
    """Construye un mock de Request."""
    if body is None:
        body = {
            "personalData": {"fullName": "Usuario1", "email": "user1@gmail.com"},
        }
    req = MagicMock()
    req.method = method
    req.args.get.side_effect = lambda k, default=None: None
    req.get_json.side_effect = lambda silent=True: body
    return req


@patch("users.user_create.validate_request")
@patch("users.user_create.verify_bearer_token")
@patch("users.user_create.firestore")
def test_create_user_happy_path(mock_firestore, mock_verify, mock_validate):
    """Happy path: body válido → 201, documento creado con id en respuesta."""
    mock_validate.return_value = None
    mock_verify.return_value = True
    mock_client = MagicMock()
    mock_firestore.client.return_value = mock_client
    mock_collection = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "newDocId123"
    mock_collection.document.return_value = mock_doc_ref
    mock_client.collection.return_value = mock_collection

    from users.user_create import create_user

    req = _make_request()
    response = create_user(req)

    assert response.status_code == 201
    data = json.loads(response.get_data(as_text=True))
    assert data == {"id": "newDocId123"}
    mock_doc_ref.set.assert_called_once()
    call_args = mock_doc_ref.set.call_args[0][0]
    assert "personalData" in call_args
    assert call_args["personalData"]["fullName"] == "Usuario1"
    assert call_args["personalData"]["email"] == "user1@gmail.com"


@patch("users.user_create.validate_request")
def test_create_user_invalid_body_null(mock_validate):
    """Body null (get_json retorna None) → 400."""
    mock_validate.return_value = None
    from users.user_create import create_user

    req = _make_request(body=None)
    req.get_json.side_effect = lambda silent=True: None
    with patch("users.user_create.verify_bearer_token", return_value=True):
        response = create_user(req)
    assert response.status_code == 400


@patch("users.user_create.validate_request")
@patch("users.user_create.verify_bearer_token")
@patch("users.user_create.firestore")
def test_create_user_body_empty_allowed(mock_firestore, mock_verify, mock_validate):
    """Body {} (sin campos permitidos) → 201, documento creado vacío."""
    mock_validate.return_value = None
    mock_verify.return_value = True
    mock_client = MagicMock()
    mock_firestore.client.return_value = mock_client
    mock_collection = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "emptyDocId"
    mock_collection.document.return_value = mock_doc_ref
    mock_client.collection.return_value = mock_collection

    from users.user_create import create_user

    req = _make_request(body={})
    response = create_user(req)

    assert response.status_code == 201
    data = json.loads(response.get_data(as_text=True))
    assert data == {"id": "emptyDocId"}
    mock_doc_ref.set.assert_called_once_with({})


@patch("users.user_create.validate_request")
def test_create_user_unauthorized(mock_validate):
    """Token inválido → 401."""
    mock_validate.return_value = None
    from users.user_create import create_user

    req = _make_request()
    with patch("users.user_create.verify_bearer_token", return_value=False):
        response = create_user(req)
    assert response.status_code == 401


@patch("users.user_create.validate_request")
@patch("users.user_create.verify_bearer_token")
@patch("users.user_create.firestore")
def test_create_user_only_allowed_keys(mock_firestore, mock_verify, mock_validate):
    """Solo se guardan claves permitidas; claves extra se ignoran."""
    mock_validate.return_value = None
    mock_verify.return_value = True
    mock_client = MagicMock()
    mock_firestore.client.return_value = mock_client
    mock_collection = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "doc1"
    mock_collection.document.return_value = mock_doc_ref
    mock_client.collection.return_value = mock_collection

    from users.user_create import create_user

    req = _make_request(body={"authUserId": "uid1", "unknownField": "ignored"})
    response = create_user(req)

    assert response.status_code == 201
    mock_doc_ref.set.assert_called_once()
    call_args = mock_doc_ref.set.call_args[0][0]
    assert "authUserId" in call_args
    assert call_args["authUserId"] == "uid1"
    assert "unknownField" not in call_args


@patch("users.user_create.validate_request")
@patch("users.user_create.verify_bearer_token")
@patch("users.user_create.firestore")
def test_create_user_multiple_calls(mock_firestore, mock_verify, mock_validate):
    """Múltiples llamadas crean documentos distintos."""
    mock_validate.return_value = None
    mock_verify.return_value = True
    mock_client = MagicMock()
    mock_firestore.client.return_value = mock_client
    mock_collection = MagicMock()
    ref1, ref2 = MagicMock(), MagicMock()
    ref1.id, ref2.id = "id1", "id2"
    mock_collection.document.side_effect = [ref1, ref2]
    mock_client.collection.return_value = mock_collection

    from users.user_create import create_user

    req1 = _make_request(body={"personalData": {"fullName": "A"}})
    req2 = _make_request(body={"avatarUrl": "https://example.com/av.jpg"})

    r1 = create_user(req1)
    r2 = create_user(req2)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert json.loads(r1.get_data(as_text=True))["id"] == "id1"
    assert json.loads(r2.get_data(as_text=True))["id"] == "id2"
    assert mock_collection.document.call_count == 2
