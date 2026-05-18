import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(args=None):
    req = MagicMock()
    req.args.get.side_effect = lambda k, default=None: (args or {}).get(k, default)
    return req


@patch("users.delete_my_route_notes.get_current_timestamp", return_value="2026-05-12T00:00:00+00:00")
@patch("users.delete_my_route_notes.FirestoreHelper")
def test_delete_my_route_notes_happy_path(mock_helper_cls, _mock_ts):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, {"name": "ruta"}]
    helper.list_document_ids.return_value = ["7", "8"]

    from users.delete_my_route_notes import handle

    req = _make_request(args={"userId": "u1"})
    resp = handle(req, "route_1")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == ""
    assert helper.delete_document.call_count == 2
    helper.update_document.assert_called_once()
    _, _, update_data = helper.update_document.call_args[0]
    assert update_data["notesCount"] == 0
    assert update_data["updatedAt"] == "2026-05-12T00:00:00+00:00"


@patch("users.delete_my_route_notes.FirestoreHelper")
def test_delete_my_route_notes_multiple_calls_stable(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [
        {"email": "a@b.com"},
        {"name": "ruta"},
        {"email": "a@b.com"},
        {"name": "ruta"},
    ]
    helper.list_document_ids.return_value = []

    from users.delete_my_route_notes import handle

    req = _make_request(args={"userId": "u1"})
    assert handle(req, "r1").status_code == 200
    assert handle(req, "r1").status_code == 200
    assert helper.update_document.call_count == 2


def test_delete_my_route_notes_missing_user_id():
    from users.delete_my_route_notes import handle

    req = _make_request(args={})
    resp = handle(req, "route_1")
    assert resp.status_code == 400


@patch("users.delete_my_route_notes.FirestoreHelper")
def test_delete_my_route_notes_user_not_found(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None

    from users.delete_my_route_notes import handle

    resp = handle(_make_request(args={"userId": "x"}), "route_1")
    assert resp.status_code == 404


@patch("users.delete_my_route_notes.FirestoreHelper")
def test_delete_my_route_notes_route_not_found(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, None]

    from users.delete_my_route_notes import handle

    resp = handle(_make_request(args={"userId": "u1"}), "route_1")
    assert resp.status_code == 404


@patch("users.delete_my_route_notes.FirestoreHelper")
def test_delete_my_route_notes_internal_error_500(mock_helper_cls):
    mock_helper_cls.side_effect = RuntimeError("fail")

    from users.delete_my_route_notes import handle

    resp = handle(_make_request(args={"userId": "u1"}), "route_1")
    assert resp.status_code == 500
