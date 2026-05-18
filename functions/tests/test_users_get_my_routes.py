import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(args: dict) -> MagicMock:
    req = MagicMock()
    req.method = "GET"
    req.args = dict(args)
    return req


def test__to_distance_km_covers_string_bool_and_nonfinite_branches():
    from users.get_my_routes import _to_distance_km

    assert _to_distance_km(None) == 0.0
    assert _to_distance_km(True) == 0.0
    assert _to_distance_km("1.2") == 1.2
    assert _to_distance_km("not-a-number") == 0.0
    assert _to_distance_km("inf") == 0.0
    assert _to_distance_km(float("inf")) == 0.0


def test__compute_distance_total_returns_0_when_total_is_nonfinite():
    from users import get_my_routes

    docs = [("r_001", {"distance": 1.0})]
    with patch.object(get_my_routes, "_to_distance_km", return_value=float("inf")):
        assert get_my_routes._compute_distance_total(docs) == 0.0


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_legacy_list_returns_array_and_queries_without_pagination(
    mock_helper_cls,
):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}

    # 1.05 + 2.01 = 3.06 -> ceil(3.06, 1 decimal) = 3.1
    helper.query_documents.return_value = [
        (
            "r_001",
            {
                "name": "Ruta 1",
                "createdAt": "2026-05-05T00:00:00+00:00",
                "distance": 1.05,
                "identifier": 101,
                "eventId": "evt_001",
            },
        ),
        (
            "r_002",
            {"name": "Ruta 2", "createdAt": "2026-05-04T00:00:00+00:00", "distance": 2.01},
        ),
    ]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1"}))
    assert resp.status_code == 200

    body = json.loads(resp.response[0])
    assert isinstance(body, list)
    assert [item["id"] for item in body] == ["r_001", "r_002"]
    assert [item["distanceTotal"] for item in body] == [3.1, 3.1]
    assert body[0]["identifier"] == 101
    assert body[0]["eventId"] == "evt_001"
    assert "identifier" not in body[1]
    assert "eventId" not in body[1]

    collection_path = "users/u1/myRoutes"
    helper.query_documents.assert_called_once_with(collection_path)
    assert helper.query_documents.call_args.kwargs == {}


def test_handle_returns_400_when_req_args_get_raises_value_error():
    from users.get_my_routes import handle

    req = MagicMock()
    req.method = "GET"
    req.args = MagicMock()
    req.args.get.side_effect = ValueError("boom")

    resp = handle(req)
    assert resp.status_code == 400


@patch("users.get_my_routes.FirestoreHelper", side_effect=RuntimeError("boom"))
def test_handle_returns_500_when_firestore_helper_raises_runtime_error(_mock_helper_cls):
    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1"}))
    assert resp.status_code == 500


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_paginated_limit_returns_object_with_pagination(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}

    # El handler hace 2 queries: (1) todas las rutas para sumar distanceTotal,
    # (2) query paginada (limit+1) para construir la página.
    docs_all_routes = [
        (
            "r_001",
            {
                "name": "Ruta 1",
                "createdAt": "2026-05-05T00:00:00+00:00",
                "distance": 1.05,
                "identifier": 101,
                "eventId": "evt_001",
            },
        ),
        (
            "r_002",
            {"name": "Ruta 2", "createdAt": "2026-05-04T00:00:00+00:00", "distance": 2.01},
        ),
    ]
    docs_page_plus_one = list(docs_all_routes)
    helper.query_documents.side_effect = [docs_all_routes, docs_page_plus_one]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1", "limit": "2"}))
    assert resp.status_code == 200

    body = json.loads(resp.response[0])
    assert set(body.keys()) == {"result", "pagination"}
    assert isinstance(body["result"], list)
    assert body["pagination"]["limit"] == 2
    assert body["pagination"]["page"] == 1
    assert [item["distanceTotal"] for item in body["result"]] == [3.1, 3.1]
    assert body["result"][0]["identifier"] == 101
    assert body["result"][0]["eventId"] == "evt_001"
    assert "identifier" not in body["result"][1]
    assert "eventId" not in body["result"][1]

    collection_path = "users/u1/myRoutes"
    assert helper.query_documents.call_count == 2
    helper.query_documents.assert_any_call(collection_path)
    helper.query_documents.assert_any_call(
        collection_path,
        order_by=[("createdAt", "desc")],
        limit=3,
        start_after_doc_id=None,
    )


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_cursor_calls_query_with_start_after_doc_id(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.query_documents.side_effect = [[], []]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1", "startAfterDocId": "abc"}))
    assert resp.status_code == 200

    body = json.loads(resp.response[0])
    assert set(body.keys()) == {"result", "pagination"}

    collection_path = "users/u1/myRoutes"
    assert helper.query_documents.call_count == 2
    helper.query_documents.assert_any_call(collection_path)
    helper.query_documents.assert_any_call(
        collection_path,
        order_by=[("createdAt", "desc")],
        limit=51,
        start_after_doc_id="abc",
    )


@pytest.mark.parametrize("raw_limit", ["0", "notanint"])
@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_invalid_limit_falls_back_to_default_50(
    mock_helper_cls, raw_limit
):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.query_documents.side_effect = [[], []]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1", "limit": raw_limit}))
    assert resp.status_code == 200

    body = json.loads(resp.response[0])
    assert body["pagination"]["limit"] == 50
    assert body["pagination"]["page"] == 1

    collection_path = "users/u1/myRoutes"
    assert helper.query_documents.call_count == 2
    helper.query_documents.assert_any_call(collection_path)
    helper.query_documents.assert_any_call(
        collection_path,
        order_by=[("createdAt", "desc")],
        limit=51,
        start_after_doc_id=None,
    )


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_missing_user_id_returns_400(mock_helper_cls):
    from users.get_my_routes import handle

    resp = handle(_make_request({}))
    assert resp.status_code == 400
    mock_helper_cls.assert_not_called()


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_user_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "missing"}))
    assert resp.status_code == 404
    helper.get_document.assert_called_once_with("users", "missing")


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_detail_returns_points_and_notes(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [
        {"email": "x@y.com"},
        {
            "name": "Ruta 1",
            "description": "detalle",
            "eventId": "evt_001",
            "identifier": 1,
            "createdAt": "2026-05-06T00:00:00+00:00",
            "updatedAt": "2026-05-06T00:00:00+00:00",
        },
    ]
    helper.query_documents.side_effect = [
        [("p_001", {"lat": 1}), ("p_002", {"lat": 2})],
        [("n_001", {"message": "ok"})],
        [
            ("ts_002", {"startPointIndex": 150, "colorHex": "#00FF00"}),
            ("ts_001", {"startPointIndex": 0, "colorHex": "#FF0000"}),
        ],
    ]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1", "routeId": "r_001"}))
    assert resp.status_code == 200

    body = json.loads(resp.response[0])
    assert body["id"] == "r_001"
    assert body["name"] == "Ruta 1"
    assert body["identifier"] == 1
    assert body["eventId"] == "evt_001"
    for key in ("updatedAt", "description", "createdAt"):
        assert key not in body
    assert "points" in body and "notes" in body and "trackStyles" in body
    assert [p["id"] for p in body["points"]] == ["p_001", "p_002"]
    assert [n["id"] for n in body["notes"]] == ["n_001"]
    assert [s["id"] for s in body["trackStyles"]] == ["ts_001", "ts_002"]
    assert [s["startPointIndex"] for s in body["trackStyles"]] == [0, 150]

    route_collection_path = "users/u1/myRoutes"
    helper.get_document.assert_any_call("users", "u1")
    helper.get_document.assert_any_call(route_collection_path, "r_001")
    helper.query_documents.assert_any_call(f"{route_collection_path}/r_001/points")
    helper.query_documents.assert_any_call(f"{route_collection_path}/r_001/notes")
    helper.query_documents.assert_any_call(f"{route_collection_path}/r_001/trackStyles")


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_detail_route_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.side_effect = [
        {"email": "x@y.com"},
        None,
    ]

    from users.get_my_routes import handle

    resp = handle(_make_request({"userId": "u1", "routeId": "missing_route"}))
    assert resp.status_code == 404


@patch("users.get_my_routes.FirestoreHelper")
def test_get_my_routes_multiple_pages_are_stable_and_use_cursor(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "x@y.com"}

    docs_all_routes = [
        (
            "r_001",
            {
                "name": "Ruta 1",
                "createdAt": "2026-05-05T00:00:00+00:00",
                "distance": 1.05,
                "identifier": 101,
                "eventId": "evt_001",
            },
        ),
        (
            "r_002",
            {"name": "Ruta 2", "createdAt": "2026-05-04T00:00:00+00:00", "distance": 2.01},
        ),
        (
            "r_003",
            {"name": "Ruta 3", "createdAt": "2026-05-03T00:00:00+00:00", "distance": 0.0},
        ),
    ]
    docs_page1_plus_one = list(docs_all_routes)
    docs_page2_plus_one = [
        (
            "r_003",
            {"name": "Ruta 3", "createdAt": "2026-05-03T00:00:00+00:00", "distance": 0.0},
        ),
    ]
    # Cada request paginado hace 2 calls: all_routes + page query.
    helper.query_documents.side_effect = [
        docs_all_routes,
        docs_page1_plus_one,
        docs_all_routes,
        docs_page2_plus_one,
    ]

    from users.get_my_routes import handle

    resp1 = handle(_make_request({"userId": "u1", "limit": "2"}))
    assert resp1.status_code == 200
    body1 = json.loads(resp1.response[0])
    assert body1["pagination"]["hasMore"] is True
    assert body1["pagination"]["lastDocId"] == "r_002"
    assert [item["distanceTotal"] for item in body1["result"]] == [3.1, 3.1]
    assert body1["result"][0]["identifier"] == 101
    assert body1["result"][0]["eventId"] == "evt_001"
    assert "identifier" not in body1["result"][1]
    assert "eventId" not in body1["result"][1]

    resp2 = handle(
        _make_request(
            {"userId": "u1", "limit": "2", "startAfterDocId": body1["pagination"]["lastDocId"]}
        )
    )
    assert resp2.status_code == 200
    body2 = json.loads(resp2.response[0])
    assert body2["pagination"]["hasMore"] is False
    assert body2["pagination"]["lastDocId"] is None
    assert [item["distanceTotal"] for item in body2["result"]] == [3.1]
    assert "identifier" not in body2["result"][0]
    assert "eventId" not in body2["result"][0]

    collection_path = "users/u1/myRoutes"
    assert helper.query_documents.call_count == 4
    # Primer request
    helper.query_documents.assert_any_call(collection_path)
    helper.query_documents.assert_any_call(
        collection_path,
        order_by=[("createdAt", "desc")],
        limit=3,
        start_after_doc_id=None,
    )
    # Segundo request
    helper.query_documents.assert_any_call(collection_path)
    helper.query_documents.assert_any_call(
        collection_path,
        order_by=[("createdAt", "desc")],
        limit=3,
        start_after_doc_id="r_002",
    )

