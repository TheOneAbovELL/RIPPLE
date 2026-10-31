"""Resume uploads persist the parsed text so span references resolve (ADR-0097).

UploadStoreContract runs here against the in-memory store and, under the slow marker,
in tests/storage/test_hardening_uploads_postgres.py against Postgres.
"""

import asyncio
import hashlib
from datetime import timedelta

import pytest

from ripple.api.wiring import Settings, build_services
from ripple.storage.uploads import (
    MAX_RESUME_TEXT_CHARS,
    InMemoryUploadStore,
    PostgresUploadStore,
    ResumeRef,
    ResumeUpload,
    UploadStore,
    parse_resume_ref,
    quote,
    sha256_of,
)
from tests.api.fakes import ScriptedResumeParser, candidate_fact
from tests.api.harness import Harness, body
from tests.api.test_wiring import ENV, _adapters
from tests.fakes.clock import DEFAULT_START

PDF = b"%PDF-1.4\n%fake resume for tests\n"
RESUME_TEXT = "Asha Rao\nB.Tech CSE, batch 2027\nCGPA 7.6 (10-point)\nSkills: Python, SQL\n"


def upload(user_id: str, *, text: str = RESUME_TEXT, filename: str = "resume.pdf") -> ResumeUpload:
    return ResumeUpload(
        user_id=user_id,
        filename=filename,
        sha256=sha256_of(text.encode()),
        text=text,
        uploaded_at=DEFAULT_START,
    )


def _upload(c, headers, content: bytes = PDF, name: str = "resume.pdf"):
    return c.post("/resume", files={"file": (name, content, "application/pdf")}, headers=headers)


# ---- pure helpers ---------------------------------------------------------------------


def test_parse_resume_ref_reads_upload_id_and_span():
    assert parse_resume_ref("resume:up-1#10-18") == ResumeRef("up-1", 10, 18)
    assert parse_resume_ref("resume:up-1") == ResumeRef("up-1")


@pytest.mark.parametrize(
    "ref", [None, "", "msg-1", "paste:abc#1-2", "resume:", "resume:up#5-2", "resume:up#a-b"]
)
def test_parse_resume_ref_rejects_anything_else(ref):
    assert parse_resume_ref(ref) is None


def test_quote_returns_the_span_and_its_whole_line():
    start = RESUME_TEXT.index("CGPA 7.6")
    found = quote(RESUME_TEXT, start, start + len("CGPA 7.6"))
    assert found is not None
    assert found.text == "CGPA 7.6"
    assert found.line == "CGPA 7.6 (10-point)"


def test_quote_handles_the_first_and_last_lines_without_newlines():
    text = "first line\nlast line"
    first = quote(text, 0, 5)
    last = quote(text, 11, 15)
    assert first is not None and first.line == "first line"
    assert last is not None and last.line == "last line"


def test_quote_is_none_outside_the_text():
    assert quote("short", 0, 10) is None
    assert quote("short", 3, 2) is None


def test_sha256_of_is_the_hex_digest_of_the_bytes():
    assert sha256_of(PDF) == hashlib.sha256(PDF).hexdigest()


def test_resume_upload_refuses_naive_timestamps_and_oversized_text():
    with pytest.raises(ValueError):
        ResumeUpload(
            user_id="u",
            filename="resume.pdf",
            sha256=sha256_of(b"x"),
            text=RESUME_TEXT,
            uploaded_at=DEFAULT_START.replace(tzinfo=None),
        )
    with pytest.raises(ValueError):
        upload("u", text="x" * (MAX_RESUME_TEXT_CHARS + 1))


# ---- store contract -------------------------------------------------------------------


class UploadStoreContract:
    """Subclass with an `upload_store` fixture and an `owner` fixture (a user id)."""

    @pytest.fixture
    def owner(self) -> str:
        return "student-1"

    def test_upload_round_trip(self, upload_store: UploadStore, owner: str):
        row = upload(owner)
        asyncio.run(upload_store.add_upload(row))
        assert asyncio.run(upload_store.get_upload(row.id)) == row
        assert asyncio.run(upload_store.get_upload("nope")) is None

    def test_uploads_for_user_are_oldest_first_and_scoped(
        self, upload_store: UploadStore, owner: str
    ):
        newer = upload(owner).model_copy(update={"uploaded_at": DEFAULT_START + timedelta(days=1)})
        older = upload(owner)
        asyncio.run(upload_store.add_upload(newer))
        asyncio.run(upload_store.add_upload(older))
        assert [u.id for u in asyncio.run(upload_store.uploads_for_user(owner))] == [
            older.id,
            newer.id,
        ]
        assert asyncio.run(upload_store.uploads_for_user("someone-else")) == []

    def test_delete_for_user_removes_every_upload_and_is_idempotent(
        self, upload_store: UploadStore, owner: str
    ):
        asyncio.run(upload_store.add_upload(upload(owner)))
        asyncio.run(upload_store.add_upload(upload(owner)))
        asyncio.run(upload_store.delete_for_user(owner))
        assert asyncio.run(upload_store.uploads_for_user(owner)) == []
        asyncio.run(upload_store.delete_for_user(owner))


class TestInMemoryUploadStore(UploadStoreContract):
    @pytest.fixture
    def upload_store(self) -> InMemoryUploadStore:
        return InMemoryUploadStore()


# ---- API ------------------------------------------------------------------------------


def test_upload_persists_the_parsed_text_under_the_returned_upload_id():
    parser = ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6"))
    h = Harness.build(resume_parser=parser)

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            uploaded = body(await _upload(c, headers, name="asha.pdf"))
        return user, uploaded

    user, uploaded = asyncio.run(run())
    stored = asyncio.run(h.services.upload_store.get_upload(uploaded["upload_id"]))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.text == parser.text
    assert stored.filename == "asha.pdf"
    assert stored.sha256 == sha256_of(PDF)
    assert stored.uploaded_at == h.clock.now()


def test_confirmed_fact_detail_quotes_the_resume_line_its_span_points_at():
    parser = ScriptedResumeParser(
        candidate_fact("branch", "CSE", "B.Tech CSE, batch 2027"),
        candidate_fact("cgpa", 7.6, "CGPA 7.6 (10-point)"),
    )
    h = Harness.build(resume_parser=parser)

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            uploaded = body(await _upload(c, headers))
            cgpa_id = next(x["id"] for x in uploaded["candidates"] if x["attribute"] == "cgpa")
            confirmed = body(await c.post(f"/resume/candidates/{cgpa_id}/confirm", headers=headers))
            memory_id = confirmed["intake"]["memory"]["id"]
            detail = await c.get(f"/memories/{memory_id}", headers=headers)
        return uploaded, confirmed, detail

    uploaded, confirmed, detail = asyncio.run(run())
    assert detail.status_code == 200, detail.text
    source = body(detail)["source"]
    start = parser.text.index("CGPA 7.6 (10-point)")
    assert confirmed["intake"]["memory"]["source_ref"] == (
        f"resume:{uploaded['upload_id']}#{start}-{start + len('CGPA 7.6 (10-point)')}"
    )
    assert source["upload_id"] == uploaded["upload_id"]
    assert source["quote"] == "CGPA 7.6 (10-point)"
    assert source["line"] == "CGPA 7.6 (10-point)"
    assert (source["start"], source["end"]) == (start, start + len("CGPA 7.6 (10-point)"))


def test_detail_source_is_none_for_non_upload_refs_and_other_users_uploads():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        other, _ = await h.user("Bina")
        theirs = upload(other.id)
        await h.services.upload_store.add_upload(theirs)
        async with h.client() as c:
            plain = body(
                await c.post(
                    "/statements",
                    json={"content": "CGPA is 7.6", "kind": "fact", "source_ref": "msg-9"},
                    headers=headers,
                )
            )["memory"]
            borrowed = body(
                await c.post(
                    "/statements",
                    json={
                        "content": "batch is 2027",
                        "kind": "fact",
                        "source_ref": f"resume:{theirs.id}#0-8",
                    },
                    headers=headers,
                )
            )["memory"]
            return (
                body(await c.get(f"/memories/{plain['id']}", headers=headers)),
                body(await c.get(f"/memories/{borrowed['id']}", headers=headers)),
            )

    plain, borrowed = asyncio.run(run())
    assert plain["source"] is None
    assert borrowed["source"] is None  # another user's upload text is never quoted


def test_upload_whose_text_exceeds_the_cap_is_refused_and_stores_nothing():
    parser = ScriptedResumeParser(
        candidate_fact("cgpa", 7.6, "CGPA 7.6"), text="x" * (MAX_RESUME_TEXT_CHARS + 1)
    )
    h = Harness.build(resume_parser=parser)

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            response = await _upload(c, headers)
        return user, response

    user, response = asyncio.run(run())
    assert response.status_code == 413
    assert asyncio.run(h.services.upload_store.uploads_for_user(user.id)) == []
    assert asyncio.run(h.candidate_store.candidates_for_user(user.id)) == []


def test_export_lists_the_users_uploads_with_their_text():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            uploaded = body(await _upload(c, headers))
            export = body(await c.get("/me/export", headers=headers))
        return uploaded, export

    uploaded, export = asyncio.run(run())
    assert [u["id"] for u in export["resume_uploads"]] == [uploaded["upload_id"]]
    assert export["resume_uploads"][0]["text"] == "CGPA 7.6"


def test_delete_me_removes_the_uploads():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            await _upload(c, headers)
            deleted = await c.delete("/me", headers=headers)
        return user, deleted

    user, deleted = asyncio.run(run())
    assert deleted.status_code == 204
    assert asyncio.run(h.services.upload_store.uploads_for_user(user.id)) == []


def test_production_wiring_uses_the_postgres_upload_store():
    services = build_services(Settings.from_env(ENV), _adapters())
    assert isinstance(services.upload_store, PostgresUploadStore)
