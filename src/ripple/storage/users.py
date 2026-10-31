"""Identity: users, hashed bearer tokens and Telegram link codes (ADR-0040).

The models and the `UserStore` protocol live here rather than in ripple.api because
storage may import only core (docs/02) and the Postgres implementation needs the
models; the API layer imports this module. Tokens: a raw token is produced by
`new_raw_token()`, shown once, and only its sha256 is stored, so a database dump does
not grant access. The in-memory implementation lives in tests/api/fakes.py.
"""

import hashlib
import secrets
from datetime import datetime
from typing import Any, Protocol

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.core.ids import new_id
from ripple.storage import users_tables as t

TOKEN_HASH_ALGORITHM = "sha256"
LINK_CODE_LENGTH = 12


def _require_aware(value: datetime | None, name: str) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    display_name: str = Field(min_length=1, max_length=128)
    created_at: datetime
    telegram_chat_id: int | None = None

    def model_post_init(self, _context: Any) -> None:
        _require_aware(self.created_at, "created_at")


class ApiToken(BaseModel):
    """A bearer credential at rest: only the hash, never the token itself."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    token_hash: str = Field(min_length=64, max_length=64)
    label: str = Field(default="default", min_length=1, max_length=64)
    created_at: datetime

    def model_post_init(self, _context: Any) -> None:
        _require_aware(self.created_at, "created_at")


class TelegramLinkCode(BaseModel):
    """A one-time code the user types into the bot; the worker consumes it (ADR-0025)."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=4, max_length=16)
    user_id: str = Field(min_length=1)
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None

    def model_post_init(self, _context: Any) -> None:
        _require_aware(self.created_at, "created_at")
        _require_aware(self.expires_at, "expires_at")
        _require_aware(self.consumed_at, "consumed_at")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")

    def usable_at(self, now: datetime) -> bool:
        return self.consumed_at is None and now < self.expires_at


def new_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.new(TOKEN_HASH_ALGORITHM, raw_token.encode("utf-8")).hexdigest()


def new_link_code() -> str:
    # Upper-case hex: easy to read aloud and type on a phone; 48 bits of entropy for a
    # code that lives minutes and can be used once (the bot side should rate-limit).
    return secrets.token_hex(LINK_CODE_LENGTH // 2).upper()


class UserStore(Protocol):
    async def add_user(self, user: User) -> None: ...

    async def get_user(self, user_id: str) -> User | None: ...

    async def list_users(self) -> list[User]:
        """Every user, oldest first then by id (the worker iterates this, WS-6)."""
        ...

    async def replace_user(self, user: User) -> None:
        """Overwrite the row with the same id (telegram_chat_id changes)."""
        ...

    async def delete_user(self, user_id: str) -> None:
        """Delete the user with every token and link code; a no-op for an unknown id."""
        ...

    async def add_token(self, token: ApiToken) -> None: ...

    async def user_for_token_hash(self, token_hash: str) -> User | None: ...

    async def add_link_code(self, code: TelegramLinkCode) -> None: ...

    async def get_link_code(self, code: str) -> TelegramLinkCode | None: ...

    async def replace_link_code(self, code: TelegramLinkCode) -> None: ...


async def link_telegram(store: UserStore, code: str, chat_id: int, now: datetime) -> User | None:
    """Consume a link code and attach the chat id; None when the code is unknown,
    expired or already used. Called by the Telegram worker (WS-6) and by tests."""
    found = await store.get_link_code(code)
    if found is None or not found.usable_at(now):
        return None
    user = await store.get_user(found.user_id)
    if user is None:
        return None
    await store.replace_link_code(found.model_copy(update={"consumed_at": now}))
    linked = user.model_copy(update={"telegram_chat_id": chat_id})
    await store.replace_user(linked)
    return linked


# ---- Postgres -----------------------------------------------------------------------


def _user(row: sa.Row[Any]) -> User:
    return User.model_validate(dict(row._mapping))


class PostgresUserStore:
    """UserStore over SQLAlchemy Core; one short transaction per call (ADR-0016)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def add_user(self, user: User) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sa.insert(t.users).values(**user.model_dump()))

    async def get_user(self, user_id: str) -> User | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(sa.select(t.users).where(t.users.c.id == user_id))).first()
        return None if row is None else _user(row)

    async def list_users(self) -> list[User]:
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(sa.select(t.users).order_by(t.users.c.created_at, t.users.c.id))
            ).all()
        return [_user(row) for row in rows]

    async def replace_user(self, user: User) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                sa.update(t.users)
                .where(t.users.c.id == user.id)
                .values(**user.model_dump(exclude={"id"}))
            )

    async def delete_user(self, user_id: str) -> None:
        async with self._engine.begin() as conn:
            for table in (t.resume_candidates, t.telegram_link_codes, t.api_tokens):
                await conn.execute(sa.delete(table).where(table.c.user_id == user_id))
            await conn.execute(sa.delete(t.users).where(t.users.c.id == user_id))

    async def add_token(self, token: ApiToken) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sa.insert(t.api_tokens).values(**token.model_dump()))

    async def user_for_token_hash(self, token_hash: str) -> User | None:
        stmt = (
            sa.select(t.users)
            .join(t.api_tokens, t.api_tokens.c.user_id == t.users.c.id)
            .where(t.api_tokens.c.token_hash == token_hash)
        )
        async with self._engine.connect() as conn:
            row = (await conn.execute(stmt)).first()
        return None if row is None else _user(row)

    async def add_link_code(self, code: TelegramLinkCode) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sa.insert(t.telegram_link_codes).values(**code.model_dump()))

    async def get_link_code(self, code: str) -> TelegramLinkCode | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.select(t.telegram_link_codes).where(t.telegram_link_codes.c.code == code)
                )
            ).first()
        return None if row is None else TelegramLinkCode.model_validate(dict(row._mapping))

    async def replace_link_code(self, code: TelegramLinkCode) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                sa.update(t.telegram_link_codes)
                .where(t.telegram_link_codes.c.code == code.code)
                .values(**code.model_dump(exclude={"code"}))
            )
