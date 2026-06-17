import sys
from unittest.mock import MagicMock

sys.path.insert(0, ".")


def test_delete_participant_event_subcollections_deletes_ec_and_vehicle():
    from competitors.competitor_participant_cleanup import (
        delete_participant_event_subcollections,
    )
    from models.firestore_collections import FirestoreCollections

    helper = MagicMock()
    helper.list_document_ids.side_effect = [["ec-1", "ec-2"], ["veh-1"]]

    delete_participant_event_subcollections(helper, "user-1", "event-1", "[test]")

    assert helper.list_document_ids.call_count == 2
    ec_path = (
        f"{FirestoreCollections.EVENTS}/event-1"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}/user-1"
        f"/{FirestoreCollections.PARTICIPANT_EMERGENCY_CONTACTS}"
    )
    vehicle_path = (
        f"{FirestoreCollections.EVENTS}/event-1"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}/user-1"
        f"/{FirestoreCollections.PARTICIPANT_VEHICLE}"
    )
    helper.list_document_ids.assert_any_call(ec_path)
    helper.list_document_ids.assert_any_call(vehicle_path)

    delete_calls = [call.args for call in helper.delete_document.call_args_list]
    assert (ec_path, "ec-1") in delete_calls
    assert (ec_path, "ec-2") in delete_calls
    assert (vehicle_path, "veh-1") in delete_calls


def test_delete_participant_event_subcollections_continues_when_list_fails():
    from competitors.competitor_participant_cleanup import (
        delete_participant_event_subcollections,
    )

    helper = MagicMock()
    helper.list_document_ids.side_effect = [RuntimeError("no ec"), ["veh-1"]]

    delete_participant_event_subcollections(helper, "user-1", "event-1", "[test]")

    assert helper.list_document_ids.call_count == 2
    assert helper.delete_document.call_count == 1


def test_delete_competitor_resources_deletes_subcollections_before_participant():
    from competitors.delete_competitor import delete_competitor_resources
    from models.firestore_collections import FirestoreCollections

    helper = MagicMock()
    helper.list_document_ids.side_effect = [[], []]

    delete_competitor_resources(helper, "user-1", "event-1")

    participant_path = (
        f"{FirestoreCollections.EVENTS}/event-1"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )
    membership_path = (
        f"{FirestoreCollections.USERS}/user-1"
        f"/{FirestoreCollections.USER_MEMBERSHIP}"
    )

    assert helper.list_document_ids.call_count == 2
    helper.delete_document.assert_any_call(participant_path, "user-1")
    helper.delete_document.assert_any_call(membership_path, "event-1")


def test_delete_competitor_user_resources_deletes_participant_subcollections_first():
    from competitors.delete_competitor_user import delete_competitor_user_resources
    from models.firestore_collections import FirestoreCollections

    helper = MagicMock()
    helper.list_document_ids.side_effect = [[], [], [], [], [], []]

    delete_competitor_user_resources(helper, "user-1", "event-1")

    participant_path = (
        f"{FirestoreCollections.EVENTS}/event-1"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )
    membership_path = (
        f"{FirestoreCollections.USERS}/user-1"
        f"/{FirestoreCollections.USER_MEMBERSHIP}"
    )

    first_list_call = helper.list_document_ids.call_args_list[0][0][0]
    assert FirestoreCollections.PARTICIPANT_EMERGENCY_CONTACTS in first_list_call

    participant_delete_index = next(
        i
        for i, call in enumerate(helper.delete_document.call_args_list)
        if call.args == (participant_path, "user-1")
    )
    user_delete_index = next(
        i
        for i, call in enumerate(helper.delete_document.call_args_list)
        if call.args == (FirestoreCollections.USERS, "user-1")
    )
    assert participant_delete_index < user_delete_index
    helper.delete_document.assert_any_call(membership_path, "event-1")
