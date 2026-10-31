import pytest

from tests.core.store_contract import StoreContract
from tests.fakes.store import InMemoryStore


class TestInMemoryStore(StoreContract):
    @pytest.fixture
    def store(self) -> InMemoryStore:
        return InMemoryStore()


def test_inmemory_store_refuses_writes_outside_a_transaction():
    import asyncio

    from tests.builders import memory

    with pytest.raises(RuntimeError, match=r"inside store\.transaction"):
        asyncio.run(InMemoryStore().add_memory(memory()))


def test_inmemory_store_refuses_nested_transactions():
    import asyncio

    async def nested():
        store = InMemoryStore()
        async with store.transaction(), store.transaction():
            pass

    with pytest.raises(RuntimeError, match="nested"):
        asyncio.run(nested())
