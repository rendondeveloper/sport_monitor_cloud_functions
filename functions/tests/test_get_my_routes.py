import json
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(args):
    req = MagicMock()
    req.method = "GET"
    req.args.get.side_effect = lambda k, default=None: args.get(k, default)
    return req


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_list(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.query_documents.return_value = [
        (
            "r_001",
            {
                "name": "ruta",
                "createdAt": "2026-05-05T00:00:00+00:00",
                "updatedAt": "2026-05-05T00:00:00+00:00",
            },
        )
    ]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1"}))
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data[0]["id"] == "r_001"
    assert "createdAt" not in data[0]
    assert "updatedAt" not in data[0]


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_detail(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [
        {"email": "x@y.com"},
        {"name": "ruta"},
    ]
    helper.query_documents.side_effect = [
        [("p_001", {"lat": 1})],
        [("n_001", {"message": "ok"})],
    ]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1", "routeId": "r_001"}))
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data["id"] == "r_001"
    assert data["points"][0]["id"] == "p_001"
    assert data["notes"][0]["id"] == "n_001"


def test_get_my_routes_missing_user_id():
    from users.get_my_routes import handle

    resp = handle(_make_request({}))
    assert resp.status_code == 400

