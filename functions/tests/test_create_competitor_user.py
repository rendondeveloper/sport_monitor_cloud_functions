"""
Tests para create_competitor_user Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Valor/tipo incorrecto
4. Consultas con data (mock Firestore)
5. Escrituras exitosas (3 pasos transaccionales)
6. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch, call

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validate_request():
    with patch(
        "competitors.create_competitor_user.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "competitors.create_competitor_user.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("competitors.create_competitor_user.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def valid_request_body():
    """Body válido: email y username a nivel raíz; emergencyContacts como lista; competition con eventId y team."""
    return {
        "personalData": {
            "fullName": "Juan Pérez",
            "phone": "+521234567890",
            "dateOfBirth": "1990-05-15T00:00:00",
            "address": "Calle 123",
            "city": "CDMX",
            "state": "CDMX",
            "country": "México",
            "postalCode": "01000",
        },
        "email": "juan@example.com",
        "username": "juanperez",
        "healthData": {
            "bloodType": "O+",
            "allergies": "Ninguna",
        },
        "emergencyContacts": [
            {
                "fullName": "María Pérez",
                "relationship": "Esposa",
                "phone": "+529876543210",
            },
        ],
        "vehicleData": {
            "brand": "Honda",
            "model": "CRF450",
            "year": 2024,
        },
        "competition": {
            "eventId": "event456",
            "number": "42",
            "category": "Pro",
            "team": "Team Red Bull",
        },
        "source": "mobile-ios",
        "system": "rally-app",
    }


def _make_request(body=None, method="POST"):
    req = MagicMock()
    req.method = method
    req.get_json.return_value = body
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestCreateCompetitorUserHappyPath:
    """Happy path: creación exitosa de los 3 pasos."""

    def test_create_full_user_success(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        # Mock: no hay duplicados
        mock_firestore_helper.query_documents.return_value = []
        # create_document: user, personalData, healthData, emergencyContact (x1), vehicle
        mock_firestore_helper.create_document.side_effect = [
            "user_abc",
            "personal_1",
            "health_1",
            "ec_1",
            "vehicle_1",
        ]
        mock_firestore_helper.create_document_with_id.return_value = "event456"
        # get_document: evento existe (event_id), participante no existe
        mock_firestore_helper.get_document.side_effect = [{}, None]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)

        assert response.status_code == 201
        data = json.loads(response.response[0])
        assert data["id"] == "user_abc"
        assert data["membershipId"] == "event456"
        participant_doc = mock_firestore_helper.create_document_with_id.call_args_list[-1].args[2]
        assert participant_doc["source"] == "mobile-ios"
        assert participant_doc["system"] == "rally-app"

    def test_create_user_without_optional_fields(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {
                "fullName": "Test User",
                "phone": "+521234567890",
            },
            "email": "test@example.com",
            "username": "testuser",
            "emergencyContacts": [
                {"fullName": "Contact", "relationship": "Friend", "phone": "+529876543210"},
            ],
            "competition": {
                "eventId": "event789",
                "number": "1",
                "category": "Am",
            },
        }

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_minimal",
            "personal_1",
            "health_1",
            "ec_1",
        ]
        mock_firestore_helper.create_document_with_id.return_value = "event789"
        mock_firestore_helper.get_document.side_effect = [{}, None]

        req = _make_request(body=body)
        response = create_competitor_user(req)

        assert response.status_code == 201


class TestCreateCompetitorUserMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_body(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.create_competitor_user import create_competitor_user

        req = _make_request(body=None)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_missing_personal_data(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {"username": "testuser", "email": "test@example.com"}
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_missing_email(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "+521234567890"},
            "emergencyContacts": [{"fullName": "C", "phone": "+529876543210"}],
            "username": "testuser",
            "competition": {"eventId": "ev1"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400


class TestCreateCompetitorUserInvalidValues:
    """Valor/tipo incorrecto -> 400."""

    def test_short_username(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "+521234567890"},
            "email": "test@example.com",
            "emergencyContacts": [{"fullName": "C", "phone": "+529876543210"}],
            "username": "ab",
            "competition": {"eventId": "ev1"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400


class TestCreateCompetitorUserDuplicate:
    """Email o username duplicado -> 409."""

    def test_duplicate_email(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        # Primera query (email) retorna resultado -> duplicado
        mock_firestore_helper.query_documents.return_value = [
            ("existing_user", {"email": "juan@example.com"})
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 409

    def test_duplicate_username(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        # Orden de queries:
        # 1) event_categories (validación condicional category)
        # 2) email existente
        # 3) username duplicado
        mock_firestore_helper.query_documents.side_effect = [
            [],
            [],
            [("existing_user", {"username": "juanperez"})],
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 409


class TestCreateCompetitorUserRollback:
    """Rollback en caso de error en paso 2 o 3."""

    def test_rollback_on_user_creation_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = RuntimeError("DB error")

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)

        assert response.status_code == 500


class TestCreateCompetitorUserJsonError:
    """Errores de parsing JSON."""

    def test_json_parse_error(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        req = _make_request(body=None)
        req.get_json.side_effect = TypeError("bad json")
        response = create_competitor_user(req)
        assert response.status_code == 400


class TestCreateCompetitorUserValidationEdgeCases:
    """Casos de validación adicionales para cubrir ramas."""

    def test_invalid_email_format(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "+521234567890"},
            "email": "not-an-email",
            "emergencyContacts": [{"fullName": "C", "relationship": "F", "phone": "+521234567890"}],
            "username": "testuser",
            "competition": {"eventId": "ev1"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_invalid_phone_format(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "123"},
            "email": "test@example.com",
            "emergencyContacts": [{"fullName": "C", "relationship": "F", "phone": "+521234567890"}],
            "username": "testuser",
            "competition": {"eventId": "ev1"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_emergency_contact_missing_phone(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "+521234567890"},
            "email": "test@example.com",
            "emergencyContacts": [{"fullName": "C"}],
            "username": "testuser",
            "competition": {"eventId": "ev1"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_competition_not_dict(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "+521234567890"},
            "email": "test@example.com",
            "emergencyContacts": [{"fullName": "C", "relationship": "F", "phone": "+521234567890"}],
            "username": "testuser",
            "competition": "not_a_dict",
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400


class TestCreateCompetitorUserValidationWithCompetition:
    """Validaciones que se alcanzan solo con competition completo."""

    def test_short_username_with_full_competition(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "email": "test@example.com",
            "username": "ab",
            "competition": {"eventId": "ev1", "number": "1", "category": "Pro"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_invalid_phone_with_full_competition(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "personalData": {"fullName": "Test", "phone": "123"},
            "email": "test@example.com",
            "competition": {"eventId": "ev1", "number": "1", "category": "Pro"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_emergency_contacts_not_list(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "email": "test@example.com",
            "emergencyContacts": "not_a_list",
            "competition": {"eventId": "ev1", "number": "1", "category": "Pro"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_emergency_contact_not_dict(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "email": "test@example.com",
            "emergencyContacts": ["not_a_dict"],
            "competition": {"eventId": "ev1", "number": "1", "category": "Pro"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_emergency_contact_partial_fields(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {
            "email": "test@example.com",
            "emergencyContacts": [{"fullName": "Solo nombre"}],
            "competition": {"eventId": "ev1", "number": "1", "category": "Pro"},
        }
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_competition_missing_creates_default(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = {"email": "test@example.com"}
        req = _make_request(body=body)
        response = create_competitor_user(req)
        assert response.status_code == 400


class TestCreateCompetitorUserEventValidation:
    """Validaciones de evento: 404 y 409."""

    def _setup_until_step4(self, mock_fh):
        """Configura mocks para que pasen pasos 1-3 y se llegue a validación de evento."""
        mock_fh.query_documents.return_value = []
        mock_fh.create_document.side_effect = [
            "user_1", "personal_1", "health_1", "ec_1", "vehicle_1",
        ]
        mock_fh.create_document_with_id.return_value = "event456"

    def test_event_not_found_returns_404(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.get_document.return_value = None

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 404
        mock_firestore_helper.delete_document.assert_not_called()

    def test_existing_participant_returns_409(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        self._setup_until_step4(mock_firestore_helper)
        # evento existe, participante ya existe
        mock_firestore_helper.get_document.side_effect = [
            {"name": "Event"},
            {"userId": "user_1"},
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 409

    def test_duplicate_pilot_number_returns_409(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        self._setup_until_step4(mock_firestore_helper)
        # evento existe, participante no existe
        mock_firestore_helper.get_document.side_effect = [{"name": "Event"}, None]
        # piloto duplicado
        mock_firestore_helper.query_documents.side_effect = [
            [],  # event_categories -> no categories
            [],  # find existing by email
            [],  # validate unique username
            [("dup_id", {"competitionCategory": {"pilotNumber": "42"}})],  # pilot duplicate
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 409


class TestCreateCompetitorUserRollbackScenarios:
    """Rollback en distintos pasos de creación."""

    def test_rollback_on_personal_data_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1",
            RuntimeError("personalData fail"),
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500
        mock_firestore_helper.delete_document.assert_called()

    def test_rollback_on_health_data_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1",
            "personal_1",
            RuntimeError("healthData fail"),
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500

    def test_rollback_on_emergency_contact_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1",
            "personal_1",
            "health_1",
            RuntimeError("ec fail"),
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500

    def test_rollback_on_vehicle_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1",
            "personal_1",
            "health_1",
            "ec_1",
            RuntimeError("vehicle fail"),
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500

    def test_rollback_on_membership_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1", "personal_1", "health_1", "ec_1", "vehicle_1",
        ]
        mock_firestore_helper.create_document_with_id.side_effect = RuntimeError("membership fail")

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500

    def test_rollback_on_competitor_creation_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1", "personal_1", "health_1", "ec_1", "vehicle_1",
        ]
        # membership OK, competitor fail
        mock_firestore_helper.create_document_with_id.side_effect = [
            "event456",
            RuntimeError("competitor fail"),
        ]
        mock_firestore_helper.get_document.side_effect = [{"name": "Event"}, None]

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500


class TestCreateCompetitorUserExceptions:
    """Excepciones -> códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.side_effect = ValueError("bad")

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 400

    def test_type_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.side_effect = TypeError("type err")

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)
        assert response.status_code == 500


class TestCreateCompetitorUserMultipleCalls:
    """Múltiples llamadas estables."""

    def test_multiple_calls(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_1", "personal_1", "health_1", "ec_1", "vehicle_1",
            "user_2", "personal_2", "health_2", "ec_2", "vehicle_2",
        ]
        mock_firestore_helper.create_document_with_id.return_value = "event456"
        mock_firestore_helper.get_document.side_effect = [{}, None, {}, None]

        for _ in range(2):
            req = _make_request(body=valid_request_body)
            response = create_competitor_user(req)
            assert response.status_code == 201


class TestCreateCompetitorUserConditionalCategory:
    """Regla condicional de competition.category según categorías del evento."""

    def test_event_with_categories_and_missing_category_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = dict(valid_request_body)
        body["competition"] = dict(valid_request_body["competition"])
        body["competition"].pop("category", None)

        mock_firestore_helper.get_document.return_value = {"name": "Event"}
        mock_firestore_helper.query_documents.return_value = [("cat_1", {"name": "Pro"})]

        req = _make_request(body=body)
        response = create_competitor_user(req)

        assert response.status_code == 400

    def test_event_without_categories_and_missing_category_returns_201(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        body = dict(valid_request_body)
        body["competition"] = dict(valid_request_body["competition"])
        body["competition"].pop("category", None)

        mock_firestore_helper.get_document.side_effect = [{"name": "Event"}, None]
        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "user_abc",
            "personal_1",
            "health_1",
            "ec_1",
            "vehicle_1",
        ]
        mock_firestore_helper.create_document_with_id.return_value = "event456"

        req = _make_request(body=body)
        response = create_competitor_user(req)

        assert response.status_code == 201

    def test_event_with_categories_and_category_present_returns_201(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor_user import create_competitor_user

        mock_firestore_helper.get_document.side_effect = [{"name": "Event"}, None]
        mock_firestore_helper.query_documents.side_effect = [
            [("cat_1", {"name": "Pro"})],  # event_categories
            [],  # find existing by email
            [],  # validate unique username
            [],  # check duplicate pilot number
        ]
        mock_firestore_helper.create_document.side_effect = [
            "user_abc",
            "personal_1",
            "health_1",
            "ec_1",
            "vehicle_1",
        ]
        mock_firestore_helper.create_document_with_id.return_value = "event456"

        req = _make_request(body=valid_request_body)
        response = create_competitor_user(req)

        assert response.status_code == 201
