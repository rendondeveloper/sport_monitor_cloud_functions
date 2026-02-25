"""
Tests para get_competitor_by_email Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Valor/tipo incorrecto (email inválido)
4. Consultas con data (mock Firestore)
5. Escrituras exitosas (N/A para GET)
6. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validate_request():
    with patch(
        "competitors.get_competitor_by_email.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "competitors.get_competitor_by_email.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("competitors.get_competitor_by_email.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_validate_email_ok():
    with patch(
        "competitors.get_competitor_by_email.validate_email", return_value=True
    ) as m:
        yield m


@pytest.fixture
def sample_user_doc():
    """Documento raíz de usuario como viene de Firestore."""
    return {
        "email": "pilot@example.com",
        "username": "pilot42",
        "authUserId": "auth_abc",
        "avatarUrl": "https://example.com/avatar.png",
        "isActive": True,
        "createdAt": "2026-02-15T08:00:00",
        "updatedAt": "2026-02-15T09:00:00",
    }


def _make_request(email="", method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}

    if email:
        req.args["email"] = email

    return req


def _setup_subcollections(mock_helper):
    """Configura query_documents y get_document para retornar datos de subcolecciones y eventos activos con register."""
    user_query = [("user123", {"email": "pilot@example.com", "username": "pilot42",
                                "authUserId": None, "avatarUrl": None,
                                "isActive": False, "createdAt": "t1", "updatedAt": "t2"})]
    personal = [("pd1", {"fullName": "Juan Pérez", "phone": "+521234567890",
                          "createdAt": "t1", "updatedAt": "t2"})]
    health = [("hd1", {"bloodType": "O+", "allergies": "",
                        "createdAt": "t1", "updatedAt": "t2"})]
    emergency = [("ec1", {"fullName": "María López", "phone": "+529876543210",
                           "relationship": "Spouse", "createdAt": "t1", "updatedAt": "t2"})]
    vehicles = [("v1", {"branch": "Honda", "year": 2024, "model": "CRF450R",
                         "color": "Red", "createdAt": "t1", "updatedAt": "t2"})]
    membership = [("event123", {"createdAt": "t1", "updatedAt": "t2"})]

    mock_helper.query_documents.side_effect = [
        user_query,
        personal,
        health,
        emergency,
        vehicles,
        membership,
    ]
    # Evento válido (status inProgress) y participante para membership (event123, user123)
    mock_helper.get_document.side_effect = [
        {"status": "inProgress"},
        {"competitionCategory": {"pilotNumber": "42", "registrationCategory": "Pro"}, "team": "Team Red"},
    ]


# ============================================================================
# TESTS
# ============================================================================


class TestGetCompetitorByEmailHappyPath:
    """Happy path: usuario encontrado con todas las subcolecciones."""

    def test_get_user_with_all_subcollections(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        _setup_subcollections(mock_firestore_helper)

        req = _make_request(email="pilot@example.com")
        response = get_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "user123"
        assert data["email"] == "pilot@example.com"
        assert len(data["personalData"]) == 1
        assert data["personalData"][0]["fullName"] == "Juan Pérez"
        assert len(data["healthData"]) == 1
        assert data["healthData"][0]["bloodType"] == "O+"
        assert len(data["emergencyContacts"]) == 1
        assert data["emergencyContacts"][0]["relationship"] == "Spouse"
        assert len(data["vehicles"]) == 1
        assert data["vehicles"][0]["branch"] == "Honda"
        assert len(data["membership"]) == 1
        assert data["membership"][0]["id"] == "event123"
        assert data["membership"][0]["register"]["number"] == "42"
        assert data["membership"][0]["register"]["category"] == "Pro"
        assert data["membership"][0]["register"]["team"] == "Team Red"

    def test_inactive_event_not_in_membership(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = [
            [("user1", {"email": "u@test.com", "username": "u", "isActive": False})],
            [], [], [], [],
            [("inactive_event", {})],
        ]
        mock_firestore_helper.get_document.return_value = {"status": "completed"}

        req = _make_request(email="u@test.com")
        response = get_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["membership"] == []


class TestGetCompetitorByEmailMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_email(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        req = _make_request()
        response = get_competitor_by_email(req)
        assert response.status_code == 400

    def test_empty_email(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        req = _make_request()
        req.args["email"] = "   "
        response = get_competitor_by_email(req)
        assert response.status_code == 400


class TestGetCompetitorByEmailInvalidEmail:
    """Email con formato inválido -> 400."""

    def test_invalid_email_format(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        with patch(
            "competitors.get_competitor_by_email.validate_email",
            return_value=False,
        ):
            req = _make_request(email="not-an-email")
            response = get_competitor_by_email(req)
            assert response.status_code == 400


class TestGetCompetitorByEmailAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.get_competitor_by_email import get_competitor_by_email

        with patch(
            "competitors.get_competitor_by_email.verify_bearer_token",
            return_value=False,
        ):
            req = _make_request(email="pilot@example.com")
            response = get_competitor_by_email(req)
            assert response.status_code == 401


class TestGetCompetitorByEmailNotFound:
    """Usuario no encontrado -> 404."""

    def test_user_not_found_by_email(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(email="unknown@example.com")
        response = get_competitor_by_email(req)
        assert response.status_code == 404


class TestGetCompetitorByEmailQueryWithData:
    """Consultas con data: verificar estructura completa de respuesta."""

    def test_response_includes_all_root_fields(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        _setup_subcollections(mock_firestore_helper)

        req = _make_request(email="pilot@example.com")
        response = get_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert "id" in data
        assert "email" in data
        assert "username" in data
        assert "authUserId" in data
        assert "avatarUrl" in data
        assert "isActive" in data
        assert "createdAt" not in data
        assert "updatedAt" not in data
        assert "personalData" in data
        assert "healthData" in data
        assert "emergencyContacts" in data
        assert "vehicles" in data
        assert "membership" in data
        for key in ("personalData", "healthData", "emergencyContacts", "vehicles"):
            for doc in data[key]:
                assert "createdAt" not in doc, f"{key} doc should not have createdAt"
                assert "updatedAt" not in doc, f"{key} doc should not have updatedAt"
        for m in data["membership"]:
            assert "id" in m and "register" in m
            assert "number" in m["register"] and "category" in m["register"] and "team" in m["register"]

    def test_user_with_empty_subcollections(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = [
            [("user50", {"email": "minimal@test.com", "username": "",
                          "isActive": False, "createdAt": "t1", "updatedAt": "t2"})],
            [],
            [],
            [],
            [],
            [],
        ]

        req = _make_request(email="minimal@test.com")
        response = get_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "user50"
        assert data["email"] == "minimal@test.com"
        assert data["personalData"] == []
        assert data["healthData"] == []
        assert data["emergencyContacts"] == []
        assert data["vehicles"] == []
        assert data["membership"] == []

    def test_user_with_multiple_emergency_contacts(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = [
            [("user77", {"email": "multi@test.com", "username": "multi",
                          "isActive": True, "createdAt": "t1", "updatedAt": "t2"})],
            [],
            [],
            [
                ("ec1", {"fullName": "Contacto 1", "phone": "+521111111111"}),
                ("ec2", {"fullName": "Contacto 2", "phone": "+522222222222"}),
            ],
            [],
            [],
        ]

        req = _make_request(email="multi@test.com")
        response = get_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data["emergencyContacts"]) == 2
        assert data["emergencyContacts"][0]["id"] == "ec1"
        assert data["emergencyContacts"][1]["id"] == "ec2"

    def test_subcollection_docs_include_id(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        _setup_subcollections(mock_firestore_helper)

        req = _make_request(email="pilot@example.com")
        response = get_competitor_by_email(req)

        data = json.loads(response.response[0])
        assert data["personalData"][0]["id"] == "pd1"
        assert data["healthData"][0]["id"] == "hd1"
        assert data["emergencyContacts"][0]["id"] == "ec1"
        assert data["vehicles"][0]["id"] == "v1"
        assert data["membership"][0]["id"] == "event123"
        assert "register" in data["membership"][0]
        assert data["membership"][0]["register"]["number"] == "42"


class TestGetCompetitorByEmailExceptions:
    """Excepciones -> códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = ValueError("bad")

        req = _make_request(email="pilot@example.com")
        response = get_competitor_by_email(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = RuntimeError("crash")

        req = _make_request(email="pilot@example.com")
        response = get_competitor_by_email(req)
        assert response.status_code == 500


class TestGetCompetitorByEmailValidateRequest:
    """validate_request bloquea -> retorna su respuesta."""

    def test_validate_request_blocks(self):
        from competitors.get_competitor_by_email import get_competitor_by_email

        blocked_response = MagicMock()
        with patch(
            "competitors.get_competitor_by_email.validate_request",
            return_value=blocked_response,
        ):
            req = _make_request(email="pilot@example.com")
            response = get_competitor_by_email(req)
            assert response is blocked_response


class TestGetCompetitorByEmailMultipleCalls:
    """Múltiples llamadas estables sin efectos colaterales."""

    def test_multiple_calls_stable(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        for _ in range(3):
            mock_firestore_helper.query_documents.side_effect = [
                [("user123", {"email": "pilot@example.com", "username": "p",
                               "isActive": True, "createdAt": "t", "updatedAt": "t"})],
                [], [], [], [], [],
            ]
            req = _make_request(email="pilot@example.com")
            response = get_competitor_by_email(req)
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert data["id"] == "user123"

    def test_multiple_calls_different_results(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_competitor_by_email import get_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = [
            [("user1", {"email": "a@test.com", "username": "", "isActive": True,
                         "createdAt": "t", "updatedAt": "t"})],
            [], [], [], [], [],
        ]
        req1 = _make_request(email="a@test.com")
        resp1 = get_competitor_by_email(req1)
        assert resp1.status_code == 200

        mock_firestore_helper.query_documents.side_effect = [
            [],
        ]
        req2 = _make_request(email="notfound@test.com")
        resp2 = get_competitor_by_email(req2)
        assert resp2.status_code == 404
