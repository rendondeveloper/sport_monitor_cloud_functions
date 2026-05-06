import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(args=None, body=None):
    req = MagicMock()
    req.method = "PUT"
    req.args.get.side_effect = lambda k, default=None: (args or {}).get(k, default)
    req.get_json.side_effect = lambda silent=True: body
    return req


@patch("users.update_my_route_notes.FirestoreHelper")
def test_update_my_route_notes_happy_path(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "x@y.com"}, {"name": "ruta"}]
    helper.list_document_ids.return_value = ["7"]

    from users.update_my_route_notes import handle

    req = _make_request(
        args={"userId": "u1"},
        body={
            "notes": [
                {"identifier": 7, "message": "actualizada"},
                {"identifier": 8, "message": "nueva", "photos": ["a"]},
            ]
        },
    )
    resp = handle(req, "route_1")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == ""
    assert helper.delete_document.call_count == 1
    assert helper.create_document_with_id.call_count == 2
    helper.update_document.assert_called_once()


def test_update_my_route_notes_missing_user_id():
    from users.update_my_route_notes import handle

    req = _make_request(body={"notes": []})
    resp = handle(req, "route_1")
    assert resp.status_code == 400


def test_update_my_route_notes_identifier_required():
    from users.update_my_route_notes import handle

    req = _make_request(args={"userId": "u1"}, body={"notes": [{"message": "x"}]})
    resp = handle(req, "route_1")
    assert resp.status_code == 400
