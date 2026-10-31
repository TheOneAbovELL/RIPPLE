"""Contracts the in-memory and Postgres UserStore / CandidateStore must both satisfy.

Subclass with a `user_store` / `candidate_store` fixture. The in-memory run lives in
tests/api/test_store_fakes.py; the Postgres run under the slow marker in
tests/storage/test_users_postgres.py and test_candidates_postgres.py.
"""

import asyncio
from datetime import timedelta

import pytest

from ripple.storage.candidates import CandidateStatus, CandidateStore, ResumeCandidate
from ripple.storage.users import (
    ApiToken,
    TelegramLinkCode,
    User,
    UserStore,
    hash_token,
    link_telegram,
    new_link_code,
    new_raw_token,
)
from tests.fakes.clock import DEFAULT_START


def _user(name: str = "Asha") -> User:
    return User(display_name=name, created_at=DEFAULT_START)


def _code(user: User, code: str | None = None) -> TelegramLinkCode:
    return TelegramLinkCode(
        code=code or new_link_code(),
        user_id=user.id,
        created_at=DEFAULT_START,
        expires_at=DEFAULT_START + timedelta(minutes=15),
    )


class UserStoreContract:
    def test_user_round_trip(self, user_store: UserStore):
        user = _user()
        asyncio.run(user_store.add_user(user))
        assert asyncio.run(user_store.get_user(user.id)) == user
        assert asyncio.run(user_store.get_user("nope")) is None

    def test_list_users_is_oldest_first(self, user_store: UserStore):
        older = _user("Asha")
        newer = User(display_name="Bina", created_at=DEFAULT_START + timedelta(days=1))
        asyncio.run(user_store.add_user(newer))
        asyncio.run(user_store.add_user(older))
        assert [u.id for u in asyncio.run(user_store.list_users())] == [older.id, newer.id]

    def test_replace_user_updates_telegram_chat_id(self, user_store: UserStore):
        user = _user()
        asyncio.run(user_store.add_user(user))
        asyncio.run(user_store.replace_user(user.model_copy(update={"telegram_chat_id": 42})))
        found = asyncio.run(user_store.get_user(user.id))
        assert found is not None and found.telegram_chat_id == 42

    def test_token_lookup_is_by_hash_only(self, user_store: UserStore):
        user = _user()
        raw = new_raw_token()
        asyncio.run(user_store.add_user(user))
        asyncio.run(
            user_store.add_token(
                ApiToken(user_id=user.id, token_hash=hash_token(raw), created_at=DEFAULT_START)
            )
        )
        assert asyncio.run(user_store.user_for_token_hash(hash_token(raw))) == user
        # The raw token is not a key anywhere: only its hash opens the door.
        assert asyncio.run(user_store.user_for_token_hash(raw[:64].ljust(64, "0"))) is None

    def test_duplicate_token_hash_is_refused(self, user_store: UserStore):
        user = _user()
        digest = hash_token(new_raw_token())
        asyncio.run(user_store.add_user(user))
        asyncio.run(
            user_store.add_token(
                ApiToken(user_id=user.id, token_hash=digest, created_at=DEFAULT_START)
            )
        )
        with pytest.raises(Exception):  # noqa: B017 - the driver decides the exception type
            asyncio.run(
                user_store.add_token(
                    ApiToken(user_id=user.id, token_hash=digest, created_at=DEFAULT_START)
                )
            )

    def test_link_telegram_consumes_the_code_once(self, user_store: UserStore):
        user = _user()
        code = _code(user)
        asyncio.run(user_store.add_user(user))
        asyncio.run(user_store.add_link_code(code))
        now = DEFAULT_START + timedelta(minutes=1)
        linked = asyncio.run(link_telegram(user_store, code.code, 777, now))
        assert linked is not None and linked.telegram_chat_id == 777
        assert asyncio.run(link_telegram(user_store, code.code, 888, now)) is None
        found = asyncio.run(user_store.get_user(user.id))
        assert found is not None and found.telegram_chat_id == 777

    def test_link_telegram_rejects_expired_or_unknown_codes(self, user_store: UserStore):
        user = _user()
        code = _code(user)
        asyncio.run(user_store.add_user(user))
        asyncio.run(user_store.add_link_code(code))
        late = DEFAULT_START + timedelta(minutes=16)
        assert asyncio.run(link_telegram(user_store, code.code, 777, late)) is None
        assert asyncio.run(link_telegram(user_store, "NOPE1234", 777, DEFAULT_START)) is None

    def test_delete_user_removes_tokens_and_codes(self, user_store: UserStore):
        user = _user()
        raw = new_raw_token()
        code = _code(user)
        asyncio.run(user_store.add_user(user))
        asyncio.run(
            user_store.add_token(
                ApiToken(user_id=user.id, token_hash=hash_token(raw), created_at=DEFAULT_START)
            )
        )
        asyncio.run(user_store.add_link_code(code))
        asyncio.run(user_store.delete_user(user.id))
        assert asyncio.run(user_store.get_user(user.id)) is None
        assert asyncio.run(user_store.user_for_token_hash(hash_token(raw))) is None
        assert asyncio.run(user_store.get_link_code(code.code)) is None
        asyncio.run(user_store.delete_user(user.id))  # idempotent


def _candidate(user_id: str, attribute: str = "cgpa", value: str | int | float | bool = 7.6):
    return ResumeCandidate(
        user_id=user_id,
        upload_id="upload-1",
        attribute=attribute,
        value=value,
        span_start=10,
        span_end=18,
        span_text="CGPA 7.6",
        confidence=0.9,
        content=f"{attribute} is {value}",
        created_at=DEFAULT_START,
    )


class CandidateStoreContract:
    @pytest.fixture
    def owner(self) -> str:
        """Candidates reference a user row; subclasses that need one override this."""
        return "student-1"

    def test_candidates_round_trip_preserving_value_types(
        self, candidate_store: CandidateStore, owner: str
    ):
        rows = [
            _candidate(owner, "cgpa", 7.6),
            _candidate(owner, "batch", 2027),
            _candidate(owner, "looking", True),
            _candidate(owner, "branch", "CSE"),
        ]
        asyncio.run(candidate_store.add_candidates(rows))
        found = asyncio.run(candidate_store.candidates_for_user(owner))
        assert sorted(c.id for c in found) == sorted(c.id for c in rows)
        by_attr = {c.attribute: c.value for c in found}
        assert by_attr == {"cgpa": 7.6, "batch": 2027, "looking": True, "branch": "CSE"}
        assert type(by_attr["looking"]) is bool and type(by_attr["batch"]) is int

    def test_status_filter_and_replace(self, candidate_store: CandidateStore, owner: str):
        row = _candidate(owner)
        asyncio.run(candidate_store.add_candidates([row]))
        decided = row.model_copy(
            update={
                "status": CandidateStatus.CONFIRMED,
                "decided_at": DEFAULT_START,
                "memory_id": "mem-1",
            }
        )
        asyncio.run(candidate_store.replace_candidate(decided))
        assert asyncio.run(candidate_store.get_candidate(row.id)) == decided
        assert (
            asyncio.run(candidate_store.candidates_for_user(owner, CandidateStatus.PENDING)) == []
        )
        assert asyncio.run(
            candidate_store.candidates_for_user(owner, CandidateStatus.CONFIRMED)
        ) == [decided]

    def test_unknown_candidate_is_none_and_delete_for_user(
        self, candidate_store: CandidateStore, owner: str
    ):
        assert asyncio.run(candidate_store.get_candidate("nope")) is None
        asyncio.run(candidate_store.add_candidates([_candidate(owner)]))
        asyncio.run(candidate_store.delete_for_user(owner))
        assert asyncio.run(candidate_store.candidates_for_user(owner)) == []
