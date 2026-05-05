"""
Tests para handle_create en routes/create_event_route.py.

Casos cubiertos:
1. Happy path con waypoints
2. Happy path sin waypoints
3. Body inválido (None)
4. name faltante
5. eventId faltante
6. colorTrack faltante
7. colorTrack = 0 (valor válido)
8. width faltante
9. Evento no encontrado o usuario no es el creador (404)
10. batch_set falla (500)
11. Campos opcionales ausentes no se incluyen en el payload
12. Campos opcionales presentes sí se incluyen en el payload
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from routes.create_event_route import handle_create


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_get_event_if_owner():
    with patch("routes.create_event_route.get_event_if_owner") as m:
        m.return_value = {"id": "evt1", "name": "Test Event"}
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("routes.create_event_route.FirestoreHelper") as MockClass:
        instance = MagicMock()
        instance.new_document_id.return_value = "generated_route_id"
        instance.batch_set.return_value = ["generated_route_id"]
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_get_current_timestamp():
    with patch(
        "routes.create_event_route.get_current_timestamp",
        return_value="2026-04-30T12:00:00+00:00",
    ) as m:
        yield m


# ============================================================================
# HELPER
# ============================================================================


def _make_request(body=None):
    req = MagicMock()
    req.method = "POST"
    req.args = {}
    req.headers = {"Authorization": "Bearer test_token"}
    req.get_json.return_value = body
    return req


def _base_body(**overrides):
    """Retorna un body mínimo válido, con overrides opcionales."""
    base = {
        "name": "Ruta Etapa 1",
        "eventId": "evt1",
        "colorTrack": 4293000015,
        "width": 3.0,
    }
    base.update(overrides)
    return base


# ============================================================================
# TESTS
# ============================================================================


class TestHandleCreateHappyPath:
    """Happy path: ruta creada correctamente con y sin waypoints."""

    def test_happy_path_with_waypoints(
        self,
        mock_get_event_if_owner,
        mock_firestore_helper,
        mock_get_current_timestamp,
    ):
        # Arrange
        body = _base_body(
            waypoints=[
                {"name": "WP1", "order": 0, "coordinates": "40.123,-74.456"},
                {"name": "WP2", "order": 1, "coordinates": "40.200,-74.500"},
            ]
        )
        req = _make_request(body)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "generated_route_id"
        assert data["name"] == "Ruta Etapa 1"
        assert data["createdAt"] == "2026-04-30T12:00:00+00:00"
        assert data["updatedAt"] == "2026-04-30T12:00:00+00:00"

        mock_firestore_helper.batch_set.assert_called_once()
        operations = mock_firestore_helper.batch_set.call_args[0][0]
        assert len(operations) == 3  # 1 ruta + 2 waypoints

    def test_happy_path_without_waypoints(
        self,
        mock_get_event_if_owner,
        mock_firestore_helper,
        mock_get_current_timestamp,
    ):
        # Arrange
        req = _make_request(_base_body())

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 200
        mock_firestore_helper.batch_set.assert_called_once()
        operations = mock_firestore_helper.batch_set.call_args[0][0]
        assert len(operations) == 1  # solo la ruta


class TestHandleCreateValidation:
    """Validaciones de campos requeridos -> 400."""

    def test_body_invalido_retorna_400(self, mock_get_event_if_owner):
        # Arrange
        req = _make_request(body=None)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 400

    def test_name_faltante_retorna_400(self, mock_get_event_if_owner):
        # Arrange
        body = _base_body()
        del body["name"]
        req = _make_request(body)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 400

    def test_event_id_faltante_retorna_400(self, mock_get_event_if_owner):
        # Arrange
        body = _base_body()
        del body["eventId"]
        req = _make_request(body)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 400

    def test_color_track_faltante_retorna_400(self, mock_get_event_if_owner):
        # Arrange
        body = _base_body()
        del body["colorTrack"]
        req = _make_request(body)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 400

    def test_color_track_cero_es_valido(
        self,
        mock_get_event_if_owner,
        mock_firestore_helper,
        mock_get_current_timestamp,
    ):
        # Arrange — colorTrack = 0 es un valor legítimo (no debe tratarse como falsy)
        req = _make_request(_base_body(colorTrack=0))

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 200

    def test_width_faltante_retorna_400(self, mock_get_event_if_owner):
        # Arrange
        body = _base_body()
        del body["width"]
        req = _make_request(body)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 400


class TestHandleCreateOwnerCheck:
    """Verificación de propiedad del evento."""

    def test_no_owner_retorna_404(self, mock_get_event_if_owner):
        # Arrange
        mock_get_event_if_owner.return_value = None
        req = _make_request(_base_body())

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 404


class TestHandleCreateErrors:
    """Errores internos -> 500."""

    def test_batch_set_falla_retorna_500(
        self,
        mock_get_event_if_owner,
        mock_firestore_helper,
        mock_get_current_timestamp,
    ):
        # Arrange
        mock_firestore_helper.batch_set.side_effect = Exception("db error")
        req = _make_request(_base_body())

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 500


class TestHandleCreateOptionalFields:
    """Campos opcionales: incluidos solo cuando tienen valor."""

    def test_campos_opcionales_no_incluidos_si_vacios(
        self,
        mock_get_event_if_owner,
        mock_firestore_helper,
        mock_get_current_timestamp,
    ):
        # Arrange — body sin routeUrl, visibleForPilots, trackPoints
        req = _make_request(_base_body())

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 200
        operations = mock_firestore_helper.batch_set.call_args[0][0]
        route_collection_path, route_id, route_payload = operations[0]
        assert "routeUrl" not in route_payload
        assert "visibleForPilots" not in route_payload
        assert "trackPoints" not in route_payload

    def test_campos_opcionales_incluidos_si_tienen_valor(
        self,
        mock_get_event_if_owner,
        mock_firestore_helper,
        mock_get_current_timestamp,
    ):
        # Arrange
        body = _base_body(
            routeUrl="https://maps.example.com/route",
            visibleForPilots=True,
            trackPoints=[{"lat": 40.1, "lng": -74.5}],
        )
        req = _make_request(body)

        # Act
        response = handle_create(req, "user123")

        # Assert
        assert response.status_code == 200
        operations = mock_firestore_helper.batch_set.call_args[0][0]
        route_collection_path, route_id, route_payload = operations[0]
        assert route_payload["routeUrl"] == "https://maps.example.com/route"
        assert route_payload["visibleForPilots"] is True
        assert route_payload["trackPoints"] == [{"lat": 40.1, "lng": -74.5}]
