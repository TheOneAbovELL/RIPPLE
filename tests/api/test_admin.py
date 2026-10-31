"""The admin CLI mints a token once and never stores it (ADR-0040)."""

import asyncio
import io

from ripple.api.admin import main
from ripple.storage.users import hash_token
from tests.api.fakes import InMemoryUserStore
from tests.fakes.clock import FakeClock


def test_create_user_prints_the_token_once_and_stores_only_its_hash():
    store = InMemoryUserStore()
    out = io.StringIO()

    code = main(
        ["create-user", "Asha"], user_store_factory=lambda: store, clock=FakeClock(), out=out
    )

    assert code == 0
    lines = out.getvalue().splitlines()
    user_id = lines[0].removeprefix("user_id: ")
    raw_token = lines[1].removeprefix("token: ")
    assert store.users[user_id].display_name == "Asha"
    stored = next(iter(store.tokens.values()))
    assert stored.token_hash == hash_token(raw_token)
    assert raw_token not in repr(store.tokens)
    assert asyncio.run(store.user_for_token_hash(hash_token(raw_token))) == store.users[user_id]


def test_create_user_without_a_database_url_fails_clearly(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main(["create-user", "Asha"]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err
