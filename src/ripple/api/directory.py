"""UserDirectory for the worker (WS-6 handover, "Contracts"): who to send digests to.

The worker's protocol is `active_user_ids()` and `telegram_chat_id(user_id) -> str |
None`; it never needs tokens or codes, so it gets this narrow view of the UserStore
rather than the store itself. Chat ids are strings on the wire (Telegram's API takes
either), hence the conversion.
"""

from collections.abc import Sequence

from ripple.storage.users import UserStore


class UserDirectoryAdapter:
    def __init__(self, user_store: UserStore) -> None:
        self._user_store = user_store

    async def active_user_ids(self) -> Sequence[str]:
        return [user.id for user in await self._user_store.list_users()]

    async def telegram_chat_id(self, user_id: str) -> str | None:
        user = await self._user_store.get_user(user_id)
        if user is None or user.telegram_chat_id is None:
            return None
        return str(user.telegram_chat_id)
