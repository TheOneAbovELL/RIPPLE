"""InMemoryUpdateLedger: at most once per update_id, bounded memory (ADR-0077)."""

import asyncio

import pytest

from ripple.notify.inbound.ledger import InMemoryUpdateLedger


def test_ledger_first_sight_is_true_once_then_false():
    ledger = InMemoryUpdateLedger()

    async def run():
        return (
            await ledger.first_sight(10),
            await ledger.first_sight(10),
            await ledger.first_sight(11),
        )

    assert asyncio.run(run()) == (True, False, True)


def test_ledger_evicts_the_oldest_ids_past_its_capacity():
    ledger = InMemoryUpdateLedger(capacity=2)

    async def run():
        await ledger.first_sight(1)
        await ledger.first_sight(2)
        await ledger.first_sight(3)  # evicts 1
        return await ledger.first_sight(1), await ledger.first_sight(3), len(ledger)

    assert asyncio.run(run()) == (True, False, 2)


def test_ledger_rejects_a_capacity_below_one():
    with pytest.raises(ValueError, match="capacity"):
        InMemoryUpdateLedger(capacity=0)
