"""Update parsing (ADR-0075): strict on the fields used, blind to the rest, counts drops."""

from ripple.notify.inbound.updates import (
    DroppedUpdates,
    IncomingCallback,
    IncomingText,
    parse_update,
)
from tests.notify.test_inbound_support import CHAT, raw_callback_update, raw_text_update


def test_parse_update_reads_a_private_text_message():
    dropped = DroppedUpdates()
    update = parse_update(raw_text_update("hello", update_id=7, message_id=3), dropped)

    assert isinstance(update, IncomingText)
    assert update == IncomingText(
        update_id=7, chat_id=CHAT, sender_id=CHAT, message_id=3, text="hello", forwarded=False
    )
    assert update.source_ref == f"telegram:{CHAT}:3"
    assert dropped.total == 0


def test_parse_update_marks_a_forwarded_message():
    update = parse_update(raw_text_update("jd", update_id=1, forwarded=True), DroppedUpdates())

    assert isinstance(update, IncomingText) and update.forwarded is True


def test_parse_update_accepts_forward_date_as_the_forward_marker():
    raw = raw_text_update("jd", update_id=1)
    raw["message"]["forward_date"] = 1761200000

    update = parse_update(raw, DroppedUpdates())

    assert isinstance(update, IncomingText) and update.forwarded is True


def test_parse_update_reads_a_callback_query_with_its_chat():
    dropped = DroppedUpdates()
    update = parse_update(
        raw_callback_update("a:s:mem-1", update_id=9, callback_id="cb-9"), dropped
    )

    assert update == IncomingCallback(
        update_id=9,
        chat_id=CHAT,
        sender_id=CHAT,
        callback_id="cb-9",
        data="a:s:mem-1",
        message_id=77,
    )
    assert dropped.total == 0


def test_parse_update_ignores_unknown_fields_everywhere():
    raw = raw_text_update("hi", update_id=1)
    raw["brand_new_top_level_field"] = {"x": 1}
    raw["message"]["sticker_set_name_of_the_future"] = "y"
    raw["message"]["from"]["language_code"] = "en"

    assert isinstance(parse_update(raw, DroppedUpdates()), IncomingText)


def test_parse_update_drops_a_group_chat_message_and_counts_it():
    dropped = DroppedUpdates()

    assert parse_update(raw_text_update("hi", update_id=1, chat_type="group"), dropped) is None
    assert dropped.by_reason == {"not_private_chat": 1}


def test_parse_update_drops_a_message_without_text():
    dropped = DroppedUpdates()
    raw = raw_text_update("", update_id=1)
    del raw["message"]["text"]
    raw["message"]["photo"] = [{"file_id": "abc"}]

    assert parse_update(raw, dropped) is None
    assert dropped.by_reason == {"no_text": 1}


def test_parse_update_drops_messages_from_bots():
    dropped = DroppedUpdates()
    raw = raw_text_update("hi", update_id=1)
    raw["message"]["from"]["is_bot"] = True

    assert parse_update(raw, dropped) is None
    assert dropped.by_reason == {"from_bot": 1}


def test_parse_update_drops_unsupported_update_kinds():
    dropped = DroppedUpdates()

    assert parse_update({"update_id": 3, "edited_message": {"message_id": 1}}, dropped) is None
    assert parse_update({"update_id": 4, "my_chat_member": {}}, dropped) is None
    assert dropped.by_reason == {"unsupported_kind": 2}


def test_parse_update_drops_invalid_and_non_object_payloads():
    dropped = DroppedUpdates()

    assert parse_update({"update_id": "not-an-int", "message": {}}, dropped) is None
    assert parse_update(["update_id", 1], dropped) is None
    assert parse_update(None, dropped) is None
    assert dropped.by_reason == {"invalid": 1, "not_an_object": 2}


def test_parse_update_drops_a_callback_without_data_or_chat():
    dropped = DroppedUpdates()
    no_data = raw_callback_update("", update_id=1)
    no_chat = raw_callback_update("a:s:x", update_id=2)
    del no_chat["callback_query"]["message"]

    assert parse_update(no_data, dropped) is None
    assert parse_update(no_chat, dropped) is None
    assert dropped.by_reason == {"no_callback_data": 1, "no_callback_chat": 1}


def test_parse_update_drops_a_callback_from_a_group_chat():
    dropped = DroppedUpdates()
    raw = raw_callback_update("a:s:x", update_id=1)
    raw["callback_query"]["message"]["chat"]["type"] = "supergroup"

    assert parse_update(raw, dropped) is None
    assert dropped.by_reason == {"not_private_chat": 1}
