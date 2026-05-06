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


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Misma fórmula (Haversine) que el handler.
    import math

    r = 6371000.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2.0) ** 2)
    )
    c = 2.0 * math.asin(math.sqrt(a))
    return r * c


def _km_ceiled_1_decimal(distance_m: float) -> float:
    import math

    km = distance_m / 1000.0
    return math.ceil(km * 10.0) / 10.0


@patch("users.create_my_route.get_current_timestamp")
@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_happy_path_includes_distance(
    mock_helper_cls, mock_now
):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    mock_now.return_value = "2026-05-06T00:00:00+00:00"
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.create_document.side_effect = [
        "route_auto_1",
        "point_auto_1",
        "point_auto_2",
        "point_auto_3",
    ]

    from users.create_my_route import handle

    payload = {
        "userId": "u1",
        "identifier": 16,
        "name": "test",
        "description": "desc",
        "eventId": None,
        "points": [
            {"latitude": 19.4326, "longitude": -99.1332, "speedKmh": 40},
            {"latitude": 19.4330, "longitude": -99.1340, "speedKmh": 41},
            {"latitude": 19.4334, "longitude": -99.1350, "speedKmh": 42},
        ],
        "notes": [
            {"identifier": 7, "message": "m1"},
            {"identifier": 8, "message": "m2", "photos": ["http://a"]},
        ],
    }
    resp = handle(_make_request(payload))
    assert resp.status_code == 201
    assert json.loads(resp.get_data(as_text=True)) == {"id": "route_auto_1"}

    # 1 create de la ruta + 3 creates de points
    assert helper.create_document.call_count == 4
    assert helper.create_document_with_id.call_count == 2
    call_args = helper.create_document_with_id.call_args_list
    assert call_args[0][0][1] == "7"
    assert call_args[1][0][1] == "8"

    # Verifica que el doc de ruta incluye distance > 0
    route_doc = helper.create_document.call_args_list[0][0][1]
    assert "distance" in route_doc
    assert route_doc["distance"] > 0.0


@patch("users.create_my_route.get_current_timestamp")
@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_points_null_distance_zero(mock_helper_cls, mock_now):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    mock_now.return_value = "2026-05-06T00:00:00+00:00"
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
    route_doc = helper.create_document.call_args_list[0][0][1]
    assert route_doc["distance"] == 0.0


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


def test_create_my_route_identifier_name_description_validation():
    from users.create_my_route import handle

    # identifier no int
    resp1 = handle(
        _make_request(
            {
                "userId": "u1",
                "identifier": "16",
                "name": "test",
                "description": "desc",
            }
        )
    )
    assert resp1.status_code == 400

    # name vacío
    resp2 = handle(
        _make_request(
            {
                "userId": "u1",
                "identifier": 16,
                "name": "   ",
                "description": "desc",
            }
        )
    )
    assert resp2.status_code == 400

    # description vacío
    resp3 = handle(
        _make_request(
            {
                "userId": "u1",
                "identifier": 16,
                "name": "test",
                "description": "",
            }
        )
    )
    assert resp3.status_code == 400


def test_create_my_route_notes_must_be_list_or_null():
    from users.create_my_route import handle

    resp = handle(
        _make_request(
            {
                "userId": "u1",
                "identifier": 16,
                "name": "test",
                "description": "desc",
                "notes": "bad",
            }
        )
    )
    assert resp.status_code == 400


@patch("users.create_my_route.get_current_timestamp")
@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_mixed_points_distance_ignores_invalid(
    mock_helper_cls, mock_now
):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    mock_now.return_value = "2026-05-06T00:00:00+00:00"
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.create_document.side_effect = [
        "route_auto_1",
        "point_auto_1",
        "point_auto_2",
        "point_auto_3",
        "point_auto_4",
        "point_auto_5",
    ]

    from users.create_my_route import handle

    # Válidos: p1, p3, p5 (p2/p4 inválidos para cálculo)
    p1 = {"latitude": 19.4326, "longitude": -99.1332, "extra": "keep"}
    p2 = {"latitude": 19.4330}  # falta longitude
    p3 = {"latitude": 19.4330, "longitude": -99.1340}
    p4 = {"latitude": "19.434", "longitude": -99.1350}  # lat no numérico
    p5 = {"latitude": 19.4334, "longitude": -99.1350}

    payload = {
        "userId": "u1",
        "identifier": 16,
        "name": "test",
        "description": "desc",
        "eventId": None,
        # incluye un item no-dict que debe ignorarse para distance
        "points": [p1, "bad_point", p2, p3, p4, p5],
        # incluye un item no-dict que debe ignorarse en normalize/validación
        "notes": ["bad_note", {"identifier": 99, "message": "ok"}],
    }
    resp = handle(_make_request(payload))
    assert resp.status_code == 201

    # Se siguen creando subdocs por cada point dict (aunque no sea válido para distance)
    assert helper.create_document.call_count == 1 + 5

    route_doc = helper.create_document.call_args_list[0][0][1]
    expected_m = _haversine_meters(19.4326, -99.1332, 19.4330, -99.1340) + _haversine_meters(
        19.4330, -99.1340, 19.4334, -99.1350
    )
    expected_km = _km_ceiled_1_decimal(expected_m)
    assert route_doc["distance"] == expected_km
    assert helper.create_document_with_id.call_count == 1


@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_body_invalid_returns_400(mock_helper_cls):
    from users.create_my_route import handle

    # body no dict
    resp = handle(_make_request(["not", "a", "dict"]))
    assert resp.status_code == 400

    # points no list ni null
    resp2 = handle(
        _make_request(
            {
                "userId": "u1",
                "identifier": 16,
                "name": "test",
                "description": "desc",
                "points": "bad",
            }
        )
    )
    assert resp2.status_code == 400
    mock_helper_cls.assert_not_called()


@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_user_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None

    from users.create_my_route import handle

    payload = {
        "userId": "missing",
        "identifier": 16,
        "name": "test",
        "description": "desc",
        "points": [],
        "notes": [],
    }
    resp = handle(_make_request(payload))
    assert resp.status_code == 404
    helper.create_document.assert_not_called()


@patch("users.create_my_route.get_current_timestamp")
@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_multiple_calls_are_stable(mock_helper_cls, mock_now):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    mock_now.return_value = "2026-05-06T00:00:00+00:00"
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.create_document.side_effect = ["route_1", "route_2"]

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

    resp1 = handle(_make_request(payload))
    resp2 = handle(_make_request(payload))
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert json.loads(resp1.get_data(as_text=True)) == {"id": "route_1"}
    assert json.loads(resp2.get_data(as_text=True)) == {"id": "route_2"}


def test_create_my_route_value_error_in_json_returns_400():
    req = MagicMock()
    req.method = "POST"

    def _raise(*_args, **_kwargs):
        raise ValueError("bad json")

    req.get_json.side_effect = _raise
    req.args = {}

    from users.create_my_route import handle

    resp = handle(req)
    assert resp.status_code == 400


@patch("users.create_my_route.get_current_timestamp")
@patch("users.create_my_route.FirestoreHelper")
def test_create_my_route_internal_error_returns_500(mock_helper_cls, mock_now):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    mock_now.return_value = "2026-05-06T00:00:00+00:00"
    helper.get_document.return_value = {"email": "x@y.com"}
    helper.create_document.side_effect = RuntimeError("boom")

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
    assert resp.status_code == 500

