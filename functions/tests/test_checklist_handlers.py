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


_ACCESS = patch(
    "checklists.checklist_common.get_event_if_owner_or_staff",
    return_value={"creator": "uid-1"},
)


@_ACCESS
@patch("checklists.create_checklist.FirestoreHelper")
def test_create_checklist_creates_participants_for_assigned_only(mock_helper_cls, mock_access):
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
    helper.list_document_ids.return_value = ["user-1"]

    body = {
        "eventId": "evt-1",
        "title": "Docs",
        "visibilityMode": "participants",
        "items": [{"name": "License", "description": "", "isRequired": True, "order": 0}],
        "assignedParticipantIds": ["user-1", "user-2"],
    }

    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 201
    assert helper.create_document_with_id.call_count == 2


@_ACCESS
def test_create_checklist_invalid_body_returns_400(mock_access):
    from checklists.create_checklist import handle_create

    response = handle_create(_req(body=None), "uid-1")
    assert response.status_code == 400


@_ACCESS
def test_create_checklist_missing_title_returns_400(mock_access):
    from checklists.create_checklist import handle_create

    body = {
        "eventId": "evt-1",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
    }
    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 400


@patch("checklists.checklist_common.get_event_if_owner_or_staff", return_value=None)
def test_create_checklist_no_access_returns_404(mock_access):
    from checklists.create_checklist import handle_create

    body = {
        "eventId": "evt-1",
        "title": "Docs",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
    }
    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 404


@patch("checklists.update_checklist.sync_participants_for_assigned_ids")
@patch("checklists.update_checklist.common.persist_template_items")
@patch("checklists.update_checklist.common.delete_all_subcollection_docs")
@_ACCESS
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_returns_detail(
    mock_helper_cls,
    mock_access,
    mock_delete_subdocs,
    mock_persist_items,
    mock_sync_participants,
):
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {
        "title": "New",
        "visibilityMode": "participants",
        "createdAt": "t1",
        "updatedAt": "t2",
    }
    mock_persist_items.return_value = [
        {"id": "item-1", "name": "License", "isRequired": True, "order": 0}
    ]
    helper.list_document_ids.return_value = ["user-1"]
    helper.query_documents.return_value = [
        ("item-1", {"name": "License", "isRequired": True, "order": 0})
    ]

    body = {
        "eventId": "evt-1",
        "checklistId": "chk-1",
        "title": "New",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
        "assignedParticipantIds": ["user-1"],
    }

    response = handle_update(
        _req(method="PUT", path="/api/events/checklists/update", body=body), "uid-1"
    )
    assert response.status_code == 200
    mock_sync_participants.assert_called_once()


@patch("checklists.update_checklist.sync_participants_for_assigned_ids")
@patch("checklists.update_checklist.common.persist_template_items")
@patch("checklists.update_checklist.common.delete_all_subcollection_docs")
@_ACCESS
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_syncs_participant_add_remove(
    mock_helper_cls,
    mock_access,
    mock_delete_subdocs,
    mock_persist_items,
    mock_sync_participants,
):
    """SPRTMNTRPP-124: PUT add/remove assignedParticipantIds invoca sync."""
    from checklists.update_checklist import handle_update

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "T", "visibilityMode": "participants"}
    mock_persist_items.return_value = [{"id": "item-1", "isRequired": True}]
    helper.list_document_ids.return_value = ["user-1"]
    helper.query_documents.return_value = []

    body = {
        "eventId": "evt-1",
        "id": "chk-1",
        "title": "T",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
        "assignedParticipantIds": ["user-1", "user-2"],
    }
    handle_update(_req(method="PUT", body=body), "uid-1")

    mock_sync_participants.assert_called_once()
    call_kwargs = mock_sync_participants.call_args[0]
    assert call_kwargs[3] == ["user-1", "user-2"]


@_ACCESS
@patch("checklists.update_checklist.FirestoreHelper")
def test_update_checklist_not_found_returns_404(mock_helper_cls, mock_access):
    from checklists.update_checklist import handle_update

    mock_helper_cls.return_value.get_document.return_value = None
    body = {
        "eventId": "evt-1",
        "checklistId": "missing",
        "title": "T",
        "visibilityMode": "participants",
        "items": [{"name": "License", "isRequired": True, "order": 0}],
    }
    response = handle_update(_req(method="PUT", body=body), "uid-1")
    assert response.status_code == 404


@_ACCESS
@patch("checklists.list_checklists.FirestoreHelper")
def test_list_checklists_returns_summaries(mock_helper_cls, mock_access):
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
    assert payload["result"][0]["itemCount"] == 2
    assert payload["result"][0]["assignedCount"] == 1


@_ACCESS
def test_list_checklists_missing_event_id_returns_400(mock_access):
    from checklists.list_checklists import handle_list

    response = handle_list(_req(method="GET", args={}), "uid-1")
    assert response.status_code == 400


@_ACCESS
@patch("checklists.get_checklist.FirestoreHelper")
def test_get_checklist_returns_detail(mock_helper_cls, mock_access):
    from checklists.get_checklist import handle_get

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {
        "title": "Technical",
        "visibilityMode": "participants",
        "createdAt": "t1",
        "updatedAt": "t2",
    }
    helper.query_documents.side_effect = [
        [("item-1", {"name": "License", "isRequired": True, "order": 0})],
        [
            (
                "user-1",
                {"participantName": "Ana Lopez", "pilotNumber": "7"},
            )
        ],
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
    assert payload["assignedParticipantIds"] == [
        {"id": "user-1", "name": "Ana Lopez", "pilotNumber": "7"}
    ]


@_ACCESS
def test_get_checklist_missing_checklist_id_returns_400(mock_access):
    from checklists.get_checklist import handle_get

    response = handle_get(
        _req(method="GET", args={"eventId": "evt-1"}),
        "uid-1",
    )
    assert response.status_code == 400


@_ACCESS
@patch("checklists.get_checklist.FirestoreHelper")
def test_get_checklist_not_found_returns_404(mock_helper_cls, mock_access):
    from checklists.get_checklist import handle_get

    mock_helper_cls.return_value.get_document.return_value = None
    response = handle_get(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "missing"}),
        "uid-1",
    )
    assert response.status_code == 404


@_ACCESS
@patch("checklists.delete_checklist.common.delete_all_subcollection_docs")
@patch("checklists.delete_checklist.FirestoreHelper")
def test_delete_checklist_cascade_removes_items_and_participants(
    mock_helper_cls, mock_delete_subdocs, mock_access
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


@_ACCESS
def test_delete_checklist_missing_checklist_id_returns_400(mock_access):
    from checklists.delete_checklist import handle_delete

    response = handle_delete(
        _req(method="DELETE", args={"eventId": "evt-1"}),
        "uid-1",
    )
    assert response.status_code == 400


@_ACCESS
@patch("checklists.delete_checklist.FirestoreHelper")
def test_delete_checklist_not_found_returns_404(mock_helper_cls, mock_access):
    from checklists.delete_checklist import handle_delete

    mock_helper_cls.return_value.get_document.return_value = None
    response = handle_delete(
        _req(method="DELETE", args={"eventId": "evt-1", "checklistId": "missing"}),
        "uid-1",
    )
    assert response.status_code == 404


@_ACCESS
@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_excludes_optional_items(mock_helper_cls, mock_access):
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
                    "itemProgress": {"item-req": {"check": False, "updateDate": None}},
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
    assert len(payload["result"][0]["items"]) == 1
    assert payload["summary"]["assignedCount"] == 1


@_ACCESS
@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_excludes_unassigned_event_subscriber(
    mock_helper_cls, mock_access
):
    """SPRTMNTRPP-125: suscriptor no asignado no aparece en result."""
    from checklists.get_participant_progress import handle_participant_progress

    helper = mock_helper_cls.return_value
    helper.get_document.return_value = {"title": "Docs"}
    helper.query_documents.side_effect = [
        [("item-1", {"name": "License", "isRequired": True, "order": 0})],
        [
            (
                "assigned-user",
                {
                    "participantName": "Assigned",
                    "itemProgress": {"item-1": {"check": True, "updateDate": "t1"}},
                    "isCompleted": True,
                },
            ),
        ],
    ]

    response = handle_participant_progress(
        _req(
            method="GET",
            args={"eventId": "evt-1", "checklistId": "chk-1"},
        ),
        "uid-1",
    )
    payload = json.loads(response.data)
    participant_ids = [row["participantId"] for row in payload["result"]]
    assert participant_ids == ["assigned-user"]
    assert "unassigned-subscriber" not in participant_ids


@_ACCESS
@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_summary_counts_match_participant_docs(
    mock_helper_cls, mock_access
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


@_ACCESS
@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_pagination_cursor_and_search(mock_helper_cls, mock_access):
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


@_ACCESS
@patch("checklists.get_participant_progress.FirestoreHelper")
def test_participant_progress_checklist_not_found_returns_404(mock_helper_cls, mock_access):
    from checklists.get_participant_progress import handle_participant_progress

    mock_helper_cls.return_value.get_document.return_value = None
    response = handle_participant_progress(
        _req(method="GET", args={"eventId": "evt-1", "checklistId": "missing"}),
        "uid-1",
    )
    assert response.status_code == 404


def test_checklist_common_normalize_and_validate():
    from checklists import checklist_common as common

    assert common.validate_visibility_mode("participants") == "participants"
    assert common.validate_visibility_mode("invalid") is None
    assert common.normalize_assigned_ids([" a ", "", "b"]) == ["a", "b"]
    assert common.normalize_assigned_ids("not-list") == []
    assert common.normalize_items([{"name": "X", "order": 2}])[0]["order"] == 2
    assert common.normalize_items([{"name": ""}]) is None
    assert common.compute_is_completed({}) is True
    assert common.compute_is_completed({"i": {"check": True}}) is True
    assert common.compute_is_completed({"i": {"check": False}}) is False


@patch("checklists.checklist_common.FirestoreHelper")
def test_delete_all_subcollection_docs(mock_helper_cls):
    from checklists.checklist_common import delete_all_subcollection_docs

    helper = mock_helper_cls.return_value
    helper.list_document_ids.return_value = ["doc-1", "doc-2"]
    delete_all_subcollection_docs(helper, "events/evt/checklists/chk/items")
    assert helper.delete_document.call_count == 2


@patch("utils.event_owner_helper.FirestoreHelper")
def test_get_event_if_owner_or_staff_allows_staff(mock_helper_cls):
    from utils.event_owner_helper import get_event_if_owner_or_staff

    helper = mock_helper_cls.return_value
    helper.get_document.side_effect = [
        None,
        {"role": "staff"},
        {"creator": "owner-1", "name": "Rally"},
    ]

    event = get_event_if_owner_or_staff("evt-1", "staff-1")
    assert event is not None
    assert event["name"] == "Rally"
