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


@patch(
    "checklists.checklist_common.get_event_if_owner_or_staff",
    return_value={"creator": "uid-1"},
)
@patch("checklists.create_checklist.FirestoreHelper")
def test_create_checklist_creates_participants_for_assigned_only(
    mock_helper_cls, mock_access
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
    helper.list_document_ids.return_value = ["user-1"]

    body = {
        "eventId": "evt-1",
        "title": "Docs",
        "visibilityMode": "participants",
        "items": [
            {
                "name": "License",
                "description": "",
                "isRequired": True,
                "order": 0,
            }
        ],
        "assignedParticipantIds": ["user-1", "user-2"],
    }

    response = handle_create(_req(body=body), "uid-1")
    assert response.status_code == 201
    assert helper.create_document_with_id.call_count == 2


@patch("checklists.update_checklist.sync_participants_for_assigned_ids")
@patch("checklists.update_checklist.common.persist_template_items")
@patch("checklists.update_checklist.common.delete_all_subcollection_docs")
@patch(
    "checklists.checklist_common.get_event_if_owner_or_staff",
    return_value={"creator": "uid-1"},
)
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
    helper.query_documents.return_value = [("item-1", {"name": "License", "isRequired": True, "order": 0})]

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


@patch(
    "checklists.checklist_common.get_event_if_owner_or_staff",
    return_value={"creator": "uid-1"},
)
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
