"""
Tests para handle_list en routes/list_event_route.py.

Casos cubiertos:
1. Happy path — lista con rutas y checkpoints
2. Happy path — lista vacía
3. user_id vacío → 400
4. eventId faltante → 400
5. Usuario no es el owner del evento → 404
6. Error interno en Firestore → 500
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from routes.list_event_route import handle_list


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_get_event_if_owner():
    with patch("routes.list_event_route.get_event_if_owner") as m:
        m.return_value = {"id": "evt1", "name": "Test Event"}
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("routes.list_event_route.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


# ============================================================================
# HELPER
# ============================================================================


def _make_request(args=None):
    req = MagicMock()
    req.method = "GET"
    req.args = args or {}
    req.headers = {"Authorization": "Bearer test_token"}
    return req


# ============================================================================
# TESTS — Happy path
# ============================================================================


class TestHandleListHappyPath:

    def test_retorna_lista_con_rutas_y_checkpoints(self, mock_get_event_if_owner, mock_firestore_helper):
        # Arrange
        # query_documents se llama 3 veces: rutas, checkpoints route1, checkpoints route2
        mock_firestore_helper.query_documents.side_effect = [
            [
                ("route1", {"name": "Etapa 1", "createdAt": "2026-01-01", "updatedAt": "2026-01-01"}),
                ("route2", {"name": "Etapa 2", "createdAt": "2026-01-01", "updatedAt": "2026-01-01"}),
            ],
            [
                ("cp1", {"name": "WP1", "order": 0, "createdAt": "2026-01-01", "updatedAt": "2026-01-01"}),
                ("cp2", {"name": "WP2", "order": 1, "createdAt": "2026-01-01", "updatedAt": "2026-01-01"}),
            ],
            [],
        ]
        req = _make_request({"eventId": "evt1"})

        # Act
        response = handle_list(req, "user1")

        # Assert
        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data) == 2
        assert data[0]["id"] == "route1"
        assert data[0]["name"] == "Etapa 1"
        assert "createdAt" not in data[0]
        assert "updatedAt" not in data[0]
        assert len(data[0]["checkpoints"]) == 2
        assert data[0]["checkpoints"][0]["id"] == "cp1"
        assert "createdAt" not in data[0]["checkpoints"][0]
        assert "updatedAt" not in data[0]["checkpoints"][0]
        assert data[1]["id"] == "route2"
        assert data[1]["checkpoints"] == []

    def test_retorna_lista_vacia(self, mock_get_event_if_owner, mock_firestore_helper):
        # Arrange — sin rutas, solo una llamada a query_documents
        mock_firestore_helper.query_documents.return_value = []
        req = _make_request({"eventId": "evt1"})

        # Act
        response = handle_list(req, "user1")

        # Assert
        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data == []


# ============================================================================
# TESTS — Validaciones → 400
# ============================================================================


class TestHandleListValidacion:

    def test_user_id_vacio_retorna_400(self, mock_get_event_if_owner):
        req = _make_request({"eventId": "evt1"})
        response = handle_list(req, "")
        assert response.status_code == 400

    def test_event_id_faltante_retorna_400(self, mock_get_event_if_owner):
        req = _make_request({})
        response = handle_list(req, "user1")
        assert response.status_code == 400


# ============================================================================
# TESTS — Ownership → 404
# ============================================================================


class TestHandleListNotFound:

    def test_usuario_no_es_owner_retorna_404(self, mock_get_event_if_owner):
        mock_get_event_if_owner.return_value = None
        req = _make_request({"eventId": "evt1"})
        response = handle_list(req, "user1")
        assert response.status_code == 404


# ============================================================================
# TESTS — Error interno → 500
# ============================================================================


class TestHandleListErrorInterno:

    def test_excepcion_en_firestore_retorna_500(self, mock_get_event_if_owner, mock_firestore_helper):
        mock_firestore_helper.query_documents.side_effect = Exception("db error")
        req = _make_request({"eventId": "evt1"})
        response = handle_list(req, "user1")
        assert response.status_code == 500
