import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_request(args=None):
    req = MagicMock()
    req.args.get.side_effect = lambda k, default=None: (args or {}).get(k, default)
    return req


@patch("users.delete_my_route.FirestoreHelper")
def test_delete_my_route_happy_path_deletes_notes_points_track_styles_route(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, {"name": "ruta"}]
    helper.list_document_ids.side_effect = [["n1", "n2"], ["p1"], ["ts1"]]

    from users.delete_my_route import handle

    req = _make_request(args={"userId": "u1"})
    resp = handle(req, "route_1")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == ""

    assert helper.list_document_ids.call_count == 3
    assert helper.delete_document.call_count == 5
    delete_calls = [helper.delete_document.call_args_list[i][0] for i in range(5)]
    assert any("notes" in c[0] and c[1] == "n1" for c in delete_calls)
    assert any("notes" in c[0] and c[1] == "n2" for c in delete_calls)
    assert any("points" in c[0] and c[1] == "p1" for c in delete_calls)
    assert any("trackStyles" in c[0] and c[1] == "ts1" for c in delete_calls)
    assert any(
        c[1] == "route_1"
        and "myRoutes" in c[0]
        and "notes" not in c[0]
        and "points" not in c[0]
        and "trackStyles" not in c[0]
        for c in delete_calls
    )


@patch("users.delete_my_route.FirestoreHelper")
def test_delete_my_route_multiple_calls_stable(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [
        {"email": "a@b.com"},
        {"name": "ruta"},
        {"email": "a@b.com"},
        {"name": "ruta"},
    ]
    helper.list_document_ids.side_effect = [[], [], [], [], [], []]

    from users.delete_my_route import handle

    req = _make_request(args={"userId": "u1"})
    r1 = handle(req, "route_1")
    r2 = handle(req, "route_1")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert helper.delete_document.call_count == 2
    assert helper.list_document_ids.call_count == 6


def test_delete_my_route_missing_user_id():
    from users.delete_my_route import handle

    req = _make_request(args={})
    resp = handle(req, "route_1")
    assert resp.status_code == 400


@patch("users.delete_my_route.FirestoreHelper")
def test_delete_my_route_user_not_found(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None

    from users.delete_my_route import handle

    req = _make_request(args={"userId": "missing"})
    resp = handle(req, "route_1")
    assert resp.status_code == 404


@patch("users.delete_my_route.FirestoreHelper")
def test_delete_my_route_route_not_found(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [{"email": "a@b.com"}, None]

    from users.delete_my_route import handle

    req = _make_request(args={"userId": "u1"})
    resp = handle(req, "route_x")
    assert resp.status_code == 404


@patch("users.delete_my_route.FirestoreHelper")
def test_delete_my_route_internal_error_500(mock_helper_cls):
    mock_helper_cls.side_effect = TypeError("boom")

    from users.delete_my_route import handle

    req = _make_request(args={"userId": "u1"})
    resp = handle(req, "route_1")
    assert resp.status_code == 500
