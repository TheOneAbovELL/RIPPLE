"""Admin CLI (ADR-0040): the only way to create a user and mint a bearer token.

    uv run python -m ripple.api.admin create-user "Asha"

prints the token exactly once; only its hash is stored. There is no sign-up endpoint
on purpose: the pilot's 10 to 15 students are enrolled by the author, with consent
collected offline (NFR-3).
"""

import argparse
import asyncio
import os
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from ripple.core.clock import Clock, SystemClock
from ripple.core.errors import ConfigurationError
from ripple.storage.engine import ENV_VAR as DATABASE_URL_VAR
from ripple.storage.engine import engine_from_url
from ripple.storage.users import (
    ApiToken,
    PostgresUserStore,
    User,
    UserStore,
    hash_token,
    new_raw_token,
)

UserStoreFactory = Callable[[], UserStore]


async def create_user(store: UserStore, clock: Clock, display_name: str) -> tuple[User, str]:
    """Create the user and one token; returns the raw token for the one-time print."""
    now = clock.now()
    user = User(display_name=display_name, created_at=now)
    raw_token = new_raw_token()
    await store.add_user(user)
    await store.add_token(
        ApiToken(user_id=user.id, token_hash=hash_token(raw_token), created_at=now)
    )
    return user, raw_token


def _postgres_user_store() -> UserStore:
    url = os.environ.get(DATABASE_URL_VAR, "").strip()
    if not url:
        raise ConfigurationError(f"{DATABASE_URL_VAR} is not set")
    return PostgresUserStore(engine_from_url(url))


def main(
    argv: Sequence[str] | None = None,
    *,
    user_store_factory: UserStoreFactory = _postgres_user_store,
    clock: Clock | None = None,
    out: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m ripple.api.admin")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="create a user and print a token once")
    create.add_argument("display_name")
    args = parser.parse_args(argv)

    if args.command == "create-user":
        try:
            store = user_store_factory()
        except ConfigurationError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        user, raw_token = asyncio.run(create_user(store, clock or SystemClock(), args.display_name))
        print(f"user_id: {user.id}", file=out)
        print(f"token: {raw_token}", file=out)
        print("Store the token now; it is not shown again.", file=out)
        return 0
    return 2  # argparse already rejected anything else


if __name__ == "__main__":
    sys.exit(main())
