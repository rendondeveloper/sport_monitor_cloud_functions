import json
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _req(method="POST", path="/api/events/checklists/create", args=None, body=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.args = dict(args) if args else {}
    req.headers = {"Authorization": "Bearer token"}
    req.get_json = lambda silent=True: body
    return req



@patch("checklists.create_checklist.sync_all_event_participants")
@patch("checklists.create_checklist.FirestoreHelper")
def test_create_checklist_syncs_all_event_participants(
    mock_helper_cls, mock_sync
):
    from checklists.create_checklist import handle_create

    helper = mock_helper_cls.return_value
    helper.create_document.return_value = "chk-1"
    helper.get_document.return_value = {
        "title": "Docs",
        "visibilityMode": "participants",
        "createdAt": "t1",
        "updatedAt": "t1",
    }
    helper.new_document_id.return_value = "item-1"
    helper.batch_set.return_value = ["item-1"]

    body = {
        "eventId": "evt-1",
        "title": "Docs",
        "visibilityMode": "participants",
        "items": [{"name": "License", "description": "", "isRequired": True, "order": 0}],
    }

    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 201
    mock_sync.assert_called_once()


def test_create_checklist_rejects_assigned_participant_ids():
    from checklists.create_checklist import handle_create

    body = {
        "eventId": "evt-1",
        "title": "Docs",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
        "assignedParticipantIds": ["user-1"],
    }
    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 400


def test_create_checklist_invalid_body_returns_400():
    from checklists.create_checklist import handle_create

    response = handle_create(_req(body=None), "uid-1")
    assert response.status_code == 400


def test_create_checklist_missing_title_returns_400():
    from checklists.create_checklist import handle_create

    body = {
        "eventId": "evt-1",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
    }
    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_patch_lat_long_no_sync(mock_helper_cls, mock_sync):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        if path.endswith("/items") and doc_id == "item-1":
            return {"name": "License", "latitude": 0.0, "longitude": 0.0, "order": 0}
        return None

    helper.get_document.side_effect = _get_document
    helper.query_documents.return_value = [
        ("item-1", {"name": "License", "latitude": 19.0, "longitude": -99.0, "order": 0})
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "item-1", "latitude": 19.0, "longitude": -99.0}],
    }

    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_not_called()

    item_update = helper.update_document.call_args
    assert item_update[0][0].endswith("/items")
    assert item_update[0][1] == "item-1"
    assert item_update[0][2]["latitude"] == 19.0
    assert item_update[0][2]["longitude"] == -99.0
    assert "name" not in item_update[0][2]


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_patch_title_only(mock_helper_cls, mock_sync):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {
        "title": "New title",
        "visibilityMode": "participants",
        "createdAt": "t1",
        "updatedAt": "t2",
    }
    helper.query_documents.return_value = [
        ("item-1", {"name": "License", "isRequired": True, "order": 0})
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "title": "New title",
    }

    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_not_called()
    helper.update_document.assert_called_once()
    update_payload = helper.update_document.call_args[0][2]
    assert update_payload["title"] == "New title"
    assert "visibilityMode" not in update_payload
    payload = json.loads(response.data)
    assert payload["eventId"] == "evt-1"
    assert payload["checklistId"] == "chk-1"
    assert payload["items"] == [{"id": "item-1"}]


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_patch_is_required_triggers_sync(mock_helper_cls, mock_sync):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        if path.endswith("/items") and doc_id == "item-1":
            return {"name": "License", "isRequired": False, "order": 0}
        return None

    helper.get_document.side_effect = _get_document
    helper.query_documents.return_value = [
        ("item-1", {"name": "License", "isRequired": True, "order": 0})
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "item-1", "isRequired": True}],
    }

    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_called_once()


def test_update_checklist_items_without_id_returns_400():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"name": "License", "isRequired": True}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


def test_update_checklist_client_item_invalid_required_and_participant_ids_returns_400():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "client-1", "isRequired": True, "participantIds": ["user-1"]}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_client_item_create_then_update_stable(mock_helper_cls):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    state = {"client_exists": False}

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        if path.endswith("/items") and doc_id == "client-1":
            return {"name": "First", "order": 0} if state["client_exists"] else None
        return None

    helper.get_document.side_effect = _get_document
    helper.query_documents.return_value = [("item-1", {"name": "Second", "order": 0})]
    helper.create_document.return_value = "item-1"

    body_create = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "client-1", "name": "First"}],
    }
    response1 = handle_update(_req(method="PUT", body=body_create), "uid-1")
    assert response1.status_code == 200
    helper.create_document.assert_called_once()
    create_args = helper.create_document.call_args[0]
    assert create_args[0].endswith("/items")
    assert create_args[1]["name"] == "First"

    state["client_exists"] = True
    helper.reset_mock()

    body_update = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "client-1", "name": "Second"}],
    }
    response2 = handle_update(_req(method="PUT", body=body_update), "uid-1")
    assert response2.status_code == 200
    helper.update_document.assert_called_once()
    args = helper.update_document.call_args[0]
    assert args[0].endswith("/items")
    assert args[1] == "client-1"
    assert args[2]["name"] == "Second"


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_mixed_real_and_client_id_items(
    mock_helper_cls, mock_sync
):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        if path.endswith("/items") and doc_id == "item-1":
            return {"name": "License", "latitude": 0.0, "longitude": 0.0, "order": 0}
        return None

    helper.get_document.side_effect = _get_document
    helper.query_documents.return_value = [
        ("item-1", {"name": "License", "latitude": 19.0, "longitude": -99.0, "order": 0})
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [
            {"id": "item-1", "latitude": 19.0, "longitude": -99.0},
            {"id": "client-1234567890", "name": "Local draft", "isRequired": True},
        ],
    }

    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_called_once()
    assert helper.update_document.call_count == 1
    assert helper.create_document.call_count == 1

    update_args = helper.update_document.call_args[0]
    assert update_args[0].endswith("/items")
    assert update_args[1] == "item-1"
    assert update_args[2]["latitude"] == 19.0

    create_args = helper.create_document.call_args[0]
    assert create_args[0].endswith("/items")
    assert create_args[1]["name"] == "Local draft"
    assert create_args[1]["isRequired"] is True


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_mixed_real_and_no_id_items(mock_helper_cls, mock_sync):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        if path.endswith("/items") and doc_id == "item-1":
            return {"name": "License", "order": 0}
        return None

    helper.get_document.side_effect = _get_document
    helper.query_documents.return_value = [
        ("item-1", {"name": "Updated", "order": 0})
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [
            {"id": "item-1", "name": "Updated"},
            {"name": "Ignored local", "order": 99},
        ],
    }

    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_not_called()
    helper.update_document.assert_called_once()
    call_args = helper.update_document.call_args[0]
    assert call_args[0].endswith("/items")
    assert call_args[1] == "item-1"
    assert call_args[2]["name"] == "Updated"


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_item_not_found_returns_404(mock_helper_cls):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        return None

    helper.get_document.side_effect = _get_document

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "missing", "latitude": 1.0}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 404


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_multiple_patch_calls_stable(mock_helper_cls, mock_sync):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {
        "title": "First",
        "visibilityMode": "participants",
        "createdAt": "t1",
        "updatedAt": "t1",
    }
    helper.query_documents.return_value = []

    for title in ("First", "Second"):
        body = {
            "eventId": "evt-1",
            "checklistId": "chk-1",
            "title": title,
        }
        helper.get_document.return_value = {
            "title": title,
            "visibilityMode": "participants",
            "createdAt": "t1",
            "updatedAt": "t1",
        }
        response = handle_update(_req(method="PUT", body=body), "uid-1")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload["eventId"] == "evt-1"
        assert payload["checklistId"] == "chk-1"

    assert mock_sync.call_count == 0
    assert helper.update_document.call_count == 2


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_client_item_creates_autogen_id_and_response_has_real_id(
    mock_helper_cls,
):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        return None

    helper.get_document.side_effect = _get_document
    helper.create_document.return_value = "item-new"
    helper.query_documents.return_value = [("item-new", {"name": "Draft", "order": 0})]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "client-abc", "name": "Draft"}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    helper.create_document.assert_called_once()
    helper.create_document_with_id.assert_not_called()

    payload = json.loads(response.data)
    assert payload["items"] == [{"id": "item-new"}]
    assert payload["items"] != [{"id": "client-abc"}]


def test_update_checklist_client_item_missing_name_returns_400():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "client-1"}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


def test_update_checklist_rejects_assigned_participant_ids():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "title": "T",
        "assignedParticipantIds": ["user-1"],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_participants_mixed_no_id_and_valid_id(
    mock_helper_cls, mock_sync
):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        if path.endswith("/participants") and doc_id == "user-1":
            return {"participantName": "Old", "pilotNumber": "10"}
        return None

    helper.get_document.side_effect = _get_document
    helper.query_documents.return_value = []

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "participants": [
            {"participantName": "Ignored"},
            {"id": "user-1", "participantName": "Ana"},
        ],
    }

    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_not_called()
    helper.update_document.assert_called_once()
    call_args = helper.update_document.call_args[0]
    assert call_args[0].endswith("/participants")
    assert call_args[1] == "user-1"
    assert call_args[2]["participantName"] == "Ana"
    assert "updatedAt" in call_args[2]


def test_update_checklist_participants_forbidden_field_returns_400():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "participants": [{"id": "user-1", "isCompleted": True}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_participants_id_not_found_returns_404(mock_helper_cls):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        return None

    helper.get_document.side_effect = _get_document

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "participants": [{"id": "missing-user", "participantName": "Ana"}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 404


def test_update_checklist_participants_not_list_returns_400():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "participants": {"id": "user-1", "participantName": "Ana"},
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


def test_update_checklist_participants_only_no_id_entries_returns_400():
    from checklists.update_checklist import handle_update

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "participants": [{"participantName": "Ignored"}, {"email": "a@test.com"}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_not_found_returns_404(mock_helper_cls):
    from checklists.update_checklist import handle_update

    mock_helper_cls.return_value.get_document.return_value = None
    body = {
        "eventId": "evt-1",
        "checklistId": "missing",
        "title": "T",
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 404


@patch("checklists.list_checklists.FirestoreHelper")
def test_list_checklists_returns_summaries(mock_helper_cls):
    from checklists.list_checklists import handle_list

    helper = mock_helper_cls.return_value
    helper.query_documents.return_value = [
        ("chk-1", {"title": "Technical", "visibilityMode": "participants", "createdAt": "t1"})
    ]
    helper.list_document_ids.side_effect = [["item-1", "item-2"], ["user-a"]]

    response = handle_list(
        _req(method="GET", path="/api/events/checklists/list", args={"eventId": "evt-1"}),
        "uid-1",
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert isinstance(payload, list)
    assert payload[0]["itemCount"] == 2
    assert payload[0]["assignedCount"] == 1


def test_list_checklists_missing_event_id_returns_400():
    from checklists.list_checklists import handle_list

    response = handle_list(_req(method="GET", args={}), "uid-1")
    assert response.status_code == 400


@patch("checklists.get_checklist.FirestoreHelper")
def test_get_checklist_returns_detail(mock_helper_cls):
    from checklists.get_checklist import handle_get

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {
        "title": "Technical",
        "description": "Cover text",
        "photoUrl": "https://example.com/cover.jpg",
        "visibilityMode": "participants",
        "createdAt": "t1",
        "updatedAt": "t2",
    }
    helper.query_documents.return_value = [
        (
            "item-1",
            {
                "name": "License",
                "isRequired": True,
                "participantIds": [],
                "order": 0,
            },
        ),
    ]

    response = handle_get(
        _req(
            method="GET",
            path="/api/events/checklists/get",
            args={"eventId": "evt-1", "checklistId": "chk-1"},
        ),
        "uid-1",
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["id"] == "chk-1"
    assert payload["description"] == "Cover text"
    assert payload["photoUrl"] == "https://example.com/cover.jpg"
    assert "assignedParticipantIds" not in payload
    assert payload["items"][0]["participantIds"] == []


def test_get_checklist_missing_checklist_id_returns_400():
    from checklists.get_checklist import handle_get

    response = handle_get(
        _req(method="GET", args={"eventId": "evt-1"}),
        "uid-1",
    )
    assert response.status_code == 400


@patch("checklists.get_checklist.FirestoreHelper")
def test_get_checklist_not_found_returns_404(mock_helper_cls):
    from checklists.get_checklist import handle_get

    mock_helper_cls.return_value.get_document.return_value = None
    response = handle_get(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "missing"}),
        "uid-1",
    )
    assert response.status_code == 404


@patch("checklists.delete_checklist.common.delete_all_subcollection_docs")
@patch("checklists.delete_checklist.FirestoreHelper")
def test_delete_checklist_cascade_removes_items_and_participants(
    mock_helper_cls, mock_delete_subdocs
):
    """SPRTMNTRPP-124: DELETE cascade elimina items y participants."""
    from checklists.delete_checklist import handle_delete

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Technical"}
    helper.list_document_ids.side_effect = [["item-1", "item-2"], ["user-1", "user-2"]]

    response = handle_delete(
        _req(
            method="DELETE",
            path="/api/events/checklists/delete",
            args={"eventId": "evt-1", "checklistId": "chk-1"},
        ),
        "uid-1",
    )
    assert response.status_code == 204
    assert mock_delete_subdocs.call_count == 2
    helper.delete_document.assert_called_once()


def test_delete_checklist_missing_checklist_id_returns_400():
    from checklists.delete_checklist import handle_delete

    response = handle_delete(
        _req(method="DELETE", args={"eventId": "evt-1"}),
        "uid-1",
    )
    assert response.status_code == 400


@patch("checklists.delete_checklist.FirestoreHelper")
def test_delete_checklist_not_found_returns_404(mock_helper_cls):
    from checklists.delete_checklist import handle_delete

    mock_helper_cls.return_value.get_document.return_value = None
    response = handle_delete(
        _req(method="DELETE", args={"eventId": "evt-1", "checklistId": "missing"}),
        "uid-1",
    )
    assert response.status_code == 404


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_includes_optional_items_with_is_required(mock_helper_cls):
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}

    def _query_side_effect(collection_path, *args, **kwargs):
        if collection_path.endswith("/items"):
            return [
                ("item-req", {"name": "License", "isRequired": True, "order": 0}),
                ("item-opt", {"name": "Photo", "isRequired": False, "order": 1}),
            ]
        return [
            (
                "user-1",
                {
                    "participantName": "Ana",
                    "pilotNumber": "7",
                    "itemProgress": {
                        "item-req": {"check": False, "updateDate": None},
                        "item-opt": {"check": False, "updateDate": None},
                    },
                    "isCompleted": False,
                },
            ),
        ]

    helper.query_documents.side_effect = _query_side_effect

    response = handle_participant_progress(
        _req(
            method="GET",
            path="/api/events/checklists/participant-progress",
            args={"eventId": "evt-1", "checklistId": "chk-1"},
        ),
        "uid-1",
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    items = payload["result"][0]["items"]
    assert {item["itemId"] for item in items} == {"item-req", "item-opt"}
    required_by_id = {item["itemId"]: item["isRequired"] for item in items}
    assert required_by_id["item-req"] is True
    assert required_by_id["item-opt"] is False
    assert payload["summary"]["assignedCount"] == 1


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_targeted_item_only_for_listed_pilot(
    mock_helper_cls
):
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}

    def _query_side_effect(collection_path, *args, **kwargs):
        if collection_path.endswith("/items"):
            return [
                ("item-global", {"name": "Global", "isRequired": True, "order": 0}),
                (
                    "item-target",
                    {
                        "name": "Target",
                        "isRequired": False,
                        "participantIds": ["user-a"],
                        "order": 1,
                    },
                ),
                (
                    "item-opt",
                    {
                        "name": "Optional all",
                        "isRequired": False,
                        "participantIds": ["user-a"],
                        "order": 2,
                    },
                ),
            ]
        return [
            (
                "user-a",
                {
                    "participantName": "Ana",
                    "itemProgress": {
                        "item-global": {"check": False, "updateDate": None},
                        "item-target": {"check": False, "updateDate": None},
                        "item-opt": {"check": True, "updateDate": "t2"},
                    },
                    "isCompleted": False,
                },
            ),
            (
                "user-b",
                {
                    "participantName": "Bob",
                    "itemProgress": {
                        "item-global": {"check": True, "updateDate": "t1"},
                        "item-opt": {"check": False, "updateDate": None},
                    },
                    "isCompleted": True,
                },
            ),
        ]

    helper.query_documents.side_effect = _query_side_effect

    response = handle_participant_progress(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "chk-1"}),
        "uid-1",
    )
    payload = json.loads(response.data)
    rows = {row["participantId"]: row for row in payload["result"]}
    assert {item["itemId"] for item in rows["user-a"]["items"]} == {
        "item-global",
        "item-target",
        "item-opt",
    }
    # item-target es opcional (isRequired=False) y debe mostrarse para TODOS,
    # aunque venga con participantIds.
    assert {item["itemId"] for item in rows["user-b"]["items"]} == {
        "item-global",
        "item-target",
        "item-opt",
    }
    items_b = {item["itemId"]: item for item in rows["user-b"]["items"]}
    assert items_b["item-target"]["check"] is False
    assert items_b["item-target"]["updateDate"] is None


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_targeted_optional_item_sets_is_required_true_only_for_target_participant(
    mock_helper_cls,
):
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}

    def _query_side_effect(collection_path, *args, **kwargs):
        if collection_path.endswith("/items"):
            return [
                (
                    "item-target",
                    {
                        "name": "X",
                        "isRequired": False,
                        "participantIds": ["user-a"],
                        "order": 0,
                    },
                )
            ]
        return [
            ("user-a", {"participantName": "A", "pilotNumber": "1", "itemProgress": {}}),
            ("user-b", {"participantName": "B", "pilotNumber": "2", "itemProgress": {}}),
        ]

    helper.query_documents.side_effect = _query_side_effect

    response = handle_participant_progress(
        _req(
            method="GET",
            path="/api/events/checklists/participant-progress",
            args={"eventId": "evt-1", "checklistId": "chk-1"},
        ),
        user_id="staff",
    )
    assert response.status_code == 200
    payload = json.loads(response.data)

    assert len(payload["result"]) == 2
    rows = {row["participantId"]: row for row in payload["result"]}

    items_a = {item["itemId"]: item for item in rows["user-a"]["items"]}
    items_b = {item["itemId"]: item for item in rows["user-b"]["items"]}

    assert items_a["item-target"]["isRequired"] is True
    assert items_b["item-target"]["isRequired"] is False


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_summary_counts_match_participant_docs(
    mock_helper_cls
):
    """SPRTMNTRPP-125: summary completedCount/incompleteCount vs docs."""
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}
    helper.query_documents.side_effect = [
        [("item-1", {"name": "License", "isRequired": True, "order": 0})],
        [
            ("u1", {"participantName": "A", "itemProgress": {}, "isCompleted": True}),
            ("u2", {"participantName": "B", "itemProgress": {}, "isCompleted": False}),
            ("u3", {"participantName": "C", "itemProgress": {}, "isCompleted": True}),
        ],
    ]

    response = handle_participant_progress(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "chk-1"}),
        "uid-1",
    )
    summary = json.loads(response.data)["summary"]
    assert summary["assignedCount"] == 3
    assert summary["completedCount"] == 2
    assert summary["incompleteCount"] == 1


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_pagination_cursor_and_search(mock_helper_cls):
    """SPRTMNTRPP-125: paginación cursor + filtro search."""
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}
    def _query_side_effect(collection_path, *args, **kwargs):
        if collection_path.endswith("/items"):
            return [("item-1", {"name": "License", "isRequired": True, "order": 0})]
        return [
            ("user-a", {"participantName": "Alice", "email": "a@test.com", "isCompleted": False}),
            ("user-b", {"participantName": "Bob", "email": "b@test.com", "isCompleted": False}),
            ("user-c", {"participantName": "Carlos", "email": "c@test.com", "isCompleted": True}),
        ]

    helper.query_documents.side_effect = _query_side_effect

    search_response = handle_participant_progress(
        _req(
            method="GET",
            args={"eventId": "evt-1", "checklistId": "chk-1", "search": "bob"},
        ),
        "uid-1",
    )
    search_payload = json.loads(search_response.data)
    assert len(search_payload["result"]) == 1
    assert search_payload["result"][0]["participantId"] == "user-b"

    page_response = handle_participant_progress(
        _req(
            method="GET",
            args={
                "eventId": "evt-1",
                "checklistId": "chk-1",
                "limit": "1",
                "cursor": "user-a",
            },
        ),
        "uid-1",
    )
    page_payload = json.loads(page_response.data)
    assert len(page_payload["result"]) == 1
    assert page_payload["result"][0]["participantId"] == "user-b"
    assert page_payload["pagination"]["hasMore"] is True
    assert page_payload["pagination"]["lastDocId"] == "user-b"


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_checklist_not_found_returns_404(mock_helper_cls):
    from checklists.get_participant_progress import handle_participant_progress

    mock_helper_cls.return_value.get_document.return_value = None
    response = handle_participant_progress(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "missing"}),
        "uid-1",
    )
    assert response.status_code == 404


def test_checklist_common_normalize_checklist_fields():
    from checklists import checklist_common as common

    fields = common.normalize_checklist_fields(
        {"description": "  Info  ", "photoUrl": "https://example.com/a.jpg"}
    )
    assert fields["description"] == "Info"
    assert fields["photoUrl"] == "https://example.com/a.jpg"

    empty = common.normalize_checklist_fields({})
    assert empty["description"] == ""
    assert empty["photoUrl"] is None


@patch("checklists.update_checklist_photos.FirestoreHelper")
def test_update_photos_event_photo_url_only(mock_helper_cls):
    from checklists.update_checklist_photos import handle_update_photos

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"name": "Rally"}

    body = {
        "eventId": "evt-1",
        "photoUrl": "https://example.com/event-cover.jpg",
    }
    response = handle_update_photos(
        _req(method="PUT", path="/api/events/checklists/update-photos", body=body),
        "uid-1",
    )
    assert response.status_code == 200
    assert response.data == b""
    helper.update_document.assert_called_once_with(
        "events",
        "evt-1",
        {
            "photoUrl": "https://example.com/event-cover.jpg",
            "updatedAt": helper.update_document.call_args[0][2]["updatedAt"],
        },
    )


@patch("checklists.update_checklist_photos.common.build_checklist_detail")
@patch("checklists.update_checklist_photos.FirestoreHelper")
def test_update_photos_items_by_id(mock_helper_cls, mock_build_detail):
    from checklists.update_checklist_photos import handle_update_photos

    helper = mock_helper_cls.return_value
    mock_build_detail.return_value = {"id": "chk-1", "eventId": "evt-1", "items": []}

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs"}
        if path.endswith("/items") and doc_id in ("item-1", "item-2"):
            return {"name": "License"}
        return None

    helper.get_document.side_effect = _get_document

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [
            {"id": "item-1", "photoUrl": "https://example.com/item.jpg"},
            {"id": "item-2", "photoUrl": None},
        ],
    }
    response = handle_update_photos(
        _req(method="PUT", path="/api/events/checklists/update-photos", body=body),
        "uid-1",
    )
    assert response.status_code == 200
    assert helper.update_document.call_count == 2
    assert json.loads(response.data)["id"] == "chk-1"


@patch("checklists.update_checklist_photos.common.build_checklist_detail")
@patch("checklists.update_checklist_photos.FirestoreHelper")
def test_update_photos_checklist_cover_with_checklist_id(mock_helper_cls, mock_build_detail):
    from checklists.update_checklist_photos import handle_update_photos

    helper = mock_helper_cls.return_value
    mock_build_detail.return_value = {"id": "chk-1", "photoUrl": "https://example.com/cover.jpg"}

    def _get_document(path, doc_id):
        if path.endswith("/checklists") and doc_id == "chk-1":
            return {"title": "Docs", "visibilityMode": "participants"}
        return None

    helper.get_document.side_effect = _get_document

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "photoUrl": "https://example.com/cover.jpg",
        "items": [{"id": "item-1", "photoUrl": "https://example.com/item.jpg"}],
    }

    def _get_for_items(path, doc_id):
        if path.endswith("/items"):
            return {"name": "Task"}
        return _get_document(path, doc_id)

    helper.get_document.side_effect = _get_for_items

    response = handle_update_photos(
        _req(method="PUT", path="/api/events/checklists/update-photos", body=body),
        "uid-1",
    )
    assert response.status_code == 200
    cover_update = helper.update_document.call_args_list[0]
    assert cover_update[0][0].endswith("/checklists")
    assert cover_update[0][1] == "chk-1"
    assert cover_update[0][2]["photoUrl"] == "https://example.com/cover.jpg"


@patch("checklists.update_checklist_photos.FirestoreHelper")
def test_update_photos_item_not_found_returns_404(mock_helper_cls):
    from checklists.update_checklist_photos import handle_update_photos

    helper = mock_helper_cls.return_value
    helper.get_document.side_effect = [
        {"title": "Docs"},
        None,
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "missing", "photoUrl": "https://example.com/x.jpg"}],
    }
    response = handle_update_photos(
        _req(method="PUT", path="/api/events/checklists/update-photos", body=body),
        "uid-1",
    )
    assert response.status_code == 404


def test_update_photos_invalid_body_returns_400():
    from checklists.update_checklist_photos import handle_update_photos

    assert (
        handle_update_photos(
            _req(method="PUT", path="/api/events/checklists/update-photos", body=None),
            "uid-1",
        ).status_code
        == 400
    )
    assert (
        handle_update_photos(
            _req(
                method="PUT",
                path="/api/events/checklists/update-photos",
                body={"eventId": "evt-1"},
            ),
            "uid-1",
        ).status_code
        == 400
    )
    assert (
        handle_update_photos(
            _req(
                method="PUT",
                path="/api/events/checklists/update-photos",
                body={
                    "eventId": "evt-1",
                    "items": [{"id": "item-1"}],
                },
            ),
            "uid-1",
        ).status_code
        == 400
    )


@patch("checklists.update_checklist_photos.FirestoreHelper")
def test_update_photos_multiple_calls_stable(mock_helper_cls):
    from checklists.update_checklist_photos import handle_update_photos

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"name": "Rally"}
    body = {"eventId": "evt-1", "photoUrl": None}

    for _ in range(2):
        response = handle_update_photos(
            _req(method="PUT", path="/api/events/checklists/update-photos", body=body),
            "uid-1",
        )
        assert response.status_code == 200


@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_includes_item_photo_url(mock_helper_cls):
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}

    def _query_side_effect(collection_path, *args, **kwargs):
        if collection_path.endswith("/items"):
            return [
                (
                    "item-req",
                    {
                        "name": "License",
                        "isRequired": True,
                        "photoUrl": "https://example.com/license.jpg",
                        "order": 0,
                    },
                ),
            ]
        return [
            (
                "user-1",
                {
                    "participantName": "Ana",
                    "itemProgress": {"item-req": {"check": False, "updateDate": None}},
                    "isCompleted": False,
                },
            ),
        ]

    helper.query_documents.side_effect = _query_side_effect

    response = handle_participant_progress(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "chk-1"}),
        "uid-1",
    )
    item = json.loads(response.data)["result"][0]["items"][0]
    assert item["photoUrl"] == "https://example.com/license.jpg"


def test_checklist_common_normalize_and_validate():
    from checklists import checklist_common as common

    assert common.validate_visibility_mode("participants") == "participants"
    assert common.validate_visibility_mode("invalid") is None
    assert common.normalize_participant_ids([" a ", "", "b"]) == ["a", "b"]
    normalized = common.normalize_items(
        [
            {
                "name": "X",
                "order": 2,
                "participantIds": ["u1"],
                "photoUrl": "  https://example.com/p.jpg  ",
            }
        ]
    )
    assert normalized[0]["order"] == 2
    assert normalized[0]["photoUrl"] == "https://example.com/p.jpg"
    assert normalized[0]["participantIds"] == ["u1"]
    assert common.normalize_items([{"name": ""}]) is None
    assert common.normalize_items(
        [{"name": "Bad", "isRequired": True, "participantIds": ["u1"]}]
    ) is None
    assert common.compute_is_completed({}) is True
    assert common.compute_is_completed({"i": {"check": True}}) is True
    assert common.compute_is_completed({"i": {"check": False}}) is False


def test_checklist_common_patch_helpers():
    from checklists import checklist_common as common

    assert common.has_updatable_fields({"title": "T"}, []) is True
    assert common.has_updatable_fields({"eventId": "e"}, []) is False
    assert common.has_updatable_fields(
        {"eventId": "e"},
        [{"id": "i1", "latitude": 1.0}],
    )

    patches = common.parse_item_patches(
        [{"id": "item-1", "latitude": 1.0, "longitude": 2.0}]
    )
    assert patches == [{"id": "item-1", "latitude": 1.0, "longitude": 2.0}]
    assert common.parse_item_patches([{"name": "X"}]) == []
    assert common.parse_item_patches(
        [{"id": "client-1", "name": "Local"}, {"name": "No id"}]
    ) == [{"id": "client-1", "name": "Local"}]
    assert common.parse_item_patches([{"id": "a"}, {"id": "a"}]) is None
    assert common.parse_item_patches(
        [{"id": "client-1"}, {"id": "client-1"}]
    ) is None
    assert common.item_patch_affects_participants({"id": "i", "isRequired": True})
    assert not common.item_patch_affects_participants({"id": "i", "latitude": 1.0})
    assert common.item_patch_affects_participants({"id": "client-1", "isRequired": True})

    checklist_patch = common.build_checklist_patch({"title": "New"}, "now")
    assert checklist_patch == {"title": "New", "updatedAt": "now"}
    assert common.build_checklist_patch({"title": ""}, "now") is None
    assert common.build_checklist_patch({}, "now") == {}

    item_payload = common.build_item_patch_payload(
        {"id": "i1", "name": "Task", "order": 3},
        "now",
    )
    assert item_payload == {"name": "Task", "order": 3, "updatedAt": "now"}

    assert common.parse_item_patches([{"id": "i1", "name": ""}]) is None
    assert common.parse_item_patches(
        [{"id": "i1", "isRequired": True, "participantIds": ["u1"]}]
    ) is None
    assert common.parse_item_patches([{"id": "i1", "order": "x"}]) is None
    assert common.parse_item_patches("bad") is None
    assert common.parse_item_patches([None]) is None

    desc_patch = common.build_checklist_patch(
        {"description": "  note ", "photoUrl": None},
        "now",
    )
    assert desc_patch["description"] == "note"
    assert desc_patch["photoUrl"] is None
    assert common.build_checklist_patch({"visibilityMode": "nope"}, "now") is None


def test_update_checklist_no_updatable_fields_returns_400():
    from checklists.update_checklist import handle_update

    body = {"eventId": "evt-1", "checklistId": "chk-1"}
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_invalid_participant_ids_returns_400(mock_helper_cls):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    helper.get_document.side_effect = lambda path, doc_id: (
        {"title": "Docs"} if path.endswith("/checklists") else None
    )

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "items": [{"id": "item-1", "participantIds": ["missing-user"]}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.update_checklist.sync_all_event_participants")
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_visibility_mode_triggers_sync(mock_helper_cls, mock_sync):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {
        "title": "Docs",
        "visibilityMode": "eventDates",
    }
    helper.query_documents.return_value = []

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "visibilityMode": "eventDates",
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 200
    mock_sync.assert_called_once()


def test_update_checklist_invalid_body_and_ids_return_400():
    from checklists.update_checklist import handle_update

    assert handle_update(_req(method="PUT", body=None), "uid-1").status_code == 400
    assert (
        handle_update(
            _req(method="PUT", body={"eventId": "evt-1", "title": "T"}),
            "uid-1",
        ).status_code
        == 400
    )
    assert (
        handle_update(
            _req(
                method="PUT",
                body={"eventId": "evt-1", "checklistId": "chk-1", "visibilityMode": "bad"},
            ),
            "uid-1",
        ).status_code
        == 400
    )


@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_internal_error_returns_500(mock_helper_cls):
    from checklists.update_checklist import handle_update

    mock_helper_cls.return_value.get_document.side_effect = RuntimeError("boom")
    body = {"eventId": "evt-1", "checklistId": "chk-1", "title": "T"}
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 500


def test_checklist_common_item_rules_for_pilot():
    from checklists import checklist_common as common

    optional = {"id": "opt", "isRequired": False, "participantIds": []}
    global_req = {"id": "glob", "isRequired": True, "participantIds": []}
    targeted = {"id": "tgt", "isRequired": False, "participantIds": ["ana"]}

    assert common.item_is_visible_for_pilot(optional, "bob") is True
    assert common.item_is_mandatory_for_pilot(optional, "bob") is False
    assert common.item_is_mandatory_for_pilot(global_req, "bob") is True
    assert common.item_is_visible_for_pilot(targeted, "ana") is True
    # Items opcionales son visibles para todos aunque tengan participantIds.
    assert common.item_is_visible_for_pilot(targeted, "bob") is True
    assert common.item_is_mandatory_for_pilot(targeted, "ana") is False

    items = [optional, global_req, targeted]
    assert common.mandatory_item_ids_for_pilot(items, "bob") == ["glob"]
    assert common.mandatory_item_ids_for_pilot(items, "ana") == ["glob"]

    shown = common.items_for_participant_progress(items, "ana")
    assert [item["id"] for item in shown] == ["opt", "glob", "tgt"]


@patch("checklists.checklist_common.FirestoreHelper")
def test_delete_all_subcollection_docs(mock_helper_cls):
    from checklists.checklist_common import delete_all_subcollection_docs

    helper = mock_helper_cls.return_value
    helper.list_document_ids.return_value = ["doc-1", "doc-2"]
    delete_all_subcollection_docs(helper, "events/evt/checklists/chk/items")
    assert helper.delete_document.call_count == 2


