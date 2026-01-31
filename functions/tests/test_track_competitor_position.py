"""
Pruebas unitarias para track_competitor_position (SPRTMNTRPP-75).
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Asegurar que functions esté en el path
sys.path.insert(0, ".")


def _make_request(
    method: str = "POST",
    event_id: str = "ev1",
    day_id: str = "day1",
    competitor_id: str = "comp1",
    body: dict | None = None,
):
    """Construye un mock de Request."""
    if body is None:
        body = {
            "coordinates": {"latitude": 19.0, "longitude": 18.0},
            "data": {"speed": "45", "type": "Millas/km"},
            "timeStamp": "12/12/2026 00:10:10",
        }
    req = MagicMock()
    req.method = method
    req.args.get.side_effect = lambda k, default=None: {
        "eventId": event_id,
        "dayId": day_id,
        "competitorId": competitor_id,
    }.get(k, default or "")
    req.get_json.side_effect = lambda silent=True: body
    return req


def _make_mock_rtdb(existing: dict | None = None):
    """Mock de Realtime Database: ref.get() retorna existing; ref.update() es mock."""
    mock_update = MagicMock()
    mock_ref = MagicMock()
    mock_ref.get.return_value = existing if existing is not None else {}
    mock_ref.update = mock_update
    return mock_ref, mock_update


@patch("tracking.track_competitor_position.validate_request")
@patch("tracking.track_competitor_position.db.reference")
def test_track_competitor_position_happy_path(mock_db_reference, mock_validate_request):
    """Happy path: parámetros y body válidos → 200, escribe current e historial en RTDB."""
    mock_validate_request.return_value = None
    mock_ref, mock_update = _make_mock_rtdb(existing={})
    mock_db_reference.return_value = mock_ref

    from tracking.track_competitor_position import track_competitor_position

    req = _make_request()
    response = track_competitor_position(req)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == ""
    mock_db_reference.assert_called_once()
    path = mock_db_reference.call_args[0][0]
    assert "sport_monitor" in path and "ev1" in path and "day1" in path and "comp1" in path
    mock_update.assert_called_once()
    call_args = mock_update.call_args[0][0]
    assert "current" in call_args
    assert "historial" in call_args
    assert call_args["current"]["latitude"] == 19.0
    assert call_args["current"]["longitude"] == 18.0
    historial = call_args["historial"]
    assert isinstance(historial, dict)
    assert len(historial) == 1
    first_entry = next(iter(historial.values()))
    assert first_entry["data"]["speed"] == "45"
    assert "id" in first_entry and isinstance(first_entry["id"], int)
    assert "coordinates" in first_entry and "data" in first_entry and "timeStamp" in first_entry


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_missing_event_id(mock_validate_request):
    """eventId faltante → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(event_id="")
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_missing_day_id(mock_validate_request):
    """dayId faltante → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(day_id="")
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_missing_competitor_id(mock_validate_request):
    """competitorId faltante → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(competitor_id="")
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_invalid_body_null(mock_validate_request):
    """Body null o inválido → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(body=None)
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_missing_coordinates(mock_validate_request):
    """Body sin coordinates → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(body={"data": {"speed": "45", "type": "km"}, "timeStamp": "12/12/2026 00:10:10"})
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_coordinates_wrong_type(mock_validate_request):
    """coordinates.latitude no numérico → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": {"latitude": "not-a-number", "longitude": 18.0},
            "data": {"speed": "45", "type": "km"},
            "timeStamp": "12/12/2026 00:10:10",
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_missing_data(mock_validate_request):
    """Body sin data → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": {"latitude": 19.0, "longitude": 18.0},
            "timeStamp": "12/12/2026 00:10:10",
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_missing_timestamp(mock_validate_request):
    """Body sin timeStamp → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": {"latitude": 19.0, "longitude": 18.0},
            "data": {"speed": "45", "type": "km"},
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_coordinates_not_object(mock_validate_request):
    """coordinates no es objeto → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": "invalid",
            "data": {"speed": "45", "type": "km"},
            "timeStamp": "12/12/2026 00:10:10",
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_longitude_not_number(mock_validate_request):
    """coordinates.longitude no numérico → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": {"latitude": 19.0, "longitude": "not-a-number"},
            "data": {"speed": "45", "type": "km"},
            "timeStamp": "12/12/2026 00:10:10",
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_data_speed_not_string(mock_validate_request):
    """data.speed no es string → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": {"latitude": 19.0, "longitude": 18.0},
            "data": {"speed": 45, "type": "km"},
            "timeStamp": "12/12/2026 00:10:10",
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_data_type_not_string(mock_validate_request):
    """data.type no es string → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request(
        body={
            "coordinates": {"latitude": 19.0, "longitude": 18.0},
            "data": {"speed": "45", "type": 123},
            "timeStamp": "12/12/2026 00:10:10",
        }
    )
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
def test_track_competitor_position_get_json_raises(mock_validate_request):
    """get_json lanza ValueError → 400."""
    mock_validate_request.return_value = None
    from tracking.track_competitor_position import track_competitor_position

    req = _make_request()
    req.get_json.side_effect = ValueError("Invalid JSON")
    response = track_competitor_position(req)
    assert response.status_code == 400


@patch("tracking.track_competitor_position.validate_request")
@patch("tracking.track_competitor_position.db.reference")
def test_track_competitor_position_update_raises_500(mock_db_reference, mock_validate_request):
    """ref.update lanza excepción → 500."""
    mock_validate_request.return_value = None
    mock_ref, mock_update = _make_mock_rtdb(existing={})
    mock_update.side_effect = RuntimeError("Realtime Database error")
    mock_db_reference.return_value = mock_ref

    from tracking.track_competitor_position import track_competitor_position

    req = _make_request()
    response = track_competitor_position(req)
    assert response.status_code == 500


@patch("tracking.track_competitor_position.validate_request")
@patch("tracking.track_competitor_position.db.reference")
def test_track_competitor_position_rtdb_ref_created_if_not_exists(mock_db_reference, mock_validate_request):
    """Si no hay datos en la ruta, ref.get() retorna {} y se escribe current e historial → 200."""
    mock_validate_request.return_value = None
    mock_ref, mock_update = _make_mock_rtdb(existing={})
    mock_db_reference.return_value = mock_ref

    from tracking.track_competitor_position import track_competitor_position

    req = _make_request()
    response = track_competitor_position(req)

    assert response.status_code == 200
    mock_update.assert_called_once()
    call_args = mock_update.call_args[0][0]
    assert "current" in call_args
    assert "historial" in call_args


@patch("tracking.track_competitor_position.validate_request")
@patch("tracking.track_competitor_position.db.reference")
def test_track_competitor_position_multiple_calls(mock_db_reference, mock_validate_request):
    """Múltiples llamadas: dos requests consecutivas retornan 200 y update se llama dos veces."""
    mock_validate_request.return_value = None
    mock_ref, mock_update = _make_mock_rtdb(existing={})
    mock_db_reference.return_value = mock_ref

    from tracking.track_competitor_position import track_competitor_position

    req1 = _make_request(body={
        "coordinates": {"latitude": 19.0, "longitude": 18.0},
        "data": {"speed": "45", "type": "km"},
        "timeStamp": "12/12/2026 00:10:10",
    })
    req2 = _make_request(body={
        "coordinates": {"latitude": 19.1, "longitude": 18.1},
        "data": {"speed": "50", "type": "km"},
        "timeStamp": "12/12/2026 00:11:00",
    })

    r1 = track_competitor_position(req1)
    r2 = track_competitor_position(req2)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_update.call_count == 2
