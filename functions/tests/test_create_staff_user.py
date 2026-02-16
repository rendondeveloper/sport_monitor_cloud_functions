"""
Tests para create_staff_user Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Valor/tipo incorrecto
4. Consultas con data (mock Firestore)
5. Escrituras exitosas (3 pasos transaccionales)
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
        "staff.create_staff_user.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "staff.create_staff_user.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("staff.create_staff_user.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_create_auth_user():
    with patch(
        "staff.create_staff_user.create_firebase_auth_user",
        return_value="auth_staff_uid",
    ) as m:
        yield m


@pytest.fixture
def mock_delete_auth_user():
    with patch(
        "staff.create_staff_user.delete_firebase_auth_user",
        return_value=True,
    ) as m:
        yield m


@pytest.fixture
def valid_staff_body():
    return {
        "personalData": {
            "fullName": "Ana García",
            "email": "ana@example.com",
            "phone": "+521234567890",
        },
        "emergencyContact": {
            "fullName": "Luis García",
            "phone": "+529876543210",
        },
        "username": "anagarcia",
        "password": "Passw0rd123",
        "confirmPassword": "Passw0rd123",
        "eventId": "event456",
        "role": "staff",
    }


@pytest.fixture
def valid_checkpoint_body(valid_staff_body):
    body = valid_staff_body.copy()
    body["role"] = "checkpoint"
    body["checkpointId"] = "cp_001"
    return body


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


class TestCreateStaffUserHappyPath:
    """Happy path: creación exitosa de los 3 pasos."""

    def test_create_staff_user_success(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_create_auth_user,
        mock_delete_auth_user,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.return_value = "staff_user_abc"
        mock_firestore_helper.create_document_with_id.return_value = "event456"

        req = _make_request(body=valid_staff_body)
        response = create_staff_user(req)

        assert response.status_code == 201
        data = json.loads(response.response[0])
        assert data["id"] == "staff_user_abc"
        assert data["authUserId"] == "auth_staff_uid"
        assert data["membershipId"] == "event456"

    def test_create_checkpoint_staff_success(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_create_auth_user,
        mock_delete_auth_user,
        valid_checkpoint_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.return_value = "cp_staff"
        mock_firestore_helper.create_document_with_id.return_value = "event456"

        req = _make_request(body=valid_checkpoint_body)
        response = create_staff_user(req)

        assert response.status_code == 201


class TestCreateStaffUserMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_body(self, mock_validate_request, mock_verify_bearer_token):
        from staff.create_staff_user import create_staff_user

        req = _make_request(body=None)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_missing_personal_data(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "test",
            "password": "Pass1234",
            "confirmPassword": "Pass1234",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_missing_role(self, mock_validate_request, mock_verify_bearer_token):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {
                "fullName": "Test",
                "email": "t@t.com",
                "phone": "+521234567890",
            },
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400


class TestCreateStaffUserInvalidValues:
    """Valor/tipo incorrecto -> 400."""

    def test_invalid_role(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {
                "fullName": "Test",
                "email": "t@t.com",
                "phone": "+521234567890",
            },
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
            "role": "invalid_role",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_checkpoint_role_without_checkpoint_id(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {
                "fullName": "Test",
                "email": "t@t.com",
                "phone": "+521234567890",
            },
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
            "role": "checkpoint",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_passwords_dont_match(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {
                "fullName": "Test",
                "email": "t@t.com",
                "phone": "+521234567890",
            },
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Different1",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400


class TestCreateStaffUserDuplicate:
    """Email o username duplicado -> 409."""

    def test_duplicate_email(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.return_value = [
            ("existing", {"personalData": {"email": "ana@example.com"}})
        ]

        req = _make_request(body=valid_staff_body)
        response = create_staff_user(req)
        assert response.status_code == 409


class TestCreateStaffUserRollback:
    """Rollback en caso de error."""

    def test_rollback_on_user_doc_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_create_auth_user,
        mock_delete_auth_user,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = RuntimeError("DB error")

        req = _make_request(body=valid_staff_body)
        response = create_staff_user(req)

        assert response.status_code == 500
        mock_delete_auth_user.assert_called_once_with("auth_staff_uid")

    def test_rollback_on_membership_failure(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_create_auth_user,
        mock_delete_auth_user,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.return_value = "staff_user_1"
        mock_firestore_helper.create_document_with_id.side_effect = RuntimeError(
            "Membership error"
        )

        req = _make_request(body=valid_staff_body)
        response = create_staff_user(req)

        assert response.status_code == 500
        # Debe eliminar el usuario y el auth user
        mock_firestore_helper.delete_document.assert_called_once()
        mock_delete_auth_user.assert_called_once_with("auth_staff_uid")


class TestCreateStaffUserJsonError:
    """Errores de parsing JSON."""

    def test_json_parse_error(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        req = _make_request(body=None)
        req.get_json.side_effect = ValueError("bad json")
        response = create_staff_user(req)
        assert response.status_code == 400


class TestCreateStaffUserValidationEdgeCases:
    """Casos adicionales de validación."""

    def test_invalid_email_format(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {"fullName": "T", "email": "bad", "phone": "+521234567890"},
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_invalid_phone_format(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {"fullName": "T", "email": "t@t.com", "phone": "1"},
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_password_no_letter(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {"fullName": "T", "email": "t@t.com", "phone": "+521234567890"},
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "testuser",
            "password": "12345678",
            "confirmPassword": "12345678",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_short_username(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {"fullName": "T", "email": "t@t.com", "phone": "+521234567890"},
            "emergencyContact": {"fullName": "C", "phone": "+521234567890"},
            "username": "ab",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_emergency_missing_phone(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from staff.create_staff_user import create_staff_user

        body = {
            "personalData": {"fullName": "T", "email": "t@t.com", "phone": "+521234567890"},
            "emergencyContact": {"fullName": "C"},
            "username": "testuser",
            "password": "Passw0rd123",
            "confirmPassword": "Passw0rd123",
            "eventId": "ev1",
            "role": "staff",
        }
        req = _make_request(body=body)
        response = create_staff_user(req)
        assert response.status_code == 400


class TestCreateStaffUserExceptions:
    """Excepciones -> códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.side_effect = ValueError("bad")

        req = _make_request(body=valid_staff_body)
        response = create_staff_user(req)
        assert response.status_code == 400

    def test_type_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.side_effect = TypeError("type err")

        req = _make_request(body=valid_staff_body)
        response = create_staff_user(req)
        assert response.status_code == 500


class TestCreateStaffUserMultipleCalls:
    """Múltiples llamadas estables."""

    def test_multiple_calls(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_create_auth_user,
        mock_delete_auth_user,
        valid_staff_body,
    ):
        from staff.create_staff_user import create_staff_user

        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.side_effect = [
            "staff_1",
            "staff_2",
            "staff_3",
        ]
        mock_firestore_helper.create_document_with_id.return_value = "event456"

        for i in range(3):
            req = _make_request(body=valid_staff_body)
            response = create_staff_user(req)
            assert response.status_code == 201
            data = json.loads(response.response[0])
            assert data["id"] == f"staff_{i + 1}"
