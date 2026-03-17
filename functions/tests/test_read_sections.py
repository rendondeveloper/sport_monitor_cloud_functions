"""
Tests para read_sections.handle: lectura de subcolecciones del perfil (personalData, healthData, etc.).
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")

_PATCH_HELPER = "users.read_sections.FirestoreHelper"


def _make_request(args=None):
    req = MagicMock()
    req.method = "GET"
    req.args = dict(args) if args else {}
    req.get_json = lambda silent=True: None
    return req


@patch(_PATCH_HELPER)
def test_read_sections_invalid_section_returns_400(mock_helper_cls):
    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "u1"})
    response = read_sections_handle(req, "invalidSection")
    assert response.status_code == 400


@patch(_PATCH_HELPER)
def test_read_sections_missing_user_id_returns_400(mock_helper_cls):
    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={})
    response = read_sections_handle(req, "personalData")
    assert response.status_code == 400


@patch(_PATCH_HELPER)
def test_read_sections_user_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None
    helper.query_documents.return_value = []

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "nonexistent"})
    response = read_sections_handle(req, "personalData")
    assert response.status_code == 404


@patch(_PATCH_HELPER)
def test_read_sections_first_doc_section_returns_single_object(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "a@b.com"}
    helper.query_documents.return_value = [
        ("pd1", {"fullName": "Juan", "phone": "+52", "city": "CDMX"}),
    ]

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "user1"})
    response = read_sections_handle(req, "personalData")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["id"] == "pd1"
    assert data["fullName"] == "Juan"
    assert data["phone"] == "+52"
    assert data.get("email") == "a@b.com"
    assert "createdAt" not in data
    assert "updatedAt" not in data


@patch(_PATCH_HELPER)
def test_read_sections_first_doc_section_empty_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "a@b.com"}
    helper.query_documents.return_value = []

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "user1"})
    response = read_sections_handle(req, "healthData")
    assert response.status_code == 404


@patch(_PATCH_HELPER)
def test_read_sections_personal_data_empty_returns_200_email_and_nulls(mock_helper_cls):
    """Usuario existe pero personalData vacío: 200 con email del user y resto de campos null."""
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "usuario@example.com"}
    helper.query_documents.return_value = []

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "user1"})
    response = read_sections_handle(req, "personalData")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["email"] == "usuario@example.com"
    assert data["id"] is None
    assert data["fullName"] is None
    assert data["phone"] is None
    assert data["address"] is None


@patch(_PATCH_HELPER)
def test_read_sections_list_section_returns_list(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "a@b.com"}
    helper.query_documents.return_value = [
        ("v1", {"branch": "Honda", "model": "CRF"}),
        ("v2", {"branch": "Yamaha", "model": "WR"}),
    ]

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "user1"})
    response = read_sections_handle(req, "vehicles")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == "v1"
    assert data[0]["branch"] == "Honda"
    assert data[1]["id"] == "v2"


@patch(_PATCH_HELPER)
def test_read_sections_list_section_empty_returns_empty_list(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "a@b.com"}
    helper.query_documents.return_value = []

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "user1"})
    response = read_sections_handle(req, "membership")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data == []


@patch(_PATCH_HELPER)
def test_read_sections_resolves_user_by_user_id_param(mock_helper_cls):
    """userId es el ID del documento en users; get_document por ID."""
    helper = MagicMock()
    mock_helper_cls.return_value = helper

    def get_doc(collection_path, doc_id):
        if doc_id == "auth123":
            return {"email": "a@b.com"}
        return None

    helper.get_document.side_effect = get_doc
    helper.query_documents.return_value = [("pd1", {"fullName": "Test"})]

    from users.read_sections import handle as read_sections_handle

    req = _make_request(args={"userId": "auth123"})
    response = read_sections_handle(req, "personalData")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["id"] == "pd1"
