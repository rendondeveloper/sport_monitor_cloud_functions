"""
Tests para delete_section_item.handle: eliminar un documento de emergencyContacts o vehicles.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")

_PATCH_HELPER = "users.delete_section_item.FirestoreHelper"


def _make_request(args=None):
    req = MagicMock()
    req.method = "DELETE"
    req.args = dict(args) if args else {}
    return req


@patch(_PATCH_HELPER)
def test_delete_section_item_missing_user_id_returns_400(mock_helper_cls):
    from users.delete_section_item import handle as delete_handle

    req = _make_request(args={"id": "doc123"})
    response = delete_handle(req, "emergencyContacts")
    assert response.status_code == 400
    mock_helper_cls.return_value.get_document.assert_not_called()


@patch(_PATCH_HELPER)
def test_delete_section_item_missing_id_returns_400(mock_helper_cls):
    from users.delete_section_item import handle as delete_handle

    req = _make_request(args={"userId": "user1"})
    response = delete_handle(req, "emergencyContacts")
    assert response.status_code == 400
    mock_helper_cls.return_value.get_document.assert_not_called()


@patch(_PATCH_HELPER)
def test_delete_section_item_user_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None

    from users.delete_section_item import handle as delete_handle

    req = _make_request(args={"userId": "user1", "id": "doc1"})
    response = delete_handle(req, "emergencyContacts")
    assert response.status_code == 404
    helper.get_document.assert_called()
    helper.delete_document.assert_not_called()


@patch(_PATCH_HELPER)
def test_delete_section_item_document_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, None]

    from users.delete_section_item import handle as delete_handle

    req = _make_request(args={"userId": "user1", "id": "doc1"})
    response = delete_handle(req, "emergencyContacts")
    assert response.status_code == 404
    assert helper.get_document.call_count == 2
    helper.delete_document.assert_not_called()


@patch(_PATCH_HELPER)
def test_delete_section_item_emergency_contact_success_returns_204(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, {"fullName": "Jane", "phone": "+52"}]  # user, then doc

    from users.delete_section_item import handle as delete_handle

    req = _make_request(args={"userId": "user1", "id": "ec1"})
    response = delete_handle(req, "emergencyContacts")
    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""
    helper.delete_document.assert_called_once()
    call_path, call_id = helper.delete_document.call_args[0]
    assert "user1" in call_path
    assert "emergencyContacts" in call_path
    assert call_id == "ec1"


@patch(_PATCH_HELPER)
def test_delete_section_item_vehicle_success_returns_204(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, {"branch": "Honda", "model": "X"}]  # user, then doc

    from users.delete_section_item import handle as delete_handle

    req = _make_request(args={"userId": "u2", "id": "veh1"})
    response = delete_handle(req, "vehicles")
    assert response.status_code == 204
    helper.delete_document.assert_called_once()
    call_path, call_id = helper.delete_document.call_args[0]
    assert "u2" in call_path
    assert "vehicles" in call_path
    assert call_id == "veh1"
