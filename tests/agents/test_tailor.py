"""Tailor agent: real candidates only, read-only, honest when nothing is recorded."""

import asyncio
import json

import pytest

from ripple.agents.tailor import NO_CANDIDATES, OpeningUnavailableError
from ripple.core.models import Memory, Status
from ripple.domains.jobs.vocabulary import Kind, opening_subject
from tests.agents.wiring import highlights, seed, tailor_agent
from tests.builders import USER, derived, fact, memory
from tests.fakes.llm import FakeLLM
from tests.fakes.retriever import ScriptedRetriever, hit
from tests.fakes.store import InMemoryStore


def _opening(**overrides) -> tuple[Memory, list[Memory]]:
    opening = memory(**{"content": "ML intern at Acme", "kind": Kind.OPENING, **overrides})
    subject = opening_subject(opening.id)
    fields = [
        fact(subject, "title", "ML intern"),
        fact(subject, "company", "Acme"),
        fact(subject, "required_skill", "pytorch"),
    ]
    return opening, fields


def _candidates_shown(llm: FakeLLM) -> set[str]:
    user = llm.calls[0].messages[1].content
    return {row["id"] for row in json.loads(user.split("```json\n")[2].split("\n```")[0])}


class ReadOnlyStore(InMemoryStore):
    def transaction(self):  # type: ignore[override]
        raise AssertionError("the Tailor must never open a transaction")


def test_tailor_suggests_real_projects_with_opening_evidence():
    store = InMemoryStore()
    opening, fields = _opening()
    project = fact("student", "project", "CNN for crop disease in PyTorch")
    skill = fact("student", "skill", "pytorch")
    asyncio.run(seed(store, opening, *fields, project, skill))
    required = fields[2]
    llm = FakeLLM(
        highlights(
            (project.id, "uses PyTorch, which the opening requires", [required.id, "not-shown"]),
            (skill.id, "the required skill itself", [required.id]),
        )
    )

    result = asyncio.run(tailor_agent(store, llm).suggest(USER, opening.id))

    assert result.opening_memory_id == opening.id and result.dropped == 0
    first, second = result.suggestions
    assert first.memory_id == project.id and first.content == project.content
    assert first.evidence_ids == (required.id,)  # unknown opening evidence filtered
    assert second.memory_id == skill.id and not second.flagged
    system, user = llm.calls[0].messages
    assert system.role == "system" and "REAL projects" in system.content
    assert project.content in user.content and "pytorch" in user.content


def test_tailor_drops_highlights_for_ids_it_did_not_show():
    store = InMemoryStore()
    opening, fields = _opening()
    project = fact("student", "project", "CNN for crop disease")
    asyncio.run(seed(store, opening, *fields, project))
    llm = FakeLLM(
        highlights(
            ("made-up-id", "a project that does not exist", []),
            (project.id, "real", []),
            (project.id, "duplicate of a real one", []),
        )
    )

    result = asyncio.run(tailor_agent(store, llm).suggest(USER, opening.id))

    assert [s.memory_id for s in result.suggestions] == [project.id]
    assert result.dropped == 2


def test_tailor_never_writes_to_the_store():
    store = ReadOnlyStore()
    opening, fields = _opening()
    project = fact("student", "project", "CNN for crop disease")
    asyncio.run(seed(store, opening, *fields, project))
    llm = FakeLLM(highlights((project.id, "fits", [])))

    result = asyncio.run(tailor_agent(store, llm).suggest(USER, opening.id))

    assert len(result.suggestions) == 1
    assert store.change_events() == [] and store.all_links() == []
    assert {m.id for m in store.all_memories()} == {opening.id, *(f.id for f in fields), project.id}


def test_tailor_includes_retrieved_candidates_and_marks_flagged_ones():
    store = InMemoryStore()
    opening, fields = _opening()
    project = fact("student", "project", "CNN for crop disease", status=Status.SUSPECT)
    fit = derived("strong fit for Acme: PyTorch project")
    asyncio.run(seed(store, opening, *fields, project, fit))
    retriever = ScriptedRetriever(hit(fit), hit(opening))
    llm = FakeLLM(highlights((project.id, "pytorch", []), (fit.id, "existing fit belief", [])))

    result = asyncio.run(tailor_agent(store, llm, retriever).suggest(USER, opening.id))

    [call] = retriever.calls
    assert call.query == "ML intern Acme pytorch" and call.include_flagged
    assert [s.memory_id for s in result.suggestions] == [project.id, fit.id]
    assert result.suggestions[0].flagged is True and result.suggestions[1].flagged is False
    assert _candidates_shown(llm) == {project.id, fit.id}  # the opening is not a candidate


def test_tailor_ignores_retrieved_fields_of_other_openings():
    store = InMemoryStore()
    opening, fields = _opening()
    other, other_fields = _opening(content="Data intern at Beta")
    project = fact("student", "project", "CNN for crop disease")
    asyncio.run(seed(store, opening, *fields, other, *other_fields, project))
    retriever = ScriptedRetriever(hit(other_fields[2]), hit(other))
    llm = FakeLLM(highlights((project.id, "pytorch", [])))

    asyncio.run(tailor_agent(store, llm, retriever).suggest(USER, opening.id))

    assert _candidates_shown(llm) == {project.id}


def test_tailor_queries_with_the_opening_text_when_it_has_no_fields():
    store = InMemoryStore()
    opening, _ = _opening()
    project = fact("student", "project", "CNN for crop disease")
    asyncio.run(seed(store, opening, project))
    retriever = ScriptedRetriever()

    asyncio.run(tailor_agent(store, FakeLLM(highlights()), retriever).suggest(USER, opening.id))

    assert retriever.calls[0].query == "ML intern at Acme"


def test_tailor_with_nothing_recorded_skips_the_model():
    store = InMemoryStore()
    opening, fields = _opening()
    asyncio.run(seed(store, opening, *fields))
    llm = FakeLLM()

    result = asyncio.run(tailor_agent(store, llm).suggest(USER, opening.id))

    assert result.suggestions == () and result.note == NO_CANDIDATES
    assert llm.calls == []


@pytest.mark.parametrize(
    ("overrides", "why"),
    [
        ({"user_id": "someone-else"}, "another user"),
        ({"status": Status.RETIRED}, "retired"),
        ({"kind": "fact"}, "kind is"),
    ],
)
def test_tailor_refuses_an_unusable_opening(overrides, why):
    store = InMemoryStore()
    opening, _ = _opening(**overrides)
    asyncio.run(seed(store, opening, fact("student", "project", "x")))

    with pytest.raises(OpeningUnavailableError, match=why):
        asyncio.run(tailor_agent(store, FakeLLM()).suggest(USER, opening.id))


def test_tailor_refuses_a_missing_opening():
    with pytest.raises(OpeningUnavailableError, match="not found"):
        asyncio.run(tailor_agent(InMemoryStore(), FakeLLM()).suggest(USER, "nope"))
