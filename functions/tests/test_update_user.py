"""
Tests para update_user Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path - actualización exitosa por cada sección y combinaciones
2. Parámetros faltantes - userId ausente, body vacío, sin secciones válidas
3. Valor/tipo incorrecto - email inválido, username corto, phone inválido, tipos incorrectos
4. Consultas con data - mock Firestore retorna docs existentes
5. Escrituras exitosas - update/create por sección
6. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_firestore_helper():
    with patch("users.update.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


def _make_request(body=None, method="PUT", user_id="user123"):
    req = MagicMock()
    req.method = method
    req.get_json.return_value = body
    req.args = {"userId": user_id} if user_id else {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}
    return req


@pytest.fixture
def full_body():
    return {
        "email": "nuevo@example.com",
        "username": "nuevousuario",
        "personalData": {
            "fullName": "Juan Actualizado",
            "phone": "+521234567890",
            "city": "CDMX",
        },
        "healthData": {
            "bloodType": "B+",
            "medications": "ninguna",
        },
        "emergencyContacts": [
            {"fullName": "Contacto Uno", "relationship": "Hermano", "phone": "+529876543210"},
            {"fullName": "Contacto Dos", "relationship": "Madre", "phone": "+521112223333"},
        ],
        "vehicleData": {
            "id": "vehicle_abc",
            "branch": "Honda",
            "model": "CRF",
            "year": 2022,
            "color": "Rojo",
        },
    }


# ============================================================================
# HAPPY PATH
# ============================================================================


class TestUpdateUserHappyPath:

    def test_update_all_sections_success(
        self,
        mock_firestore_helper,
        full_body,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = [
            {"email": "old@example.com"},  # usuario existe
            {"branch": "Yamaha"},           # vehiculo existe para upsert
        ]
        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.list_document_ids.return_value = ["existing_doc_1"]

        req = _make_request(body=full_body)
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "user123"
        assert set(data["updated"]) == {
            "email", "username", "personalData", "healthData", "emergencyContacts", "vehicleData"
        }

    def test_update_only_email(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "old@example.com"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(body={"email": "nuevo@example.com"})
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["updated"] == ["email"]

    def test_update_only_personal_data(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["pd_doc_1"]

        req = _make_request(body={"personalData": {"fullName": "Nuevo Nombre", "city": "GDL"}})
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["updated"] == ["personalData"]
        mock_firestore_helper.update_document.assert_called()

    def test_update_only_health_data(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["hd_doc_1"]

        req = _make_request(body={"healthData": {"bloodType": "O-"}})
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["updated"] == ["healthData"]

    def test_update_emergency_contacts_replace(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["old_ec_1", "old_ec_2"]

        contacts = [{"fullName": "Nuevo Contacto", "phone": "+521234567890"}]
        req = _make_request(body={"emergencyContacts": contacts})
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["updated"] == ["emergencyContacts"]
        assert mock_firestore_helper.delete_document.call_count == 2
        assert mock_firestore_helper.create_document.call_count == 1

    def test_update_emergency_contacts_empty_list(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["ec_1"]

        req = _make_request(body={"emergencyContacts": []})
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.delete_document.assert_called_once()
        mock_firestore_helper.create_document.assert_not_called()

    def test_update_vehicle_by_id_existing(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},  # usuario
            {"branch": "Yamaha"},            # vehiculo existe
        ]

        vehicle = {"id": "v_123", "branch": "Honda", "model": "CRF", "year": 2022, "color": "Rojo"}
        req = _make_request(body={"vehicleData": vehicle})
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["updated"] == ["vehicleData"]
        mock_firestore_helper.update_document.assert_called()

    def test_update_vehicle_by_id_not_existing_creates(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},  # usuario
            None,                           # vehiculo no existe
        ]

        vehicle = {"id": "v_new", "branch": "Kawasaki", "model": "ZX", "year": 2021, "color": "Verde"}
        req = _make_request(body={"vehicleData": vehicle})
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.create_document_with_id.assert_called()

    def test_update_vehicle_no_id_creates_new(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.create_document.return_value = "new_vehicle_id"

        vehicle = {"branch": "Suzuki", "model": "GSX", "year": 2023, "color": "Azul"}
        req = _make_request(body={"vehicleData": vehicle})
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.create_document.assert_called()

    def test_competition_is_ignored(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(body={
            "email": "nuevo@example.com",
            "competition": {"eventId": "ev1", "number": "99"},
        })
        response = update_handle(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert "competition" not in data["updated"]

    def test_personal_data_no_existing_doc_creates(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = []
        mock_firestore_helper.create_document.return_value = "new_pd"

        req = _make_request(body={"personalData": {"fullName": "Test"}})
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.create_document.assert_called()

    def test_personal_data_email_in_body_not_written_to_subcollection(
        self,
        mock_firestore_helper,
    ):
        """Si personalData incluye email en el body, no se escribe en la subcolección (email es campo raíz)."""
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["pd1"]

        req = _make_request(
            body={
                "personalData": {
                    "fullName": "Juan",
                    "phone": "+521234567890",
                    "email": "ignorado@subcollection.com",
                },
            },
        )
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.update_document.assert_called_once()
        call_args = mock_firestore_helper.update_document.call_args[0]
        fields = call_args[2]
        assert "email" not in fields
        assert fields.get("fullName") == "Juan"
        assert fields.get("phone") == "+521234567890"


# ============================================================================
# PARAMETROS FALTANTES -> 400
# ============================================================================


class TestUpdateUserMissingParams:

    def test_missing_user_id(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"email": "test@example.com"}, user_id=None)
        response = update_handle(req)
        assert response.status_code == 400

    def test_empty_user_id(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"email": "test@example.com"}, user_id="")
        response = update_handle(req)
        assert response.status_code == 400

    def test_missing_body(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body=None)
        response = update_handle(req)
        assert response.status_code == 400

    def test_body_without_known_sections(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"competition": {"eventId": "ev1"}})
        response = update_handle(req)
        assert response.status_code == 400

    def test_empty_body_dict(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={})
        response = update_handle(req)
        assert response.status_code == 400


# ============================================================================
# VALOR / TIPO INCORRECTO -> 400
# ============================================================================


class TestUpdateUserInvalidValues:

    def test_invalid_email_format(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"email": "not-an-email"})
        response = update_handle(req)
        assert response.status_code == 400

    def test_empty_email(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"email": "   "})
        response = update_handle(req)
        assert response.status_code == 400

    def test_short_username(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"username": "ab"})
        response = update_handle(req)
        assert response.status_code == 400

    def test_invalid_phone_in_personal_data(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"personalData": {"phone": "123"}})
        response = update_handle(req)
        assert response.status_code == 400

    def test_personal_data_not_dict(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"personalData": "not_a_dict"})
        response = update_handle(req)
        assert response.status_code == 400

    def test_health_data_not_dict(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"healthData": ["not", "a", "dict"]})
        response = update_handle(req)
        assert response.status_code == 400

    def test_emergency_contacts_not_list(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"emergencyContacts": "not_a_list"})
        response = update_handle(req)
        assert response.status_code == 400

    def test_emergency_contact_missing_fullname(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"emergencyContacts": [{"phone": "+521234567890"}]})
        response = update_handle(req)
        assert response.status_code == 400

    def test_emergency_contact_missing_phone(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"emergencyContacts": [{"fullName": "Alguien"}]})
        response = update_handle(req)
        assert response.status_code == 400

    def test_emergency_contact_not_dict(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"emergencyContacts": ["not_a_dict"]})
        response = update_handle(req)
        assert response.status_code == 400

    def test_vehicle_data_not_dict(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body={"vehicleData": "not_a_dict"})
        response = update_handle(req)
        assert response.status_code == 400

    def test_json_parse_error(
        self,
    ):
        from users.update import handle as update_handle

        req = _make_request(body=None)
        req.get_json.side_effect = TypeError("bad json")
        response = update_handle(req)
        assert response.status_code == 400


# ============================================================================
# CONSULTAS CON DATA (MOCKED FIRESTORE)
# ============================================================================


class TestUpdateUserFirestoreQueries:

    def test_user_not_found_returns_404(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = None

        req = _make_request(body={"email": "test@example.com"})
        response = update_handle(req)
        assert response.status_code == 404

    def test_duplicate_email_another_user_returns_409(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "old@example.com"}
        mock_firestore_helper.query_documents.return_value = [
            ("otro_usuario_id", {"email": "nuevo@example.com"})
        ]

        req = _make_request(body={"email": "nuevo@example.com"})
        response = update_handle(req)
        assert response.status_code == 409

    def test_same_user_email_no_conflict(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "mismo@example.com"}
        # query retorna el mismo userId -> no es conflicto
        mock_firestore_helper.query_documents.return_value = [
            ("user123", {"email": "mismo@example.com"})
        ]

        req = _make_request(body={"email": "mismo@example.com"}, user_id="user123")
        response = update_handle(req)
        assert response.status_code == 200

    def test_duplicate_username_another_user_returns_409(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        # Solo se llama query_documents para username (email no viene en body)
        mock_firestore_helper.query_documents.return_value = [
            ("otro_usuario", {"username": "ocupado"}),
        ]

        req = _make_request(body={"username": "ocupado"})
        response = update_handle(req)
        assert response.status_code == 409

    def test_personal_data_existing_doc_updated(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["pd_existing"]

        req = _make_request(body={"personalData": {"fullName": "Actualizado"}})
        update_handle(req)

        mock_firestore_helper.update_document.assert_called_once()
        call_args = mock_firestore_helper.update_document.call_args[0]
        assert "pd_existing" in call_args


# ============================================================================
# ESCRITURAS EXITOSAS
# ============================================================================


class TestUpdateUserWriteOperations:

    def test_root_fields_update_called_with_correct_data(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle
        from models.firestore_collections import FirestoreCollections

        mock_firestore_helper.get_document.return_value = {"email": "old@example.com"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(body={"email": "nuevo@example.com", "username": "nuevousr"})
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.update_document.assert_called_once()
        call_args = mock_firestore_helper.update_document.call_args[0]
        assert call_args[0] == FirestoreCollections.USERS
        assert call_args[1] == "user123"
        assert call_args[2]["email"] == "nuevo@example.com"
        assert call_args[2]["username"] == "nuevousr"

    def test_emergency_contacts_delete_then_create(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["ec_old1", "ec_old2"]

        contacts = [
            {"fullName": "A", "phone": "+521112223333"},
            {"fullName": "B", "phone": "+524445556666"},
        ]
        req = _make_request(body={"emergencyContacts": contacts})
        response = update_handle(req)

        assert response.status_code == 200
        assert mock_firestore_helper.delete_document.call_count == 2
        assert mock_firestore_helper.create_document.call_count == 2

    def test_vehicle_upsert_update_existing(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},
            {"branch": "Old"},
        ]

        req = _make_request(body={
            "vehicleData": {"id": "v1", "branch": "New", "model": "M", "year": 2020, "color": "C"}
        })
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.update_document.assert_called()

    def test_vehicle_upsert_create_with_id(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},
            None,  # vehiculo no existe
        ]

        req = _make_request(body={
            "vehicleData": {"id": "v_new", "branch": "B", "model": "M", "year": 2020, "color": "C"}
        })
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.create_document_with_id.assert_called()

    def test_vehicle_upsert_create_without_id(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.create_document.return_value = "auto_id"

        req = _make_request(body={"vehicleData": {"branch": "B", "model": "M", "year": 2020, "color": "C"}})
        response = update_handle(req)

        assert response.status_code == 200
        mock_firestore_helper.create_document.assert_called()


# ============================================================================
# AUTENTICACION
# ============================================================================


# 401 Unauthorized lo valida user_route; update.handle no comprueba token.


# ============================================================================
# EXCEPCIONES
# ============================================================================


class TestUpdateUserExceptions:

    def test_value_error_returns_400(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = ValueError("bad")
        req = _make_request(body={"email": "test@example.com"})
        response = update_handle(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = RuntimeError("db down")
        req = _make_request(body={"email": "test@example.com"})
        response = update_handle(req)
        assert response.status_code == 500

    def test_type_error_returns_500(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.side_effect = TypeError("type err")
        req = _make_request(body={"email": "test@example.com"})
        response = update_handle(req)
        assert response.status_code == 500


# ============================================================================
# MULTIPLES LLAMADAS AL MISMO API
# ============================================================================


class TestUpdateUserMultipleCalls:

    def test_multiple_calls_stable(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.query_documents.return_value = []

        for i in range(3):
            mock_firestore_helper.get_document.return_value = {"email": f"old{i}@example.com"}
            req = _make_request(body={"email": f"usuario{i}@example.com"}, user_id=f"user_{i}")
            response = update_handle(req)
            assert response.status_code == 200

    def test_two_different_sections_sequential(
        self,
        mock_firestore_helper,
    ):
        from users.update import handle as update_handle

        mock_firestore_helper.get_document.return_value = {"email": "test@example.com"}
        mock_firestore_helper.list_document_ids.return_value = ["doc1"]

        req1 = _make_request(body={"personalData": {"fullName": "Nombre 1"}})
        res1 = update_handle(req1)
        assert res1.status_code == 200
        assert json.loads(res1.response[0])["updated"] == ["personalData"]

        req2 = _make_request(body={"healthData": {"bloodType": "A+"}})
        res2 = update_handle(req2)
        assert res2.status_code == 200
        assert json.loads(res2.response[0])["updated"] == ["healthData"]
