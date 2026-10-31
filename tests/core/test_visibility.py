from ripple.core.models import Status
from ripple.core.visibility import visible_for_retrieval
from tests.builders import memory


def test_visible_for_retrieval_keeps_input_order():
    first, second = memory(content="a"), memory(content="b")
    assert [v.memory.content for v in visible_for_retrieval([second, first])] == ["b", "a"]


def test_visible_for_retrieval_hides_flagged_without_opt_in():
    assert visible_for_retrieval([memory(status=Status.SUSPECT)]) == []
    assert visible_for_retrieval([memory(status=Status.PENDING_USER)]) == []


def test_visible_for_retrieval_never_shows_retired_even_with_opt_in():
    assert visible_for_retrieval([memory(status=Status.RETIRED)], include_flagged=True) == []
