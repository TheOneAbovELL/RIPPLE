import asyncio
import json
from datetime import UTC, datetime

import pytest

from ripple.core.change_detection import ChangeKind, detect_structured_update
from ripple.core.models import Status, StructuredFact
from ripple.llm.change_detector import LLMChangeDetector
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from tests.builders import fact, memory
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM


def _detector(llm: FakeLLM) -> LLMChangeDetector:
    config = RouterConfig(tasks={"change_detector": [ModelSpec(provider="fake", model="f")]})
    return LLMChangeDetector(Router(config, {"fake": llm}), FakeClock())


# ---- deterministic stage -----------------------------------------------------------


def test_structured_same_attribute_new_value_is_an_update():
    old = fact("student", "cgpa", 7.6)
    result = detect_structured_update(
        StructuredFact(subject="student", attribute="cgpa", value=7.9), [old]
    )
    assert result is not None
    assert (result.kind, result.updates_memory_id) == (ChangeKind.UPDATE, old.id)


def test_structured_same_value_is_not_a_change():
    old = fact("student", "cgpa", 7.6)
    result = detect_structured_update(
        StructuredFact(subject="student", attribute="cgpa", value=7.6), [old]
    )
    assert result is not None and result.kind is ChangeKind.UNCHANGED


def test_structured_ignores_retired_candidates_and_other_attributes():
    retired = fact("student", "cgpa", 7.6, status=Status.RETIRED)
    other = fact("student", "batch", 2027)
    new = StructuredFact(subject="student", attribute="cgpa", value=7.9)
    assert detect_structured_update(new, [retired, other]) is None


def test_structured_without_structured_input_defers():
    assert detect_structured_update(None, [fact("student", "cgpa", 7.6)]) is None


# ---- LLM stage -----------------------------------------------------------------------


def test_llm_detector_classifies_temporary_with_valid_to():
    llm = FakeLLM(
        json.dumps(
            {"kind": "temporary", "reason": "exams", "valid_to": "2026-11-30T23:59:00+00:00"}
        )
    )
    result = asyncio.run(_detector(llm).classify("busy with exams this month", None, []))
    assert result.kind is ChangeKind.TEMPORARY
    assert result.valid_to == datetime(2026, 11, 30, 23, 59, tzinfo=UTC)
    assert "Current date-time: 2026-10-19" in llm.calls[0].messages[1].content


def test_llm_detector_update_with_unknown_id_becomes_new():
    llm = FakeLLM(
        json.dumps({"kind": "update", "reason": "same thing", "updates_memory_id": "ghost"})
    )
    result = asyncio.run(
        _detector(llm).classify("I like Go now", None, [memory(content="likes Rust")])
    )
    assert result.kind is ChangeKind.NEW and result.updates_memory_id is None


def test_llm_detector_update_with_known_id_is_kept():
    existing = memory(content="likes Rust")
    llm = FakeLLM(
        json.dumps({"kind": "update", "reason": "same thing", "updates_memory_id": existing.id})
    )
    result = asyncio.run(_detector(llm).classify("I like Go now", None, [existing]))
    assert (result.kind, result.updates_memory_id) == (ChangeKind.UPDATE, existing.id)


def test_llm_detector_rejects_temporary_with_past_valid_to():
    from ripple.core.errors import LLMOutputInvalidError

    llm = FakeLLM(
        json.dumps({"kind": "temporary", "reason": "exams", "valid_to": "2026-01-01T00:00:00Z"})
    )
    with pytest.raises(LLMOutputInvalidError, match="future"):
        asyncio.run(_detector(llm).classify("busy", None, []))


def test_llm_detector_retries_temporary_without_valid_to():
    llm = FakeLLM(
        json.dumps({"kind": "temporary", "reason": "exams"}),
        json.dumps({"kind": "temporary", "reason": "exams", "valid_to": "2026-11-30T00:00:00Z"}),
    )
    result = asyncio.run(_detector(llm).classify("busy this month", None, []))
    assert result.kind is ChangeKind.TEMPORARY and len(llm.calls) == 2
