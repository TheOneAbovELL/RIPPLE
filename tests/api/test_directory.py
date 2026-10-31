"""The worker's UserDirectory view over the UserStore (WS-6 contract)."""

import asyncio
from datetime import timedelta

from ripple.api.directory import UserDirectoryAdapter
from ripple.storage.users import User
from tests.api.fakes import InMemoryUserStore
from tests.fakes.clock import DEFAULT_START


def test_directory_lists_users_in_creation_order_and_reports_chat_ids_as_strings():
    store = InMemoryUserStore()
    linked = User(display_name="Asha", created_at=DEFAULT_START, telegram_chat_id=123456789012)
    unlinked = User(display_name="Bina", created_at=DEFAULT_START + timedelta(hours=1))
    asyncio.run(store.add_user(unlinked))
    asyncio.run(store.add_user(linked))
    directory = UserDirectoryAdapter(store)

    assert list(asyncio.run(directory.active_user_ids())) == [linked.id, unlinked.id]
    assert asyncio.run(directory.telegram_chat_id(linked.id)) == "123456789012"
    assert asyncio.run(directory.telegram_chat_id(unlinked.id)) is None
    assert asyncio.run(directory.telegram_chat_id("nobody")) is None
