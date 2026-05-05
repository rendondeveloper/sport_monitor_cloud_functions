import json
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(body):
    req = MagicMock()
    req.method = "POST"
    req.get_json.side_effect = lambda silent=True: body
    req.args = {}
    return req


@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_happy_path(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.create_document.side_effect = ["route_auto_1", "point_auto_1", "point_auto_2", "note_auto_1", "note_auto_2"]

    from users.create_my_route import handle

    payload = {
        "userId": "u1",
        "identifier": 16,
        "name": "test",
        "description": "desc",
        "eventId": None,
        "points": [{"a": 1}, {"a": 2}],
        "notes": [
            {"identifier": 7, "message": "m1"},
            {"identifier": 8, "message": "m2", "photos": ["http://a"]},
        ],
    }
    resp = handle(_make_request(payload))
    assert resp.status_code == 201
    assert json.loads(resp.get_data(as_text=True)) == {"id": "route_auto_1"}
    assert helper.create_document.call_count == 3
    assert helper.create_document_with_id.call_count == 2
    call_args = helper.create_document_with_id.call_args_list
    assert call_args[0][0][1] == "7"
    assert call_args[1][0][1] == "8"


@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_allows_null_points_notes(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.create_document.return_value = "route_auto_1"

    from users.create_my_route import handle

    payload = {
        "userId": "u1",
        "identifier": 16,
        "name": "test",
        "description": "desc",
        "eventId": None,
        "points": None,
        "notes": None,
    }
    resp = handle(_make_request(payload))
    assert resp.status_code == 201
    assert helper.create_document.call_count == 1


def test_create_my_route_missing_user_id():
    from users.create_my_route import handle

    resp = handle(
        _make_request(
            {
                "identifier": 16,
                "name": "test",
                "description": "desc",
            }
        )
    )
    assert resp.status_code == 400


def test_create_my_route_note_identifier_required_int():
    from users.create_my_route import handle

    resp = handle(
        _make_request(
            {
                "userId": "u1",
                "identifier": 16,
                "name": "test",
                "description": "desc",
                "notes": [{"message": "sin identifier"}],
            }
        )
    )
    assert resp.status_code == 400

